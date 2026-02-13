"use client";

// ---------------------------------------------------------------------------
// Architecture module grid for the landing page.
// Shows real module data with status indicators and hover descriptions.
// ---------------------------------------------------------------------------

interface ModuleInfo {
  name: string;
  path: string;
  lines: number;
  status: "complete" | "stubbed" | "planned";
  description: string;
}

const GITHUB_BASE = "https://github.com/FLASH-73/Nextis_Bridge/tree/main/nextis";

const MODULES: ModuleInfo[] = [
  {
    name: "Hardware Types",
    path: "hardware/types.py",
    lines: 99,
    status: "complete",
    description: "Motor enums, arm definitions, pairing configs",
  },
  {
    name: "Arm Registry",
    path: "hardware/arm_registry.py",
    lines: 501,
    status: "complete",
    description: "YAML-backed arm CRUD with LeRobot factory",
  },
  {
    name: "Mock Hardware",
    path: "hardware/mock.py",
    lines: 128,
    status: "complete",
    description: "MockRobot and MockLeader for hardware-free dev",
  },
  {
    name: "Teleop Loop",
    path: "control/teleop_loop.py",
    lines: 553,
    status: "complete",
    description: "60Hz control loop — leader to follower with blending",
  },
  {
    name: "Joint Mapping",
    path: "control/joint_mapping.py",
    lines: 236,
    status: "complete",
    description: "Dynamixel to Damiao value conversion",
  },
  {
    name: "Force Feedback",
    path: "control/force_feedback.py",
    lines: 145,
    status: "complete",
    description: "Gripper EMA and joint virtual spring",
  },
  {
    name: "Leader Assist",
    path: "control/leader_assist.py",
    lines: 288,
    status: "complete",
    description: "Gravity comp, friction assist, haptics, damping",
  },
  {
    name: "Safety Monitor",
    path: "control/safety.py",
    lines: 210,
    status: "complete",
    description: "Load and torque monitoring with emergency stop",
  },
  {
    name: "Intervention",
    path: "control/intervention.py",
    lines: 148,
    status: "complete",
    description: "Velocity-based human takeover detection",
  },
  {
    name: "Primitives",
    path: "control/primitives.py",
    lines: 351,
    status: "stubbed",
    description: "7 motion primitives — pick, place, insert, screw, press fit",
  },
  {
    name: "Assembly Models",
    path: "assembly/models.py",
    lines: 147,
    status: "complete",
    description: "Pydantic graph — parts, steps, dependencies",
  },
  {
    name: "CAD Parser",
    path: "assembly/cad_parser.py",
    lines: 438,
    status: "complete",
    description: "STEP file to parts, contacts, and GLB meshes via OCP",
  },
  {
    name: "Mesh Utils",
    path: "assembly/mesh_utils.py",
    lines: 279,
    status: "complete",
    description: "Tessellation, bounding box, color assignment",
  },
  {
    name: "Sequence Planner",
    path: "assembly/sequence_planner.py",
    lines: 263,
    status: "complete",
    description: "Heuristic step ordering — size-based, pick-place-insert",
  },
  {
    name: "Sequencer",
    path: "execution/sequencer.py",
    lines: 395,
    status: "complete",
    description: "State machine — walks graph, retries, escalates to human",
  },
  {
    name: "Policy Router",
    path: "execution/policy_router.py",
    lines: 104,
    status: "stubbed",
    description: "Dispatch to primitive or learned policy",
  },
  {
    name: "Recorder",
    path: "learning/recorder.py",
    lines: 302,
    status: "complete",
    description: "Step-segmented 50Hz threaded HDF5 recording",
  },
  {
    name: "Analytics Store",
    path: "analytics/store.py",
    lines: 198,
    status: "complete",
    description: "JSON file-backed per-step run metrics",
  },
  {
    name: "Perception",
    path: "perception/",
    lines: 0,
    status: "planned",
    description: "Step completion classifiers — not yet implemented",
  },
  {
    name: "API + Routes",
    path: "api/",
    lines: 996,
    status: "complete",
    description: "FastAPI — 6 route modules, WebSocket, static mesh serving",
  },
];

const STATUS_DOT: Record<ModuleInfo["status"], string> = {
  complete: "bg-status-success",
  stubbed: "bg-status-warning",
  planned: "bg-status-pending",
};

export function ArchitectureGrid() {
  return (
    <div>
      <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {MODULES.map((mod) => (
          <a
            key={mod.path}
            href={mod.lines > 0 ? `${GITHUB_BASE}/${mod.path}` : undefined}
            target="_blank"
            rel="noopener noreferrer"
            className="group rounded-md border border-bg-tertiary bg-bg-secondary px-3 py-2.5 transition-colors hover:border-accent/30"
          >
            <div className="flex items-start gap-2">
              <div
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${STATUS_DOT[mod.status]}`}
              />
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-text-primary">{mod.name}</p>
                <p className="font-mono text-[11px] text-text-tertiary">
                  {mod.lines > 0 ? `${mod.lines} lines` : "planned"}
                </p>
                <p className="mt-1 hidden text-[12px] leading-snug text-text-secondary group-hover:block">
                  {mod.description}
                </p>
              </div>
            </div>
          </a>
        ))}
      </div>

      <div className="mt-6 flex gap-6">
        {(["complete", "stubbed", "planned"] as const).map((status) => (
          <div key={status} className="flex items-center gap-1.5">
            <div className={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[status]}`} />
            <span className="text-[11px] font-medium uppercase tracking-[0.02em] text-text-tertiary">
              {status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
