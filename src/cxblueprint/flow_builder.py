"""
Flow - Unified flow builder and decompiler
"""

from pathlib import Path
import json
from typing import List, Optional, Dict, Set, Tuple, TypeVar, Type, Any
import uuid
from .canvas_layout import CanvasLayoutEngine
from .flow_analyzer import FlowAnalyzer, FlowValidationError
from .blocks.base import FlowBlock
from .blocks.participant_actions import (
    MessageParticipant,
    MessageParticipantIteratively,
    DisconnectParticipant,
    GetParticipantInput,
    ConnectParticipantWithLexBot,
    ShowView,
)
from .blocks.flow_control_actions import (
    TransferToFlow,
    CheckHoursOfOperation,
    EndFlowExecution,
    Compare,
    Wait,
    DistributeByPercentage,
    CheckMetricData,
)
from .blocks.interactions import (
    InvokeLambdaFunction,
    CreateCallbackContact,
)
from .blocks.contact_actions import (
    UpdateContactAttributes,
    UpdateContactTargetQueue,
    TransferContactToQueue,
    UpdateContactRecordingBehavior,
    UpdateContactCallbackNumber,
    UpdateContactEventHooks,
    UpdateContactRoutingBehavior,
    CreateTask,
)
from .blocks.types import LexV2Bot, LexBot, ViewResource, Media

T = TypeVar("T", bound=FlowBlock)  # Generic FlowBlock type for method returns

# Map AWS block types to Python classes (for decompilation)
BLOCK_TYPE_MAP: Dict[str, Type[FlowBlock]] = {
    # Participant Actions
    "DisconnectParticipant": DisconnectParticipant,
    "MessageParticipant": MessageParticipant,
    "MessageParticipantIteratively": MessageParticipantIteratively,
    "GetParticipantInput": GetParticipantInput,
    "ConnectParticipantWithLexBot": ConnectParticipantWithLexBot,
    "ShowView": ShowView,
    # Flow Control Actions
    "EndFlowExecution": EndFlowExecution,
    "TransferToFlow": TransferToFlow,
    "Compare": Compare,
    "CheckHoursOfOperation": CheckHoursOfOperation,
    "Wait": Wait,
    "DistributeByPercentage": DistributeByPercentage,
    "CheckMetricData": CheckMetricData,
    # Interactions
    "InvokeLambdaFunction": InvokeLambdaFunction,
    "CreateCallbackContact": CreateCallbackContact,
    # Contact Actions
    "UpdateContactRecordingBehavior": UpdateContactRecordingBehavior,
    "UpdateContactAttributes": UpdateContactAttributes,
    "UpdateContactTargetQueue": UpdateContactTargetQueue,
    "TransferContactToQueue": TransferContactToQueue,
    "UpdateContactCallbackNumber": UpdateContactCallbackNumber,
    "UpdateContactEventHooks": UpdateContactEventHooks,
    "UpdateContactRoutingBehavior": UpdateContactRoutingBehavior,
    "CreateTask": CreateTask,
}


class Flow:
    """Unified flow builder and decompiler for AWS Connect flows."""

    def __init__(self, name: str, debug: bool = False):
        self.name = name
        self.version = "2019-10-30"
        self.blocks: List[FlowBlock] = []
        self._start_action: Optional[str] = None
        self.debug = debug
        self.layout_engine = CanvasLayoutEngine(debug)
        # Statistics tracking
        self._block_stats: dict[str, int] = {}

        if debug:
            print(f"Building flow: {name}")

    @classmethod
    def build(cls, name: str, description: str = "", debug: bool = False) -> "Flow":
        """
        Create a new flow builder.

        Args:
            name: The name of the contact flow
            description: Optional description (currently unused but reserved)
            debug: Enable debug output

        Returns:
            Flow instance for building

        Example:
            >>> flow = Flow.build("Customer Service Flow")
            >>> flow.play_prompt("Hello!")
            >>> json_output = flow.compile_to_json()
        """
        return cls(name, debug)

    @classmethod
    def decompile(cls, filepath: str, debug: bool = False) -> "Flow":
        """
        Decompile an AWS Connect flow JSON file.

        Args:
            filepath: Path to the JSON file
            debug: Enable debug output

        Returns:
            Flow instance with loaded blocks

        Example:
            >>> flow = Flow.decompile("existing_flow.json")
            >>> # Modify flow...
            >>> updated_json = flow.compile_to_json()
        """
        # Load JSON
        with open(filepath, "r") as f:
            flow_json = json.load(f)

        # Create Flow instance
        flow_name = flow_json.get("Name", "Decompiled Flow")
        instance = cls(flow_name, debug)

        # Track unknown block types
        unknown_types = set()

        # Decompile blocks using BLOCK_TYPE_MAP
        actions = flow_json.get("Actions", [])
        for action_data in actions:
            block_type = action_data.get("Type")

            if block_type not in BLOCK_TYPE_MAP:
                unknown_types.add(block_type)
                if debug:
                    print(f"[WARNING] Unknown block type: {block_type}")
                    print(f"   Block data: {json.dumps(action_data, indent=2)}\n")

            block_class = BLOCK_TYPE_MAP.get(block_type, FlowBlock)
            block = block_class.from_dict(action_data)
            instance.blocks.append(block)
            instance._track_block_type(block)

        if unknown_types and debug:
            print(
                f"[SUMMARY] Found {len(unknown_types)} unknown block type(s): {', '.join(sorted(unknown_types))}\n"
            )

        # Set start action
        if flow_json.get("StartAction"):
            instance._start_action = flow_json["StartAction"]

        if debug:
            print(f"Decompiled flow: {flow_name} ({len(instance.blocks)} blocks)")

        return instance

    @classmethod
    def load(cls, filepath: str, debug: bool = False) -> "Flow":
        """Load an AWS Connect flow from a JSON file. Alias for decompile()."""
        return cls.decompile(filepath, debug)

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
        text: str | None = None,
        lex_v2_bot: LexV2Bot | None = None,
        lex_bot: LexBot | None = None,
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
        self, hours_of_operation_id: str | None = None, **kwargs
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

    def transfer_to_queue(self) -> TransferContactToQueue:
        """Create a transfer to queue block.

        The target queue must be set beforehand via update_target_queue()
        or UpdateContactTargetQueue.
        """
        block = TransferContactToQueue(identifier=str(uuid.uuid4()))
        return self._register_block(block)

    def wait(self, seconds: int = 60) -> Wait:
        """Create a wait block.

        Args:
            seconds: Time to wait in seconds (default: 60)
        """
        block = Wait(identifier=str(uuid.uuid4()), time_limit_seconds=seconds)
        return self._register_block(block)

    def pause_recording(self) -> UpdateContactRecordingBehavior:
        """Pause call recording (PCI compliance)."""
        block = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
            recording_behavior={"RecordedParticipants": []},
        )
        return self._register_block(block)

    def resume_recording(self) -> UpdateContactRecordingBehavior:
        """Resume call recording."""
        block = UpdateContactRecordingBehavior(
            identifier=str(uuid.uuid4()),
            recording_behavior={"RecordedParticipants": ["Agent", "Customer"]},
        )
        return self._register_block(block)

    def compare(self, comparison_value: str) -> Compare:
        """Create a compare/branch block for conditional logic.

        Args:
            comparison_value: JSONPath expression to evaluate
                (e.g. '$.Attributes.customer_tier')
        """
        block = Compare(
            identifier=str(uuid.uuid4()), comparison_value=comparison_value
        )
        return self._register_block(block)

    def distribute_by_percentage(
        self, percentages: list[int]
    ) -> DistributeByPercentage:
        """Create a percentage-based distribution block for A/B testing.

        Args:
            percentages: List of percentages that must sum to 100.
                e.g. [50, 50] for 50/50, [30, 40, 30] for 3-way split.

        Example:
            split = flow.distribute_by_percentage([50, 50])
            split.branch(0, path_a).otherwise(path_b)
        """
        if sum(percentages) != 100:
            raise ValueError(f"Percentages must sum to 100, got {sum(percentages)}")
        block = DistributeByPercentage(
            identifier=str(uuid.uuid4()), percentages=percentages
        )
        return self._register_block(block)

    # Compilation

    def analyze(self) -> Dict[str, Any]:
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

    def stats(self) -> Dict[str, Any]:
        """
        Get comprehensive flow statistics.

        Returns:
            Dictionary containing:
            - total_blocks: Total number of blocks
            - block_types: Count of each block type
            - error_handler_coverage: Error handler statistics
            - canvas_dimensions: Width and height of canvas
            - validation_status: "passed" or "failed"

        Example:
            >>> flow = Flow.build("Test")
            >>> stats = flow.stats()
            >>> print(f"Total blocks: {stats['total_blocks']}")
        """
        # Basic counts
        total_blocks = len(self.blocks)
        block_types = dict(self._block_stats)

        # Error handler coverage
        blocks_requiring_handlers = sum(
            1 for block in self.blocks if block.type == "GetParticipantInput"
        )
        blocks_with_handlers = 0
        if blocks_requiring_handlers > 0:
            analyzer = (
                FlowAnalyzer(self.blocks, self._start_action)
                if self._start_action
                else None
            )
            if analyzer:
                missing = analyzer.find_missing_error_handlers()
                blocks_with_handlers = blocks_requiring_handlers - len(missing)

        coverage_percent = (
            (blocks_with_handlers / blocks_requiring_handlers * 100)
            if blocks_requiring_handlers > 0
            else 100.0
        )

        # Canvas dimensions
        canvas_width = 0
        canvas_height = 0
        if self._start_action:
            positions = self.layout_engine.calculate_positions(
                self.blocks, self._start_action
            )
            if positions:
                x_coords = [pos["x"] for pos in positions.values()]
                y_coords = [pos["y"] for pos in positions.values()]
                canvas_width = max(x_coords) - min(x_coords) + 200  # Add block width
                canvas_height = max(y_coords) - min(y_coords) + 100  # Add block height

        # Validation status
        validation_status = "unknown"
        if self._start_action:
            analyzer = FlowAnalyzer(self.blocks, self._start_action)
            validation_status = "failed" if analyzer.has_issues() else "passed"

        return {
            "total_blocks": total_blocks,
            "block_types": block_types,
            "error_handler_coverage": {
                "blocks_with_handlers": blocks_with_handlers,
                "blocks_requiring_handlers": blocks_requiring_handlers,
                "coverage_percent": round(coverage_percent, 1),
            },
            "canvas_dimensions": {
                "width": canvas_width,
                "height": canvas_height,
            },
            "validation_status": validation_status,
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

        # Build a lookup from block identifier to block object
        blocks_by_id = {block.identifier: block for block in self.blocks}

        for block_id, position in positions.items():
            action_meta: Dict[str, Any] = {"position": position}

            # Enrich DistributeByPercentage with conditionMetadata
            block = blocks_by_id.get(block_id)
            if isinstance(block, DistributeByPercentage) and block.percentages:
                conditions, condition_metadata = block.build_condition_metadata()
                action_meta["conditions"] = conditions
                action_meta["conditionMetadata"] = condition_metadata

            metadata["ActionMetadata"][block_id] = action_meta

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
