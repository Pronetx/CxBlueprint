# Examples

This directory contains examples demonstrating how to use CxBlueprint to build AWS Connect flows.

## Directory Structure

### `code_examples/`
Python code examples showing different flow patterns:

- **`simple_flow.py`** - Basic flow with a prompt and disconnect
- **`menu_flow.py`** - Simple menu with 2 options
- **`burger_order_flow.py`** - Complex multi-level menu flow
- **`student_loan_ivr.py`** - Advanced IVR with retry logic and repeat functionality
- **`loan_center_main_menu.py`** - Loan center menu with function wrapper
- **`Loan_main_menu.py`** - Loan center menu in script style

### `complete_terraform_example/`
Complete end-to-end example showing:
- Flow generation with dynamic ARN placeholders
- Terraform infrastructure provisioning
- Lambda function integration
- Complete deployment workflow

See [complete_terraform_example/README.md](complete_terraform_example/README.md) for details.

## Running Examples

### Code Examples
```bash
cd examples/code_examples
python simple_flow.py
python menu_flow.py
python burger_order_flow.py
```

### Terraform Example
```bash
cd examples/complete_terraform_example
python flow_generator.py
cd terraform && terraform init && terraform apply
```

## API Usage

All examples use the unified `Flow` API:

```python
from flow_builder import Flow

# Create a new flow
flow = Flow.build("My Flow Name")
flow.play_prompt("Hello!")
flow.disconnect()

# Compile to JSON
flow.compile_to_file("output.json")
```

For more details, see the [main README](../readme.md).
