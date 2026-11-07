#!/usr/bin/env python3
"""Uni OS command line: ``python tools/uni_os.py <command> [options]``.

Works from any current directory (it puts its own folder on ``sys.path``).
Needs Python 3.11+ and nothing else. Run ``python tools/uni_os.py --help``.
"""

import os
import sys

if sys.version_info < (3, 11):
    sys.stderr.write("uni-os needs Python 3.11 or newer (it uses tomllib).\n")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uni_os.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
