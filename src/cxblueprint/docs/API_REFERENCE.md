# Flow API Reference

## Overview

The `Flow` provides three ways to add blocks to your flow:

1. **Fluent API** - Simple methods for common blocks
2. **Convenience Methods** - Helper methods for complex blocks
3. **Generic `add()`** - Full control for specialized blocks

### Class Methods

| Method | Description |
|--------|-------------|
| `Flow.build(name, debug=False)` | Create a new flow |
| `Flow.decompile(filepath, debug=False)` | Load an existing AWS Connect flow JSON |
| `Flow.load(filepath, debug=False)` | Alias for `decompile()` |

---

## 1. Fluent API (Common Blocks)

### `play_prompt(text: str) -> MessageParticipant`
Play a text-to-speech message to the customer.

```python
welcome = flow.play_prompt("Welcome to our service.")
```

### `get_input(text: str, timeout: int = 5) -> GetParticipantInput`
Get DTMF input from the customer.

```python
menu = flow.get_input("Press 1 for sales, 2 for support", timeout=10)
menu.when("1", sales_path)
menu.when("2", support_path)
```

### `disconnect() -> DisconnectParticipant`
Disconnect the call.

```python
goodbye = flow.play_prompt("Goodbye!")
disconnect = flow.disconnect()
goodbye.then(disconnect)
```

### `transfer_to_flow(contact_flow_id: str) -> TransferToFlow`
Transfer to another contact flow.

```python
transfer = flow.transfer_to_flow("{{GOODBYE_FLOW_ARN}}")
welcome.then(transfer)
```

---

## 2. Convenience Methods (Complex Blocks)

### `lex_bot(...) -> ConnectParticipantWithLexBot`
Connect customer to a Lex chatbot.

```python
from cxblueprint.blocks.types import LexV2Bot

bot = flow.lex_bot(
    text="How can I help you?",
    lex_v2_bot=LexV2Bot(alias_arn="{{LEX_BOT_ARN}}"),
    lex_session_attributes={"category": "support"}
)
bot.on_intent("CheckBalance", balance_handler)
```

### `invoke_lambda(function_arn: str, timeout_seconds: str = "8") -> InvokeLambdaFunction`
Invoke an AWS Lambda function.

```python
lambda_result = flow.invoke_lambda(
    function_arn="{{LAMBDA_ARN}}",
    timeout_seconds="10"
)
lambda_result.then(next_step)
```

### `check_hours(hours_of_operation_id: str = None) -> CheckHoursOfOperation`
Check if within business hours.

```python
hours = flow.check_hours("{{HOURS_ID}}")
hours.when("True", open_path).when("False", closed_path)
```

### `update_attributes(**attributes) -> UpdateContactAttributes`
Update contact attributes.

```python
attrs = flow.update_attributes(
    CustomerType="Premium",
    Source="Web"
)
```

### `show_view(view_resource: ViewResource, ...) -> ShowView`
Display a view in the agent workspace.

```python
from cxblueprint.blocks.types import ViewResource

view = flow.show_view(
    view_resource=ViewResource(id="{{VIEW_ID}}", version="1.0"),
    view_data={"type": "billing"}
)
```

### `end_flow() -> EndFlowExecution`
End the flow execution.

```python
end = flow.end_flow()
```

### `transfer_to_queue() -> TransferContactToQueue`
Transfer contact to a queue. Queue must be set beforehand via `UpdateContactTargetQueue`.

```python
queue_xfer = flow.transfer_to_queue()
queue_xfer.on_error("QueueAtCapacity", overflow_handler)
queue_xfer.on_error("NoMatchingError", error_handler)
```

### `wait(seconds: int = 60) -> Wait`
Pause flow execution for specified duration.

```python
pause = flow.wait(seconds=30)
pause.then(next_step)
```

### `pause_recording() -> UpdateContactRecordingBehavior`
Pause call recording (PCI compliance).

```python
pause_rec = flow.pause_recording()
```

### `resume_recording() -> UpdateContactRecordingBehavior`
Resume call recording after pausing.

```python
resume_rec = flow.resume_recording()
```

### `compare(comparison_value: str) -> Compare`
Branch based on a JSONPath expression (e.g. contact attributes).

```python
branch = flow.compare("$.Attributes.customer_tier")
branch.when("premium", vip_path) \
    .when("standard", normal_path) \
    .otherwise(default_path) \
    .on_error("NoMatchingCondition", default_path)
```

### `distribute_by_percentage(percentages: list[int]) -> DistributeByPercentage`
A/B test or percentage-based traffic routing. Percentages must sum to 100.

```python
split = flow.distribute_by_percentage([50, 50])
split.branch(0, path_a).branch(1, path_b)

# 3-way split
split = flow.distribute_by_percentage([30, 40, 30])
split.branch(0, path_a).branch(1, path_b).branch(2, path_c)
```

---

## 3. Generic `add()` Method (Specialized Blocks)

For blocks not covered by convenience methods, instantiate directly and use `add()`:

```python
from cxblueprint.blocks.contact_actions import CreateTask
from cxblueprint.blocks.participant_actions import MessageParticipantIteratively
import uuid

# Create a task with custom parameters
task = CreateTask(
    identifier=str(uuid.uuid4()),
    parameters={
        "Name": "Follow-up call",
        "Description": "Customer requested callback",
        "TemplateId": "{{TASK_TEMPLATE}}",
        "Priority": "1"
    }
)
flow.add(task)

# Use iterative messaging
messages = MessageParticipantIteratively(
    identifier=str(uuid.uuid4()),
    messages=[
        {"Text": "Please wait..."},
        {"Text": "Still processing..."},
        {"Text": "Almost done..."}
    ],
    interrupt_frequency_seconds="10"
)
flow.add(messages)
```

---

## Fluent Chaining

All methods return the block, allowing fluent chaining:

```python
flow.play_prompt("Hello") \\
    .then(flow.get_input("Press 1 or 2", timeout=10)) \\
    .when("1", option1) \\
    .when("2", option2) \\
    .on_error("NoMatchError", fallback)
```

---

## Block-Specific Methods

### `then(next_block) -> Self`
Set the next action (available on all blocks).

```python
block_a.then(block_b)
```

### `on_error(error_type: str, next_block) -> Self`
Handle specific errors (available on all blocks).

```python
block.on_error("Timeout", timeout_handler)
block.on_error("NoMatchError", error_handler)
```

### `when(value: str, next_block, operator: str = "Equals") -> Self`
Branch based on a condition value (available on **all blocks**).

```python
# DTMF input
menu.when("1", option1).when("2", option2)

# Business hours
hours.when("True", open_path).when("False", closed_path)

# Compare attribute
branch.when("premium", vip_path).when("standard", normal_path)

# Lambda result
lookup.when("found", success).when("not_found", error)
```

### `otherwise(next_block) -> Self`
Default branch when no condition matches (available on **all blocks**).

```python
menu.otherwise(invalid_input_handler)
branch.otherwise(default_path)
```

### `on_intent(intent_name: str, next_block) -> Self`
Branch based on Lex intent (ConnectParticipantWithLexBot only).

```python
lex_bot.on_intent("CheckBalance", balance_check)
lex_bot.on_intent("ResetPassword", reset_flow)
```

---

## Template Placeholders

Use template placeholders for resources that will be resolved during deployment:

```python
# Flow ARNs
flow.transfer_to_flow("{{GOODBYE_FLOW_ARN}}")

# Lambda ARNs
flow.invoke_lambda("{{BALANCE_LAMBDA_ARN}}")

# Lex Bots
from cxblueprint.blocks.types import LexV2Bot
lex_v2_bot=LexV2Bot(alias_arn="{{LEX_BOT_ARN}}")

# Hours of Operation
flow.check_hours("{{HOURS_OF_OPERATION_ID}}")

# Views
from cxblueprint.blocks.types import ViewResource
view_resource=ViewResource(id="{{VIEW_ID}}", version="1.0")
```

These are resolved by Terraform/CDK during deployment:

```hcl
# terraform example
content = templatefile("flow.json", {
  GOODBYE_FLOW_ARN = aws_connect_contact_flow.goodbye.arn
  BALANCE_LAMBDA_ARN = aws_lambda_function.balance.arn
})
```

---

## Example: Complete Flow

```python
from cxblueprint import Flow
from cxblueprint.blocks.types import LexV2Bot
from cxblueprint.blocks.contact_actions import CreateTask
import uuid

# Create flow
flow = Flow.build("Customer Support")

# Welcome
welcome = flow.play_prompt("Welcome to customer support")

# Main menu
menu = flow.get_input("Press 1 for account, 2 for technical support", timeout=10)
welcome.then(menu)

# Option 1: Account via Lambda
account_check = flow.invoke_lambda("{{ACCOUNT_LAMBDA_ARN}}")
menu.when("1", account_check)

account_msg = flow.play_prompt("Your account status is...")
account_check.then(account_msg)

# Option 2: Tech support via Lex
lex = flow.lex_bot(
    text="Technical support bot is ready",
    lex_v2_bot=LexV2Bot(alias_arn="{{LEX_BOT_ARN}}")
)
menu.when("2", lex)

# Error handling: Create task
error_msg = flow.play_prompt("I didn't understand. Creating a support ticket.")
menu.on_error("NoMatchError", error_msg)

task = CreateTask(
    identifier=str(uuid.uuid4()),
    parameters={"Name": "Support Request", "TemplateId": "{{TASK_TEMPLATE}}"}
)
flow.add(task)
error_msg.then(task)

# All paths converge
thank_you = flow.play_prompt("Thank you!")
account_msg.then(thank_you)
lex.then(thank_you)
task.then(thank_you)

# End
disconnect = flow.disconnect()
thank_you.then(disconnect)

# Compile
flow.compile_to_file("output/support_flow.json")
```

---

## Design Philosophy

1. **Simple blocks = Simple API** - Common blocks have clean methods
2. **Complex blocks = Helpers** - Frequently-used complex blocks get convenience methods
3. **Specialized blocks = Full control** - Use direct instantiation + `add()` for custom configs
4. **Future-proof** - New AWS block types don't require API changes

This hybrid approach balances simplicity with power.