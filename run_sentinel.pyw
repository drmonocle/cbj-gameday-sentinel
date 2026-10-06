"""Double-click launcher (no console window). Also used by the auto-start entry."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cbj_sentinel.app import main  # noqa: E402

main()
