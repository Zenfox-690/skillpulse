"""
Entrypoint for `python -m skillpulse`.
"""

import sys
from skillpulse.cli import main

if __name__ == "__main__":
    sys.exit(main())
