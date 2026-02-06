"""
QA Test: Basic IVR - Simple Greeting + Menu + Disconnect

Builds a basic customer service IVR flow:
  welcome prompt -> press 1/2/3 menu -> department message -> disconnect

Tests:
  - All convenience methods work (play_prompt, get_input, disconnect, end_flow)
  - Block chaining with then()
  - Conditional branching with when()
  - Error handlers on get_input
  - Discoverability probes for intuitive method names
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
import json
import traceback
from qa_helpers import QAReport, print_report


def run_test() -> QAReport:
    report = QAReport("test_basic_ivr")

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

    report.probe_method(flow_probe, "say", "play_prompt")
    report.probe_method(flow_probe, "message", "play_prompt")
    report.probe_method(flow_probe, "prompt", "play_prompt")
    report.probe_method(flow_probe, "menu", "get_input")
    report.probe_method(flow_probe, "gather_digits", "get_input")
    report.probe_method(flow_probe, "hangup", "disconnect")
    report.probe_method(flow_probe, "end_call", "disconnect")

    # ----------------------------------------------------------------
    # Phase 3: Verify end_flow() works in an isolated mini-flow
    # ----------------------------------------------------------------
    try:
        mini = Flow.build("EndFlow Probe")
        p = mini.play_prompt("Ending now.")
        e = mini.end_flow()
        p.then(e)
        mini.validate()
        report.success(
            "end_flow() created EndFlowExecution block and validates correctly",
            f"type={e.type}",
        )
    except Exception as ex:
        report.error("end_flow() isolated test failed", ex)

    # ----------------------------------------------------------------
    # Phase 4: Build the IVR flow
    # ----------------------------------------------------------------
    try:
        flow = Flow.build("Basic Customer Service IVR")
        report.success("Flow.build() created flow instance")
    except Exception as e:
        report.error("Flow.build() failed", e)
        return report

    # Step 1: Welcome prompt
    try:
        welcome = flow.play_prompt(
            "Thank you for calling Acme Corp. Please listen carefully as our menu options have changed."
        )
        report.success(
            "play_prompt() created MessageParticipant block",
            f"type={welcome.type}, text length={len(welcome.text)}",
        )
    except Exception as e:
        report.error("play_prompt() failed", e)
        return report

    # Step 2: Main menu with get_input
    try:
        menu = flow.get_input(
            "Press 1 for Sales, Press 2 for Support, Press 3 for Billing.",
            timeout=8,
        )
        report.success(
            "get_input() created GetParticipantInput block",
            f"type={menu.type}, timeout={menu.input_time_limit_seconds}",
        )
    except Exception as e:
        report.error("get_input() failed", e)
        return report

    # Step 3: Department prompts for each option
    try:
        sales_msg = flow.play_prompt("You selected Sales. A representative will be with you shortly.")
        support_msg = flow.play_prompt("You selected Support. Please hold while we connect you.")
        billing_msg = flow.play_prompt("You selected Billing. Let us pull up your account.")
        invalid_msg = flow.play_prompt("Sorry, that was not a valid selection. Goodbye.")
        timeout_msg = flow.play_prompt("We did not receive your input. Goodbye.")
        report.success("Created 5 department/error message blocks via play_prompt()")
    except Exception as e:
        report.error("play_prompt() failed for department messages", e)
        return report

    # Step 4: Disconnect blocks (one per terminal path for clean canvas wiring)
    try:
        disconnect_sales = flow.disconnect()
        disconnect_support = flow.disconnect()
        disconnect_billing = flow.disconnect()
        disconnect_invalid = flow.disconnect()
        disconnect_timeout = flow.disconnect()
        disconnect_error = flow.disconnect()
        report.success("Created 6 disconnect blocks for clean canvas wiring")
    except Exception as e:
        report.error("disconnect() failed", e)
        return report

    # ----------------------------------------------------------------
    # Phase 5: Wire the flow together
    # ----------------------------------------------------------------

    # Welcome -> Menu
    try:
        welcome.then(menu)
        report.success(
            "then() wired welcome -> menu",
            f"NextAction set to {menu.identifier[:8]}...",
        )
    except Exception as e:
        report.error("then() chaining failed", e)
        return report

    # Menu conditions
    try:
        menu.when("1", sales_msg).when("2", support_msg).when("3", billing_msg)
        conditions = menu.transitions.get("Conditions", [])
        report.success(
            f"when() added {len(conditions)} conditions to menu",
            f"Values: {[c['Condition']['Operands'][0] for c in conditions]}",
        )
    except Exception as e:
        report.error("when() conditional branching failed", e)
        return report

    # Menu otherwise (default/fallback)
    try:
        menu.otherwise(invalid_msg)
        report.success(
            "otherwise() set default branch",
            f"NextAction -> {invalid_msg.identifier[:8]}...",
        )
    except Exception as e:
        report.error("otherwise() failed", e)

    # Menu error handlers (all 3 required)
    try:
        menu.on_error("InputTimeLimitExceeded", timeout_msg)
        menu.on_error("NoMatchingCondition", invalid_msg)
        menu.on_error("NoMatchingError", disconnect_error)
        errors = menu.transitions.get("Errors", [])
        report.success(
            f"on_error() added {len(errors)} error handlers",
            f"Types: {[e['ErrorType'] for e in errors]}",
        )
    except Exception as e:
        report.error("on_error() failed", e)
        return report

    # Terminal wiring: each message -> its disconnect
    try:
        sales_msg.then(disconnect_sales)
        support_msg.then(disconnect_support)
        billing_msg.then(disconnect_billing)
        invalid_msg.then(disconnect_invalid)
        timeout_msg.then(disconnect_timeout)
        report.success("Wired all department messages to their disconnect blocks")
    except Exception as e:
        report.error("Terminal wiring failed", e)
        return report

    # ----------------------------------------------------------------
    # Phase 6: Record block count
    # ----------------------------------------------------------------
    report.block_count = len(flow.blocks)
    report.success(
        f"Flow contains {report.block_count} blocks",
        f"Block types: {dict(flow._block_stats)}",
    )

    # ----------------------------------------------------------------
    # Phase 7: Validation
    # ----------------------------------------------------------------
    try:
        flow.validate()
        report.validation_passed = True
        report.success("flow.validate() passed with no issues")
    except Exception as e:
        report.error("flow.validate() raised an error", e)

    # ----------------------------------------------------------------
    # Phase 8: Compilation
    # ----------------------------------------------------------------
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "output",
        "test_basic_ivr.json",
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

    # Verify the output JSON structure
    if report.compiled:
        try:
            with open(output_path, "r") as f:
                compiled_json = json.load(f)
            actions = compiled_json.get("Actions", [])
            report.success(
                f"Output JSON is valid with {len(actions)} actions",
                f"StartAction: {compiled_json.get('StartAction', 'MISSING')[:8]}...",
            )
        except Exception as e:
            report.error("Output JSON verification failed", e)

    # ----------------------------------------------------------------
    # Phase 9: Friction notes
    # ----------------------------------------------------------------
    report.friction(
        "play_prompt() name may not be intuitive for chat-only flows",
        "Users building chat flows might look for send_message() or say().",
    )
    report.friction(
        "Must create separate disconnect blocks for clean canvas wiring",
        "A single shared disconnect causes crossed wires on the AWS canvas. "
        "Documentation should emphasize this pattern.",
    )

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
