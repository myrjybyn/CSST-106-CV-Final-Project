"""Run the milestone prototype from a fresh checkout without PYTHONPATH setup."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from posture_check.__main__ import main

if __name__ == "__main__":
    main()
