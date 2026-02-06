"""
QA Test 8: Callback Request with Wait

Scenario: greeting -> ask if they want callback -> collect phone number input
           -> update callback number -> create callback -> wait -> confirmation -> disconnect

Tests:
- CreateCallbackContact via flow.add() (no convenience method)
- Wait via flow.add() (no convenience method)
- UpdateContactCallbackNumber via flow.add()
- Discoverability probes for intuitive method names
- Friction around callback block parameters and missing convenience methods
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import uuid
import json
import os
import tempfile

from qa_helpers import QAReport


def run_test() -> QAReport:
    report = QAReport("test_callback_flow")

    # ------------------------------------------------------------------ #
    # 1. Imports
    # ------------------------------------------------------------------ #
    try:
        from cxblueprint import Flow
        from cxblueprint.blocks.interactions import CreateCallbackContact
        from cxblueprint.blocks.flow_control_actions import Wait
        from cxblueprint.blocks.contact_actions import UpdateContactCallbackNumber
        report.success(
            "All callback-related block imports succeeded",
            "CreateCallbackContact, Wait, UpdateContactCallbackNumber imported from their sub-packages",
        )
    except ImportError as exc:
        report.error("Failed to import callback-related blocks", exc)
        return report

    # ------------------------------------------------------------------ #
    # 2. Discoverability probes -- intuitive method names on Flow
    # ------------------------------------------------------------------ #
    flow_probe = Flow.build("Callback Probe", debug=False)

    # Callback convenience methods
    report.probe_method(flow_probe, "callback", "add(CreateCallbackContact(...))")
    report.probe_method(flow_probe, "create_callback", "add(CreateCallbackContact(...))")
    report.probe_method(flow_probe, "request_callback", "add(CreateCallbackContact(...))")

    # Wait convenience methods
    report.probe_method(flow_probe, "wait", "add(Wait(...))")
    report.probe_method(flow_probe, "pause", "add(Wait(...))")
    report.probe_method(flow_probe, "hold", "add(Wait(...))")

    report.friction(
        "No convenience method for CreateCallbackContact",
        "Callbacks are a core Connect feature. A flow.callback() or "
        "flow.create_callback() method would greatly improve discoverability. "
        "Users must manually import and construct the block.",
    )
    report.friction(
        "No convenience method for Wait block",
        "flow.wait(seconds=30) would be much more intuitive than importing Wait "
        "and manually constructing it with flow.add().",
    )

    # ------------------------------------------------------------------ #
    # 3. Build the callback request flow
    # ------------------------------------------------------------------ #
    try:
        flow = Flow.build("Callback Request Flow", debug=False)

        # -- greeting --
        greeting = flow.play_prompt(
            "Thank you for calling. We are experiencing high call volumes."
        )
        report.success("Created greeting prompt block")

        # -- ask if they want a callback --
        error_handler = flow.disconnect()

        ask_callback = flow.get_input(
            "Would you like us to call you back? Press 1 for yes, 2 for no.",
            timeout=5,
        )
        greeting.then(ask_callback)
        report.success("Created callback question input block")

        # -- "no" path: just disconnect --
        no_thanks = flow.play_prompt("No problem. Please stay on the line.")
        no_disconnect = flow.disconnect()
        no_thanks.then(no_disconnect)

        # -- "yes" path: collect phone number --
        collect_phone = flow.get_input(
            "Please enter your 10-digit phone number followed by the pound key.",
            timeout=15,
        )
        report.success("Created phone number collection input block")

        # Wire the ask_callback conditions
        ask_callback.when("1", collect_phone)
        ask_callback.when("2", no_thanks)
        ask_callback.otherwise(error_handler)
        ask_callback.on_error("InputTimeLimitExceeded", error_handler)
        ask_callback.on_error("NoMatchingCondition", error_handler)
        ask_callback.on_error("NoMatchingError", error_handler)
        report.success("Wired ask_callback conditions and error handlers")

    except Exception as exc:
        report.error("Failed to build initial flow structure", exc)
        return report

    # ------------------------------------------------------------------ #
    # 4. UpdateContactCallbackNumber via flow.add()
    # ------------------------------------------------------------------ #
    try:
        update_cb_number = UpdateContactCallbackNumber(
            identifier=str(uuid.uuid4()),
        )
        flow.add(update_cb_number)
        report.success(
            "Added UpdateContactCallbackNumber via flow.add()",
            "Block accepts no extra constructor arguments beyond base FlowBlock fields; "
            "the actual phone number is presumably set via contact attributes or external reference.",
        )
        report.friction(
            "UpdateContactCallbackNumber constructor has no phone_number parameter",
            "The block is a bare FlowBlock subclass with no typed fields for the callback number. "
            "Users must manually construct parameters={...} or rely on prior contact attributes. "
            "A phone_number= kwarg would clarify intent.",
        )
    except Exception as exc:
        report.error("Failed to create UpdateContactCallbackNumber", exc)

    # ------------------------------------------------------------------ #
    # 5. CreateCallbackContact via flow.add()
    # ------------------------------------------------------------------ #
    try:
        create_callback = CreateCallbackContact(
            identifier=str(uuid.uuid4()),
        )
        flow.add(create_callback)
        report.success(
            "Added CreateCallbackContact via flow.add()",
            "Block is a minimal FlowBlock subclass with no extra typed fields.",
        )
        report.friction(
            "CreateCallbackContact has no typed parameters (queue, delay, etc.)",
            "In AWS Connect, CreateCallbackContact accepts QueueId, CallbackNumber, "
            "InitialContactId, and other parameters. The CxBlueprint block exposes none "
            "of these as typed constructor arguments. Users must know the raw AWS parameter "
            "names and pass them via parameters={...}.",
        )
    except Exception as exc:
        report.error("Failed to create CreateCallbackContact", exc)

    # ------------------------------------------------------------------ #
    # 6. Wait block via flow.add()
    # ------------------------------------------------------------------ #
    try:
        wait_block = Wait(
            identifier=str(uuid.uuid4()),
            time_limit_seconds=5,
        )
        flow.add(wait_block)
        report.success(
            "Added Wait block via flow.add() with time_limit_seconds=5",
            f"Wait block repr: {wait_block!r}",
        )
    except Exception as exc:
        report.error("Failed to create Wait block", exc)

    # -- confirmation and disconnect --
    try:
        confirmation = flow.play_prompt(
            "Your callback has been scheduled. You will receive a call shortly. Goodbye."
        )
        final_disconnect = flow.disconnect()

        # Wire the "yes" path end-to-end
        collect_phone.then(update_cb_number)

        # Wire collect_phone error handlers
        collect_phone.on_error("InputTimeLimitExceeded", error_handler)
        collect_phone.on_error("NoMatchingCondition", error_handler)
        collect_phone.on_error("NoMatchingError", error_handler)

        update_cb_number.then(create_callback)
        create_callback.then(wait_block)
        wait_block.then(confirmation)
        confirmation.then(final_disconnect)
        report.success("Wired complete callback flow path: phone -> update_number -> create_callback -> wait -> confirm -> disconnect")

    except Exception as exc:
        report.error("Failed to wire callback flow path", exc)

    # ------------------------------------------------------------------ #
    # 7. Validate and compile
    # ------------------------------------------------------------------ #
    report.block_count = len(flow.blocks)

    try:
        flow.validate()
        report.validation_passed = True
        report.success(
            "Flow validation passed",
            f"Total blocks: {report.block_count}",
        )
    except Exception as exc:
        report.error("Flow validation failed", exc)

    output_path = os.path.join(
        tempfile.gettempdir(), "qa_test_callback_flow.json"
    )
    try:
        flow.compile_to_file(output_path)
        report.compiled = True
        report.success(
            "Flow compiled to file successfully",
            f"Output: {output_path}",
        )

        # Verify JSON structure
        with open(output_path, "r") as f:
            compiled = json.load(f)

        action_types = [a["Type"] for a in compiled["Actions"]]
        if "CreateCallbackContact" in action_types:
            report.success("CreateCallbackContact present in compiled output")
        else:
            report.error("CreateCallbackContact missing from compiled output")

        if "Wait" in action_types:
            report.success("Wait block present in compiled output")
        else:
            report.error("Wait block missing from compiled output")

        if "UpdateContactCallbackNumber" in action_types:
            report.success("UpdateContactCallbackNumber present in compiled output")
        else:
            report.error("UpdateContactCallbackNumber missing from compiled output")

        report.success(
            f"Compiled JSON has {len(compiled['Actions'])} actions",
            f"Action types: {action_types}",
        )

    except Exception as exc:
        report.error("Flow compilation to file failed", exc)

    # ------------------------------------------------------------------ #
    # 8. Summary friction notes
    # ------------------------------------------------------------------ #
    report.missing(
        "flow.callback() convenience method",
        "CreateCallbackContact is one of the most common Amazon Connect patterns. "
        "A convenience method like flow.callback(queue_id=..., delay_seconds=...) "
        "would dramatically improve the developer experience.",
    )
    report.missing(
        "flow.wait() convenience method",
        "Wait blocks are commonly paired with callbacks and queue holds. "
        "A simple flow.wait(seconds=30) would be consistent with the existing "
        "convenience method patterns (flow.play_prompt, flow.disconnect, etc.).",
    )
    report.missing(
        "Typed parameters on CreateCallbackContact",
        "queue_id, callback_number, initial_contact_id, and delay_seconds "
        "should be first-class constructor parameters, not raw dict entries.",
    )

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
