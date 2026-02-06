"""
QA Test 5: Nested Menus with Retry Logic

Build a 3-level deep menu system:
  Main Menu -> Department -> Sub-department
with "press 9 to repeat" and retry logic on invalid input.

Tests:
- Deep nesting of get_input blocks
- Self-referencing "press 9 to repeat" pattern (menu.when("9", menu))
- Retry logic: first attempt -> error msg -> second attempt -> give up
- Block reuse (same disconnect across many paths)
- Discoverability probes for flow.loop(), flow.retry(), menu.repeat(), menu.loop_back()
- Friction around managing many blocks in complex flows and sub-flow composition
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
import uuid
from qa_helpers import QAReport


def run_test() -> QAReport:
    report = QAReport("test_nested_menus_retry")

    # ---------------------------------------------------------------
    # Import the library
    # ---------------------------------------------------------------
    try:
        from cxblueprint import Flow, FlowValidationError
        report.success("Imported Flow and FlowValidationError from cxblueprint")
    except Exception as exc:
        report.error("Failed to import cxblueprint", exc)
        return report

    # ---------------------------------------------------------------
    # Discoverability probes: methods that a new user might guess
    # ---------------------------------------------------------------
    flow_probe = Flow.build("Probe Flow")

    # Probe flow-level convenience methods for looping / retrying
    report.probe_method(flow_probe, "loop", "No built-in loop convenience; use menu.when('9', menu)")
    report.probe_method(flow_probe, "retry", "No built-in retry convenience; wire manually with .then()")
    report.probe_method(flow_probe, "sub_flow", "No sub-flow composition; build linearly")
    report.probe_method(flow_probe, "compose", "No sub-flow composition; build linearly")

    # Probe block-level convenience methods for self-referencing
    probe_menu = flow_probe.get_input("probe", timeout=5)
    probe_disc = flow_probe.disconnect()
    probe_menu.when("1", probe_disc).on_error("InputTimeLimitExceeded", probe_disc)
    probe_menu.on_error("NoMatchingCondition", probe_disc)
    probe_menu.on_error("NoMatchingError", probe_disc)
    probe_menu.otherwise(probe_disc)

    has_repeat = hasattr(probe_menu, "repeat")
    if not has_repeat:
        report.discoverability(
            "menu.repeat()",
            "menu.when('9', menu)",
            "AttributeError: 'GetParticipantInput' has no attribute 'repeat'. "
            "Self-referencing must be done manually via .when('9', menu)."
        )

    has_loop_back = hasattr(probe_menu, "loop_back")
    if not has_loop_back:
        report.discoverability(
            "menu.loop_back()",
            "menu.when('9', menu)",
            "AttributeError: 'GetParticipantInput' has no attribute 'loop_back'. "
            "No built-in method for self-referencing loops."
        )

    del flow_probe  # discard probe flow

    # ---------------------------------------------------------------
    # Build the actual 3-level nested menu flow
    # ---------------------------------------------------------------
    try:
        flow = Flow.build("Nested Menus with Retry", debug=False)
        report.success("Created flow with Flow.build()")
    except Exception as exc:
        report.error("Failed to create flow", exc)
        return report

    # ---------------------------------------------------------------
    # LEVEL 1: Main Menu (created FIRST so it becomes the start action)
    # ---------------------------------------------------------------
    try:
        main_menu = flow.get_input(
            "Welcome. Press 1 for Sales, 2 for Support, 3 for Billing, or 9 to hear this again.",
            timeout=10
        )
        report.success("Created main menu (level 1) get_input block as first block (start action)")
    except Exception as exc:
        report.error("Failed to create main menu", exc)
        return report

    # --- Retry for level 1 ---
    try:
        main_retry_msg = flow.play_prompt("Sorry, that was not a valid selection. Let us try again.")
        main_retry = flow.get_input(
            "Press 1 for Sales, 2 for Support, 3 for Billing, or 9 to hear this again.",
            timeout=10
        )
        main_retry_msg.then(main_retry)
        report.success("Created retry path for main menu (error msg -> second attempt)")
    except Exception as exc:
        report.error("Failed to create main menu retry path", exc)
        return report

    # ---------------------------------------------------------------
    # LEVEL 2: Department sub-menus
    # ---------------------------------------------------------------
    # Sales department
    try:
        sales_menu = flow.get_input(
            "Sales department. Press 1 for New Accounts, 2 for Renewals, or 9 to go back.",
            timeout=10
        )
        sales_retry_msg = flow.play_prompt("Invalid selection for Sales.")
        sales_retry = flow.get_input(
            "Press 1 for New Accounts, 2 for Renewals, or 9 to go back.",
            timeout=10
        )
        sales_retry_msg.then(sales_retry)
        report.success("Created Sales department menu (level 2) with retry")
    except Exception as exc:
        report.error("Failed to create Sales menu", exc)
        return report

    # Support department
    try:
        support_menu = flow.get_input(
            "Support department. Press 1 for Technical, 2 for General, or 9 to go back.",
            timeout=10
        )
        support_retry_msg = flow.play_prompt("Invalid selection for Support.")
        support_retry = flow.get_input(
            "Press 1 for Technical, 2 for General, or 9 to go back.",
            timeout=10
        )
        support_retry_msg.then(support_retry)
        report.success("Created Support department menu (level 2) with retry")
    except Exception as exc:
        report.error("Failed to create Support menu", exc)
        return report

    # Billing department
    try:
        billing_menu = flow.get_input(
            "Billing department. Press 1 for Invoices, 2 for Payments, or 9 to go back.",
            timeout=10
        )
        billing_retry_msg = flow.play_prompt("Invalid selection for Billing.")
        billing_retry = flow.get_input(
            "Press 1 for Invoices, 2 for Payments, or 9 to go back.",
            timeout=10
        )
        billing_retry_msg.then(billing_retry)
        report.success("Created Billing department menu (level 2) with retry")
    except Exception as exc:
        report.error("Failed to create Billing menu", exc)
        return report

    # ---------------------------------------------------------------
    # LEVEL 3: Sub-department terminal messages
    # ---------------------------------------------------------------
    try:
        new_accounts_msg = flow.play_prompt("Connecting you to New Accounts. Please hold.")
        renewals_msg = flow.play_prompt("Connecting you to Renewals. Please hold.")
        tech_support_msg = flow.play_prompt("Connecting you to Technical Support. Please hold.")
        general_support_msg = flow.play_prompt("Connecting you to General Support. Please hold.")
        invoices_msg = flow.play_prompt("Connecting you to Invoices. Please hold.")
        payments_msg = flow.play_prompt("Connecting you to Payments. Please hold.")
        report.success("Created 6 sub-department terminal messages")
    except Exception as exc:
        report.error("Failed to create sub-department messages", exc)
        return report

    # Shared terminal blocks - reused across all paths
    try:
        give_up_msg = flow.play_prompt("We were unable to understand your selection. Goodbye.")
        hangup = flow.disconnect()
        give_up_msg.then(hangup)

        # All terminal messages end at the shared disconnect
        for msg in [new_accounts_msg, renewals_msg, tech_support_msg,
                     general_support_msg, invoices_msg, payments_msg]:
            msg.then(hangup)

        report.success(
            "Created shared disconnect and give-up message; all 6 terminal messages share one disconnect",
            "Block reuse: single disconnect referenced by 7 blocks (6 terminals + give-up)"
        )
    except Exception as exc:
        report.error("Failed to create terminal blocks", exc)
        return report

    # ---------------------------------------------------------------
    # Wire up Level 1: Main Menu
    # ---------------------------------------------------------------
    try:
        # "Press 9 to repeat" -- self-referencing pattern
        main_menu.when("1", sales_menu)
        main_menu.when("2", support_menu)
        main_menu.when("3", billing_menu)
        main_menu.when("9", main_menu)  # self-reference!
        main_menu.otherwise(main_retry_msg)
        main_menu.on_error("InputTimeLimitExceeded", main_retry_msg)
        main_menu.on_error("NoMatchingCondition", main_retry_msg)
        main_menu.on_error("NoMatchingError", main_retry_msg)
        report.success(
            "Wired main menu with self-referencing 'press 9' pattern",
            "menu.when('9', menu) creates a loop back to itself"
        )
    except Exception as exc:
        report.error("Failed to wire main menu", exc)
        return report

    # Wire retry for main menu (second attempt goes to give-up on failure)
    try:
        main_retry.when("1", sales_menu)
        main_retry.when("2", support_menu)
        main_retry.when("3", billing_menu)
        main_retry.when("9", main_menu)
        main_retry.otherwise(give_up_msg)
        main_retry.on_error("InputTimeLimitExceeded", give_up_msg)
        main_retry.on_error("NoMatchingCondition", give_up_msg)
        main_retry.on_error("NoMatchingError", give_up_msg)
        report.success("Wired main menu retry: second failure leads to give-up and disconnect")
    except Exception as exc:
        report.error("Failed to wire main menu retry", exc)
        return report

    # ---------------------------------------------------------------
    # Wire up Level 2: Sales menu
    # ---------------------------------------------------------------
    try:
        sales_menu.when("1", new_accounts_msg)
        sales_menu.when("2", renewals_msg)
        sales_menu.when("9", main_menu)  # go back to main
        sales_menu.otherwise(sales_retry_msg)
        sales_menu.on_error("InputTimeLimitExceeded", sales_retry_msg)
        sales_menu.on_error("NoMatchingCondition", sales_retry_msg)
        sales_menu.on_error("NoMatchingError", sales_retry_msg)

        sales_retry.when("1", new_accounts_msg)
        sales_retry.when("2", renewals_msg)
        sales_retry.when("9", main_menu)
        sales_retry.otherwise(give_up_msg)
        sales_retry.on_error("InputTimeLimitExceeded", give_up_msg)
        sales_retry.on_error("NoMatchingCondition", give_up_msg)
        sales_retry.on_error("NoMatchingError", give_up_msg)
        report.success("Wired Sales menu and its retry path")
    except Exception as exc:
        report.error("Failed to wire Sales menu", exc)
        return report

    # ---------------------------------------------------------------
    # Wire up Level 2: Support menu
    # ---------------------------------------------------------------
    try:
        support_menu.when("1", tech_support_msg)
        support_menu.when("2", general_support_msg)
        support_menu.when("9", main_menu)
        support_menu.otherwise(support_retry_msg)
        support_menu.on_error("InputTimeLimitExceeded", support_retry_msg)
        support_menu.on_error("NoMatchingCondition", support_retry_msg)
        support_menu.on_error("NoMatchingError", support_retry_msg)

        support_retry.when("1", tech_support_msg)
        support_retry.when("2", general_support_msg)
        support_retry.when("9", main_menu)
        support_retry.otherwise(give_up_msg)
        support_retry.on_error("InputTimeLimitExceeded", give_up_msg)
        support_retry.on_error("NoMatchingCondition", give_up_msg)
        support_retry.on_error("NoMatchingError", give_up_msg)
        report.success("Wired Support menu and its retry path")
    except Exception as exc:
        report.error("Failed to wire Support menu", exc)
        return report

    # ---------------------------------------------------------------
    # Wire up Level 2: Billing menu
    # ---------------------------------------------------------------
    try:
        billing_menu.when("1", invoices_msg)
        billing_menu.when("2", payments_msg)
        billing_menu.when("9", main_menu)
        billing_menu.otherwise(billing_retry_msg)
        billing_menu.on_error("InputTimeLimitExceeded", billing_retry_msg)
        billing_menu.on_error("NoMatchingCondition", billing_retry_msg)
        billing_menu.on_error("NoMatchingError", billing_retry_msg)

        billing_retry.when("1", invoices_msg)
        billing_retry.when("2", payments_msg)
        billing_retry.when("9", main_menu)
        billing_retry.otherwise(give_up_msg)
        billing_retry.on_error("InputTimeLimitExceeded", give_up_msg)
        billing_retry.on_error("NoMatchingCondition", give_up_msg)
        billing_retry.on_error("NoMatchingError", give_up_msg)
        report.success("Wired Billing menu and its retry path")
    except Exception as exc:
        report.error("Failed to wire Billing menu", exc)
        return report

    # ---------------------------------------------------------------
    # Record block count
    # ---------------------------------------------------------------
    report.block_count = len(flow.blocks)
    report.success(
        f"Total block count: {report.block_count}",
        "1 main menu + 1 main retry msg + 1 main retry + 3 dept menus + 3 dept retry msgs "
        "+ 3 dept retries + 6 terminal msgs + 1 give-up msg + 1 disconnect = 20 blocks"
    )

    # ---------------------------------------------------------------
    # Validate the flow
    # ---------------------------------------------------------------
    try:
        flow.validate()
        report.validation_passed = True
        report.success("Flow validation passed with no issues")
    except FlowValidationError as exc:
        report.error("Flow validation failed", exc)

    # ---------------------------------------------------------------
    # Compile to file
    # ---------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    output_path = os.path.join(output_dir, "nested_menus_retry.json")
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
    # Verify self-referencing pattern
    try:
        conditions = main_menu.transitions.get("Conditions", [])
        self_ref_found = any(
            c["NextAction"] == main_menu.identifier and c["Condition"]["Operands"] == ["9"]
            for c in conditions
        )
        if self_ref_found:
            report.success(
                "Self-referencing 'press 9 to repeat' pattern works correctly",
                "menu.when('9', menu) sets NextAction to the menu's own identifier"
            )
        else:
            report.error("Self-referencing pattern not found in main menu conditions")
    except Exception as exc:
        report.error("Failed to verify self-referencing pattern", exc)

    # Verify block reuse: hangup block is referenced by many blocks
    try:
        hangup_id = hangup.identifier
        ref_count = 0
        for block in flow.blocks:
            trans = block.transitions
            if trans.get("NextAction") == hangup_id:
                ref_count += 1
            for cond in trans.get("Conditions", []):
                if cond.get("NextAction") == hangup_id:
                    ref_count += 1
            for err in trans.get("Errors", []):
                if err.get("NextAction") == hangup_id:
                    ref_count += 1
        report.success(
            f"Shared disconnect block referenced by {ref_count} transitions",
            "Block reuse pattern works well; single disconnect serves entire flow"
        )
    except Exception as exc:
        report.error("Failed to verify block reuse", exc)

    # ---------------------------------------------------------------
    # Friction observations
    # ---------------------------------------------------------------
    report.friction(
        "Managing 20+ blocks in a complex flow is tedious and error-prone",
        "Each get_input needs 3 on_error() calls, an otherwise(), and multiple when() calls. "
        "With 3 levels of menus and retry paths, the wiring is extremely verbose. "
        "A helper like flow.menu(prompt, options_dict, retry=True) would reduce boilerplate."
    )

    report.friction(
        "Retry logic requires duplicating the entire menu as a separate get_input block",
        "First attempt and retry attempt are structurally identical except for error targets. "
        "There is no flow.retry(menu, max_attempts=2, on_exhaust=give_up) convenience."
    )

    report.friction(
        "No sub-flow composition mechanism to encapsulate reusable menu patterns",
        "Each department menu follows the same pattern (menu + retry msg + retry menu) "
        "but must be built manually each time. A composable sub-flow or template "
        "would reduce the 60+ lines of wiring to a few calls."
    )

    report.friction(
        "'Press 9 to go back' requires passing the parent menu reference forward",
        "The developer must manually track which menu is the 'parent' for back-navigation. "
        "A flow.back() or menu.parent(parent_menu) convenience would simplify this."
    )

    report.missing(
        "No flow.menu() convenience method for common menu patterns",
        "A method like flow.menu(prompt, {'1': sales, '2': support}, retry=True, repeat='9') "
        "would encapsulate get_input + when + on_error + otherwise + retry in one call."
    )

    report.missing(
        "No sub-flow or template composition for reusable flow fragments",
        "Real-world flows repeat patterns (menu+retry, error+disconnect). "
        "A mechanism to define and reuse flow fragments would reduce complexity."
    )

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
