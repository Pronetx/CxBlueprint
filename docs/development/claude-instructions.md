# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CxBlueprint is a Python DSL for creating and editing Amazon Connect contact flows. It provides two core capabilities:

1. **Flow Builder**: Programmatically create contact flows with a fluent API
2. **Flow Decompiler**: Parse AWS Connect JSON into Flow objects for modification

Both capabilities are unified in the `Flow` class:
- `Flow.build(name)` - Create new flows
- `Flow.decompile(filepath)` - Load and modify existing flows

## Commands

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

- **`src/flow_builder.py`** - `Flow` class for programmatic flow creation and decompilation. Auto-generates UUIDs, sets entry points, calculates block positions using BFS layout algorithm. Includes `Flow.build()` for creating flows and `Flow.decompile()` for loading existing flows.

- **`src/contact_flow.py`** - `ContactFlow` container that holds actions and serializes back to AWS JSON (used internally by decompilation).

- **`src/blocks/base.py`** - `FlowBlock` dataclass base with fluent API methods (`then()`, `on_error()`) and serialization.

- **`src/blocks/`** - Individual block implementations (21 total) that inherit from `FlowBlock`. Each handles its own parameters and type.

### Flow Builder Fluent API Pattern

Blocks are created via factory methods, then wired with chained calls:
```python
flow = Flow.build("My Flow")
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

`Flow._calculate_positions_bfs()` uses breadth-first search to position blocks level-by-level for the AWS Connect visual canvas. Collision detection prevents overlapping blocks.

## Data Flow

```
JSON files → Flow.decompile() → Flow instance with FlowBlock objects
                                                    ↓
Flow → FlowBlock objects → compile() → JSON (output/)
```

## Adding New Block Types

1. Create `src/blocks/new_block_type.py` inheriting from `FlowBlock`
2. Set `type` class attribute to match AWS block type name
3. Implement `from_dict()` if custom parameter parsing needed
4. Add to `src/blocks/__init__.py` exports
5. Add to `BLOCK_TYPE_MAP` in `src/flow_builder.py`
6. Optionally add factory method to `Flow`
