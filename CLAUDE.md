# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CxBlueprint is a Python DSL for creating and editing Amazon Connect contact flows. It provides two core capabilities:

1. **Decompiler**: Parse AWS Connect JSON into Python block objects
2. **Flow Builder**: Programmatically create contact flows with a fluent API

## Commands

### Run the decompiler (batch process all flows)
```bash
cd src && python main.py
```
This reads JSON files from `input/`, decompiles them to Python objects, recompiles them, and writes to `output/` with `Cx_` prefix.

### Run a flow builder example
```bash
cd examples && python simple_flow.py
cd examples && python menu_flow.py
```

### Validate a flow against AWS Connect API
```bash
./validate_flow.sh output/my_flow.json
```
Requires AWS CLI configured with profile `cxforge` and access to the Connect instance.

### Validate all flows
```bash
./validate_all_flows.sh
```

## Architecture

### Core Components

- **`src/flow_builder.py`** - `ContactFlowBuilder` class for programmatic flow creation. Auto-generates UUIDs, sets entry points, calculates block positions using BFS layout algorithm.

- **`src/decompiler.py`** - `FlowDecompiler` class that maps AWS block types to Python classes and parses JSON into `ContactFlow` objects.

- **`src/contact_flow.py`** - `ContactFlow` container that holds actions and serializes back to AWS JSON.

- **`src/blocks/base.py`** - `FlowBlock` dataclass base with fluent API methods (`then()`, `on_error()`) and serialization.

- **`src/blocks/`** - Individual block implementations (21 total) that inherit from `FlowBlock`. Each handles its own parameters and type.

### Flow Builder Fluent API Pattern

Blocks are created via factory methods, then wired with chained calls:
```python
flow = ContactFlowBuilder("My Flow")
welcome = flow.play_prompt("Hello")
menu = flow.get_input("Press 1 or 2")
disconnect = flow.disconnect()

welcome.then(menu).on_error("NoMatchingError", disconnect)
menu.when("1", option1).when("2", option2).otherwise(disconnect)
```

### Block Wiring

- `then(block)` - Sets NextAction transition
- `on_error(error_type, block)` - Adds error transition
- `when(value, block)` - Adds condition (GetParticipantInput only)
- `otherwise(block)` - Sets default action (GetParticipantInput only)

### Layout Algorithm

`ContactFlowBuilder._calculate_positions_bfs()` uses breadth-first search to position blocks level-by-level for the AWS Connect visual canvas. Collision detection prevents overlapping blocks.

## Data Flow

```
JSON files (input/) → FlowDecompiler → ContactFlow → FlowBlock objects
                                                    ↓
ContactFlowBuilder → FlowBlock objects → compile() → JSON (output/)
```

## Adding New Block Types

1. Create `src/blocks/new_block_type.py` inheriting from `FlowBlock`
2. Set `type` class attribute to match AWS block type name
3. Implement `from_dict()` if custom parameter parsing needed
4. Add to `src/blocks/__init__.py` exports
5. Add to `FlowDecompiler.BLOCK_TYPE_MAP` in `src/decompiler.py`
6. Optionally add factory method to `ContactFlowBuilder`
