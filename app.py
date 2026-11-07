"""Launch the Posture Check desktop interface from the repository root."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from posture_check.gui import main

if __name__ == '__main__':
    main()
