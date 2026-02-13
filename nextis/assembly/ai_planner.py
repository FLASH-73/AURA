"""AI-powered assembly plan analysis using Claude.

Sends an assembly graph to Claude for review, gets back structured
suggestions for improving step ordering, handler selection, and
primitive parameters.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from nextis.assembly.models import AssemblyGraph
from nextis.errors import PlannerError

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert robotics assembly planner. You review heuristic assembly \
plans and suggest improvements for a 7-DOF robotic arm system.

Available motion primitives (parameterized, no learning required):
- move_to: Move arm to target pose (params: target_pose, velocity)
- pick: Grasp a part (params: part_id, grasp_index, approach_height)
- place: Place part at target (params: target_pose, approach_height, release_force)
- guarded_move: Move until force threshold (params: direction, force_threshold, max_distance)
- linear_insert: Insert along axis with compliance (params: target_pose, force_limit, \
compliance_axes)
- screw: Screw fastener (params: target_pose, torque_limit, rotations)
- press_fit: Press part into place (params: direction, force_target, max_distance)

Handler types:
- "primitive": parameterized motion primitive — for straightforward pick/place/insert actions
- "policy": learned policy trained from human demonstrations — for tight tolerances, gear \
meshing, snap fits, complex contact geometry, or anything requiring force-sensitive adaptation"""


@dataclass
class PlanSuggestion:
    """A single suggested change to the assembly plan."""

    step_id: str
    field: str
    old_value: str
    new_value: str
    reason: str


@dataclass
class PlanAnalysis:
    """Full analysis result from the AI planner."""

    suggestions: list[PlanSuggestion] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    difficulty_score: int = 5
    estimated_teaching_minutes: int = 0
    summary: str = ""


class AIPlanner:
    """Analyze assembly plans using Claude.

    Sends the assembly graph as structured JSON to Claude, asks for
    a review of the heuristic plan, and parses the structured response.

    Args:
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
        model: Claude model to use.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model

    async def analyze(self, graph: AssemblyGraph) -> PlanAnalysis:
        """Analyze an assembly plan and return suggestions.

        Args:
            graph: The assembly graph to analyze.

        Returns:
            PlanAnalysis with suggestions, warnings, and metadata.

        Raises:
            PlannerError: If the API key is missing, API call fails,
                or response cannot be parsed.
        """
        if not self._api_key:
            raise PlannerError(
                "ANTHROPIC_API_KEY not set. Configure it in the environment "
                "or pass api_key to AIPlanner."
            )

        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise PlannerError("anthropic package not installed. Run: pip install anthropic") from e

        graph_json = graph.model_dump(by_alias=True)
        prompt = self._build_prompt(graph_json)

        try:
            client = AsyncAnthropic(api_key=self._api_key)
            message = await client.messages.create(
                model=self._model,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            logger.error("Anthropic API call failed: %s", e)
            raise PlannerError(f"AI analysis failed: {e}") from e

        raw_text = message.content[0].text
        logger.info(
            "AI analysis complete for %s (%d chars response)",
            graph.id,
            len(raw_text),
        )
        return self._parse_response(raw_text)

    def _build_prompt(self, graph_json: dict[str, Any]) -> str:
        """Build the analysis prompt with the assembly graph embedded."""
        return f"""Analyze this robotic assembly plan and suggest improvements.

## Assembly Graph
```json
{json.dumps(graph_json, indent=2)}
```

Review the plan and respond with ONLY a JSON object (no markdown fences, no extra text):
{{
  "suggestions": [
    {{
      "stepId": "step_XXX",
      "field": "handler|primitiveType|maxRetries|name",
      "oldValue": "current value as string",
      "newValue": "suggested value as string",
      "reason": "brief explanation"
    }}
  ],
  "warnings": ["potential issues or risks"],
  "difficultyScore": <1-10 integer>,
  "estimatedTeachingMinutes": <total minutes for all policy steps>,
  "summary": "2-3 sentence overall assessment"
}}

Focus on:
1. Steps using "primitive" that should use "policy" (tight tolerances, gear meshing, snap fits)
2. Steps using "policy" that could use "primitive" (simple pick/place with large clearance)
3. Wrong primitive types for the operation described
4. Unrealistic force thresholds or retry counts
5. Dependency ordering issues
6. Steps that need more retries due to high variance operations"""

    def _parse_response(self, raw_text: str) -> PlanAnalysis:
        """Parse Claude's JSON response into a PlanAnalysis.

        Handles markdown fences defensively and uses defaults for
        missing fields.
        """
        text = raw_text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            first_newline = text.find("\n")
            text = text[first_newline + 1 :] if first_newline != -1 else text[3:]
        if text.endswith("```"):
            text = text[:-3].rstrip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response: %s\nRaw: %.500s", e, raw_text)
            raise PlannerError("AI returned invalid JSON response") from e

        suggestions = [
            PlanSuggestion(
                step_id=s.get("stepId", ""),
                field=s.get("field", ""),
                old_value=str(s.get("oldValue", "")),
                new_value=str(s.get("newValue", "")),
                reason=s.get("reason", ""),
            )
            for s in data.get("suggestions", [])
        ]

        return PlanAnalysis(
            suggestions=suggestions,
            warnings=data.get("warnings", []),
            difficulty_score=max(1, min(10, int(data.get("difficultyScore", 5)))),
            estimated_teaching_minutes=max(0, int(data.get("estimatedTeachingMinutes", 0))),
            summary=data.get("summary", ""),
        )
