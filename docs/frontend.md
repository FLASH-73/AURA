# AURA — Frontend Design System

## Product Name

**AURA** — Autonomous Universal Robotic Assembly. AIRA is the arm, AURA is the brain that orchestrates assembly.

CLI commands use `aura`: `aura run`, `aura teach step_003`, `aura status`.
The frontend header says **AURA** in the wordmark. The page title is "AURA — Assembly Platform."

---

## Design Philosophy

**Confident, bright, precise.** This is a professional tool that looks like it belongs in 2026, not a hackathon dashboard and not a dark hacker terminal. Think Linear meets Vercel meets precision engineering. The software should feel as solid as the machines it controls.

### Core Principles

1. **Bright and warm** — white backgrounds, natural light feel. The operator is building physical things; the interface should feel physical too, like good paper and clean workbenches.

2. **Color is information** — the background is neutral. Color only appears when it means something: step status, alerts, the brand accent. If something is colored, it's telling you something. If it's not telling you something, it's grey or black.

3. **Typography is hierarchy** — big numbers for metrics (cycle time, success rate). Medium weight for labels. Light weight for secondary info. The data should be scannable from across a desk.

4. **Whitespace is confidence** — don't cram. A few well-placed elements with room to breathe looks more professional than a dense grid of cards. The 3D viewer gets generous space. Metrics have padding. Let the interface feel calm even when the robot is running.

5. **No decoration** — no gradients, no glassmorphism, no blob backgrounds, no floating particles, no animated borders. Every pixel earns its place by conveying information or supporting readability.

---

## Color System

```css
:root {
  /* Backgrounds */
  --bg-primary: #FAFAF8;        /* Warm white — main background */
  --bg-secondary: #F2F1EE;      /* Slightly darker — cards, panels */
  --bg-tertiary: #E8E7E4;       /* Borders, dividers, subtle contrast */
  --bg-viewer: #F5F5F3;         /* 3D viewer background — very subtle warm */

  /* Text */
  --text-primary: #1A1A18;      /* Near-black — headings, primary content */
  --text-secondary: #6B6B66;    /* Medium grey — labels, descriptions */
  --text-tertiary: #9C9C97;     /* Light grey — timestamps, metadata */

  /* Brand */
  --accent: #E05A1A;            /* Warm deep orange — AURA brand color */
  --accent-hover: #C94D15;      /* Darker on hover */
  --accent-light: #FDF0EB;      /* Very light orange — subtle backgrounds */

  /* Status (these are the ONLY other colors in the UI) */
  --status-success: #2A9D5C;    /* Green — step complete, connected */
  --status-running: #2574D4;    /* Blue — autonomous execution */
  --status-warning: #D4930A;    /* Amber — needs attention, retrying */
  --status-error: #D43825;      /* Red — failed, disconnected, e-stop */
  --status-human: #7C5CBA;      /* Purple — human in control */
  --status-pending: #C8C7C3;    /* Light grey — not yet started */

  /* Status backgrounds (for badges and step cards) */
  --status-success-bg: #EDFAF2;
  --status-running-bg: #EBF2FC;
  --status-warning-bg: #FDF6E8;
  --status-error-bg: #FCEDEB;
  --status-human-bg: #F3EFFB;
}
```

### Usage Rules

- The brand accent (`--accent`) appears in: the AURA wordmark, primary action buttons (Start Assembly, Save), active tab indicators, and selected items. Nowhere else.
- Status colors appear ONLY on step status badges, connection indicators, and metric thresholds. Never as background fills for entire sections.
- Text is always `--text-primary` or `--text-secondary`. Never use status colors for body text.
- Borders use `--bg-tertiary`. One pixel, solid. No colored borders except on focused inputs (use `--accent`).

---

## Typography

```css
/* Primary: Geist Sans (Vercel's typeface — clean, modern, excellent readability) */
/* Fallback: system fonts */
--font-sans: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Monospace: for data, motor values, code, timestamps */
--font-mono: 'Geist Mono', 'SF Mono', 'Fira Code', monospace;
```

### Type Scale

| Element | Size | Weight | Font | Color |
|---------|------|--------|------|-------|
| Page title (AURA wordmark) | 18px | 600 | Sans | `--text-primary` |
| Section heading | 14px | 600 | Sans | `--text-primary` |
| Body / labels | 13px | 400 | Sans | `--text-secondary` |
| Metric value (large) | 32px | 600 | Mono | `--text-primary` |
| Metric value (medium) | 20px | 500 | Mono | `--text-primary` |
| Metric label | 11px | 500 | Sans uppercase | `--text-tertiary` |
| Data readout | 12px | 400 | Mono | `--text-secondary` |
| Button text | 13px | 500 | Sans | white or `--text-primary` |
| Badge / status | 11px | 600 | Sans | status color |

### Rules

- Never use font sizes below 11px
- Headings are `font-weight: 600`, never bold (700+)
- Uppercase ONLY for metric labels and status badges
- Letter-spacing: `0.02em` on uppercase labels, `0` everywhere else
- Line height: 1.5 for body text, 1.2 for headings, 1.0 for metrics

---

## Layout

### Main Screen (Assembly Dashboard)

This is the ONE screen. Everything happens here. No modals, no page navigation, no sidebar drawers (except settings).

```
┌─────────────────────────────────────────────────────────────────┐
│  AURA     [Assembly: Bearing Housing v1]       ⏱ 02:34   ▶ ⏸ ■ │  ← Top bar
├─────────────────────────────────────────┬───────────────────────┤
│                                         │                       │
│                                         │  Assembly Steps       │
│                                         │  ┌─────────────────┐  │
│                                         │  │ ① Pick housing ✓│  │
│          3D Assembly Viewer             │  │ ② Place housing ✓│  │
│                                         │  │ ③ Pick bearing ●│  │
│     [animated assembly sequence]        │  │ ④ Insert bearing │  │
│     [parts appear step by step]         │  │ ⑤ Press fit      │  │
│     [approach vectors visible]          │  └─────────────────┘  │
│                                         │                       │
│                                         │  Step Detail          │
│                                         │  ┌─────────────────┐  │
│                                         │  │ Pick bearing     │  │
│   ┌──────────────────────────────┐      │  │ Handler: primitive│ │
│   │ 📷 Camera PiP (during exec) │      │  │ Success: 94%     │  │
│   └──────────────────────────────┘      │  │ Avg time: 3.2s   │  │
│                                         │  └─────────────────┘  │
├─────────────────────────────────────────┴───────────────────────┤
│  Cycle 02:34  │  Success 87%  │  Steps 3/8  │  Run #14         │  ← Bottom bar
└─────────────────────────────────────────────────────────────────┘
```

### Top Bar

- Left: **AURA** wordmark in accent color. Assembly name as a dropdown selector.
- Center: Cycle time (large monospace number, counting up during execution).
- Right: Run controls — Start (▶), Pause (⏸), Stop (■), Intervene (🤚). Only active states are enabled. E-stop button is always visible, always red.

### Left Panel — 3D Assembly Viewer (60% width, always visible)

The 3D viewer is the hero of the entire product. It is always present, never hidden behind a tab. It serves three different roles depending on the phase:

**During Setup (no execution running):**
- Full interactive mode — orbit, zoom, pan
- Shows all parts in their final assembled positions (ghost/transparent)
- User clicks "Play Sequence" → parts animate in one by one, each arriving from its approach direction
- Clicking a step in the right panel highlights the relevant part(s) and shows the approach vector
- Parts can be individually selected to inspect grasp points

**During Execution (assembly running):**
- Camera picture-in-picture overlay in the bottom-left corner (resizable, ~25% of viewer)
- 3D view auto-tracks the current step: zooms to the relevant part, highlights it in accent color
- Completed parts solidify to full opacity
- Current part pulses subtly
- Pending parts remain ghosted
- Force/contact data can be overlaid as simple vectors on the current part

**During Teaching (teleop recording for a step):**
- Camera feed becomes full-screen in a modal overlay (operator needs to see the real robot)
- 3D viewer still visible behind at reduced opacity for spatial reference
- After recording, viewer shows the step that was just demonstrated

### Camera Picture-in-Picture

During execution, the live camera feed floats over the 3D viewer:
- Bottom-left corner, 25% viewer width, rounded corners, subtle shadow
- Click to expand to full viewer area (3D viewer slides to background)
- Click again to return to PiP
- Multiple cameras: small tabs at top of PiP to switch between feeds
- Status indicator dot: green = streaming, red = disconnected

### Right Panel (40% width)

**Two sections, stacked:**

1. **Assembly Steps** (top 55%) — Vertical list of steps. Each step is a card showing: step number, name, handler type (primitive/policy icon), status badge. The current step is highlighted. Click a step to see its detail below AND to highlight the corresponding part in the 3D viewer. During execution, auto-scrolls to current step.

   For linear assemblies, this is a simple vertical list. When parallel steps are needed later, this can be upgraded to a React Flow DAG.

2. **Step Detail** (bottom 45%) — Selected step's info: handler configuration, success rate chart (last N runs), average duration, number of demos recorded, trained policy info. Action buttons: "Record Demos", "Train", "Test Step".

### Bottom Bar

Persistent metrics strip: total cycle time, overall success rate, steps completed / total, run number. All in monospace. Updates in real-time during execution.

### Responsive Behavior

Don't worry about mobile. This runs on a laptop or desktop next to the robot. Minimum width: 1280px. If window is narrower, panels stack vertically (3D viewer on top, step list below).

---

## 3D Assembly Viewer — Detailed Specification

This is the most important component in the entire product. Build it with care.

### Technology

- `@react-three/fiber` — React renderer for Three.js
- `@react-three/drei` — helpers (OrbitControls, Environment, ContactShadows)
- `three` — core 3D engine
- Parts arrive from the backend as `.glb` (glTF binary) files, tessellated server-side by PythonOCC

### Scene Setup

```
Background:    --bg-viewer (#F5F5F3) — warm, not pure white
Lighting:      One soft directional light (slightly warm) + ambient
               No harsh shadows. Soft contact shadows on the ground plane only.
Ground plane:  Subtle grid — 1px lines, --bg-tertiary at 30% opacity
               Extends beyond the assembly. Gives spatial grounding.
Camera:        Perspective, default position at 45° azimuth, 30° elevation
               OrbitControls: rotate (left drag), zoom (scroll), pan (right drag)
               Smooth damping enabled (damping factor 0.1)
```

### Part Rendering

Parts have four visual states:

| State | Appearance |
|-------|------------|
| **Ghost** (pending) | Wireframe or 10% opacity fill. Neutral grey `#D4D4D0`. Shows where the part will end up. |
| **Active** (current step) | Full opacity, slight warm tint. Accent-colored edge outline (2px). Subtle pulse (opacity 0.85↔1.0, 2s period). |
| **Complete** (step done) | Full opacity, neutral material. No outline. Solid and settled. |
| **Selected** (user clicked) | Full opacity, accent outline, grasp points and approach vector visible. |

Material: MeshStandardMaterial with roughness 0.6, metalness 0.1. Not shiny, not flat. Like machined aluminum under soft light. Parts should look physical.

### Assembly Animation

When the user clicks "Play Sequence" or during the setup review:

1. Start with empty scene (just ground plane)
2. For each step in order:
   - Part fades in at its **approach position** (offset along approach vector, ~2x part height above)
   - Part moves along approach vector to its **final assembled position** (500ms ease-in-out)
   - Brief pause (300ms)
   - Next step begins
3. Total animation is controllable: play, pause, step forward, step backward
4. Timeline scrubber at the bottom of the viewer (thin, unobtrusive)

The approach position and vector come from the assembly graph's step data. If not specified, default to straight-down approach (part drops from above).

### Approach Vectors

Shown as thin lines with small arrowheads:
- Color: `--text-tertiary` at 60% opacity
- Length: proportional to part size (1.5x bounding box height)
- Only visible on active or selected parts
- Arrow points in the direction the part travels during insertion

### Grasp Points

Shown as small spheres (radius = 3% of part bounding box):
- Color: `--accent` at 80% opacity
- Only visible when a part is selected and the step uses a primitive
- Connected to the part surface with a thin line
- Tooltip on hover: grasp index, approach angle

### Camera Controls Overlay

Top-right of the viewer, minimal buttons (icon only, 28px, semi-transparent background on hover):
- 🔄 Reset view (return to default camera position)
- 📐 Toggle wireframe overlay
- 💥 Toggle exploded view (parts spread apart along their approach vectors)
- ▶ Play/pause assembly animation
- ⏮ ⏭ Step backward/forward in animation

### Performance

- Target: 60fps with up to 50 parts visible
- Use instancing for identical parts (e.g., multiple screws)
- LOD (Level of Detail) if parts have >50K triangles: simplify when zoomed out
- Lazy load part meshes — show bounding boxes immediately, swap in real geometry
- Frustum culling enabled by default in Three.js

### The Demo Moment

When a STEP file is uploaded and parsed, the 3D viewer should:

1. Parts appear one by one in their assembled positions (fast, 100ms each)
2. Brief pause showing the complete assembly
3. "Explode" — parts spread apart along their approach vectors
4. "Assemble" — parts animate back together in the proposed sequence order
5. User sees the assembly plan come alive in seconds

This is the moment someone understands what AURA does. Make it smooth, make it fast, make it feel inevitable.

---

## Components

### Step Card

```
┌──────────────────────────────────┐
│  ③  Pick bearing         ● ACTIVE │
│      primitive · pick     3.2s avg │
└──────────────────────────────────┘
```

- Left: step number in a circle (filled with status color when complete/active)
- Center: step name (primary text), handler type + primitive name (secondary text)
- Right: status badge, average duration

States:
- **Pending** — grey circle, grey text, grey badge
- **Active** — accent circle (pulsing subtly), primary text, blue "RUNNING" badge
- **Success** — green filled circle with checkmark, primary text, green "DONE" badge
- **Failed** — red circle with X, primary text, red "FAILED" badge
- **Human** — purple circle, primary text, purple "HUMAN" badge
- **Retrying** — amber circle, primary text, amber "RETRY 2/3" badge

### Metric Card

```
┌──────────────┐
│  CYCLE TIME  │  ← label: 11px, uppercase, tertiary color
│    02:34     │  ← value: 32px, monospace, primary color
│  avg 02:12   │  ← context: 12px, mono, tertiary color
└──────────────┘
```

No border. No background. Just the number with its label. The whitespace around it IS the card.

### Action Button

Primary (Start Assembly): accent background, white text, 13px font-weight 500, 8px padding vertical, 16px horizontal, 6px border-radius. No shadow.

Secondary (Pause, Train): transparent background, `--text-primary` text, 1px `--bg-tertiary` border. Same sizing.

Danger (E-Stop, Stop): `--status-error` background, white text. Always visible during execution.

### Status Badge

Pill shape: 11px uppercase text, 600 weight, 2px vertical padding, 8px horizontal, 10px border-radius. Background is the `--status-*-bg` variant, text is the `--status-*` color. No border.

### 3D Viewer

See the **3D Assembly Viewer — Detailed Specification** section above for full rendering, animation, and interaction specs. The viewer is the hero component and deserves the most engineering attention.

### Camera Picture-in-Picture

Floating overlay during execution:
- Bottom-left of 3D viewer, ~25% viewer width
- Rounded corners (8px), subtle drop shadow (0 2px 8px rgba(0,0,0,0.08))
- Click to expand / collapse (25% → 60% of viewer)
- Camera selector tabs if multiple feeds
- Green/red streaming status dot

### Upload Dialog

Modal triggered by "+" button in TopBar:
- Drag-and-drop zone for `.step` / `.stp` files
- File input fallback
- States: idle → uploading (spinner) → error
- Calls `POST /assemblies/upload` with FormData
- On success: closes, triggers assembly list refresh, selects new assembly
- Close on Escape key or overlay click

### Recording Controls

Shown in StepDetail panel when a step is selected:
- "Record Demos" button starts teleop + recording (`POST /recording/step/{stepId}/start`)
- Elapsed timer (MM:SS format) during active recording
- "Stop Recording" flushes to HDF5, "Discard" abandons
- Shows demo count for current step

### Demo List

Below RecordingControls in StepDetail:
- Lists all recorded demos for the selected step
- Each row: timestamp, duration, delete button
- Fetches from `GET /recording/demos/{assemblyId}/{stepId}`
- Empty state: "No demos recorded yet"

### Training Progress

Shown in StepDetail for policy-type steps:
- "Train Policy" button → `POST /training/step/{stepId}/train`
- Polls `GET /training/jobs/{jobId}` every 2s during training
- Shows: progress %, loss sparkline (Recharts AreaChart), status
- States: idle → training (with progress) → complete (policy ID) → failed

### Mini Chart

Small inline chart used in StepDetail metrics:
- Recharts AreaChart showing recent run success/failure
- Maps runs to 1 (success) / 0 (failure) values
- Minimal: no axes, no labels, just the shape

### Animation System

Pure logic in `lib/animation.ts` (no React or Three.js dependencies):
- Phase machine: `idle → demo_fadein → demo_hold → demo_explode → demo_assemble → playing → scrubbing`
- Per-part render state: `{ position, opacity, visualState }` computed by `computePartAnimation()`
- Easing: cubic ease-in-out
- Scrubber: bidirectional `scrubberToStep()` / `stepToScrubber()` mapping

`lib/useAnimationControls.ts` — React hook wrapping animation state:
- Returns: `toggleAnimation`, `stepForward`, `stepBackward`, `replayDemo`, `scrubStart`, `scrub`, `scrubEnd`, `forceIdle`
- Auto-plays demo on assembly change

`viewer/AnimationController.tsx` — Renderless component inside Canvas:
- `useFrame` callback ticks phase machine every frame
- Writes to shared refs (not React state) for 60fps performance
- Computes centroid and explode offsets on part change

---

## Tech Stack

```json
{
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@react-three/fiber": "^9.0.0",
    "@react-three/drei": "^10.0.0",
    "three": "^0.182.0",
    "recharts": "^3.7.0",
    "tailwindcss": "^4.0.0",
    "swr": "^2.4.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/react": "^19.0.0",
    "@types/three": "^0.182.0"
  }
}
```

### Rules

- **TypeScript strict mode.** No `any`. No `// @ts-ignore`.
- **One component per file**, max 200 lines. If it's bigger, split it.
- **No component libraries** (no shadcn, no MUI, no Chakra). Hand-craft the ~25 components you need. They'll be simpler and more cohesive.
- **No prop drilling** beyond 2 levels. Use React context for shared state (assembly, execution status, WebSocket connection).
- **Data fetching:** `useSWR` for polling data (metrics, step status). WebSocket for real-time streams (motor telemetry, camera feeds).
- **No `useEffect` for data fetching.** Use SWR or Server Components.
- **State management:** React state + context. No Redux, no Zustand, no Jotai. The state is simple: current assembly, execution status, selected step.

### File Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout with Providers wrapper
│   ├── page.tsx                # Assembly dashboard (main + only screen)
│   └── globals.css             # Tailwind v4 @theme inline + color tokens
├── components/
│   ├── Providers.tsx           # SWR + WebSocket + Assembly + Execution context nesting
│   ├── TopBar.tsx              # AURA wordmark, assembly selector, upload, controls
│   ├── BottomBar.tsx           # Metrics strip + teleop indicator
│   ├── DemoBanner.tsx          # "Demo Mode" banner when no hardware connected
│   ├── RunControls.tsx         # Start / pause / resume / stop / intervene / E-stop
│   ├── UploadDialog.tsx        # Modal: drag-drop .step/.stp upload → POST /assemblies/upload
│   ├── StepList.tsx            # Assembly steps list with auto-scroll
│   ├── StepCard.tsx            # Individual step card (status icon, badge, duration)
│   ├── StepDetail.tsx          # Selected step info + metrics + recording + training
│   ├── RecordingControls.tsx   # Start/stop/discard recording with elapsed timer
│   ├── DemoList.tsx            # Recorded demos with timestamps and delete
│   ├── TrainingProgress.tsx    # Train button, polling progress, loss sparkline
│   ├── MetricCard.tsx          # Single metric display (label, value, context)
│   ├── MiniChart.tsx           # Recharts AreaChart for success/failure history
│   ├── StatusBadge.tsx         # Step status pill (pending/running/success/failed/human/retrying)
│   ├── ActionButton.tsx        # Primary / secondary / danger variants
│   ├── CameraPiP.tsx           # Picture-in-picture camera overlay (placeholder)
│   ├── TeachingOverlay.tsx     # Full-screen camera during teleop recording
│   └── viewer/
│       ├── AssemblyViewer.tsx  # Main Three.js canvas + scene setup
│       ├── PartMesh.tsx        # Single part: ghost/active/complete/selected states
│       ├── AnimationController.tsx # Renderless: ticks phase machine at 60fps via useFrame
│       ├── ViewerControls.tsx  # Overlay buttons (reset, wireframe, explode, play, step)
│       ├── AnimationTimeline.tsx # Draggable scrubber bar with step dots
│       ├── GroundPlane.tsx     # Grid + contact shadows
│       ├── ApproachVector.tsx  # Arrow showing insertion direction
│       └── GraspPoint.tsx      # Grasp pose indicator sphere
├── context/
│   ├── AssemblyContext.tsx      # SWR-backed assembly + step selection
│   ├── ExecutionContext.tsx     # Sequencer state (WebSocket or mock timer fallback)
│   └── WebSocketContext.tsx     # Real-time connection with mock heartbeat fallback
├── lib/
│   ├── types.ts                # Shared TypeScript types (mirrors backend models)
│   ├── api.ts                  # All API calls + withMockFallback() wrapper
│   ├── ws.ts                   # AuraWebSocket class with graceful degradation
│   ├── animation.ts            # Pure animation logic (no React/Three.js deps)
│   ├── useAnimationControls.ts # React hook for 3D viewer animation state
│   ├── hooks.ts                # useKeyboardShortcuts, useConnectionStatus
│   └── mock-data.ts            # Mock assembly, execution state, metrics
├── package.json
└── tsconfig.json
```

Note: Tailwind v4 uses `@theme inline` in `globals.css` — there is no `tailwind.config.ts`.

### API Client Pattern

```typescript
// lib/api.ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// All fetches use withMockFallback() — catches TypeError (network unavailable)
// and returns mock data from lib/mock-data.ts. HTTP errors are NOT caught.

export const api = {
  // Health / System
  health: () => get<{ status: string }>("/health"),
  fetchSystemInfo: () => get<SystemInfo>("/system/info"),

  // Assembly
  getAssemblies: () => get<AssemblySummary[]>("/assemblies"),
  getAssembly: (id: string) => get<Assembly>(`/assemblies/${id}`),
  uploadCAD: (file: File) => postFile<Assembly>("/assemblies/upload", file),
  updateStep: (assemblyId: string, stepId: string, data: Partial<AssemblyStep>) =>
    patch(`/assemblies/${assemblyId}/steps/${stepId}`, data),

  // Execution
  startAssembly: (id: string) => post(`/execution/start`, { assembly_id: id }),
  pauseExecution: () => post("/execution/pause"),
  resumeExecution: () => post("/execution/resume"),
  stopExecution: () => post("/execution/stop"),
  intervene: () => post("/execution/intervene"),
  getExecutionState: () => get<ExecutionState>("/execution/state"),

  // Teleop
  startTeleop: (arms: string[], mock?: boolean) => post("/teleop/start", { arms }, mock),
  stopTeleop: () => post("/teleop/stop"),
  getTeleopState: () => get<TeleopState>("/teleop/state"),

  // Recording
  startRecording: (stepId: string, assemblyId: string) =>
    post(`/recording/step/${stepId}/start`, { assembly_id: assemblyId }),
  stopRecording: () => post("/recording/stop"),
  discardRecording: () => post("/recording/discard"),
  listDemos: (assemblyId: string, stepId: string) =>
    get<DemoInfo[]>(`/recording/demos/${assemblyId}/${stepId}`),

  // Training (STUBBED on backend)
  trainStep: (stepId: string, config: TrainConfig) =>
    post(`/training/step/${stepId}/train`, config),
  getTrainingJob: (jobId: string) => get<TrainStatus>(`/training/jobs/${jobId}`),
  listTrainingJobs: () => get<TrainStatus[]>("/training/jobs"),

  // Analytics
  getStepMetrics: (assemblyId: string) => get<StepMetrics[]>(`/analytics/${assemblyId}/steps`),
};
```

---

## Animations & Transitions

Minimal. Intentional. Never decorative.

**Allowed:**
- Step status badge color transitions: 200ms ease
- Panel show/hide: 150ms ease-out
- Current step highlight pulse: subtle opacity oscillation (0.8 → 1.0, 2s period)
- 3D viewer part appearance: quick fade-in (200ms) when stepping through sequence
- Loading indicators: simple spinner or progress bar

**Not allowed:**
- Page transitions
- Card hover animations
- Staggered list reveals
- Parallax
- Bouncing, wobbling, or spring physics
- Anything that makes the user wait

---

## Accessibility

- All interactive elements have focus states (2px `--accent` outline)
- Status is never conveyed by color alone (always has text label or icon)
- Keyboard navigation for step list (arrow keys) and run controls (spacebar = start/pause)
- Minimum contrast ratio: 4.5:1 for body text, 3:1 for large text
- Camera feeds have alt text describing what the camera shows ("Workspace camera — top view")

---

## What This Is NOT

- Not a design system for a marketing site
- Not a component library to be published
- Not a dark-themed hacker interface
- Not a mobile-first responsive app
- Not a dashboard with 20 different pages
- Not anything with a sidebar navigation

It's ONE screen that shows an operator everything they need to set up, teach, run, and monitor an assembly. If you need a second screen, you've designed the first one wrong.
