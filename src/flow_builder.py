"""
Contact Flow Builder - Programmatic flow generation
"""

from pathlib import Path
import json
from typing import List, Optional, Dict, Set, Tuple, TypeVar
import uuid
from canvas_layout import CanvasLayoutEngine
from flow_analyzer import FlowAnalyzer, FlowValidationError
from blocks.base import FlowBlock
from blocks.participant_actions import (
    MessageParticipant,
    DisconnectParticipant,
    GetParticipantInput,
    ConnectParticipantWithLexBot,
    ShowView,
)
from blocks.flow_control_actions import (
    TransferToFlow,
    CheckHoursOfOperation,
    EndFlowExecution,
)
from blocks.interactions import InvokeLambdaFunction
from blocks.contact_actions import UpdateContactAttributes
from blocks.types import LexV2Bot, LexBot, ViewResource, Media

T = TypeVar("T", bound=FlowBlock)  # Generic FlowBlock type for method returns


class ContactFlowBuilder:
    """Build contact flows programmatically."""

    def __init__(self, name: str, debug: bool = False):
        self.name = name
        self.version = "2019-10-30"
        self.blocks: List[FlowBlock] = []
        self._start_action: Optional[str] = None
        self.debug = debug
        self.layout_engine = CanvasLayoutEngine(debug)
        # Statistics tracking
        self._block_stats = {}

        if debug:
            print(f"Building flow: {name}")

    def _track_block_type(self, block: FlowBlock):
        """Track block type statistics."""
        block_type = block.type
        self._block_stats[block_type] = self._block_stats.get(block_type, 0) + 1

    def _log_block_added(self, block: FlowBlock, action: str = "Added"):
        """Log when a block is added."""
        if self.debug:
            print(f"  {action}: {block.type}")

    def _register_block(self, block: T) -> T:
        """Register a block with the flow."""
        self.blocks.append(block)
        self._track_block_type(block)
        self._log_block_added(block)

        # Set start action to first block if not set
        if self._start_action is None:
            self._start_action = block.identifier

        return block

    def play_prompt(self, text: str) -> MessageParticipant:
        """Create a play prompt block."""
        block = MessageParticipant(identifier=str(uuid.uuid4()), text=text)
        return self._register_block(block)

    def get_input(self, text: str, timeout: int = 5) -> GetParticipantInput:
        """Create a get participant input block."""
        block = GetParticipantInput(
            identifier=str(uuid.uuid4()),
            text=text,
            input_time_limit_seconds=timeout,
            store_input=False,
        )
        return self._register_block(block)

    def disconnect(self) -> DisconnectParticipant:
        """Create a disconnect block."""
        block = DisconnectParticipant(identifier=str(uuid.uuid4()))
        return self._register_block(block)

    def transfer_to_flow(self, contact_flow_id: str) -> TransferToFlow:
        """Create a transfer to flow block."""
        block = TransferToFlow(
            identifier=str(uuid.uuid4()), contact_flow_id=contact_flow_id
        )
        return self._register_block(block)

    # Generic block registration

    def add(self, block: T) -> T:
        """Add a pre-configured block to the flow.

        Use this for specialized blocks that aren't covered by convenience methods.
        The block must already have an identifier set.

        Example:
            from blocks.participant_actions import ConnectParticipantWithLexBot
            from blocks.types import LexV2Bot

            lex = ConnectParticipantWithLexBot(
                identifier=str(uuid.uuid4()),
                text="How can I help you?",
                lex_v2_bot=LexV2Bot(alias_arn="arn:aws:lex:...")
            )
            flow.add(lex)
        """
        return self._register_block(block)

    # Convenience methods for common complex blocks

    def lex_bot(
        self,
        text: str = None,
        lex_v2_bot: LexV2Bot = None,
        lex_bot: LexBot = None,
        **kwargs,
    ) -> ConnectParticipantWithLexBot:
        """Create a Lex bot interaction block.

        Args:
            text: Prompt text to play before bot interaction
            lex_v2_bot: Lex V2 bot configuration (recommended)
            lex_bot: Legacy Lex bot configuration
            **kwargs: Additional parameters (lex_session_attributes, etc.)
        """
        block = ConnectParticipantWithLexBot(
            identifier=str(uuid.uuid4()),
            text=text,
            lex_v2_bot=lex_v2_bot,
            lex_bot=lex_bot,
            **kwargs,
        )
        return self._register_block(block)

    def invoke_lambda(
        self, function_arn: str, timeout_seconds: int = 8, **kwargs
    ) -> InvokeLambdaFunction:
        """Create a Lambda function invocation block.

        Args:
            function_arn: ARN of the Lambda function (or template like {{LAMBDA_ARN}})
            timeout_seconds: Function timeout in seconds (default: 8)
            **kwargs: Additional parameters
        """
        block = InvokeLambdaFunction(
            identifier=str(uuid.uuid4()),
            lambda_function_arn=function_arn,
            invocation_time_limit_seconds=timeout_seconds,
            **kwargs,
        )
        return self._register_block(block)

    def check_hours(
        self, hours_of_operation_id: str = None, **kwargs
    ) -> CheckHoursOfOperation:
        """Create a business hours check block.

        Args:
            hours_of_operation_id: Hours of operation ID (or template)
            **kwargs: Additional parameters
        """
        params = {}
        if hours_of_operation_id:
            params["HoursOfOperationId"] = hours_of_operation_id
        params.update(kwargs)

        block = CheckHoursOfOperation(identifier=str(uuid.uuid4()), parameters=params)
        return self._register_block(block)

    def update_attributes(self, **attributes) -> UpdateContactAttributes:
        """Create a contact attributes update block.

        Args:
            **attributes: Attributes to update (passed as parameters)
        """
        block = UpdateContactAttributes(
            identifier=str(uuid.uuid4()), attributes=attributes
        )
        return self._register_block(block)

    def show_view(self, view_resource: ViewResource, **kwargs) -> ShowView:
        """Create an agent workspace view block.

        Args:
            view_resource: View resource configuration
            **kwargs: Additional parameters (view_data, etc.)
        """
        block = ShowView(
            identifier=str(uuid.uuid4()), view_resource=view_resource, **kwargs
        )
        return self._register_block(block)

    def end_flow(self) -> EndFlowExecution:
        """Create an end flow execution block."""
        block = EndFlowExecution(identifier=str(uuid.uuid4()))
        return self._register_block(block)

    # Compilation

    def analyze(self) -> Dict[str, any]:
        """Analyze flow for structural issues."""
        if not self._start_action:
            return {
                "orphaned_blocks": [],
                "missing_error_handlers": {},
                "unterminated_paths": [],
            }

        analyzer = FlowAnalyzer(self.blocks, self._start_action)
        return {
            "orphaned_blocks": analyzer.find_orphaned_blocks(),
            "missing_error_handlers": analyzer.find_missing_error_handlers(),
            "unterminated_paths": analyzer.find_unterminated_paths(),
        }

    def validate(self) -> bool:
        """Validate flow and raise error if issues found."""
        if self.debug:
            print("Validating flow structure...")

        if not self._start_action:
            raise FlowValidationError("Flow has no start action")

        analyzer = FlowAnalyzer(self.blocks, self._start_action)

        if analyzer.has_issues():
            if self.debug:
                print("Validation failed:")
            print(analyzer.generate_report())
            raise FlowValidationError("Flow validation failed")

        if self.debug:
            print("  Validation passed")

        return True

    def _build_metadata(self) -> dict:
        """Build metadata including block positions."""
        metadata = {
            "entryPointPosition": {"x": 0, "y": 0},
            "snapToGrid": False,
            "ActionMetadata": {},
            "Annotations": [],
        }

        # Calculate positions using layout engine
        positions = self.layout_engine.calculate_positions(
            self.blocks, self._start_action
        )

        for block_id, position in positions.items():
            metadata["ActionMetadata"][block_id] = {"position": position}

        return metadata

    def compile(self) -> dict:
        """Compile flow to AWS Connect JSON format."""
        if self.debug:
            print("Compiling flow...")

        # Run validation before compilation
        self.validate()

        if self.debug:
            print("Calculating block positions...")

        compiled_flow = {
            "Version": self.version,
            "StartAction": self._start_action or "",
            "Metadata": self._build_metadata(),
            "Actions": [block.to_dict() for block in self.blocks],
        }

        if self.debug:
            self._print_compilation_summary()

        return compiled_flow

    def _print_compilation_summary(self):
        """Print a professional summary of the compiled flow."""
        print("\nFlow compilation completed")
        print("-" * 40)
        print(f"Flow name: {self.name}")
        print(f"Total blocks: {len(self.blocks)}")

        if self._block_stats:
            print("Block types:")
            for block_type, count in sorted(self._block_stats.items()):
                print(f"  {block_type}: {count}")

        # Get canvas dimensions if available
        positions = self.layout_engine.calculate_positions(
            self.blocks, self._start_action
        )
        if positions:
            x_coords = [pos["x"] for pos in positions.values()]
            y_coords = [pos["y"] for pos in positions.values()]
            canvas_width = max(x_coords) - min(x_coords) + 200  # Add block width
            canvas_height = max(y_coords) - min(y_coords) + 100  # Add block height
            print(f"Canvas size: {canvas_width}px × {canvas_height}px")

        print("-" * 40)

    def compile_to_json(self, indent: int = 2) -> str:
        """Compile flow to JSON string."""
        return json.dumps(self.compile(), indent=indent)

    def compile_to_file(self, filepath: str):
        """Compile flow and save to file."""
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(self.compile_to_json())

        if self.debug:
            print(f"Saved to: {filepath}")
