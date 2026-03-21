#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys


SKILL_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
SCRIPT_PATH = SCRIPTS_DIR / "tasktracker_call.py"


def _ensure_scripts_dir_on_path():
    scripts_dir = str(SCRIPTS_DIR)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


if __name__ == "__main__":
    _ensure_scripts_dir_on_path()
    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
