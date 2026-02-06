"""
QA Test: Queue Transfer - Department Routing with Queue Transfer

Builds a flow that routes callers to different queues based on menu selection:
  welcome -> menu (press 1/2) -> set target queue -> transfer to queue -> disconnect

Tests:
  - TransferContactToQueue via flow.add() (no convenience method)
  - UpdateContactTargetQueue via flow.add()
  - Import discovery for blocks not covered by convenience methods
  - uuid import requirement for block identifiers
  - Discoverability probes for intuitive queue-related method names
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
import json
import traceback
from qa_helpers import QAReport, print_report


def run_test() -> QAReport:
    report = QAReport("test_queue_transfer")

    # ----------------------------------------------------------------
    # Phase 1: Import verification
    # ----------------------------------------------------------------
    try:
        from cxblueprint import Flow
        report.success("Import Flow from cxblueprint")
    except Exception as e:
        report.error("Failed to import Flow from cxblueprint", e)
        return report

    # Import uuid -- required for blocks added via flow.add()
    try:
        import uuid
        report.success("Import uuid (required for flow.add() blocks)")
        report.friction(
            "Must import uuid separately for flow.add() blocks",
            "Convenience methods auto-generate UUIDs, but flow.add() blocks "
            "require the caller to provide str(uuid.uuid4()). This is easy to "
            "forget and adds boilerplate.",
        )
    except Exception as e:
        report.error("Failed to import uuid", e)
        return report

    # Import TransferContactToQueue and UpdateContactTargetQueue
    try:
        from cxblueprint.blocks.contact_actions import (
            TransferContactToQueue,
            UpdateContactTargetQueue,
        )
        report.success(
            "Import TransferContactToQueue, UpdateContactTargetQueue from "
            "cxblueprint.blocks.contact_actions"
        )
    except Exception as e:
        report.error("Failed to import queue blocks from cxblueprint.blocks.contact_actions", e)
        return report

    # Note the import path friction
    report.friction(
        "Import path cxblueprint.blocks.contact_actions is deep and not obvious",
        "A new user would need to read docs or source to discover "
        "cxblueprint.blocks.contact_actions.TransferContactToQueue. "
        "Consider re-exporting common blocks from the top-level cxblueprint module.",
    )

    # ----------------------------------------------------------------
    # Phase 2: Discoverability probes
    # ----------------------------------------------------------------
    flow_probe = Flow.build("Probe Flow")

    report.probe_method(flow_probe, "transfer_to_queue", "add(TransferContactToQueue(...))")
    report.probe_method(flow_probe, "queue_transfer", "add(TransferContactToQueue(...))")
    report.probe_method(flow_probe, "set_queue", "add(UpdateContactTargetQueue(...))")

    report.missing(
        "No convenience method for transfer_to_queue()",
        "TransferContactToQueue is one of the most common blocks in contact "
        "center flows. A flow.transfer_to_queue() convenience method would "
        "significantly improve usability.",
    )
    report.missing(
        "No convenience method for set_queue() / update_target_queue()",
        "UpdateContactTargetQueue is typically used right before "
        "TransferContactToQueue. A flow.set_queue(queue_id) method would "
        "reduce boilerplate.",
    )

    # ----------------------------------------------------------------
    # Phase 3: Build the queue transfer flow
    # ----------------------------------------------------------------
    try:
        flow = Flow.build("Department Queue Router")
        report.success("Flow.build() created flow instance")
    except Exception as e:
        report.error("Flow.build() failed", e)
        return report

    # Welcome message
    try:
        welcome = flow.play_prompt(
            "Welcome to Acme Corp. We will route you to the right department."
        )
        report.success("play_prompt() created welcome block")
    except Exception as e:
        report.error("play_prompt() failed", e)
        return report

    # Menu: press 1 for Sales, 2 for Support
    try:
        menu = flow.get_input(
            "Press 1 for Sales or Press 2 for Technical Support.",
            timeout=10,
        )
        report.success("get_input() created menu block")
    except Exception as e:
        report.error("get_input() failed", e)
        return report

    # Sales queue path: UpdateContactTargetQueue -> TransferContactToQueue
    try:
        sales_queue_id = "arn:aws:connect:us-east-1:123456789012:instance/inst-id/queue/sales-queue-id"
        set_sales_queue = flow.add(
            UpdateContactTargetQueue(
                identifier=str(uuid.uuid4()),
                parameters={"QueueId": sales_queue_id},
            )
        )
        report.success(
            "flow.add(UpdateContactTargetQueue) registered sales queue block",
            f"type={set_sales_queue.type}",
        )
    except Exception as e:
        report.error("flow.add(UpdateContactTargetQueue) failed for sales queue", e)
        return report

    try:
        transfer_sales = flow.add(
            TransferContactToQueue(
                identifier=str(uuid.uuid4()),
            )
        )
        report.success(
            "flow.add(TransferContactToQueue) registered sales transfer block",
            f"type={transfer_sales.type}",
        )
    except Exception as e:
        report.error("flow.add(TransferContactToQueue) failed for sales", e)
        return report

    # Support queue path: UpdateContactTargetQueue -> TransferContactToQueue
    try:
        support_queue_id = "arn:aws:connect:us-east-1:123456789012:instance/inst-id/queue/support-queue-id"
        set_support_queue = flow.add(
            UpdateContactTargetQueue(
                identifier=str(uuid.uuid4()),
                parameters={"QueueId": support_queue_id},
            )
        )
        transfer_support = flow.add(
            TransferContactToQueue(
                identifier=str(uuid.uuid4()),
            )
        )
        report.success("Created support queue path (UpdateTargetQueue + TransferToQueue)")
    except Exception as e:
        report.error("Failed to create support queue path", e)
        return report

    # Error / fallback path
    try:
        error_msg = flow.play_prompt("Sorry, that was not a valid option. Please try again later.")
        disconnect_error = flow.disconnect()
        disconnect_transfer_err_sales = flow.disconnect()
        disconnect_transfer_err_support = flow.disconnect()
        report.success("Created error/fallback blocks")
    except Exception as e:
        report.error("Failed to create error blocks", e)
        return report

    # ----------------------------------------------------------------
    # Phase 4: Wire the flow
    # ----------------------------------------------------------------
    try:
        # Welcome -> Menu
        welcome.then(menu)

        # Menu branches
        menu.when("1", set_sales_queue).when("2", set_support_queue)
        menu.otherwise(error_msg)
        menu.on_error("InputTimeLimitExceeded", error_msg)
        menu.on_error("NoMatchingCondition", error_msg)
        menu.on_error("NoMatchingError", error_msg)

        # Sales path: set queue -> transfer
        set_sales_queue.then(transfer_sales)
        set_sales_queue.on_error("NoMatchingError", disconnect_transfer_err_sales)

        # Support path: set queue -> transfer
        set_support_queue.then(transfer_support)
        set_support_queue.on_error("NoMatchingError", disconnect_transfer_err_support)

        # Transfer error handling
        transfer_sales.on_error("NoMatchingError", disconnect_transfer_err_sales)
        transfer_support.on_error("NoMatchingError", disconnect_transfer_err_support)

        # Error path terminal
        error_msg.then(disconnect_error)

        report.success("Flow wiring completed: welcome -> menu -> queue paths")
    except Exception as e:
        report.error("Flow wiring failed", e)
        return report

    # ----------------------------------------------------------------
    # Phase 5: Friction analysis around flow.add() pattern
    # ----------------------------------------------------------------
    report.friction(
        "flow.add() requires constructing blocks manually with UUIDs",
        "Compare: flow.play_prompt('text') vs "
        "flow.add(TransferContactToQueue(identifier=str(uuid.uuid4()), "
        "parameters={...})). The manual approach is verbose and error-prone.",
    )
    report.friction(
        "No typed parameters for UpdateContactTargetQueue",
        "UpdateContactTargetQueue accepts raw dict parameters. Users must know "
        "the AWS parameter key names like 'QueueId'. A typed constructor with "
        "queue_id= would be safer.",
    )
    report.friction(
        "TransferContactToQueue has no parameters for queue hold music or priority",
        "Common queue transfer configuration (hold prompt, priority, timeout) "
        "requires separate blocks. A convenience method could bundle these.",
    )

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
        "test_queue_transfer.json",
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
            # Verify our queue blocks are present
            if "TransferContactToQueue" in action_types:
                report.success("TransferContactToQueue block present in compiled output")
            else:
                report.error("TransferContactToQueue block MISSING from compiled output")
            if "UpdateContactTargetQueue" in action_types:
                report.success("UpdateContactTargetQueue block present in compiled output")
            else:
                report.error("UpdateContactTargetQueue block MISSING from compiled output")
        except Exception as e:
            report.error("Output JSON verification failed", e)

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
