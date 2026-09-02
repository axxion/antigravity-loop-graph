#!/usr/bin/env python3
"""
LoopGraph Backward-Compatibility Entry Point.
Delegates to the modular loopgraph package while preserving original CLI flags and script usage.
"""

import sys
from loopgraph.cli import main

if __name__ == "__main__":
    sys.exit(main())
