# CxBlueprint

Programmatic Amazon Connect contact flow generation using Python. Lets AI models and developers build contact flows from plain English instead of hand-writing JSON.

**23 of 54 AWS Connect block types supported (43%)** — covers all common IVR, routing, A/B testing, and queue transfer patterns. Includes an [MCP server](#mcp-server) for AI-assisted flow generation with Claude Desktop, Cursor, and VS Code.

## Simple Example

```python
from cxblueprint import Flow

flow = Flow.build("Burger Order")

welcome = flow.play_prompt("Welcome to Burger Palace!")
menu = flow.get_input("Press 1 for Classic Burger or 2 for Veggie Burger", timeout=10)
welcome.then(menu)

classic = flow.play_prompt("You selected Classic Burger. Your order is confirmed!")
veggie = flow.play_prompt("You selected Veggie Burger. Your order is confirmed!")
error_msg = flow.play_prompt("Invalid selection. Goodbye.")

disconnect = flow.disconnect()

menu.when("1", classic) \
    .when("2", veggie) \
    .otherwise(error_msg) \
    .on_error("InputTimeLimitExceeded", error_msg) \
    .on_error("NoMatchingCondition", error_msg) \
    .on_error("NoMatchingError", error_msg)

classic.then(disconnect)
veggie.then(disconnect)
error_msg.then(disconnect)

flow.compile_to_file("burger_order.json")
```

### Terraform Template Example

Use placeholders for dynamic resource ARNs:

```python
from cxblueprint import Flow

flow = Flow.build("Counter Flow")

welcome = flow.play_prompt("Thank you for calling!")
invoke_counter = flow.invoke_lambda(
    function_arn="${COUNTER_LAMBDA_ARN}",  # Resolved by Terraform
    timeout_seconds="8"
)
welcome.then(invoke_counter)

say_count = flow.play_prompt("You are caller number $.External.count")
invoke_counter.then(say_count)

disconnect = flow.disconnect()
say_count.then(disconnect)
invoke_counter.on_error("NoMatchingError", disconnect)

flow.compile_to_file("counter_flow.json")
```

## Generated Flow Examples

Here's what the generated flows look like in the Amazon Connect console:

![Example Generated Flow](docs/example_generated_flow.png)

![Example Generated Flow 2](docs/example_generate_flow2.png)

## Installation

```bash
pip install cxblueprint

# With MCP server for AI integration
pip install cxblueprint[mcp]
```

## MCP Server

CxBlueprint includes an MCP server that lets AI tools (Claude Desktop, Cursor, VS Code) build contact flows conversationally.

Configure Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cxblueprint": {
      "command": "cxblueprint-mcp"
    }
  }
}
```

Then ask Claude: *"Build me an IVR with a welcome message and 3 menu options for sales, support, and billing"*

The AI reads the bundled documentation automatically and uses the `compile_flow` tool to generate valid Amazon Connect JSON.

## Block Coverage

**23 / 54 block types implemented (43%)**

| Category | Implemented | Total | Coverage |
|----------|-------------|-------|----------|
| [Participant Actions](src/cxblueprint/blocks/participant_actions/) | 6 | 6 | **100%** |
| [Contact Actions](src/cxblueprint/blocks/contact_actions/) | 8 | 25 | 32% |
| [Flow Control Actions](src/cxblueprint/blocks/flow_control_actions/) | 7 | 15 | 47% |
| [Interactions](src/cxblueprint/blocks/interactions/) | 2 | 8 | 25% |

See each category's README for the full per-block breakdown.

## Features

- Fluent Python API for building flows
- MCP server for AI-assisted flow generation
- Canvas layout positioning for AWS Connect visual editor
- Automatic UUID generation for blocks
- Conditional branching and error handling
- AWS Lambda and Lex V2 bot integration
- Template placeholder support for Terraform/IaC
- Decompile existing flows back to Python

## Project Structure

```
src/cxblueprint/
  flow_builder.py       # Main builder API
  flow_analyzer.py      # Flow validation
  mcp_server.py         # MCP server for AI integration
  blocks/               # All Connect block types
examples/               # Sample flows
docs/                   # API reference & AI instructions
```

## Documentation

- [API Reference](docs/API_REFERENCE.md)
- [Terraform Example](terraform_example/README.md)

## Requirements

- Python 3.11+
- AWS credentials (for deployment)
- Terraform (optional, for infrastructure)
