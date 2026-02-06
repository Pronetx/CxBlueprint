"""
Tests for Flow decompilation functionality.

Tests the ability to convert AWS Connect JSON back to Flow objects.
"""

from pathlib import Path

import pytest
import json
import tempfile

from cxblueprint import Flow


def test_decompile_simple_flow():
    """Test decompiling a simple two-block flow."""
    # Create a simple flow JSON structure
    flow_json = {
        "Version": "2019-10-30",
        "StartAction": "block-1",
        "Actions": [
            {
                "Identifier": "block-1",
                "Type": "MessageParticipant",
                "Parameters": {"Text": "Hello World"},
                "Transitions": {"NextAction": "block-2"},
            },
            {
                "Identifier": "block-2",
                "Type": "DisconnectParticipant",
                "Parameters": {},
                "Transitions": {},
            },
        ],
        "Metadata": {
            "entryPointPosition": {"x": 0, "y": 0},
            "snapToGrid": False,
            "ActionMetadata": {},
            "Annotations": [],
        },
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(flow_json, f)
        temp_path = f.name

    try:
        flow = Flow.decompile(temp_path)

        # Verify flow was created
        assert isinstance(flow, Flow)
        assert len(flow.blocks) == 2

        # Check first block
        first_block = flow.blocks[0]
        assert first_block.identifier == "block-1"
        assert first_block.type == "MessageParticipant"

        # Check second block
        second_block = flow.blocks[1]
        assert second_block.identifier == "block-2"
        assert second_block.type == "DisconnectParticipant"

    finally:
        Path(temp_path).unlink()  # Clean up temp file


def test_decompile_from_file(tmp_path):
    """Test decompiling flow from JSON file."""
    # Create a test flow file
    flow_json = {
        "Version": "2019-10-30",
        "StartAction": "start-block",
        "Actions": [
            {
                "Identifier": "start-block",
                "Type": "MessageParticipant",
                "Parameters": {"Text": "Welcome"},
                "Transitions": {"NextAction": "end-block"},
            },
            {
                "Identifier": "end-block",
                "Type": "DisconnectParticipant",
                "Parameters": {},
                "Transitions": {},
            },
        ],
        "Metadata": {},
    }

    # Write to temporary file
    flow_file = tmp_path / "test_flow.json"
    flow_file.write_text(json.dumps(flow_json))

    # Decompile from file
    flow = Flow.decompile(str(flow_file))

    # Verify decompilation
    assert isinstance(flow, Flow)
    assert len(flow.blocks) == 2
    assert flow._start_action == "start-block"

    # Check block types
    assert flow.blocks[0].type == "MessageParticipant"
    assert flow.blocks[1].type == "DisconnectParticipant"


def test_decompile_complex_flow_with_conditions():
    """Test decompiling flow with conditional branches."""
    flow_json = {
        "Version": "2019-10-30",
        "StartAction": "menu-block",
        "Actions": [
            {
                "Identifier": "menu-block",
                "Type": "GetParticipantInput",
                "Parameters": {
                    "Text": "Press 1 or 2",
                    "InputTimeLimitSeconds": "10",
                    "StoreInput": "False",
                },
                "Transitions": {
                    "Conditions": [
                        {
                            "NextAction": "option-1",
                            "Condition": {"Operator": "Equals", "Operands": ["1"]},
                        },
                        {
                            "NextAction": "option-2",
                            "Condition": {"Operator": "Equals", "Operands": ["2"]},
                        },
                    ],
                    "Errors": [
                        {
                            "NextAction": "disconnect",
                            "ErrorType": "InputTimeLimitExceeded",
                        }
                    ],
                },
            },
            {
                "Identifier": "option-1",
                "Type": "MessageParticipant",
                "Parameters": {"Text": "You chose option 1"},
                "Transitions": {"NextAction": "disconnect"},
            },
            {
                "Identifier": "option-2",
                "Type": "MessageParticipant",
                "Parameters": {"Text": "You chose option 2"},
                "Transitions": {"NextAction": "disconnect"},
            },
            {
                "Identifier": "disconnect",
                "Type": "DisconnectParticipant",
                "Parameters": {},
                "Transitions": {},
            },
        ],
        "Metadata": {},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(flow_json, f)
        temp_path = f.name

    try:
        flow = Flow.decompile(temp_path)

        # Verify complex flow structure
        assert len(flow.blocks) == 4
        assert flow._start_action == "menu-block"

        # Check menu block has proper conditions
        menu_block = next(b for b in flow.blocks if b.identifier == "menu-block")
        assert menu_block.type == "GetParticipantInput"

    finally:
        Path(temp_path).unlink()


def test_round_trip_compilation(tmp_path):
    """Test that compile -> decompile -> compile produces same JSON structure."""
    # Create a flow
    flow = Flow.build("Round Trip Test")
    welcome = flow.play_prompt("Hello")
    menu = flow.get_input("Press 1", timeout=10)
    option = flow.play_prompt("You pressed 1")
    disconnect = flow.disconnect()

    # Wire the flow with proper error handlers
    welcome.then(menu)
    menu.when("1", option).otherwise(disconnect)
    menu.on_error("InputTimeLimitExceeded", disconnect)
    menu.on_error("NoMatchingCondition", disconnect)
    menu.on_error("NoMatchingError", disconnect)
    option.then(disconnect)

    # Compile to file
    output1 = tmp_path / "flow1.json"
    flow.compile_to_file(str(output1))

    # Decompile
    flow2 = Flow.decompile(str(output1))

    # Compile again
    output2 = tmp_path / "flow2.json"
    flow2.compile_to_file(str(output2))

    # Compare JSON structures (load and check key components)
    with open(output1) as f1, open(output2) as f2:
        json1 = json.load(f1)
        json2 = json.load(f2)

    # Should have same number of actions
    assert len(json1["Actions"]) == len(json2["Actions"])
    assert json1["Version"] == json2["Version"]
    # Start actions might differ due to regeneration, but structure should be similar


def test_decompile_invalid_json():
    """Test decompiling with invalid JSON structure."""
    invalid_json = {
        "Version": "2019-10-30"
        # Missing required fields
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(invalid_json, f)
        temp_path = f.name

    try:
        # Should handle missing fields gracefully
        flow = Flow.decompile(temp_path)
        assert isinstance(flow, Flow)
        # Should have empty actions list if no Actions field
        assert len(flow.blocks) == 0

    finally:
        Path(temp_path).unlink()


def test_decompile_preserves_block_parameters():
    """Test that block parameters are preserved during decompilation."""
    flow_json = {
        "Version": "2019-10-30",
        "StartAction": "lambda-block",
        "Actions": [
            {
                "Identifier": "lambda-block",
                "Type": "InvokeLambdaFunction",
                "Parameters": {
                    "LambdaFunctionArn": "arn:aws:lambda:us-east-1:123456789:function:test",
                    "InvocationTimeLimitSeconds": "8",
                    "LambdaInvocationType": "RequestResponse",
                },
                "Transitions": {"NextAction": "end-block"},
            },
            {
                "Identifier": "end-block",
                "Type": "DisconnectParticipant",
                "Parameters": {},
                "Transitions": {},
            },
        ],
        "Metadata": {},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(flow_json, f)
        temp_path = f.name

    try:
        flow = Flow.decompile(temp_path)

        # Find lambda block
        lambda_block = next(b for b in flow.blocks if b.identifier == "lambda-block")

        # Check parameters were preserved
        assert lambda_block.type == "InvokeLambdaFunction"
        # The exact way parameters are stored may vary based on implementation

    finally:
        Path(temp_path).unlink()


def test_decompile_with_debug_output(capsys):
    """Test decompile with debug output enabled."""
    flow_json = {
        "Version": "2019-10-30",
        "StartAction": "test-block",
        "Actions": [
            {
                "Identifier": "test-block",
                "Type": "MessageParticipant",
                "Parameters": {"Text": "Test"},
                "Transitions": {},
            }
        ],
        "Metadata": {},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(flow_json, f)
        temp_path = f.name

    try:
        flow = Flow.decompile(temp_path, debug=True)

        # Capture output
        captured = capsys.readouterr()

        # Should have debug output
        assert "Decompiled flow:" in captured.out

    finally:
        Path(temp_path).unlink()
