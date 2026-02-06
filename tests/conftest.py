"""
Shared test fixtures for CxBlueprint tests.
"""

import pytest

from cxblueprint import Flow
from cxblueprint.blocks.participant_actions import (
    MessageParticipant,
    DisconnectParticipant,
    GetParticipantInput,
)
from cxblueprint.blocks.flow_control_actions import EndFlowExecution


@pytest.fixture
def simple_flow():
    """Create a simple 2-block flow: prompt → disconnect."""
    flow = Flow.build("Simple Test Flow")
    prompt = flow.play_prompt("Hello, world!")
    disconnect = flow.disconnect()
    prompt.then(disconnect)
    return flow


@pytest.fixture
def menu_flow():
    """Create a 5-block menu flow with branching."""
    flow = Flow.build("Menu Test Flow")

    welcome = flow.play_prompt("Welcome!")
    menu = flow.get_input("Press 1 for sales, 2 for support", timeout=10)
    sales = flow.play_prompt("Transferring to sales...")
    support = flow.play_prompt("Transferring to support...")
    disconnect = flow.disconnect()

    welcome.then(menu)
    menu.when("1", sales).when("2", support).otherwise(disconnect)
    menu.on_error("InputTimeLimitExceeded", disconnect)
    menu.on_error("NoMatchingCondition", disconnect)
    menu.on_error("NoMatchingError", disconnect)
    sales.then(disconnect)
    support.then(disconnect)

    return flow


@pytest.fixture
def orphaned_flow():
    """Create a flow with orphaned blocks for testing validation."""
    flow = Flow.build("Orphaned Test Flow")

    # Connected block
    prompt = flow.play_prompt("Hello")
    disconnect = flow.disconnect()
    prompt.then(disconnect)

    # Orphaned block (not connected)
    orphaned = MessageParticipant(identifier="orphaned-block-123", text="I am orphaned")
    flow.blocks.append(orphaned)

    return flow


@pytest.fixture
def unterminated_flow():
    """Create a flow with unterminated paths for testing validation."""
    flow = Flow.build("Unterminated Test Flow")

    # Block with no next action
    prompt = flow.play_prompt("Hello")
    # Intentionally don't add .then() - this creates unterminated path

    return flow


@pytest.fixture
def missing_error_handlers_flow():
    """Create a flow with GetParticipantInput missing required error handlers."""
    flow = Flow.build("Missing Handlers Test Flow")

    prompt = flow.play_prompt("Welcome")
    menu = flow.get_input("Press 1", timeout=10)
    disconnect = flow.disconnect()

    prompt.then(menu)
    menu.when("1", disconnect)
    # Intentionally missing error handlers for:
    # - InputTimeLimitExceeded
    # - NoMatchingCondition
    # - NoMatchingError

    return flow


@pytest.fixture
def branching_flow():
    """Create a flow with multiple branches for testing canvas layout."""
    flow = Flow.build("Branching Test Flow")

    start = flow.play_prompt("Welcome to our service")
    menu = flow.get_input("Press 1 for sales, 2 for support, 3 for billing", timeout=10)
    sales = flow.play_prompt("Connecting to sales...")
    support = flow.play_prompt("Connecting to support...")
    billing = flow.play_prompt("Connecting to billing...")
    disconnect = flow.disconnect()

    start.then(menu)
    menu.when("1", sales).when("2", support).when("3", billing).otherwise(disconnect)
    menu.on_error("InputTimeLimitExceeded", disconnect)
    menu.on_error("NoMatchingCondition", disconnect)
    menu.on_error("NoMatchingError", disconnect)
    sales.then(disconnect)
    support.then(disconnect)
    billing.then(disconnect)

    return flow


@pytest.fixture
def sample_blocks():
    """Create a collection of sample blocks for testing."""
    import uuid

    blocks = {
        "message": MessageParticipant(
            identifier=str(uuid.uuid4()), text="Hello, world!"
        ),
        "disconnect": DisconnectParticipant(identifier=str(uuid.uuid4())),
        "get_input": GetParticipantInput(
            identifier=str(uuid.uuid4()),
            text="Press 1",
            input_time_limit_seconds=5,
            store_input=False,
        ),
        "end_flow": EndFlowExecution(identifier=str(uuid.uuid4())),
    }

    return blocks


@pytest.fixture
def mock_aws_json():
    """Return a valid AWS Connect JSON structure for testing decompilation."""
    return {
        "Version": "2019-10-30",
        "StartAction": "block-1",
        "Actions": [
            {
                "Identifier": "block-1",
                "Type": "MessageParticipant",
                "Parameters": {"Text": "Hello, world!"},
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
            "ActionMetadata": {
                "block-1": {"position": {"x": 150, "y": 50}},
                "block-2": {"position": {"x": 430, "y": 50}},
            },
        },
    }
