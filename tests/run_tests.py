"""
Comprehensive Test Runner for Antigravity LoopGraph.
"""

import sys

from tests.test_guardrails import test_path_sandbox_containment, test_command_blocklist
from tests.test_tools import (
    test_file_tools,
    test_search_and_discovery_tools,
    test_command_execution,
    test_tool_registries,
)
from tests.test_board_parser import (
    test_board_serialization_and_parsing,
    test_project_state_dependency_resolution,
    test_ledger_logging,
)
from tests.test_graph import (
    test_basic_stategraph_transitions,
    test_react_loop_anti_thrashing,
)
from tests.test_edge_cases import (
    test_security_path_traversal_and_drive_escaping,
    test_security_command_injection_and_chained_attacks,
    test_file_tools_edge_cases,
)

ALL_TESTS = [
    ("test_path_sandbox_containment", test_path_sandbox_containment),
    ("test_command_blocklist", test_command_blocklist),
    ("test_file_tools", test_file_tools),
    ("test_search_and_discovery_tools", test_search_and_discovery_tools),
    ("test_command_execution", test_command_execution),
    ("test_tool_registries", test_tool_registries),
    ("test_board_serialization_and_parsing", test_board_serialization_and_parsing),
    ("test_project_state_dependency_resolution", test_project_state_dependency_resolution),
    ("test_ledger_logging", test_ledger_logging),
    ("test_basic_stategraph_transitions", test_basic_stategraph_transitions),
    ("test_react_loop_anti_thrashing", test_react_loop_anti_thrashing),
    ("test_security_path_traversal_and_drive_escaping", test_security_path_traversal_and_drive_escaping),
    ("test_security_command_injection_and_chained_attacks", test_security_command_injection_and_chained_attacks),
    ("test_file_tools_edge_cases", test_file_tools_edge_cases),
]


def run_all():
    print("=" * 65)
    print("  RUNNING ANTIGRAVITY LOOPGRAPH TEST SUITE")
    print("=" * 65)
    passed = 0
    failed = 0

    for name, fn in ALL_TESTS:
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
    print(f"  TOTAL RESULTS: {passed} passed, {failed} failed.")
    print("=" * 65)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
