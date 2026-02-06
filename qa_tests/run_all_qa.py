#!/usr/bin/env python3
"""Run all QA tests and generate consolidated gap analysis report."""

import os
import sys

# Ensure imports work from repo root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

from qa_helpers import QAReport, print_report, print_aggregate_report, run_test_safely

# Import all test modules
from test_basic_ivr import run_test as test_basic_ivr
from test_queue_transfer import run_test as test_queue_transfer
from test_business_hours_lambda import run_test as test_business_hours_lambda
from test_lex_bot import run_test as test_lex_bot
from test_nested_menus_retry import run_test as test_nested_menus_retry
from test_ab_testing import run_test as test_ab_testing
from test_attributes_and_compare import run_test as test_attributes_and_compare
from test_callback_flow import run_test as test_callback_flow
from test_recording_control import run_test as test_recording_control
from test_decompile_modify import run_test as test_decompile_modify
from test_transfer_to_flow import run_test as test_transfer_to_flow
from test_zero_knowledge import run_test as test_zero_knowledge


TESTS = [
    (test_basic_ivr, "Basic IVR"),
    (test_queue_transfer, "Queue Transfer"),
    (test_business_hours_lambda, "Business Hours + Lambda"),
    (test_lex_bot, "Lex Bot"),
    (test_nested_menus_retry, "Nested Menus + Retry"),
    (test_ab_testing, "A/B Testing"),
    (test_attributes_and_compare, "Attributes + Compare"),
    (test_callback_flow, "Callback Flow"),
    (test_recording_control, "Recording Control"),
    (test_decompile_modify, "Decompile + Modify"),
    (test_transfer_to_flow, "Transfer to Flow"),
]

# Zero-knowledge test only runs when API key is available
if os.environ.get("ANTHROPIC_API_KEY"):
    TESTS.append((test_zero_knowledge, "Zero-Knowledge Agent"))


def main():
    reports: list[QAReport] = []

    for test_func, test_name in TESTS:
        print(f"\nRunning: {test_name}...")
        report = run_test_safely(test_func, test_name)
        print_report(report)
        reports.append(report)

    print_aggregate_report(reports)

    # Return non-zero if any test failed to compile
    failures = sum(1 for r in reports if not r.compiled)
    if failures:
        print(f"\n{failures} test(s) failed to compile.")
    return failures


if __name__ == "__main__":
    sys.exit(main())
