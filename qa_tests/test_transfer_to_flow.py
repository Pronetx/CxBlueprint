"""
QA Test: Transfer to Flow - Cross-Flow References

Builds two flows in the same Python file:
  1. Main flow: welcome -> transfer to greeting flow (using template placeholder)
  2. Greeting flow: greeting message -> disconnect

Tests:
  - flow.transfer_to_flow() convenience method
  - Template placeholder pattern for cross-flow ARN references (${FLOW_ARN})
  - Building multiple flows in one file
  - Both flows compile independently
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
import json
from qa_helpers import QAReport, print_report


def run_test() -> QAReport:
    report = QAReport("test_transfer_to_flow")

    # ----------------------------------------------------------------
    # Phase 1: Import verification
    # ----------------------------------------------------------------
    try:
        from cxblueprint import Flow
        report.success("Imported Flow from cxblueprint")
    except Exception as e:
        report.error("Failed to import Flow", e)
        return report

    # ----------------------------------------------------------------
    # Phase 2: Build the Greeting Flow (target of transfer)
    # ----------------------------------------------------------------
    try:
        greeting_flow = Flow.build("Greeting Sub-Flow")
        report.success("Created greeting_flow with Flow.build()")
    except Exception as e:
        report.error("Failed to create greeting flow", e)
        return report

    try:
        greeting_msg = greeting_flow.play_prompt(
            "Thank you for being transferred! A specialist will be with you shortly."
        )
        greeting_dc = greeting_flow.disconnect()
        greeting_msg.then(greeting_dc)
        report.success("Built greeting flow: message -> disconnect")
    except Exception as e:
        report.error("Failed to build greeting flow", e)
        return report

    # ----------------------------------------------------------------
    # Phase 3: Build the Main Flow (source of transfer)
    # ----------------------------------------------------------------
    try:
        main_flow = Flow.build("Main Flow with Transfer")
        report.success("Created main_flow with Flow.build()")
    except Exception as e:
        report.error("Failed to create main flow", e)
        return report

    try:
        welcome = main_flow.play_prompt("Welcome to our service.")
        report.success("Created welcome prompt in main flow")
    except Exception as e:
        report.error("Failed to create welcome prompt", e)
        return report

    # Use template placeholder for the greeting flow ARN
    try:
        transfer = main_flow.transfer_to_flow("${GREETING_FLOW_ARN}")
        report.success(
            "Created transfer_to_flow('${GREETING_FLOW_ARN}')",
            "Uses template placeholder resolved at deploy time via Terraform/CDK",
        )
    except Exception as e:
        report.error("transfer_to_flow() failed", e)
        return report

    # Also add a fallback disconnect in case transfer fails
    try:
        error_msg = main_flow.play_prompt(
            "We are unable to transfer your call. Please try again later."
        )
        error_dc = main_flow.disconnect()
        error_msg.then(error_dc)
        report.success("Created error path: error_msg -> disconnect")
    except Exception as e:
        report.error("Failed to create error path", e)
        return report

    # Wire main flow
    try:
        welcome.then(transfer)
        transfer.on_error("NoMatchingError", error_msg)
        report.success("Wired main flow: welcome -> transfer -> (error) -> disconnect")
    except Exception as e:
        report.error("Failed to wire main flow", e)
        return report

    # ----------------------------------------------------------------
    # Phase 4: Validate and compile both flows
    # ----------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    # Compile greeting flow
    try:
        greeting_flow.validate()
        greeting_path = os.path.join(output_dir, "greeting_flow.json")
        greeting_flow.compile_to_file(greeting_path)
        report.success(f"Greeting flow compiled to {greeting_path}")
    except Exception as e:
        report.error("Greeting flow compilation failed", e)

    # Compile main flow
    try:
        main_flow.validate()
        report.validation_passed = True
        main_path = os.path.join(output_dir, "main_flow_with_transfer.json")
        main_flow.compile_to_file(main_path)
        report.compiled = True
        report.success(f"Main flow compiled to {main_path}")
    except Exception as e:
        report.error("Main flow compilation failed", e)

    # ----------------------------------------------------------------
    # Phase 5: Verify output JSON
    # ----------------------------------------------------------------
    report.block_count = len(main_flow.blocks)
    report.success(
        f"Main flow contains {report.block_count} blocks",
        f"Block types: {dict(main_flow._block_stats)}",
    )

    if report.compiled:
        try:
            with open(main_path, "r") as f:
                compiled = json.load(f)
            actions = compiled.get("Actions", [])
            action_types = [a.get("Type") for a in actions]

            # Verify TransferToFlow block exists
            if "TransferToFlow" in action_types:
                report.success("TransferToFlow block present in compiled output")
            else:
                report.error("TransferToFlow block MISSING from compiled output")

            # Verify the transfer block has the placeholder ARN
            for action in actions:
                if action.get("Type") == "TransferToFlow":
                    flow_id = action.get("Parameters", {}).get("ContactFlowId", "")
                    if "${GREETING_FLOW_ARN}" in flow_id:
                        report.success(
                            "TransferToFlow contains template placeholder",
                            f"ContactFlowId: {flow_id}",
                        )
                    else:
                        report.error(
                            f"TransferToFlow ContactFlowId missing placeholder: {flow_id}"
                        )
        except Exception as e:
            report.error("Output JSON verification failed", e)

    return report


if __name__ == "__main__":
    print_report(run_test())
