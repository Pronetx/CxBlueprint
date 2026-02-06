# CLAUDE.md - AI Contributor Guide for CxBlueprint

This file provides comprehensive guidance to AI assistants (Claude, GitHub Copilot, etc.) when working with code in this repository.

## Section 1: Project Identity

### What CxBlueprint Is
Python DSL for Amazon Connect contact flow generation. Code-first approach to building IVR flows programmatically instead of using the visual editor.

### Core Philosophy
- **Pragmatic over perfect**: Working solutions over architectural purity
- **Infrastructure-as-code friendly**: Template placeholders for Terraform/CDK
- **Version control for flows**: Treat flows as code, diff-able, review-able
- **Zero external dependencies**: Pure Python stdlib only

### Primary Use Cases
1. **Terraform/CDK integration**: Generate flows with `${VARIABLE}` placeholders resolved at deploy time
2. **Programmatic flow generation**: Build complex IVR systems from data/config
3. **Flow modification via decompilation**: Load existing AWS flows, modify, re-deploy

### Non-Goals
- Not a visual flow editor (generates JSON for AWS visual editor)
- Not a runtime flow execution engine (AWS Connect handles execution)
- Not an AWS SDK wrapper (pure data generation, no API calls)

### Current Status
- **Block Coverage**: 24/48 AWS block types implemented (50%)
- **Maturity**: Production-ready for common IVR/routing use cases
- **Testing**: Hybrid approach (AWS validation scripts + examples, unit tests being added)

---

## Section 2: Architecture Deep Dive

### 2.1 Core Components

#### Flow (flow_builder.py, 449 lines)
**Responsibilities**:
- Unified builder/decompiler interface
- Block registry management
- Start action tracking
- Flow validation orchestration
- Compilation to AWS JSON

**Key Methods**:
- `Flow.build(name, description, debug)` → Create new flow
- `Flow.decompile(filepath, debug)` → Load existing AWS JSON
- `play_prompt(text)`, `get_input(text, timeout)`, `disconnect()` → Convenience block creators
- `invoke_lambda(arn, timeout)`, `lex_bot(...)`, `check_hours(...)` → Complex block creators
- `add(block)` → Generic block registration
- `validate()` → Structural validation (raises FlowValidationError)
- `compile()` → Generate AWS JSON dict
- `compile_to_json(indent)` → Generate JSON string
- `compile_to_file(filepath)` → Save to file

**Internal**:
- `_register_block(block)` → Add block to registry, set start_action if first, track stats
- `_build_metadata()` → Generate canvas positions via CanvasLayoutEngine

#### FlowBlock (blocks/base.py, 58 lines)
**Base dataclass** for all block types.

**Attributes**:
- `identifier: str` → UUID (auto-generated)
- `type: str` → AWS block type name (e.g., "GetParticipantInput")
- `parameters: Dict[str, Any]` → AWS-compatible parameter dict
- `transitions: Dict[str, Any]` → NextAction, Conditions, Errors

**Fluent API Methods** (all return `Self` for chaining):
- `then(next_block)` → Set NextAction transition
- `on_error(error_type, next_block)` → Add error transition

**Serialization**:
- `to_dict()` → Convert to AWS JSON format
- `from_dict(data)` → Parse from AWS JSON (classmethod)

**Pattern**: All 24 block implementations inherit this base class.

#### CanvasLayoutEngine (canvas_layout.py, 309 lines)
**Automatic positioning** for AWS Connect visual canvas.

**Algorithm** (5-phase BFS):
1. **Level assignment**: BFS from start, assign column based on shortest path distance
2. **Row assignment**: Assign rows within each level
   - NextAction blocks stay in same row (horizontal flow)
   - Branching (Conditions/Errors) creates new rows (vertical fan-out)
3. **Compaction**: Remove gaps, make rows contiguous (renumber 0, 1, 2, ...)
4. **Cumulative Y calculation**: Each row gets height based on tallest block
5. **Pixel conversion**: Convert (level, row) → (x, y) pixel coordinates

**Configuration Constants**:
- `BLOCK_WIDTH = 200` (estimated block width)
- `HORIZONTAL_SPACING = 280` (pixels between columns)
- `VERTICAL_SPACING_MIN = 180` (minimum pixels between rows)
- `START_X = 150`, `START_Y = 50` (canvas origin)

**No AWS dependencies**: Pure graph layout, works offline.

#### FlowAnalyzer (flow_analyzer.py, 142 lines)
**Pre-deployment structural validation**.

**Three Validation Checks**:
1. `find_orphaned_blocks()` → Detects blocks unreachable from start (BFS traversal)
2. `find_missing_error_handlers()` → GetParticipantInput requires: InputTimeLimitExceeded, NoMatchingCondition, NoMatchingError
3. `find_unterminated_paths()` → Blocks without NextAction/Conditions/Errors (except terminal types: DisconnectParticipant, EndFlowExecution, TransferToFlow, TransferContactToQueue)

**Integration**:
- Called automatically in `Flow.validate()` before compilation
- Raises `FlowValidationError` with human-readable report if issues found
- Can be called standalone via `flow.analyze()` (returns dict, doesn't raise)

### 2.2 Block Type System

**48 total AWS block types** (per AWS Connect API Reference)

**24 implemented (50% coverage)**:

**Participant Actions** (6/6 - 100%):
- MessageParticipant
- GetParticipantInput
- DisconnectParticipant
- ConnectParticipantWithLexBot
- MessageParticipantIteratively
- ShowView

**Flow Control** (7/15 - 47%):
- Compare
- CheckHoursOfOperation
- EndFlowExecution
- TransferToFlow
- Wait
- DistributeByPercentage
- CheckMetricData

**Contact Actions** (8/25 - 32%):
- UpdateContactAttributes
- UpdateContactRecordingBehavior
- UpdateContactTargetQueue
- TransferContactToQueue
- UpdateContactCallbackNumber
- UpdateContactEventHooks
- UpdateContactRoutingBehavior
- CreateTask

**Interactions** (2/8 - 25%):
- InvokeLambdaFunction
- CreateCallbackContact

**Registration**: BLOCK_TYPE_MAP in flow_builder.py (lines 48-76) maps AWS type strings to Python classes for decompilation.

**Implementation Status**: Each category directory has README.md listing implemented vs remaining blocks.

### 2.3 Type Definitions (blocks/types.py, 202 lines)

**Shared data structures** used across multiple block types:

**Media** → Audio/video file reference
- `uri: str` (S3 URI)
- `source_type: str = "S3"`
- `media_type: str = "Audio"`

**LexV2Bot** → Lex V2 bot configuration
- `alias_arn: str` (bot alias ARN)

**LexBot** → Legacy Lex bot configuration
- `name: str`, `region: str`, `alias: str`

**ViewResource** → Agent workspace view
- `id: str`, `version: str`

**InputValidation** → Phone/custom validation for GetParticipantInput
- `phone_number_validation: Optional[PhoneNumberValidation]`
- `custom_validation: Optional[CustomValidation]`

**DTMFConfiguration** → DTMF input settings
- `input_termination_sequence`, `disable_cancel_key`, `interdigit_time_limit_seconds`

**Pattern**: All use dataclasses with `to_dict()`/`from_dict()` serialization methods.

### 2.4 Data Flow & Lifecycle

**Build Mode**:
```
Flow.build(name) →
  add blocks via convenience methods (play_prompt, get_input) →
  wire with fluent API (.then(), .when(), .on_error()) →
  validate() checks structure (FlowAnalyzer) →
  compile() generates AWS JSON (with canvas positions)
```

**Decompile Mode**:
```
Flow.decompile(filepath) →
  parse JSON →
  map block types via BLOCK_TYPE_MAP →
  create FlowBlock instances →
  modify blocks programmatically →
  validate() →
  compile() →
  AWS JSON output
```

**Validation Pipeline**:
```
Flow.validate() →
  FlowAnalyzer(blocks, start_action) →
  if has_issues():
    generate_report() →
    raise FlowValidationError
```

**Canvas Layout**:
```
CanvasLayoutEngine.calculate_positions() →
  BFS traversal →
  level assignment (columns) →
  row assignment (within columns) →
  pixel positions →
  stored in Metadata.ActionMetadata for AWS visual editor
```

---

## Section 3: Design Patterns & Conventions

### 3.1 Fluent API Pattern (Critical for Usability)

**All blocks return `Self` for method chaining**.

**Base methods** (FlowBlock):
- `then(next_block)` → Set NextAction
- `on_error(error_type, handler_block)` → Add error transition

**Specialized methods** (block-specific):
- `when(value, block)` → GetParticipantInput conditional routing
- `otherwise(block)` → GetParticipantInput default fallback
- `on_intent(intent_name, block)` → ConnectParticipantWithLexBot intent routing

**Example**:
```python
menu = flow.get_input("Press 1 or 2", timeout=10)
menu.when("1", opt1).when("2", opt2).otherwise(default).on_error("InputTimeLimitExceeded", timeout_handler)
```

### 3.2 AWS Parameter Serialization Pattern (Important Quirk)

**CRITICAL**: AWS Connect JSON expects **string representations** of all parameter values.

**Conversion Rules**:
- Python `bool` → AWS `"True"` or `"False"` (string, not boolean)
- Python `int` → AWS `"5"`, `"8"`, `"900"` (string, not number)
- Python `Optional[str]` → AWS `"value"` or omit parameter

**Example**:
```python
# In Python dataclass
timeout: int = 5
store_input: bool = False

# In AWS JSON Parameters
"InputTimeLimitSeconds": "5"
"StoreInput": "False"
```

**Conversion happens in**:
- `_build_parameters()` or `to_dict()` → Python types to AWS strings
- `from_dict()` → AWS strings to Python types

**Reverse conversion**:
```python
# Parsing from AWS
timeout = int(params.get("InputTimeLimitSeconds", "5"))
store = params.get("StoreInput", "False") == "True"
```

### 3.3 Block Registration Pattern (All Convenience Methods Follow This)

```python
def convenience_method(self, ...args) -> BlockType:
    """Convenience method for creating BlockType."""
    block = BlockType(
        identifier=str(uuid.uuid4()),  # Always auto-generate UUID
        ...args  # Typed parameters
    )
    return self._register_block(block)  # Adds to self.blocks, tracks stats, sets start_action if first
```

**Pattern used by**: `play_prompt()`, `get_input()`, `disconnect()`, `invoke_lambda()`, `lex_bot()`, `check_hours()`, `update_attributes()`, `show_view()`, `end_flow()`.

### 3.4 Decompilation Pattern (For Adding from_dict to Blocks)

```python
@classmethod
def from_dict(cls, data: dict) -> 'BlockType':
    """Parse block from AWS JSON format."""
    identifier = data.get("Identifier")
    params = data.get("Parameters", {})
    transitions = data.get("Transitions", {})

    # Parse AWS string parameters back to Python types
    timeout = int(params.get("InputTimeLimitSeconds", "5"))
    store = params.get("StoreInput", "False") == "True"

    # Reconstruct nested objects (Media, LexBot, ViewResource)
    media = Media.from_dict(params["Media"]) if "Media" in params else None

    return cls(
        identifier=identifier,
        timeout=timeout,
        store_input=store,
        media=media,
        parameters=params,  # Preserve raw params
        transitions=transitions
    )
```

### 3.5 Block Implementation Template (Use This for New Blocks)

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from cxblueprint.blocks.base import FlowBlock

@dataclass
class NewBlockType(FlowBlock):
    """
    Brief description of block purpose.

    AWS API Reference: https://docs.aws.amazon.com/connect/latest/APIReference/...
    """

    # Typed parameters matching AWS Parameters
    param1: str
    param2: Optional[int] = None
    param3: bool = False

    def __post_init__(self):
        self.type = "AWSBlockTypeName"  # Exact AWS type name (case-sensitive)
        self._build_parameters()

    def _build_parameters(self):
        """Convert Python types to AWS parameter dict."""
        self.parameters = {
            "Param1": self.param1,
        }
        if self.param2 is not None:
            self.parameters["Param2"] = str(self.param2)  # String conversion
        self.parameters["Param3"] = str(self.param3)  # Boolean as string

    @classmethod
    def from_dict(cls, data: dict) -> 'NewBlockType':
        """Parse from AWS JSON format."""
        params = data.get("Parameters", {})
        return cls(
            identifier=data["Identifier"],
            param1=params.get("Param1", ""),
            param2=int(params["Param2"]) if "Param2" in params else None,
            param3=params.get("Param3", "False") == "True",
            parameters=params,
            transitions=data.get("Transitions", {})
        )
```

---

## Section 4: Critical Workflows (How To...)

### 4.1 Adding New Block Types (8-Step Process)

1. **Create file**: `src/blocks/<category>/<block_name>.py` inheriting from FlowBlock
2. **Set type**: Set `type` attribute to match AWS block type name exactly (case-sensitive)
3. **Define fields**: Add dataclass fields with Python types matching AWS Parameters
4. **Implement __post_init__**: Call `_build_parameters()` to populate `self.parameters`
5. **Implement _build_parameters**: Convert Python types to AWS string parameters
6. **Implement from_dict**: Parse AWS JSON back to Python types (for decompilation)
7. **Register**: Add to `BLOCK_TYPE_MAP` in `flow_builder.py` (line 48)
8. **Export**: Add to category's `__init__.py` exports

**Optional**: Add convenience method to Flow class if commonly used (e.g., `play_prompt()`, `get_input()`).

### 4.2 Testing Approach (Hybrid Strategy)

**Unit Tests** (NEW - being added):
- `pytest` for core logic without AWS dependencies
- Test modules:
  - `tests/test_flow_analyzer.py` → Validation logic
  - `tests/test_canvas_layout.py` → Positioning algorithm
  - `tests/test_decompilation.py` → Round-trip fidelity (compile → decompile → compile)
  - `tests/test_flow_builder.py` → Flow class API integration
- Run: `pytest -v`

**Integration Tests** (EXISTING):
- AWS validation scripts test against live AWS Connect instance
- `src/scripts/validate_flow.sh` → Creates flow in AWS, validates schema, deletes
- `src/scripts/validate_all_flows.sh` → Batch validation
- Requires AWS credentials with profile `cxforge` and Connect instance access

**Example Files** (EXISTING):
- Executable demonstrations double as smoke tests
- `examples/code_examples/simple_flow.py` (2 blocks)
- `examples/code_examples/menu_flow.py` (5 blocks)
- `examples/code_examples/burger_order_flow.py` (20 blocks, complex branching)

### 4.3 Debugging Flows

**Enable debug output**:
```python
flow = Flow.build("Test Flow", debug=True)
# Prints: block additions, validation results, compilation summary, canvas dimensions
```

**Analyze without raising errors**:
```python
issues = flow.analyze()
print(issues["orphaned_blocks"])
print(issues["missing_error_handlers"])
print(issues["unterminated_paths"])
```

**Validate with exceptions**:
```python
try:
    flow.validate()
except FlowValidationError as e:
    print(f"Validation failed: {e}")
```

### 4.4 Template Placeholders for IaC

Use placeholders for values resolved at deployment time:
- **Terraform**: `${VARIABLE}`
- **Jinja2/Generic**: `{{VARIABLE}}`

**Common placeholders**:
- Lambda ARNs: `${COUNTER_LAMBDA_ARN}`
- Flow ARNs: `{{GOODBYE_FLOW_ARN}}`
- Hours of Operation IDs: `{{HOURS_ID}}`
- Queue IDs: `${SUPPORT_QUEUE_ID}`

**Example**:
```python
flow.invoke_lambda(function_arn="${COUNTER_LAMBDA_ARN}")
flow.check_hours(hours_of_operation_id="{{HOURS_ID}}")
flow.transfer_to_flow(contact_flow_id="${GOODBYE_FLOW_ARN}")
```

---

## Section 5: Known Limitations & Architectural Decisions

### 5.1 Design Trade-offs

**No AWS SDK dependency**:
- Pure data generation, no runtime AWS calls
- Trade-off: Validation happens at deployment, not build time
- Benefit: Fast, offline, no AWS credentials required

**String-based serialization**:
- Follows AWS API exactly (all parameters as strings)
- Trade-off: Requires conversion boilerplate in blocks
- Benefit: Guaranteed AWS compatibility

**BFS layout algorithm**:
- Simple, predictable, fast
- Trade-off: Not optimal for all graph topologies, may have visual overlaps in very complex flows
- Benefit: Good enough for 95% of use cases

**No input validation**:
- Relies on AWS API for validation (ARN formats, timeout ranges)
- Trade-off: Errors surface late (at deployment)
- Benefit: Faster development, don't duplicate AWS validation logic

**Pragmatic testing**:
- AWS integration tests + examples instead of comprehensive unit tests (changing to hybrid approach)
- Trade-off: Refactoring risk, need AWS credentials
- Benefit: Confidence in AWS compatibility

### 5.2 Block Coverage

**24/48 AWS block types implemented (50%)**

**Focus areas**:
- Common IVR/routing patterns
- Lambda integration
- Lex bot integration
- Basic contact attribute manipulation

**Not prioritized**:
- Customer Profiles blocks (4 types) - less common use case
- Advanced analytics blocks (3 types) - specialized
- Complex routing blocks (6 types) - niche scenarios

**Strategy**: Implement on-demand based on user needs.

### 5.3 Type Safety

**Good**:
- Comprehensive type hints throughout
- Dataclasses for all blocks and types
- TypeVar for generic method returns

**Gaps**:
- No mypy enforcement in development/CI (being added)
- String-to-type conversions not validated at build time
- Some `Dict[str, Any]` usage in parameters (intentional for flexibility)

---

## Section 6: File Navigation Guide

### Critical Files (Modify Frequently)

**[src/flow_builder.py](src/flow_builder.py)** (449 lines)
- Main API, block registration, compilation
- BLOCK_TYPE_MAP for decompilation
- All convenience methods (play_prompt, get_input, etc.)
- Validation and compilation orchestration

**[src/blocks/base.py](src/blocks/base.py)** (58 lines)
- FlowBlock base class
- Fluent API methods (then, on_error)
- Changes here affect all 24 block implementations

**[src/blocks/types.py](src/blocks/types.py)** (202 lines)
- Shared type definitions
- Nested object serialization
- Media, LexV2Bot, ViewResource, InputValidation, DTMFConfiguration

### Core Logic (Understand Before Modifying)

**[src/canvas_layout.py](src/canvas_layout.py)** (309 lines)
- Complex BFS positioning algorithm
- High value for unit testing
- Modify carefully, easy to break visual layout

**[src/flow_analyzer.py](src/flow_analyzer.py)** (142 lines)
- Validation rules
- Easy to extend with new checks
- Good starting point for contributions

### Block Implementations (24 Files Across 4 Categories)

**[src/blocks/participant_actions/](src/blocks/participant_actions/)** - 6 blocks (COMPLETE: 6/6)
**[src/blocks/flow_control_actions/](src/blocks/flow_control_actions/)** - 7 blocks (PARTIAL: 7/15)
**[src/blocks/contact_actions/](src/blocks/contact_actions/)** - 8 blocks (PARTIAL: 8/25)
**[src/blocks/interactions/](src/blocks/interactions/)** - 2 blocks (PARTIAL: 2/8)

Each category has README.md with implementation status.

### Documentation

**[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - Public API for users
**[docs/FLOW_BUILDER.md](docs/FLOW_BUILDER.md)** - Builder patterns and usage
**[docs/development/claude-instructions.md](docs/development/claude-instructions.md)** - THIS FILE (AI contributor guide)
**[readme.md](readme.md)** - User-facing project overview

### Examples (Executable, Tested)

**[examples/code_examples/](examples/code_examples/)** - 6 Python example flows
**[examples/complete_terraform_example/](examples/complete_terraform_example/)** - End-to-end deployment

### Scripts (AWS Validation)

**[src/scripts/validate_flow.sh](src/scripts/validate_flow.sh)** - Validate single flow
**[src/scripts/validate_all_flows.sh](src/scripts/validate_all_flows.sh)** - Batch validation
**[src/scripts/download_flows.sh](src/scripts/download_flows.sh)** - Download from AWS Connect

---

## Section 7: Development Guidelines for AI Contributors

### 7.1 Code Style

**Dataclasses everywhere**:
- All blocks use `@dataclass` decorator
- All type definitions use `@dataclass`
- Prefer dataclasses over plain classes

**Type hints mandatory**:
- All public methods
- All function signatures
- All class attributes
- Use `Optional[T]` for nullable, `Dict[str, Any]` when flexible

**Docstrings with AWS links**:
- Include AWS API Reference links in block docstrings
- Explain purpose, parameters, restrictions, error types
- Document mutually exclusive parameters

**Fluent API consistency**:
- All block methods that modify transitions return `Self`
- Enables method chaining
- Critical for usability

**No external dependencies**:
- Keep library standalone (only Python stdlib)
- Do not add requirements to requirements.txt (only requirements-dev.txt)

### 7.2 AWS API Alignment

**Block type names match AWS exactly** (case-sensitive):
- Correct: `GetParticipantInput`
- Wrong: `get_participant_input`, `getParticipantInput`

**Parameter names match AWS exactly**:
- Correct: `InputTimeLimitSeconds`
- Wrong: `input_time_limit_seconds`, `timeLimit`

**Follow AWS API Reference** structure:
- Check official AWS Connect API documentation for each block
- Match parameter structure exactly
- Document all restrictions and error types

**Test against live AWS**:
- Use validation scripts to verify AWS compatibility
- Don't assume compatibility without testing

### 7.3 Commit Patterns (Observed from Git History)

**Descriptive messages**:
- "Implement CheckMetricData block type"
- "Fix positioning overlap for nested conditions"
- "Add round-trip decompilation tests"

**Incremental changes**:
- One block type per commit
- Not bulk refactors
- Small, reviewable diffs

**Cleanup commits**:
- "Remove unused imports"
- "Update canvas_layout comments"
- "Fix type hints in flow_builder"

### 7.4 What NOT to Do (Anti-Patterns)

**Don't add external dependencies**:
- Keep library standalone
- No boto3, no requests, no pandas
- Only stdlib

**Don't create abstractions for single-use cases**:
- Wait for pattern to emerge (3+ uses)
- Simple is better than clever

**Don't optimize prematurely**:
- Canvas layout is "good enough"
- Focus on correctness over performance

**Don't break AWS JSON compatibility**:
- Always test against AWS API
- String serialization is required, not optional

**Don't skip validation**:
- Always call `Flow.validate()` before `compile()`
- Validation prevents deployment failures

**Don't over-engineer block implementations**:
- Simple dataclasses are fine
- Don't add complexity without clear benefit

### 7.5 When to Ask for Clarification

**Ask when**:
- AWS API documentation is ambiguous about required vs optional parameters
- Multiple AWS block types could serve the same purpose (which to implement?)
- Canvas layout behavior differs from AWS Connect visual editor (is this a bug or expected?)
- Unsure whether to add unit tests or rely on AWS validation for a feature
- Parameter type conversions are unclear (string? int? both?)

**Don't assume**:
- Parameter requirements without checking AWS API Reference
- Backward compatibility without testing decompilation
- Validation rules without understanding AWS Connect behavior

---

## Section 8: Future Development Roadmap

### High-Priority Improvements

1. **Complete pytest unit test suite** (IN PROGRESS)
   - FlowAnalyzer tests (validation logic)
   - CanvasLayoutEngine tests (positioning algorithm)
   - Round-trip decompilation tests
   - Flow class integration tests

2. **Set up pre-commit hooks**
   - black for code formatting
   - mypy for type checking
   - ruff for linting

3. **Add mypy type checking**
   - Configure in pyproject.toml
   - Run in CI/CD
   - Fix type errors incrementally

4. **Standardize error handling**
   - Exception hierarchy (ValidationError, CompilationError, DecompilationError)
   - Better error messages with suggested fixes
   - Error codes for programmatic handling

5. **Serialization helpers**
   - Centralize AWS string conversion logic
   - Reduce boilerplate in block implementations
   - `to_aws_bool()`, `from_aws_bool()`, `to_aws_int()`, `from_aws_int()`

### Medium-Priority Improvements

1. **Implement remaining 24 block types**
   - Prioritize by usage frequency
   - UpdateContactData (common)
   - TransferContactToAgent (common)
   - Loop (flow control)

2. **Extract parameter validation to mixins**
   - Reusable validation patterns
   - Consistent error messages

3. **Add flow statistics method**
   - `Flow.stats()` → block counts, error handler coverage, canvas dimensions

4. **Document canvas layout algorithm**
   - Detailed explanation with diagrams
   - Edge cases and limitations

5. **Add block usage examples in docstrings**
   - Code examples for each block
   - Common patterns and gotchas

### Low-Priority Improvements (Nice-to-Have)

1. **CI/CD pipeline** with GitHub Actions
2. **Package as pip-installable** module
3. **Flow diff tool** for version control
4. **Visual flow renderer** (Mermaid/Graphviz)
5. **Flow template library** for common patterns
6. **Flow linter** for best practices

---

## Quick Reference Commands

### Run Examples
```bash
cd examples/code_examples
python simple_flow.py
python menu_flow.py
python burger_order_flow.py
```

### Run Tests
```bash
pytest -v                                    # All tests
pytest tests/test_flow_analyzer.py          # Specific module
pytest --cov=src --cov-report=html          # With coverage
```

### Validate Against AWS
```bash
cd src/scripts
./validate_flow.sh ../../examples/code_examples/simple.json
./validate_all_flows.sh
```

### Type Check
```bash
mypy src/flow_builder.py src/flow_analyzer.py src/canvas_layout.py
```

---

## End of CLAUDE.md

This guide is optimized for AI assistant comprehension. For human-readable documentation, see [readme.md](../../readme.md) and [docs/API_REFERENCE.md](../API_REFERENCE.md).
