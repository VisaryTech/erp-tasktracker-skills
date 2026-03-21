#!/usr/bin/env python3
from pathlib import Path
import runpy


SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "tasktracker_call.py"


if __name__ == "__main__":
    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
