"""
Comprehensive Test Runner for Antigravity LoopGraph Suite.
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
from tests.test_heuristic_planner import (
    test_heuristic_planner_from_vision,
    test_plan_without_api_key,
)
from tests.test_edge_cases import (
    test_security_path_traversal_and_drive_escaping,
    test_security_command_injection_and_chained_attacks,
    test_file_tools_edge_cases,
)
from tests.test_guardrails_bypass import test_guardrails_blocks_known_bypasses
from tests.test_antigravity_scaffold import (
    test_scaffold_writes_skill_and_rules_files,
    test_scaffold_is_idempotent_and_preserves_edits,
)
from tests.test_config_and_deps import (
    test_config_file_values_are_loaded,
    test_no_config_path_still_returns_defaults,
    test_dependency_cycle_is_detected,
    test_self_dependency_is_detected,
    test_longer_cycle_is_detected,
    test_dangling_dependency_is_detected,
    test_healthy_dependency_chain_reports_no_problem,
    test_child_env_keeps_path,
)
from tests.test_board_warnings import (
    test_row_whose_title_contains_dashes_is_not_dropped,
    test_separator_row_is_still_skipped,
    test_short_row_is_reported_not_silently_dropped,
    test_non_integer_priority_is_reported,
    test_unknown_status_is_reported,
    test_duplicate_task_id_is_reported,
    test_clean_board_produces_no_warnings,
    test_warnings_reset_between_parses,
)
from tests.test_python_compat import (
    test_declared_minimum_matches_this_guard,
    test_no_backslash_inside_fstring_expressions,
    test_guard_detects_a_known_offender,
    test_all_sources_parse,
)

LOOPGRAPH_TESTS = [
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
    ("test_heuristic_planner_from_vision", test_heuristic_planner_from_vision),
    ("test_plan_without_api_key", test_plan_without_api_key),
    ("test_security_path_traversal_and_drive_escaping", test_security_path_traversal_and_drive_escaping),
    ("test_security_command_injection_and_chained_attacks", test_security_command_injection_and_chained_attacks),
    ("test_file_tools_edge_cases", test_file_tools_edge_cases),
    ("test_guardrails_blocks_known_bypasses", test_guardrails_blocks_known_bypasses),
    ("test_scaffold_writes_skill_and_rules_files", test_scaffold_writes_skill_and_rules_files),
    ("test_scaffold_is_idempotent_and_preserves_edits", test_scaffold_is_idempotent_and_preserves_edits),
    ("test_config_file_values_are_loaded", test_config_file_values_are_loaded),
    ("test_no_config_path_still_returns_defaults", test_no_config_path_still_returns_defaults),
    ("test_dependency_cycle_is_detected", test_dependency_cycle_is_detected),
    ("test_self_dependency_is_detected", test_self_dependency_is_detected),
    ("test_longer_cycle_is_detected", test_longer_cycle_is_detected),
    ("test_dangling_dependency_is_detected", test_dangling_dependency_is_detected),
    ("test_healthy_dependency_chain_reports_no_problem", test_healthy_dependency_chain_reports_no_problem),
    ("test_child_env_keeps_path", test_child_env_keeps_path),
    ("test_row_whose_title_contains_dashes_is_not_dropped", test_row_whose_title_contains_dashes_is_not_dropped),
    ("test_separator_row_is_still_skipped", test_separator_row_is_still_skipped),
    ("test_short_row_is_reported_not_silently_dropped", test_short_row_is_reported_not_silently_dropped),
    ("test_non_integer_priority_is_reported", test_non_integer_priority_is_reported),
    ("test_unknown_status_is_reported", test_unknown_status_is_reported),
    ("test_duplicate_task_id_is_reported", test_duplicate_task_id_is_reported),
    ("test_clean_board_produces_no_warnings", test_clean_board_produces_no_warnings),
    ("test_warnings_reset_between_parses", test_warnings_reset_between_parses),
    ("test_declared_minimum_matches_this_guard", test_declared_minimum_matches_this_guard),
    ("test_no_backslash_inside_fstring_expressions", test_no_backslash_inside_fstring_expressions),
    ("test_guard_detects_a_known_offender", test_guard_detects_a_known_offender),
    ("test_all_sources_parse", test_all_sources_parse),
]


def run_all():
    print("=" * 65)
    print("  RUNNING ANTIGRAVITY LOOPGRAPH TEST SUITE")
    print("=" * 65)
    passed = 0
    failed = 0

    for name, fn in LOOPGRAPH_TESTS:
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
    print(f"  LOOPGRAPH RESULTS: {passed} passed, {failed} failed.")
    print("=" * 65)
    return failed


if __name__ == "__main__":
    sys.exit(1 if run_all() > 0 else 0)
