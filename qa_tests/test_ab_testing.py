"""
QA Test 6: A/B Split with Percentage Distribution

Build: welcome -> 50/50 split -> path A (new greeting) vs path B (old greeting)
       -> same menu -> disconnect.

Tests:
- flow.distribute_by_percentage() convenience method
- DistributeByPercentage .branch() method for wiring percentage buckets
- NumberLessThan conditions with cumulative percentages (AWS spec)
- Empty parameters (AWS spec requirement)
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
from qa_helpers import QAReport


def run_test() -> QAReport:
    report = QAReport("test_ab_testing")

    # ---------------------------------------------------------------
    # Import the library
    # ---------------------------------------------------------------
    try:
        from cxblueprint import Flow, FlowValidationError
        report.success("Imported Flow, FlowValidationError")
    except Exception as exc:
        report.error("Failed to import required classes", exc)
        return report

    # ---------------------------------------------------------------
    # Build the A/B testing flow
    # ---------------------------------------------------------------
    try:
        flow = Flow.build("AB Testing Flow", debug=False)
        report.success("Created flow with Flow.build()")
    except Exception as exc:
        report.error("Failed to create flow", exc)
        return report

    # Step 1: Welcome message
    try:
        welcome = flow.play_prompt("Welcome to our service. We are testing a new experience.")
        report.success("Created welcome prompt")
    except Exception as exc:
        report.error("Failed to create welcome prompt", exc)
        return report

    # Step 2: Create the A/B split block using convenience method
    try:
        ab_split = flow.distribute_by_percentage([50, 50])
        report.success(
            "Created DistributeByPercentage via flow.distribute_by_percentage([50, 50])",
            "Convenience method handles uuid, type, and empty parameters"
        )
    except Exception as exc:
        report.error("Failed to create DistributeByPercentage block", exc)
        return report

    # Wire welcome -> split
    try:
        welcome.then(ab_split)
        report.success("Wired welcome.then(ab_split)")
    except Exception as exc:
        report.error("Failed to wire welcome to split", exc)
        return report

    # Step 3: Create the two greeting paths
    try:
        new_greeting = flow.play_prompt(
            "Thank you for calling! We are excited to offer you our enhanced service experience."
        )
        old_greeting = flow.play_prompt(
            "Thank you for calling. How may we direct your call?"
        )
        report.success("Created Path A (new greeting) and Path B (old greeting) prompts")
    except Exception as exc:
        report.error("Failed to create greeting prompts", exc)
        return report

    # Step 4: Wire the split block to both paths using .branch() for ALL buckets
    try:
        ab_split.branch(0, new_greeting).branch(1, old_greeting)
        report.success(
            "Wired DistributeByPercentage via .branch(0, new_greeting).branch(1, old_greeting)",
            "branch() auto-calculates NumberLessThan cumulative threshold for ALL buckets"
        )
    except Exception as exc:
        report.error("Failed to wire DistributeByPercentage branches", exc)
        return report

    # Step 5: Create shared menu after both greeting paths
    try:
        shared_menu = flow.get_input(
            "Press 1 for Sales, 2 for Support.",
            timeout=10
        )
        report.success("Created shared menu (converging both A/B paths)")
    except Exception as exc:
        report.error("Failed to create shared menu", exc)
        return report

    # Wire both greetings to the shared menu
    try:
        new_greeting.then(shared_menu)
        old_greeting.then(shared_menu)
        report.success("Both greeting paths converge to the shared menu")
    except Exception as exc:
        report.error("Failed to wire greetings to shared menu", exc)
        return report

    # Step 6: Create terminal blocks for the menu
    try:
        sales_msg = flow.play_prompt("Connecting you to Sales.")
        support_msg = flow.play_prompt("Connecting you to Support.")
        invalid_msg = flow.play_prompt("Invalid selection. Goodbye.")
        hangup = flow.disconnect()

        sales_msg.then(hangup)
        support_msg.then(hangup)
        invalid_msg.then(hangup)
        report.success("Created menu options (Sales, Support, Invalid) all terminating at disconnect")
    except Exception as exc:
        report.error("Failed to create menu terminal blocks", exc)
        return report

    # Wire the shared menu
    try:
        shared_menu.when("1", sales_msg)
        shared_menu.when("2", support_msg)
        shared_menu.otherwise(invalid_msg)
        shared_menu.on_error("InputTimeLimitExceeded", invalid_msg)
        shared_menu.on_error("NoMatchingCondition", invalid_msg)
        shared_menu.on_error("NoMatchingError", invalid_msg)
        report.success("Wired shared menu with conditions and error handlers")
    except Exception as exc:
        report.error("Failed to wire shared menu", exc)
        return report

    # ---------------------------------------------------------------
    # Record block count
    # ---------------------------------------------------------------
    report.block_count = len(flow.blocks)
    report.success(
        f"Total block count: {report.block_count}",
        "welcome + ab_split + new_greeting + old_greeting + shared_menu "
        "+ sales_msg + support_msg + invalid_msg + hangup = 9 blocks"
    )

    # ---------------------------------------------------------------
    # Validate the flow
    # ---------------------------------------------------------------
    try:
        flow.validate()
        report.validation_passed = True
        report.success("Flow validation passed")
    except FlowValidationError as exc:
        report.error("Flow validation failed", exc)

    # ---------------------------------------------------------------
    # Compile to file
    # ---------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    output_path = os.path.join(output_dir, "ab_testing.json")
    try:
        flow.compile_to_file(output_path)
        report.compiled = True
        report.success(f"Flow compiled successfully to {output_path}")
    except FlowValidationError as exc:
        report.error("Compilation failed due to validation error", exc)
    except Exception as exc:
        report.error("Compilation failed with unexpected error", exc)

    # ---------------------------------------------------------------
    # Structural assertions
    # ---------------------------------------------------------------
    # Verify parameters are empty (AWS spec)
    try:
        assert ab_split.parameters == {}, \
            f"Parameters should be empty, got {ab_split.parameters}"
        report.success("DistributeByPercentage parameters are empty {} (AWS spec)")
    except AssertionError as exc:
        report.error("Parameters not empty", exc)
    except Exception as exc:
        report.error("Failed to verify parameters", exc)

    # Verify ALL conditions use NumberLessThan (both buckets)
    try:
        conditions = ab_split.transitions.get("Conditions", [])
        assert len(conditions) == 2, \
            f"Expected 2 conditions (ALL buckets), got {len(conditions)}"
        # Bucket A: NumberLessThan "51" (catches 1-50 = 50%)
        assert conditions[0]["Condition"]["Operator"] == "NumberLessThan", \
            f"Expected NumberLessThan, got {conditions[0]['Condition']['Operator']}"
        assert conditions[0]["Condition"]["Operands"] == ["51"], \
            f"Expected operand '51' for first 50% bucket, got {conditions[0]['Condition']['Operands']}"
        # Bucket B: NumberLessThan "101" (catches 51-100 = 50%)
        assert conditions[1]["Condition"]["Operator"] == "NumberLessThan", \
            f"Expected NumberLessThan, got {conditions[1]['Condition']['Operator']}"
        assert conditions[1]["Condition"]["Operands"] == ["101"], \
            f"Expected operand '101' for second 50% bucket, got {conditions[1]['Condition']['Operands']}"
        report.success(
            "DistributeByPercentage uses NumberLessThan for ALL buckets",
            "Condition A: NumberLessThan '51', Condition B: NumberLessThan '101'"
        )
    except AssertionError as exc:
        report.error("Condition format incorrect", exc)
    except Exception as exc:
        report.error("Failed to verify conditions", exc)

    # Verify Errors array has NoMatchingCondition (auto-added by to_dict)
    try:
        errors = ab_split.transitions.get("Errors", [])
        error_types = [e["ErrorType"] for e in errors]
        assert "NoMatchingCondition" in error_types, \
            f"Expected NoMatchingCondition in Errors, got {error_types}"
        report.success("Errors array contains NoMatchingCondition (AWS spec)")
    except AssertionError as exc:
        report.error("Errors array incorrect", exc)
    except Exception as exc:
        report.error("Failed to verify Errors array", exc)

    # Verify convergence: both paths reach the same menu
    try:
        new_next = new_greeting.transitions.get("NextAction")
        old_next = old_greeting.transitions.get("NextAction")
        assert new_next == old_next == shared_menu.identifier, \
            "A/B paths do not converge to the same menu block"
        report.success(
            "Both A/B paths correctly converge to the same shared menu",
            "Diamond pattern: split -> A/B -> converge -> menu -> disconnect"
        )
    except AssertionError as exc:
        report.error("A/B paths do not converge", exc)
    except Exception as exc:
        report.error("Failed to verify path convergence", exc)

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
