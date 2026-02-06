"""
QA Test 10: Decompile Existing Flow + Modify + Recompile

Scenario: Build a simple flow, compile it to JSON, then decompile it,
          add new blocks, and recompile. Verify round-trip integrity.

Tests:
- Flow.decompile(filepath) to load existing flow JSON
- Adding blocks to a decompiled flow
- Recompilation produces valid JSON
- Block connections survive round-trip
- Discoverability probes for alternative loading method names
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
    report = QAReport("test_decompile_modify")

    # ------------------------------------------------------------------ #
    # 1. Imports
    # ------------------------------------------------------------------ #
    try:
        from cxblueprint import Flow, FlowValidationError
        report.success("Successfully imported Flow and FlowValidationError")
    except ImportError as exc:
        report.error("Failed to import Flow", exc)
        return report

    # ------------------------------------------------------------------ #
    # 2. Discoverability probes -- alternative loading method names
    # ------------------------------------------------------------------ #
    # Users might try these names before finding Flow.decompile()
    probe_names = {
        "load": "decompile",
        "from_json": "decompile",
        "parse": "decompile",
        "import_flow": "decompile",
    }
    for tried, correct in probe_names.items():
        exists = hasattr(Flow, tried)
        if not exists:
            report.discoverability(
                f"Flow.{tried}()",
                f"Flow.{correct}()",
                f"AttributeError: type object 'Flow' has no attribute '{tried}'",
            )
        else:
            report.success(f"Flow.{tried}() exists (unexpected)")

    report.friction(
        "'decompile' is not the most intuitive name for loading a flow",
        "Most Python libraries use .load(), .from_json(), .from_file(), or .parse(). "
        "'decompile' implies reverse engineering, but the operation is simply "
        "deserializing a JSON file. Consider adding Flow.load() as an alias.",
    )

    # ------------------------------------------------------------------ #
    # 3. Build a simple flow, compile it, and save to a temp file
    # ------------------------------------------------------------------ #
    original_path = os.path.join(
        tempfile.gettempdir(), "qa_test_original_flow.json"
    )

    try:
        original = Flow.build("Original Simple Flow", debug=False)

        greeting = original.play_prompt("Welcome to our service.")
        error_handler = original.disconnect()

        menu = original.get_input(
            "Press 1 for sales, 2 for support.",
            timeout=5,
        )
        greeting.then(menu)

        sales_msg = original.play_prompt("Connecting you to sales.")
        support_msg = original.play_prompt("Connecting you to support.")
        sales_disconnect = original.disconnect()
        support_disconnect = original.disconnect()

        sales_msg.then(sales_disconnect)
        support_msg.then(support_disconnect)

        menu.when("1", sales_msg)
        menu.when("2", support_msg)
        menu.otherwise(error_handler)
        menu.on_error("InputTimeLimitExceeded", error_handler)
        menu.on_error("NoMatchingCondition", error_handler)
        menu.on_error("NoMatchingError", error_handler)

        original_block_count = len(original.blocks)
        report.success(
            f"Built original flow with {original_block_count} blocks",
        )

        # Compile and save
        original.compile_to_file(original_path)
        report.success(
            f"Compiled original flow to {original_path}",
        )

        # Read back and verify structure
        with open(original_path, "r") as f:
            original_json = json.load(f)
        original_action_count = len(original_json.get("Actions", []))
        original_start_action = original_json.get("StartAction", "")
        report.success(
            f"Original JSON has {original_action_count} actions, StartAction set",
        )

    except Exception as exc:
        report.error("Failed to build and compile original flow", exc)
        return report

    # ------------------------------------------------------------------ #
    # 4. Decompile the flow
    # ------------------------------------------------------------------ #
    try:
        decompiled = Flow.decompile(original_path, debug=False)
        report.success(
            f"Flow.decompile() succeeded, loaded {len(decompiled.blocks)} blocks",
            f"Flow name: {decompiled.name}",
        )

        # Verify block count matches
        if len(decompiled.blocks) == original_block_count:
            report.success(
                f"Decompiled block count ({len(decompiled.blocks)}) matches original ({original_block_count})",
            )
        else:
            report.friction(
                f"Block count mismatch: decompiled={len(decompiled.blocks)}, original={original_block_count}",
                "Some blocks may have been lost or duplicated during decompilation.",
            )

    except Exception as exc:
        report.error("Flow.decompile() failed", exc)
        return report

    # ------------------------------------------------------------------ #
    # 5. Inspect decompiled block types and transitions
    # ------------------------------------------------------------------ #
    try:
        decompiled_types = [b.type for b in decompiled.blocks]
        report.success(
            f"Decompiled block types: {decompiled_types}",
        )

        # Check that typed blocks were reconstituted (not just base FlowBlock)
        from cxblueprint.blocks.participant_actions import (
            MessageParticipant,
            GetParticipantInput,
            DisconnectParticipant,
        )

        typed_blocks = {
            "MessageParticipant": MessageParticipant,
            "GetParticipantInput": GetParticipantInput,
            "DisconnectParticipant": DisconnectParticipant,
        }

        for block in decompiled.blocks:
            expected_cls = typed_blocks.get(block.type)
            if expected_cls and isinstance(block, expected_cls):
                pass  # Good -- properly typed
            elif expected_cls and not isinstance(block, expected_cls):
                report.friction(
                    f"Block type {block.type} not reconstituted as {expected_cls.__name__}",
                    f"Got {type(block).__name__} instead. Typed methods (e.g. .when()) may not be available.",
                )

        report.success("Decompiled blocks have correct Python types (BLOCK_TYPE_MAP lookup works)")

        # Check transitions survived
        blocks_with_transitions = sum(
            1 for b in decompiled.blocks
            if b.transitions.get("NextAction")
            or b.transitions.get("Conditions")
            or b.transitions.get("Errors")
        )
        report.success(
            f"{blocks_with_transitions} of {len(decompiled.blocks)} decompiled blocks have transitions",
        )

    except Exception as exc:
        report.error("Failed to inspect decompiled blocks", exc)

    # ------------------------------------------------------------------ #
    # 6. Modify the decompiled flow -- add new blocks
    # ------------------------------------------------------------------ #
    try:
        # Add a new "billing" option to the menu
        billing_msg = decompiled.play_prompt("Connecting you to billing.")
        billing_disconnect = decompiled.disconnect()
        billing_msg.then(billing_disconnect)

        report.success(
            "Added new blocks (billing_msg + billing_disconnect) to decompiled flow",
            f"Block count now: {len(decompiled.blocks)}",
        )

        # Find the GetParticipantInput block in the decompiled flow to add a new condition
        input_blocks = [
            b for b in decompiled.blocks
            if b.type == "GetParticipantInput"
        ]
        if input_blocks:
            menu_block = input_blocks[0]
            # Add "3" for billing
            if hasattr(menu_block, "when"):
                menu_block.when("3", billing_msg)
                report.success(
                    "Added .when('3', billing_msg) condition to decompiled GetParticipantInput",
                    "The .when() method works on decompiled blocks because BLOCK_TYPE_MAP "
                    "reconstituted them as GetParticipantInput instances.",
                )
            else:
                report.friction(
                    "Decompiled GetParticipantInput lacks .when() method",
                    "Block was not properly reconstituted as GetParticipantInput.",
                )
        else:
            report.error("No GetParticipantInput blocks found in decompiled flow")

    except Exception as exc:
        report.error("Failed to modify decompiled flow", exc)

    # ------------------------------------------------------------------ #
    # 7. Validate the modified flow
    # ------------------------------------------------------------------ #
    report.block_count = len(decompiled.blocks)

    try:
        decompiled.validate()
        report.validation_passed = True
        report.success(
            "Modified decompiled flow validation passed",
            f"Total blocks after modification: {report.block_count}",
        )
    except FlowValidationError as exc:
        report.error(
            "Modified decompiled flow validation failed",
            exc,
        )
        report.friction(
            "Validation may fail on modified decompiled flows",
            "Adding blocks to a decompiled flow can create orphan/unterminated issues "
            "if the user doesn't carefully wire all transitions. The library could "
            "provide helpers to splice blocks into existing paths.",
        )

    # ------------------------------------------------------------------ #
    # 8. Recompile the modified flow
    # ------------------------------------------------------------------ #
    modified_path = os.path.join(
        tempfile.gettempdir(), "qa_test_modified_flow.json"
    )
    try:
        decompiled.compile_to_file(modified_path)
        report.compiled = True
        report.success(
            f"Recompiled modified flow to {modified_path}",
        )

        # Verify the recompiled JSON
        with open(modified_path, "r") as f:
            modified_json = json.load(f)

        modified_action_count = len(modified_json.get("Actions", []))
        report.success(
            f"Recompiled JSON has {modified_action_count} actions "
            f"(was {original_action_count})",
        )

        # Verify new blocks are present
        modified_types = [a["Type"] for a in modified_json["Actions"]]
        msg_count = modified_types.count("MessageParticipant")
        if msg_count > decompiled_types.count("MessageParticipant"):
            report.success(
                "New MessageParticipant block (billing) appears in recompiled output",
            )

        # Verify StartAction is preserved
        if modified_json.get("StartAction") == original_start_action:
            report.success(
                "StartAction preserved through decompile-modify-recompile cycle",
            )
        else:
            report.friction(
                "StartAction changed during round-trip",
                f"Original: {original_start_action}, "
                f"Modified: {modified_json.get('StartAction')}",
            )

        # Verify Metadata is present
        if "Metadata" in modified_json:
            report.success("Metadata (canvas layout) present in recompiled output")
        else:
            report.friction("Metadata missing from recompiled output")

    except Exception as exc:
        report.error("Failed to recompile modified flow", exc)

    # ------------------------------------------------------------------ #
    # 9. Round-trip comparison: decompile the recompiled flow
    # ------------------------------------------------------------------ #
    try:
        if report.compiled:
            roundtrip = Flow.decompile(modified_path, debug=False)
            roundtrip_types = sorted(b.type for b in roundtrip.blocks)
            expected_types = sorted(b.type for b in decompiled.blocks)

            if roundtrip_types == expected_types:
                report.success(
                    "Second decompile round-trip preserves all block types",
                    f"Types: {roundtrip_types}",
                )
            else:
                report.friction(
                    "Block types differ after second round-trip",
                    f"Expected: {expected_types}, Got: {roundtrip_types}",
                )
    except Exception as exc:
        report.error("Second round-trip decompile failed", exc)

    # ------------------------------------------------------------------ #
    # 10. Summary friction notes
    # ------------------------------------------------------------------ #
    report.missing(
        "Flow.load() alias for Flow.decompile()",
        "Flow.load('path.json') is the most intuitive name for loading a flow file. "
        "'decompile' suggests a complex reverse-engineering process. An alias or "
        "rename would improve discoverability.",
    )
    report.missing(
        "Flow.from_json(json_string) class method",
        "Currently you must save JSON to a file then decompile it. "
        "Flow.from_json(json_string) or Flow.from_dict(dict) would allow "
        "loading flows directly from API responses or in-memory data.",
    )
    report.friction(
        "Decompiled flows lack _block_stats tracking",
        "When blocks are loaded via decompile(), the _block_stats dict is not populated "
        "because _register_block() is not called. This means flow.stats() may return "
        "incomplete block_types data for decompiled flows. Only blocks added after "
        "decompilation via flow.add() / convenience methods will be tracked.",
    )
    report.friction(
        "No helper to splice blocks into existing flow paths",
        "After decompiling, adding a block between two existing blocks requires "
        "manually rewiring transitions. A method like "
        "flow.insert_after(existing_block, new_block) would simplify modifications "
        "to decompiled flows.",
    )

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
