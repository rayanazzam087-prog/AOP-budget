"""AOP-Budget: plan checking vs. sub-task revision under a coordination budget,
a reimplementation of Agent-Oriented Planning (Li et al., ICLR 2025)."""
__version__ = "0.1.0"

import sys as _sys

for _s in (_sys.stdout, _sys.stderr):  # Windows consoles default to cp1252
    try:
        _s.reconfigure(errors="replace")
    except Exception:
        pass
