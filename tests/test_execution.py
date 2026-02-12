"""Integration tests for the execution engine (Sequencer + PolicyRouter + Analytics).

Tests the full state machine: start → step dispatch → retries → human
intervention → analytics recording — all without real hardware (primitives
are stubs that return success after a short sleep).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from nextis.analytics.store import AnalyticsStore
from nextis.api.schemas import ExecutionState
from nextis.assembly.models import AssemblyGraph
from nextis.control.primitives import PrimitiveLibrary
from nextis.execution.policy_router import PolicyRouter
from nextis.execution.sequencer import Sequencer, SequencerState


def _make_sequencer(
    graph: AssemblyGraph,
    states: list[ExecutionState] | None = None,
    analytics: AnalyticsStore | None = None,
    done_event: asyncio.Event | None = None,
) -> Sequencer:
    """Create a Sequencer with a state-collecting callback."""

    def on_change(state: ExecutionState) -> None:
        if states is not None:
            states.append(state)
        if done_event and state.phase in ("complete", "error"):
            done_event.set()

    primitives = PrimitiveLibrary()
    router = PolicyRouter(primitive_library=primitives, robot=None)
    return Sequencer(
        graph=graph,
        on_state_change=on_change,
        router=router,
        analytics=analytics,
    )


async def _wait_for(event: asyncio.Event, timeout: float = 30.0) -> None:
    """Await an event with a timeout."""
    await asyncio.wait_for(event.wait(), timeout=timeout)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


async def test_sequencer_runs_all_steps(primitives_only_graph: AssemblyGraph) -> None:
    """All 3 primitive steps run to completion."""
    done = asyncio.Event()
    states: list[ExecutionState] = []

    seq = _make_sequencer(primitives_only_graph, states=states, done_event=done)
    await seq.start()
    await _wait_for(done)

    assert seq.state == SequencerState.COMPLETE

    # Every step should be marked success
    final = seq.get_execution_state()
    for sid in primitives_only_graph.step_order:
        assert final.step_states[sid].status == "success"

    # Elapsed time should be positive
    assert final.elapsed_ms > 0


async def test_sequencer_pause_resume(primitives_only_graph: AssemblyGraph) -> None:
    """Pause after start, resume, then run to completion."""
    done = asyncio.Event()
    first_step_complete = asyncio.Event()
    states: list[ExecutionState] = []

    def on_change(state: ExecutionState) -> None:
        states.append(state)
        # Detect first step success
        s1 = state.step_states.get("step_001")
        if s1 and s1.status == "success" and not first_step_complete.is_set():
            first_step_complete.set()
        if state.phase in ("complete", "error"):
            done.set()

    primitives = PrimitiveLibrary()
    router = PolicyRouter(primitive_library=primitives, robot=None)
    seq = Sequencer(
        graph=primitives_only_graph,
        on_state_change=on_change,
        router=router,
    )

    await seq.start()
    await _wait_for(first_step_complete, timeout=15.0)

    await seq.pause()
    assert seq.state == SequencerState.PAUSED

    await seq.resume()
    assert seq.state in (SequencerState.STEP_ACTIVE, SequencerState.RUNNING)

    await _wait_for(done)
    assert seq.state == SequencerState.COMPLETE


async def test_sequencer_human_intervention(bearing_housing_graph: AssemblyGraph) -> None:
    """step_004 (policy) fails all retries → WAITING_FOR_HUMAN → human completes."""
    waiting = asyncio.Event()
    done = asyncio.Event()

    def on_change(state: ExecutionState) -> None:
        if state.phase == "teaching":
            waiting.set()
        if state.phase in ("complete", "error"):
            done.set()

    primitives = PrimitiveLibrary()
    router = PolicyRouter(primitive_library=primitives, robot=None)
    seq = Sequencer(
        graph=bearing_housing_graph,
        on_state_change=on_change,
        router=router,
    )

    await seq.start()
    await _wait_for(waiting, timeout=30.0)

    assert seq.state == SequencerState.WAITING_FOR_HUMAN
    assert seq.current_step is not None
    assert seq.current_step.id == "step_004"

    # Human completes the step
    await seq.complete_human_step(success=True)

    # Sequencer should continue to step_005 and complete
    await _wait_for(done, timeout=15.0)
    assert seq.state == SequencerState.COMPLETE


async def test_sequencer_stop(primitives_only_graph: AssemblyGraph) -> None:
    """Stop mid-execution → state is IDLE, task is cancelled."""
    seq = _make_sequencer(primitives_only_graph)
    await seq.start()

    # Let it start the first step
    await asyncio.sleep(0.05)
    assert seq.state in (SequencerState.STEP_ACTIVE, SequencerState.RUNNING)

    await seq.stop()
    assert seq.state == SequencerState.IDLE


async def test_sequencer_emits_state_changes(primitives_only_graph: AssemblyGraph) -> None:
    """Verify the stream of state-change emissions."""
    done = asyncio.Event()
    states: list[ExecutionState] = []

    seq = _make_sequencer(primitives_only_graph, states=states, done_event=done)
    await seq.start()
    await _wait_for(done)

    phases = [s.phase for s in states]

    # First emission should be "running" (sequencer starting)
    assert phases[0] == "running"
    # Last emission should be "complete"
    assert phases[-1] == "complete"
    # Should see "running" phases for each step (STEP_ACTIVE maps to "running")
    assert phases.count("complete") == 1


async def test_analytics_records_results(
    primitives_only_graph: AssemblyGraph,
    analytics_dir: Path,
) -> None:
    """Run sequencer with AnalyticsStore → metrics are recorded for each step."""
    store = AnalyticsStore(root=analytics_dir)
    done = asyncio.Event()

    seq = _make_sequencer(
        primitives_only_graph,
        analytics=store,
        done_event=done,
    )
    await seq.start()
    await _wait_for(done)

    assert seq.state == SequencerState.COMPLETE

    # Check metrics for each step
    metrics_list = store.get_step_metrics_for(
        "test_assembly",
        primitives_only_graph.step_order,
    )
    assert len(metrics_list) == 3

    for m in metrics_list:
        assert m.success_rate == 1.0
        assert m.total_attempts == 1
        assert m.avg_duration_ms > 0
        assert len(m.recent_runs) == 1
        assert m.recent_runs[0].success is True
