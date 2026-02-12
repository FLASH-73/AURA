"""Start the Manus API server."""

import os
import sys
from pathlib import Path

# Ensure the project root is on PYTHONPATH so uvicorn's reloader subprocess
# can find the nextis package.
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, PROJECT_ROOT)
os.environ["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("nextis.api.app:app", host="0.0.0.0", port=8000, reload=True)
