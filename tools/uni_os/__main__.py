"""Allow ``python -m uni_os`` when ``tools/`` is on ``sys.path``."""

import sys

from .cli import main

sys.exit(main())
