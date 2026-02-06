"""
QA Test 7: Set Attributes + Conditional Branch with Compare

Build: collect input -> set attribute based on selection -> use Compare block
       to branch on attribute value -> different handling per branch -> disconnect.

Tests:
- update_attributes() convenience method
- Compare block via flow.add() (no convenience method)
- Whether Compare block can read contact attributes for conditional routing
- Compare block branching (requires manual transitions manipulation)
- Discoverability probes for flow.compare(), flow.branch(), flow.condition(),
  flow.if_then(), flow.check_attribute()
- Friction around: no way to branch on attributes without Compare block,
  Compare block not documented in MODEL_INSTRUCTIONS
"""

import sys
sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

import os
from qa_helpers import QAReport


def run_test() -> QAReport:
    report = QAReport("test_attributes_and_compare")

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
    # Discoverability probes: convenience methods a user might expect
    # ---------------------------------------------------------------
    probe_flow = Flow.build("Probe Flow")

    report.probe_method(probe_flow, "compare", "flow.compare() exists")
    report.probe_method(probe_flow, "branch", "flow.compare() for branching")
    report.probe_method(probe_flow, "check_attribute", "flow.compare()")

    del probe_flow

    # ---------------------------------------------------------------
    # Build the flow: Input -> Set Attribute -> Compare -> Branch
    # ---------------------------------------------------------------
    try:
        flow = Flow.build("Attributes and Compare Flow", debug=False)
        report.success("Created flow with Flow.build()")
    except Exception as exc:
        report.error("Failed to create flow", exc)
        return report

    # Step 1: Collect customer type selection
    try:
        menu = flow.get_input(
            "Press 1 for Standard support, 2 for Premium support, 3 for Enterprise support.",
            timeout=10
        )
        report.success("Created input menu for customer type selection")
    except Exception as exc:
        report.error("Failed to create input menu", exc)
        return report

    # Step 2: Create attribute-setting blocks for each selection
    try:
        set_standard = flow.update_attributes(customer_tier="standard")
        report.success(
            "Created update_attributes(customer_tier='standard') via convenience method",
            "update_attributes() works with keyword arguments as attribute key-value pairs"
        )
    except Exception as exc:
        report.error("Failed to create standard attributes block", exc)
        return report

    try:
        set_premium = flow.update_attributes(customer_tier="premium")
        report.success("Created update_attributes(customer_tier='premium')")
    except Exception as exc:
        report.error("Failed to create premium attributes block", exc)
        return report

    try:
        set_enterprise = flow.update_attributes(customer_tier="enterprise")
        report.success("Created update_attributes(customer_tier='enterprise')")
    except Exception as exc:
        report.error("Failed to create enterprise attributes block", exc)
        return report

    # Verify that the attributes dict is correctly populated
    try:
        assert set_standard.attributes == {"customer_tier": "standard"}, \
            f"Expected {{'customer_tier': 'standard'}}, got {set_standard.attributes}"
        assert set_premium.attributes == {"customer_tier": "premium"}, \
            f"Expected {{'customer_tier': 'premium'}}, got {set_premium.attributes}"
        assert set_enterprise.attributes == {"customer_tier": "enterprise"}, \
            f"Expected {{'customer_tier': 'enterprise'}}, got {set_enterprise.attributes}"
        report.success(
            "update_attributes() correctly stores attributes as key-value dict",
            "Verified all 3 attribute blocks have correct customer_tier values"
        )
    except AssertionError as exc:
        report.error("Attribute verification failed", exc)
    except Exception as exc:
        report.error("Unexpected error verifying attributes", exc)

    # Step 3: Create Compare block using convenience method
    try:
        compare_tier = flow.compare("$.Attributes.customer_tier")
        report.success(
            "Created Compare block via flow.compare('$.Attributes.customer_tier')",
            "Convenience method handles uuid and parameter setup"
        )
    except Exception as exc:
        report.error("Failed to create Compare block", exc)
        return report

    # Wire attribute blocks to the compare block
    try:
        set_standard.then(compare_tier)
        set_premium.then(compare_tier)
        set_enterprise.then(compare_tier)
        report.success("All three attribute blocks wired to the Compare block")
    except Exception as exc:
        report.error("Failed to wire attribute blocks to Compare", exc)
        return report

    # Step 4: Verify Compare has .when() and .otherwise() from FlowBlock base
    try:
        assert hasattr(compare_tier, "when"), "Compare should have .when() from FlowBlock"
        assert hasattr(compare_tier, "otherwise"), "Compare should have .otherwise() from FlowBlock"
        report.success(
            "Compare block has .when() and .otherwise() methods from FlowBlock base",
            "Enables fluent API: compare.when('value', block).otherwise(default)"
        )
    except AssertionError as exc:
        report.error("Compare missing expected methods", exc)

    # Step 5: Create branch handlers for each tier
    try:
        standard_msg = flow.play_prompt(
            "You have been classified as a Standard support customer. "
            "Expected wait time is 15 minutes."
        )
        premium_msg = flow.play_prompt(
            "Welcome, Premium customer. You will be connected to a priority agent shortly."
        )
        enterprise_msg = flow.play_prompt(
            "Welcome, Enterprise customer. Your dedicated account manager has been notified."
        )
        default_msg = flow.play_prompt(
            "We could not determine your support tier. Connecting you to General Support."
        )
        report.success("Created 4 branch handler messages (standard, premium, enterprise, default)")
    except Exception as exc:
        report.error("Failed to create branch handler messages", exc)
        return report

    # Wire Compare branches using .when(), .otherwise(), and NoMatchingCondition error
    try:
        compare_tier.when("standard", standard_msg) \
            .when("premium", premium_msg) \
            .when("enterprise", enterprise_msg) \
            .otherwise(default_msg) \
            .on_error("NoMatchingCondition", default_msg)
        report.success(
            "Wired Compare block via .when()/.otherwise()/.on_error('NoMatchingCondition')",
            "3 conditions + default via otherwise + NoMatchingCondition error for AWS 'No match' port"
        )
    except Exception as exc:
        report.error("Failed to wire Compare branches", exc)
        return report

    # Step 6: All messages terminate at disconnect
    try:
        hangup = flow.disconnect()
        standard_msg.then(hangup)
        premium_msg.then(hangup)
        enterprise_msg.then(hangup)
        default_msg.then(hangup)
        report.success("All branch handlers terminate at shared disconnect")
    except Exception as exc:
        report.error("Failed to wire terminal blocks", exc)
        return report

    # Step 7: Wire the input menu
    try:
        error_msg = flow.play_prompt("Invalid selection. Please try again later. Goodbye.")
        error_msg.then(hangup)

        menu.when("1", set_standard)
        menu.when("2", set_premium)
        menu.when("3", set_enterprise)
        menu.otherwise(error_msg)
        menu.on_error("InputTimeLimitExceeded", error_msg)
        menu.on_error("NoMatchingCondition", error_msg)
        menu.on_error("NoMatchingError", error_msg)
        report.success("Wired input menu with conditions, errors, and otherwise")
    except Exception as exc:
        report.error("Failed to wire input menu", exc)
        return report

    # ---------------------------------------------------------------
    # Record block count
    # ---------------------------------------------------------------
    report.block_count = len(flow.blocks)
    report.success(
        f"Total block count: {report.block_count}",
        "menu + 3 set_attr + compare + 4 msgs + error_msg + hangup = 11 blocks"
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
        # The validator may not understand Compare Conditions traversal
        report.friction(
            "Validator may not traverse Compare block Conditions for reachability analysis",
            f"Validation error: {exc}. The FlowAnalyzer._get_all_targets() method "
            "does traverse Conditions, so this should work. If it fails, it may be "
            "because Compare.transitions['Conditions'] is set after initial block creation."
        )

    # ---------------------------------------------------------------
    # Compile to file
    # ---------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    output_path = os.path.join(output_dir, "attributes_and_compare.json")
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
    # Verify the attribute -> compare -> branch chain
    try:
        # Check that set_standard points to compare_tier
        assert set_standard.transitions.get("NextAction") == compare_tier.identifier, \
            "set_standard should point to compare_tier"
        # Check that compare_tier has 3 conditions
        conditions = compare_tier.transitions.get("Conditions", [])
        assert len(conditions) == 3, f"Expected 3 conditions, got {len(conditions)}"
        # Check condition values
        operand_values = [c["Condition"]["Operands"][0] for c in conditions]
        assert "standard" in operand_values, "'standard' not found in condition operands"
        assert "premium" in operand_values, "'premium' not found in condition operands"
        assert "enterprise" in operand_values, "'enterprise' not found in condition operands"
        report.success(
            "Attribute -> Compare -> Branch chain verified structurally",
            "3 conditions with operands ['standard', 'premium', 'enterprise'] confirmed"
        )
    except AssertionError as exc:
        report.error("Structural assertion failed", exc)
    except Exception as exc:
        report.error("Unexpected error in structural assertions", exc)

    # Verify that update_attributes produces correct to_dict() output
    try:
        std_dict = set_standard.to_dict()
        attrs_in_params = std_dict.get("Parameters", {}).get("Attributes", {})
        if "customer_tier" in attrs_in_params and attrs_in_params["customer_tier"] == "standard":
            report.success(
                "UpdateContactAttributes.to_dict() correctly serializes attributes",
                f"Parameters.Attributes = {attrs_in_params}"
            )
        else:
            report.friction(
                "UpdateContactAttributes.to_dict() may not serialize attributes as expected",
                f"Got Parameters.Attributes = {attrs_in_params}"
            )
    except Exception as exc:
        report.error("Failed to verify to_dict() output", exc)

    # ---------------------------------------------------------------
    # Remaining friction observations
    # ---------------------------------------------------------------
    report.friction(
        "Developer must know AWS JSONPath syntax for attribute references",
        "The developer must know that '$.Attributes.customer_tier' is the correct "
        "reference syntax for contact attributes. This is an AWS Connect detail "
        "that leaks through the abstraction."
    )

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
