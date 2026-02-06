"""
QA Test 9: Pause/Resume Recording for PCI Compliance

Scenario: greeting -> "We need your credit card" -> pause recording
           -> get card digits -> resume recording -> confirmation -> disconnect

Tests:
- UpdateContactRecordingBehavior via flow.add() (no convenience method)
- Understanding constructor signature for pause vs resume
- Discoverability probes for intuitive method names
- Friction around PCI compliance being extremely common but lacking convenience methods
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
    report = QAReport("test_recording_control")

    # ------------------------------------------------------------------ #
    # 1. Imports
    # ------------------------------------------------------------------ #
    try:
        from cxblueprint import Flow
        from cxblueprint.blocks.contact_actions import UpdateContactRecordingBehavior
        report.success(
            "Successfully imported UpdateContactRecordingBehavior",
            "Available from cxblueprint.blocks.contact_actions",
        )
    except ImportError as exc:
        report.error("Failed to import UpdateContactRecordingBehavior", exc)
        return report

    # ------------------------------------------------------------------ #
    # 2. Discoverability probes -- intuitive method names on Flow
    # ------------------------------------------------------------------ #
    flow_probe = Flow.build("Recording Probe", debug=False)

    report.probe_method(flow_probe, "pause_recording", "add(UpdateContactRecordingBehavior(...))")
    report.probe_method(flow_probe, "resume_recording", "add(UpdateContactRecordingBehavior(...))")
    report.probe_method(flow_probe, "stop_recording", "add(UpdateContactRecordingBehavior(...))")
    report.probe_method(flow_probe, "start_recording", "add(UpdateContactRecordingBehavior(...))")

    report.friction(
        "No convenience methods for recording control (pause/resume)",
        "PCI-DSS compliance requires pausing recording during payment card entry. "
        "This is one of the most common contact center patterns, yet CxBlueprint "
        "provides no flow.pause_recording() or flow.resume_recording() convenience. "
        "Users must manually import and construct UpdateContactRecordingBehavior.",
    )

    # ------------------------------------------------------------------ #
    # 3. Explore UpdateContactRecordingBehavior constructor
    # ------------------------------------------------------------------ #
    # The block has a recording_behavior: Optional[Dict[str, Any]] field.
    # Users must know what dict structure AWS Connect expects.
    # In AWS Connect, RecordingBehavior has:
    #   { "RecordedParticipants": ["Agent", "Customer"] }  for recording ON
    #   { "RecordedParticipants": [] }  for recording OFF (pause)

    # Test: create a "pause" block (empty RecordedParticipants)
    try:
        pause_recording = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
            recording_behavior={"RecordedParticipants": []},
        )
        report.success(
            "Created pause-recording block with recording_behavior={'RecordedParticipants': []}",
            f"Block repr: {pause_recording!r}",
        )
    except Exception as exc:
        report.error("Failed to create pause-recording block", exc)
        return report

    # Test: create a "resume" block (both participants recorded)
    try:
        resume_recording = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
            recording_behavior={"RecordedParticipants": ["Agent", "Customer"]},
        )
        report.success(
            "Created resume-recording block with recording_behavior={'RecordedParticipants': ['Agent', 'Customer']}",
            f"Block repr: {resume_recording!r}",
        )
    except Exception as exc:
        report.error("Failed to create resume-recording block", exc)
        return report

    report.friction(
        "recording_behavior parameter is an opaque dict, not a typed enum/flag",
        "Users must know the AWS Connect JSON structure to configure pause vs resume. "
        "A more ergonomic API would be: "
        "UpdateContactRecordingBehavior(pause=True) or "
        "UpdateContactRecordingBehavior(record_agent=False, record_customer=False). "
        "The current Dict[str, Any] type gives no IDE hints about valid values.",
    )

    # Test: what happens with no recording_behavior at all?
    try:
        bare_block = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
        )
        report.success(
            "Created recording block with no recording_behavior (defaults to None)",
            f"Block repr: {bare_block!r} -- parameters: {bare_block.parameters}",
        )
        report.friction(
            "UpdateContactRecordingBehavior can be constructed with no recording_behavior",
            "Creating a recording behavior block without specifying the behavior "
            "is confusing. The constructor should arguably require recording_behavior "
            "or provide clear defaults (e.g., pause=True).",
        )
    except Exception as exc:
        report.error("Bare UpdateContactRecordingBehavior construction failed", exc)

    # ------------------------------------------------------------------ #
    # 4. Build the PCI-compliance flow
    # ------------------------------------------------------------------ #
    try:
        flow = Flow.build("PCI Compliance Recording Flow", debug=False)

        # -- greeting --
        greeting = flow.play_prompt(
            "Thank you for calling. Your call may be recorded for quality assurance."
        )
        report.success("Created greeting prompt")

        # -- payment notice --
        payment_notice = flow.play_prompt(
            "We will now collect your payment information. "
            "Recording will be paused for your security."
        )
        greeting.then(payment_notice)
        report.success("Created payment notice prompt")

        # -- pause recording --
        pause_block = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
            recording_behavior={"RecordedParticipants": []},
        )
        flow.add(pause_block)
        payment_notice.then(pause_block)
        report.success("Added pause-recording block to flow")

        # -- collect card digits --
        error_disconnect = flow.disconnect()

        card_input = flow.get_input(
            "Please enter your 16-digit card number followed by the pound key.",
            timeout=30,
        )
        pause_block.then(card_input)
        report.success("Created card number input block with 30-second timeout")

        # Wire error handlers for card_input
        card_input.on_error("InputTimeLimitExceeded", error_disconnect)
        card_input.on_error("NoMatchingCondition", error_disconnect)
        card_input.on_error("NoMatchingError", error_disconnect)
        report.success("Wired card_input error handlers")

        # -- resume recording --
        resume_block = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
            recording_behavior={"RecordedParticipants": ["Agent", "Customer"]},
        )
        flow.add(resume_block)
        card_input.then(resume_block)
        report.success("Added resume-recording block to flow")

        # -- confirmation and disconnect --
        confirmation = flow.play_prompt(
            "Thank you. Your payment has been received. Recording has been resumed."
        )
        resume_block.then(confirmation)

        final_disconnect = flow.disconnect()
        confirmation.then(final_disconnect)
        report.success("Wired confirmation -> disconnect path")

    except Exception as exc:
        report.error("Failed to build PCI compliance flow", exc)
        return report

    # ------------------------------------------------------------------ #
    # 5. Validate and compile
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
        tempfile.gettempdir(), "qa_test_recording_control.json"
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

        recording_blocks = [
            a for a in compiled["Actions"]
            if a["Type"] == "UpdateContactRecordingBehavior"
        ]
        if len(recording_blocks) == 2:
            report.success(
                "Both pause and resume recording blocks present in compiled output",
                f"Found {len(recording_blocks)} UpdateContactRecordingBehavior blocks",
            )
        else:
            report.error(
                f"Expected 2 recording behavior blocks, found {len(recording_blocks)}"
            )

        # Verify the pause block has empty RecordedParticipants
        pause_params = recording_blocks[0].get("Parameters", {}) if recording_blocks else {}
        pause_rb = pause_params.get("RecordingBehavior", {})
        if pause_rb.get("RecordedParticipants") == []:
            report.success(
                "Pause block correctly serialized with empty RecordedParticipants",
            )
        else:
            report.friction(
                "Pause block RecordingBehavior not serialized as expected",
                f"Got: {pause_rb}",
            )

        # Verify the resume block has both participants
        if len(recording_blocks) >= 2:
            resume_params = recording_blocks[1].get("Parameters", {})
            resume_rb = resume_params.get("RecordingBehavior", {})
            if set(resume_rb.get("RecordedParticipants", [])) == {"Agent", "Customer"}:
                report.success(
                    "Resume block correctly serialized with Agent and Customer participants",
                )
            else:
                report.friction(
                    "Resume block RecordingBehavior not serialized as expected",
                    f"Got: {resume_rb}",
                )

        report.success(
            f"Compiled JSON has {len(compiled['Actions'])} actions",
            f"Action types: {action_types}",
        )

    except Exception as exc:
        report.error("Flow compilation to file failed", exc)

    # ------------------------------------------------------------------ #
    # 6. Summary friction notes
    # ------------------------------------------------------------------ #
    report.missing(
        "flow.pause_recording() convenience method",
        "PCI-DSS compliance is required for any contact center handling payments. "
        "A simple flow.pause_recording() that internally creates "
        "UpdateContactRecordingBehavior(recording_behavior={'RecordedParticipants': []}) "
        "would make this trivially easy.",
    )
    report.missing(
        "flow.resume_recording() convenience method",
        "Complementary to pause_recording(). Should create "
        "UpdateContactRecordingBehavior with both Agent and Customer in RecordedParticipants.",
    )
    report.missing(
        "Typed enum or helper for recording states",
        "Instead of raw dicts like {'RecordedParticipants': []}, the library could provide "
        "RecordingState.PAUSED, RecordingState.AGENT_ONLY, RecordingState.BOTH, etc. "
        "This would prevent typos and improve IDE auto-completion.",
    )
    report.friction(
        "PCI compliance is extremely common but requires deep AWS knowledge",
        "Building a PCI-compliant payment flow requires understanding: "
        "(1) the RecordedParticipants parameter format, "
        "(2) that empty list means pause, "
        "(3) that you need two separate blocks for pause/resume. "
        "A higher-level abstraction like flow.pci_payment_section(card_input_block) "
        "could wrap this entire pattern.",
    )

    return report


if __name__ == "__main__":
    from qa_helpers import print_report
    print_report(run_test())
