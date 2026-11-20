"""Compatibility entry point for the shared offline renderer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.render import main

if __name__ == "__main__":
    raise SystemExit(main())
