"""
QA Test: Business Hours + Lambda Integration

Builds a flow that checks business hours, then invokes a Lambda for account
lookup if open, or plays a closed message and disconnects if closed:

  check_hours -> (True)  -> invoke_lambda -> compare result -> route -> disconnect
              -> (False) -> closed message -> disconnect

AWS Spec notes:
  - InvokeLambdaFunction does NOT support Conditions in Transitions.
    Lambda results are available at $.External.* and must be inspected
    via a separate Compare block.
  - Lambda timeout max is 8 seconds.

Tests:
  - check_hours() convenience method with .when() branching
  - invoke_lambda() convenience method (no conditions, only then/on_error)
  - flow.compare() to branch on Lambda result ($.External.lookupResult)
  - Correct Lambda -> Compare -> Branch pattern per AWS spec
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
import json
from qa_helpers import QAReport, print_report


def run_test() -> QAReport:
    report = QAReport("test_business_hours_lambda")

    # ----------------------------------------------------------------
    # Phase 1: Import verification
    # ----------------------------------------------------------------
    try:
        from cxblueprint import Flow
        report.success("Import Flow from cxblueprint")
    except Exception as e:
        report.error("Failed to import Flow from cxblueprint", e)
        return report

    # ----------------------------------------------------------------
    # Phase 2: Discoverability probes
    # ----------------------------------------------------------------
    flow_probe = Flow.build("Probe Flow")

    report.probe_method(flow_probe, "check_business_hours", "check_hours")
    report.probe_method(flow_probe, "hours_check", "check_hours")
    report.probe_method(flow_probe, "lambda_invoke", "invoke_lambda")
    report.probe_method(flow_probe, "call_lambda", "invoke_lambda")

    # ----------------------------------------------------------------
    # Phase 3: Build the flow
    # ----------------------------------------------------------------
    try:
        flow = Flow.build("Business Hours with Lambda Lookup")
        report.success("Flow.build() created flow instance")
    except Exception as e:
        report.error("Flow.build() failed", e)
        return report

    # Step 1: Check hours of operation
    try:
        hours_check = flow.check_hours(
            hours_of_operation_id="arn:aws:connect:us-east-1:123456789012:instance/inst-id/operating-hours/business-hours-id"
        )
        report.success(
            "check_hours() created CheckHoursOfOperation block",
            f"type={hours_check.type}",
        )
    except Exception as e:
        report.error("check_hours() failed", e)
        return report

    # Step 2: Open path - invoke Lambda for account lookup (max 8s timeout)
    try:
        lambda_lookup = flow.invoke_lambda(
            function_arn="arn:aws:lambda:us-east-1:123456789012:function:AccountLookup",
            timeout_seconds=8,
        )
        report.success(
            "invoke_lambda() created InvokeLambdaFunction block",
            f"type={lambda_lookup.type}, timeout={lambda_lookup.invocation_time_limit_seconds}",
        )
    except Exception as e:
        report.error("invoke_lambda() failed", e)
        return report

    # Step 3: Compare block to branch on Lambda result
    # Per AWS spec, Lambda does NOT support Conditions. Must use Compare block
    # to inspect $.External.* attributes set by the Lambda response.
    try:
        check_result = flow.compare("$.External.lookupResult")
        report.success(
            "Created Compare block for Lambda result routing",
            "Inspects $.External.lookupResult set by Lambda response",
        )
    except Exception as e:
        report.error("Failed to create Compare block for Lambda result", e)
        return report

    # Step 4: Lambda result routing messages
    try:
        found_msg = flow.play_prompt(
            "We found your account. Let me connect you with a specialist."
        )
        not_found_msg = flow.play_prompt(
            "We could not locate your account. Please hold for general assistance."
        )
        lambda_error_msg = flow.play_prompt(
            "We are experiencing technical difficulties. Please try again later."
        )
        report.success("Created Lambda result routing messages")
    except Exception as e:
        report.error("Failed to create Lambda result messages", e)
        return report

    # Step 5: Closed path
    try:
        closed_msg = flow.play_prompt(
            "We are currently closed. Our business hours are Monday through "
            "Friday, 9 AM to 5 PM Eastern. Please call back during business hours."
        )
        report.success("Created closed-hours message block")
    except Exception as e:
        report.error("Failed to create closed message", e)
        return report

    # Step 6: Disconnect blocks
    try:
        disconnect_found = flow.disconnect()
        disconnect_not_found = flow.disconnect()
        disconnect_lambda_err = flow.disconnect()
        disconnect_closed = flow.disconnect()
        disconnect_hours_err = flow.disconnect()
        report.success("Created 5 disconnect blocks")
    except Exception as e:
        report.error("Failed to create disconnect blocks", e)
        return report

    # ----------------------------------------------------------------
    # Phase 4: Wire the flow - Hours branching
    # ----------------------------------------------------------------
    try:
        hours_check.when("True", lambda_lookup) \
            .when("False", closed_msg) \
            .on_error("NoMatchingError", disconnect_hours_err)
        report.success(
            "Wired hours_check with .when('True'/..'False') and on_error",
        )
    except Exception as e:
        report.error("CheckHoursOfOperation branching failed", e)
        return report

    # ----------------------------------------------------------------
    # Phase 5: Wire Lambda -> Compare -> Branches (correct AWS pattern)
    # ----------------------------------------------------------------

    # Lambda only supports .then() and .on_error() — NO conditions
    try:
        lambda_lookup.then(check_result)
        lambda_lookup.on_error("NoMatchingError", lambda_error_msg)
        report.success(
            "Lambda wired: .then(check_result).on_error('NoMatchingError', error_msg)",
            "Lambda does NOT support Conditions per AWS spec - uses Compare block instead",
        )
    except Exception as e:
        report.error("Lambda wiring failed", e)
        return report

    # Compare block branches on the Lambda result
    try:
        check_result.when("found", found_msg) \
            .when("not_found", not_found_msg) \
            .on_error("NoMatchingCondition", lambda_error_msg) \
            .on_error("NoMatchingError", lambda_error_msg)
        report.success(
            "Compare block wired: .when('found'/.'not_found') + error handlers",
            "Pattern: Lambda -> Compare($.External.lookupResult) -> branch",
        )
    except Exception as e:
        report.error("Compare block branching failed", e)
        return report

    # Terminal wiring
    try:
        found_msg.then(disconnect_found)
        not_found_msg.then(disconnect_not_found)
        lambda_error_msg.then(disconnect_lambda_err)
        closed_msg.then(disconnect_closed)
        report.success("Wired all message blocks to their disconnect blocks")
    except Exception as e:
        report.error("Terminal wiring failed", e)
        return report

    # ----------------------------------------------------------------
    # Phase 6: Block count and validation
    # ----------------------------------------------------------------
    report.block_count = len(flow.blocks)
    report.success(
        f"Flow contains {report.block_count} blocks",
        f"Block types: {dict(flow._block_stats)}",
    )

    try:
        flow.validate()
        report.validation_passed = True
        report.success("flow.validate() passed with no issues")
    except Exception as e:
        report.error("flow.validate() raised an error", e)

    # ----------------------------------------------------------------
    # Phase 7: Compilation
    # ----------------------------------------------------------------
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "output",
        "test_business_hours_lambda.json",
    )
    try:
        flow.compile_to_file(output_path)
        report.compiled = True
        report.success(
            "compile_to_file() succeeded",
            f"Output: {output_path}",
        )
    except Exception as e:
        report.error("compile_to_file() failed", e)

    # Verify output JSON
    if report.compiled:
        try:
            with open(output_path, "r") as f:
                compiled_json = json.load(f)
            actions = compiled_json.get("Actions", [])
            action_types = [a.get("Type") for a in actions]
            report.success(
                f"Output JSON valid: {len(actions)} actions",
                f"Action types: {action_types}",
            )

            # Verify Lambda block has NO conditions (AWS spec)
            for action in actions:
                if action.get("Type") == "InvokeLambdaFunction":
                    transitions = action.get("Transitions", {})
                    has_conditions = "Conditions" in transitions
                    if has_conditions:
                        report.error(
                            "InvokeLambdaFunction has Conditions (WRONG per AWS spec)",
                        )
                    else:
                        report.success(
                            "InvokeLambdaFunction has no Conditions (correct per AWS spec)",
                            "Transitions: NextAction + Errors only",
                        )
                    # Verify timeout is <= 8
                    timeout = action.get("Parameters", {}).get("InvocationTimeLimitSeconds")
                    if timeout and int(timeout) <= 8:
                        report.success(f"Lambda timeout is {timeout}s (within 8s limit)")
                    else:
                        report.error(f"Lambda timeout {timeout}s exceeds 8s AWS limit")

            # Verify Compare block exists for Lambda result routing
            if "Compare" in action_types:
                report.success("Compare block present for Lambda result routing")
            else:
                report.error("Compare block MISSING (needed for Lambda result routing)")

        except Exception as e:
            report.error("Output JSON verification failed", e)

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
