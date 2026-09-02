"""
Comprehensive Test Runner for Antigravity LoopGraph.

Delegates to run_loopgraph_tests (always available) and, if the optional
antigravity_optimizer package is present locally, run_optimizer_tests too.
This file intentionally has no test list of its own, so the loopgraph and
optimizer suites cannot drift out of sync with each other (see KALITE-RAPOR
2026-09-02, madde 3).
"""

import importlib.util
import sys

from tests import run_loopgraph_tests


def run_all():
    failed = run_loopgraph_tests.run_all()

    if importlib.util.find_spec("antigravity_optimizer") is not None:
        from tests import run_optimizer_tests
        failed += run_optimizer_tests.run_all()
    else:
        print("(antigravity_optimizer not installed locally - optimizer suite skipped)")

    return failed


if __name__ == "__main__":
    sys.exit(1 if run_all() > 0 else 0)
