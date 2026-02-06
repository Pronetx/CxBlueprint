# CxBlueprint

Programmatic Amazon Connect contact flow generation using Python. Allows for Ai models to generate contact flows based on human languages **way** easier than writing JSON as majority of the time it will fail to generate a valid contact flow from scratch.
### Simple Example

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

# Chain menu options with error handling
menu.when("1", classic) \
    .when("2", veggie) \
    .otherwise(error_msg) \
    .on_error("InputTimeLimitExceeded", error_msg) \
    .on_error("NoMatchingCondition", error_msg) \
    .on_error("NoMatchingError", error_msg)

# Or without chaining:
# menu.when("1", classic)
# menu.when("2", veggie)
# menu.otherwise(error_msg)
# menu.on_error("InputTimeLimitExceeded", error_msg)
# menu.on_error("NoMatchingCondition", error_msg)
# menu.on_error("NoMatchingError", error_msg)

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

## MCP Server (AI Integration)

CxBlueprint includes an MCP server that lets AI tools (Claude Desktop, Cursor, VS Code) build contact flows conversationally.

```bash
pip install cxblueprint[mcp]
```

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

## Features

- Fluent Python API for building flows
- MCP server for AI-assisted flow generation
- Naive block positioning for AWS Connect visual canvas
- Automatic UUID generation for blocks
- Error/Conditional handling support
- Integration with AWS Lambda and lexv2 bots
- Template placeholder support for Terraform/IaC
- Decompile existing flows to Python
- Majority of Amazon Connect block types supported
- Shell scripts to download, validate, and test flows against Connect


## Possible Future Uses/Ideas:
- Compliance Checking, check flow structures for best practices, encryption, etc.
- Optimization Suggestions, analyze flows for efficiency improvements.
- Output to diagram formats for other visualization tools.
- Template library of common flow patterns.

## Installation

```bash
pip install cxblueprint

# With MCP server for AI integration
pip install cxblueprint[mcp]
```

## Quick Start

```bash
# See Terraform example
cd terraform_example
python flow_generator.py

# Deploy with Terraform
cd terraform
terraform init
terraform apply
```

## Project Structure

```
src/cxblueprint/
  __init__.py           # Package exports
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
