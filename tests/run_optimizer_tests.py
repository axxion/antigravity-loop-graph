"""
Dedicated Test Runner for Antigravity Token Optimizer Suite.
"""

import sys

from tests.test_ast_skeleton import test_python_ast_skeleton, test_typescript_skeleton
from tests.test_compressor import (
    test_command_compression,
    test_search_compression,
    test_data_compactor,
    test_context_buffer_store,
)
from tests.test_auditor import test_project_auditor
from tests.test_generators import test_generators_installation
from tests.test_edge_cases import (
    test_ast_skeleton_syntax_errors_and_edge_cases,
    test_compressor_massive_outputs,
)

OPTIMIZER_TESTS = [
    ("test_python_ast_skeleton", test_python_ast_skeleton),
    ("test_typescript_skeleton", test_typescript_skeleton),
    ("test_command_compression", test_command_compression),
    ("test_search_compression", test_search_compression),
    ("test_data_compactor", test_data_compactor),
    ("test_context_buffer_store", test_context_buffer_store),
    ("test_project_auditor", test_project_auditor),
    ("test_generators_installation", test_generators_installation),
    ("test_ast_skeleton_syntax_errors_and_edge_cases", test_ast_skeleton_syntax_errors_and_edge_cases),
    ("test_compressor_massive_outputs", test_compressor_massive_outputs),
]


def run_all():
    print("=" * 65)
    print("  RUNNING ANTIGRAVITY TOKEN OPTIMIZER TEST SUITE")
    print("=" * 65)
    passed = 0
    failed = 0

    for name, fn in OPTIMIZER_TESTS:
        try:
            fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("=" * 65)
    print(f"  OPTIMIZER RESULTS: {passed} passed, {failed} failed.")
    print("=" * 65)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
