"""Start the AURA demo stack for the upload-to-execution flow.

Usage:
    python scripts/demo_flow.py          # start backend only
    python scripts/demo_flow.py --open   # start backend + open browser

Starts the FastAPI backend on port 8000 in a subprocess.
Open a second terminal and run: cd frontend && npm run dev
Then open http://localhost:3000, press Space to start execution.
"""

import argparse
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BANNER = """
╔═══════════════════════════════════════════════╗
║  AURA — Upload-to-Execution Demo              ║
║                                               ║
║  API:       http://localhost:8000              ║
║  Dashboard: http://localhost:3000              ║
║  Mode:      Mock (no hardware)                ║
║                                               ║
║  1. Run:  cd frontend && npm run dev           ║
║  2. Open: http://localhost:3000                ║
║  3. Press Space to start assembly execution    ║
║                                               ║
║  Ctrl+C to stop                               ║
╚═══════════════════════════════════════════════╝
"""


def wait_for_health(url: str, timeout: float = 15.0) -> bool:
    """Poll the health endpoint until it responds or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (URLError, OSError):
            pass
        time.sleep(0.5)
    return False


def main() -> None:
    """Launch the AURA backend and wait for it to be ready."""
    parser = argparse.ArgumentParser(description="AURA demo flow launcher")
    parser.add_argument(
        "--open", action="store_true", help="Open browser to localhost:3000"
    )
    args = parser.parse_args()

    print(BANNER)

    # Start the backend as a subprocess
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "run_api.py")],
        cwd=str(PROJECT_ROOT),
    )

    # Forward SIGTERM to the subprocess
    def handle_signal(signum: int, _frame: object) -> None:
        proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)

    # Wait for backend readiness
    print("  Waiting for backend...")
    if wait_for_health("http://localhost:8000/health"):
        print("  Backend ready on http://localhost:8000")
    else:
        print("  Warning: backend did not respond within 15s (continuing anyway)")

    if args.open:
        webbrowser.open("http://localhost:3000")
        print("  Opened browser to http://localhost:3000")

    print("\n  Dashboard at http://localhost:3000 — Press Space to start assembly\n")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        proc.terminate()
        proc.wait(timeout=5)
        print("  Done.")


if __name__ == "__main__":
    main()
