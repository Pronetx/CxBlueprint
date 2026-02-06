"""
Tests for Flow builder functionality.

Tests the main Flow class for building contact flows.
"""

import pytest
import json

from cxblueprint import Flow, FlowValidationError


def test_flow_initialization():
    """Test Flow initialization."""
    flow = Flow.build("Test Flow")
    assert flow.name == "Test Flow"
    assert flow.version == "2019-10-30"
    assert len(flow.blocks) == 0
    assert flow._start_action is None


def test_flow_with_debug():
    """Test Flow initialization with debug mode."""
    flow = Flow.build("Debug Flow", debug=True)
    assert flow.debug is True


def test_play_prompt_block():
    """Test creating play prompt blocks."""
    flow = Flow.build("Test Flow")
    prompt = flow.play_prompt("Hello World")

    assert len(flow.blocks) == 1
    assert prompt.type == "MessageParticipant"
    assert prompt.text == "Hello World"
    assert flow._start_action == prompt.identifier


def test_get_input_block():
    """Test creating get input blocks."""
    flow = Flow.build("Test Flow")
    input_block = flow.get_input("Press 1", timeout=15)

    assert len(flow.blocks) == 1
    assert input_block.type == "GetParticipantInput"
    assert input_block.text == "Press 1"
    assert input_block.input_time_limit_seconds == 15


def test_disconnect_block():
    """Test creating disconnect blocks."""
    flow = Flow.build("Test Flow")
    disconnect = flow.disconnect()

    assert len(flow.blocks) == 1
    assert disconnect.type == "DisconnectParticipant"


def test_block_chaining():
    """Test chaining blocks with then()."""
    flow = Flow.build("Test Flow")
    welcome = flow.play_prompt("Welcome")
    disconnect = flow.disconnect()

    welcome.then(disconnect)

    assert welcome.transitions["NextAction"] == disconnect.identifier


def test_conditional_branching():
    """Test conditional branching with when()."""
    flow = Flow.build("Test Flow")
    menu = flow.get_input("Press 1 or 2")
    option1 = flow.play_prompt("Option 1")
    option2 = flow.play_prompt("Option 2")

    menu.when("1", option1).when("2", option2)

    conditions = menu.transitions["Conditions"]
    assert len(conditions) == 2
    assert conditions[0]["Condition"]["Operands"] == ["1"]
    assert conditions[0]["NextAction"] == option1.identifier
    assert conditions[1]["Condition"]["Operands"] == ["2"]
    assert conditions[1]["NextAction"] == option2.identifier


def test_error_handling():
    """Test error handler setup."""
    flow = Flow.build("Test Flow")
    menu = flow.get_input("Press 1")
    error_block = flow.disconnect()

    menu.on_error("InputTimeLimitExceeded", error_block)

    errors = menu.transitions["Errors"]
    assert len(errors) == 1
    assert errors[0]["ErrorType"] == "InputTimeLimitExceeded"
    assert errors[0]["NextAction"] == error_block.identifier


def test_otherwise_fallback():
    """Test otherwise fallback setup."""
    flow = Flow.build("Test Flow")
    menu = flow.get_input("Press 1")
    fallback = flow.disconnect()

    menu.otherwise(fallback)

    # The otherwise method sets NextAction, not DefaultAction
    assert menu.transitions["NextAction"] == fallback.identifier


def test_update_attributes_block():
    """Test creating update attributes blocks."""
    flow = Flow.build("Test Flow")
    update = flow.update_attributes(customer_type="premium", status="active")

    assert len(flow.blocks) == 1
    assert update.type == "UpdateContactAttributes"
    assert update.attributes["customer_type"] == "premium"
    assert update.attributes["status"] == "active"


def test_invoke_lambda_block():
    """Test creating Lambda invocation blocks."""
    flow = Flow.build("Test Flow")
    lambda_block = flow.invoke_lambda(
        function_arn="arn:aws:lambda:us-east-1:123:function:test", timeout_seconds=8
    )

    assert len(flow.blocks) == 1
    assert lambda_block.type == "InvokeLambdaFunction"
    assert (
        lambda_block.lambda_function_arn == "arn:aws:lambda:us-east-1:123:function:test"
    )
    assert lambda_block.invocation_time_limit_seconds == 8


def test_check_hours_block():
    """Test creating hours of operation check blocks."""
    flow = Flow.build("Test Flow")
    hours_block = flow.check_hours(hours_of_operation_id="business-hours-id")

    assert len(flow.blocks) == 1
    assert hours_block.type == "CheckHoursOfOperation"


def test_end_flow_block():
    """Test creating end flow execution blocks."""
    flow = Flow.build("Test Flow")
    end_block = flow.end_flow()

    assert len(flow.blocks) == 1
    assert end_block.type == "EndFlowExecution"


def test_transfer_to_flow_block():
    """Test creating transfer to flow blocks."""
    flow = Flow.build("Test Flow")
    transfer = flow.transfer_to_flow("other-flow-id")

    assert len(flow.blocks) == 1
    assert transfer.type == "TransferToFlow"
    assert transfer.contact_flow_id == "other-flow-id"


def test_compilation_to_dict():
    """Test compiling flow to dictionary."""
    flow = Flow.build("Test Flow")
    welcome = flow.play_prompt("Hello")
    disconnect = flow.disconnect()
    welcome.then(disconnect)

    compiled = flow.compile()

    assert compiled["Version"] == "2019-10-30"
    assert compiled["StartAction"] == welcome.identifier
    assert len(compiled["Actions"]) == 2
    assert "Metadata" in compiled


def test_compilation_validation():
    """Test that compilation runs validation."""
    flow = Flow.build("Invalid Flow")
    menu = flow.get_input("Press 1", timeout=10)
    # Don't add required error handlers - this should fail validation

    with pytest.raises(FlowValidationError):
        flow.compile()


def test_compilation_to_json():
    """Test compiling flow to JSON string."""
    flow = Flow.build("Test Flow")
    welcome = flow.play_prompt("Hello")
    disconnect = flow.disconnect()
    welcome.then(disconnect)

    json_str = flow.compile_to_json()

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert parsed["Version"] == "2019-10-30"
    assert len(parsed["Actions"]) == 2


def test_compilation_to_file(tmp_path):
    """Test compiling flow to file."""
    flow = Flow.build("Test Flow")
    welcome = flow.play_prompt("Hello")
    disconnect = flow.disconnect()
    welcome.then(disconnect)

    output_file = tmp_path / "test_flow.json"
    flow.compile_to_file(str(output_file))

    # File should exist and contain valid JSON
    assert output_file.exists()
    content = json.loads(output_file.read_text())
    assert content["Version"] == "2019-10-30"


def test_block_statistics_tracking():
    """Test that block statistics are tracked."""
    flow = Flow.build("Test Flow")
    flow.play_prompt("Hello")
    flow.play_prompt("World")
    flow.get_input("Press 1")
    flow.disconnect()

    # Should have tracked different block types
    assert flow._block_stats["MessageParticipant"] == 2
    assert flow._block_stats["GetParticipantInput"] == 1
    assert flow._block_stats["DisconnectParticipant"] == 1


def test_complex_flow_creation():
    """Test creating a complex flow with multiple branches."""
    flow = Flow.build("Complex Flow")

    welcome = flow.play_prompt("Welcome to our service")
    menu = flow.get_input("Press 1 for sales, 2 for support", timeout=10)
    sales = flow.play_prompt("Connecting to sales")
    support = flow.play_prompt("Connecting to support")
    invalid = flow.play_prompt("Invalid selection")
    disconnect = flow.disconnect()

    # Wire the flow
    welcome.then(menu)
    menu.when("1", sales).when("2", support).otherwise(invalid)
    menu.on_error("InputTimeLimitExceeded", invalid)
    menu.on_error("NoMatchingCondition", invalid)
    menu.on_error("NoMatchingError", invalid)

    sales.then(disconnect)
    support.then(disconnect)
    invalid.then(disconnect)

    # Should compile without validation errors
    compiled = flow.compile()
    assert len(compiled["Actions"]) == 6


def test_block_repr():
    """Test block string representation."""
    flow = Flow.build("Test Flow")
    prompt = flow.play_prompt("Test message")

    repr_str = repr(prompt)
    assert "MessageParticipant" in repr_str
    # Check that the text parameter appears in the repr
    assert "Test message" in repr_str


# ---- New tests for QA-identified gaps ----


def test_transfer_to_queue_block():
    """Test creating transfer to queue blocks."""
    flow = Flow.build("Test Flow")
    xfer = flow.transfer_to_queue()

    assert len(flow.blocks) == 1
    assert xfer.type == "TransferContactToQueue"


def test_wait_block():
    """Test creating wait blocks with seconds parameter."""
    flow = Flow.build("Test Flow")
    w = flow.wait(seconds=30)

    assert len(flow.blocks) == 1
    assert w.type == "Wait"
    assert w.time_limit_seconds == 30


def test_pause_recording_block():
    """Test pause recording creates correct RecordedParticipants=[]."""
    flow = Flow.build("Test Flow")
    pause = flow.pause_recording()

    assert pause.type == "UpdateContactRecordingBehavior"
    assert pause.recording_behavior == {"RecordedParticipants": []}


def test_resume_recording_block():
    """Test resume recording creates correct RecordedParticipants."""
    flow = Flow.build("Test Flow")
    resume = flow.resume_recording()

    assert resume.type == "UpdateContactRecordingBehavior"
    assert resume.recording_behavior == {
        "RecordedParticipants": ["Agent", "Customer"]
    }


def test_compare_block():
    """Test compare block propagates comparison_value."""
    flow = Flow.build("Test Flow")
    branch = flow.compare("$.Attributes.customer_tier")

    assert branch.type == "Compare"
    assert branch.comparison_value == "$.Attributes.customer_tier"


def test_flow_load_alias(tmp_path):
    """Test that Flow.load() works as alias for Flow.decompile()."""
    # Create a minimal flow and save it
    flow = Flow.build("Original")
    welcome = flow.play_prompt("Hello")
    disconnect = flow.disconnect()
    welcome.then(disconnect)

    output_file = tmp_path / "test_load.json"
    flow.compile_to_file(str(output_file))

    # Load via alias
    loaded = Flow.load(str(output_file))
    assert len(loaded.blocks) == 2
    assert loaded._start_action is not None


def test_when_on_check_hours():
    """Test .when() works on CheckHoursOfOperation (inherited from base)."""
    flow = Flow.build("Test Flow")
    hours = flow.check_hours(hours_of_operation_id="test-hours")
    open_path = flow.play_prompt("We are open")
    closed_path = flow.play_prompt("We are closed")

    hours.when("True", open_path).when("False", closed_path)

    conditions = hours.transitions["Conditions"]
    assert len(conditions) == 2
    assert conditions[0]["Condition"]["Operands"] == ["True"]
    assert conditions[0]["NextAction"] == open_path.identifier
    assert conditions[1]["Condition"]["Operands"] == ["False"]
    assert conditions[1]["NextAction"] == closed_path.identifier


def test_when_on_compare():
    """Test .when() + .otherwise() on Compare block."""
    flow = Flow.build("Test Flow")
    branch = flow.compare("$.Attributes.tier")
    premium = flow.play_prompt("VIP")
    standard = flow.play_prompt("Standard")
    default = flow.play_prompt("Default")

    branch.when("premium", premium).when("standard", standard).otherwise(default)

    conditions = branch.transitions["Conditions"]
    assert len(conditions) == 2
    assert conditions[0]["Condition"]["Operands"] == ["premium"]
    assert branch.transitions["NextAction"] == default.identifier


def test_otherwise_on_lex_bot():
    """Test .otherwise() on ConnectParticipantWithLexBot."""
    from cxblueprint.blocks.types import LexV2Bot

    flow = Flow.build("Test Flow")
    bot = flow.lex_bot(
        text="How can I help?",
        lex_v2_bot=LexV2Bot(alias_arn="arn:aws:lex:us-east-1:123:bot-alias/test"),
    )
    fallback = flow.play_prompt("I didn't understand")

    bot.on_intent("CheckBalance", flow.play_prompt("Checking balance"))
    bot.otherwise(fallback)

    assert bot.transitions["NextAction"] == fallback.identifier
    assert len(bot.transitions["Conditions"]) == 1


def test_decompile_stats_tracking(tmp_path):
    """Test that decompiled flows have populated _block_stats."""
    # Create and save a flow
    flow = Flow.build("Stats Test")
    flow.play_prompt("Hello")
    flow.play_prompt("World")
    flow.get_input("Press 1", timeout=5)
    disconnect = flow.disconnect()

    # Wire minimally for compilation
    flow.blocks[0].then(flow.blocks[1])
    flow.blocks[1].then(flow.blocks[2])
    flow.blocks[2].then(disconnect)
    flow.blocks[2].on_error("InputTimeLimitExceeded", disconnect)
    flow.blocks[2].on_error("NoMatchingCondition", disconnect)
    flow.blocks[2].on_error("NoMatchingError", disconnect)

    output_file = tmp_path / "stats_test.json"
    flow.compile_to_file(str(output_file))

    # Decompile and check stats
    loaded = Flow.decompile(str(output_file))
    assert loaded._block_stats["MessageParticipant"] == 2
    assert loaded._block_stats["GetParticipantInput"] == 1
    assert loaded._block_stats["DisconnectParticipant"] == 1
