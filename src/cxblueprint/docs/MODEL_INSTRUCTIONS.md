# CxBlueprint: AI Model Instructions

## CRITICAL RULES (READ FIRST)

### Rule 1: GetParticipantInput Contains Its Own Prompt
**NEVER** create a separate `play_prompt()` before a `get_input()`. The prompt text goes INSIDE the `get_input()` block.

```python
# WRONG - DO NOT DO THIS
prompt = flow.play_prompt("Press 1 for Sales, 2 for Support")
menu = flow.get_input("Please make your selection", timeout=10)
prompt.then(menu)

# CORRECT - DO THIS
menu = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)
```

The `get_input()` block plays its text parameter as audio to the caller, then waits for DTMF input. There is no need for a preceding prompt block.

### Rule 2: Always Handle All Error Cases
Every `get_input()` block MUST have error handlers:

```python
menu = flow.get_input("Press 1 or 2", timeout=10)
menu.when("1", option1) \
    .when("2", option2) \
    .otherwise(fallback) \
    .on_error("InputTimeLimitExceeded", fallback) \
    .on_error("NoMatchingCondition", fallback) \
    .on_error("NoMatchingError", fallback)
```

### Rule 3: Every Path Must End
All flow paths must terminate at either:
- `flow.disconnect()` - Ends the call
- `flow.end_flow()` - Ends flow without disconnecting
- A queue transfer or flow transfer

### Rule 4: Condition Values Are Strings
DTMF conditions are always strings, not integers:

```python
# WRONG
menu.when(1, sales)

# CORRECT
menu.when("1", sales)
```

---

## Library Overview

CxBlueprint generates Amazon Connect contact flow JSON from Python code.

```python
from cxblueprint import Flow

flow = Flow.build("My Flow Name", debug=True)
# ... create and connect blocks ...
flow.compile_to_file("output/my_flow.json")
```

### Debug Mode
Setting `debug=True` prints helpful information during flow construction:
- Each block added to the flow
- Validation results (orphaned blocks, missing error handlers)
- Canvas layout dimensions
- Compilation summary

Use debug mode when developing flows to catch issues early.

---

## Block Types and When to Use Them

### Customer-Facing Blocks

| Method | Use When | Example |
|--------|----------|---------|
| `flow.play_prompt(text)` | Play a message with NO user response expected | Announcements, confirmations, goodbye messages |
| `flow.get_input(text, timeout=5)` | Collect DTMF keypress from caller | Menus, PIN entry, confirmations |
| `flow.disconnect()` | End the call | Final block in most paths |

**Note on timeout**: Default is 5 seconds. For menus, use 8-10 seconds to give users time to listen and respond.

### Integration Blocks

| Method | Use When | Example |
|--------|----------|---------|
| `flow.invoke_lambda(arn)` | Call external logic/APIs | Account lookup, data validation |
| `flow.check_hours(id)` | Route by business hours | Open/closed routing |
| `flow.lex_bot(text, lex_v2_bot)` | Natural language input | Voice assistants |

### Data Blocks

| Method | Use When | Example |
|--------|----------|---------|
| `flow.update_attributes(**attrs)` | Store data for later | Customer type, session data |

### Flow Control Blocks

| Method | Use When | Example |
|--------|----------|---------|
| `flow.transfer_to_flow(id)` | Jump to another flow | Sub-flows, error flows |
| `flow.end_flow()` | End without disconnect | Module completion |

---

## Connection Methods

### `.then(block)` - Sequential Connection
Connects one block to the next in sequence:

```python
welcome = flow.play_prompt("Welcome!")
menu = flow.get_input("Press 1 or 2", timeout=10)
welcome.then(menu)
```

### `.when(value, block)` - Conditional Branch
Routes based on user input or block output:

```python
menu = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)
menu.when("1", sales_block)
menu.when("2", support_block)
```

### `.otherwise(block)` - Default Branch
Fallback when no conditions match:

```python
menu.otherwise(error_block)
```

### `.on_error(error_type, block)` - Error Handler
Handle specific error conditions:

```python
menu.on_error("InputTimeLimitExceeded", timeout_block)
menu.on_error("NoMatchingCondition", invalid_block)
menu.on_error("NoMatchingError", error_block)
```

### Chaining
All connection methods return the block, enabling chaining:

```python
menu.when("1", sales) \
    .when("2", support) \
    .otherwise(error) \
    .on_error("InputTimeLimitExceeded", error) \
    .on_error("NoMatchingCondition", error) \
    .on_error("NoMatchingError", error)
```

---

## Block Reuse vs Creating New Blocks

### When to Reuse Blocks
You can reuse the same block in multiple paths:

```python
disconnect = flow.disconnect()

# Reuse same disconnect block
sales.then(disconnect)
support.then(disconnect)
error.then(disconnect)
```

**Advantages**: Fewer total blocks, simpler flow structure

### When to Create New Blocks
Sometimes you need separate instances of the same block type:

```python
disconnect_success = flow.disconnect()
disconnect_error = flow.disconnect()

# Different endpoints for success vs error
order_complete.then(disconnect_success)
invalid_input.then(disconnect_error)
```

**When to use separate blocks**:
- When you need different metadata/tracking for different paths
- When AWS Connect reporting needs to distinguish between different exit points
- When the flow logic makes it clearer (e.g., "error disconnect" vs "success disconnect")

**Rule of thumb**: Reuse blocks when they're truly identical. Create new blocks when the semantic meaning differs, even if the block type is the same.

---

## Error Handlers on play_prompt Blocks

Most `play_prompt()` blocks don't need error handlers, but you CAN add them:

```python
welcome = flow.play_prompt("Welcome!")
welcome.on_error("NoMatchingError", disconnect)
```

**When to add error handlers to play_prompt**:
- For consistency in complex flows (easier to reason about)
- When the prompt contains dynamic content that might fail
- As a defensive practice (catches unexpected AWS errors)

**Common practice**: Add `.on_error("NoMatchingError", disconnect)` to all blocks in production flows for robustness.

---

## Common Error Types

| Error Type | Trigger |
|------------|---------|
| `InputTimeLimitExceeded` | User didn't press any key within timeout |
| `NoMatchingCondition` | User pressed a key not in any `.when()` condition |
| `NoMatchingError` | Catch-all for unexpected errors |

---

## Complete Flow Example

**Requirement:** "Create an IVR where callers press 1 for account balance, 2 for payments, or 3 for an agent. Handle invalid input and timeout."

```python
from cxblueprint import Flow

flow = Flow.build("Account Services IVR", debug=True)

# Create all blocks first
welcome = flow.play_prompt("Thank you for calling Account Services.")

main_menu = flow.get_input(
    "Press 1 for account balance, 2 for payments, or 3 to speak with an agent.",
    timeout=10
)

balance_msg = flow.play_prompt("Your current balance is $150.00.")
payment_msg = flow.play_prompt("Transferring you to our payment system.")
agent_msg = flow.play_prompt("Please hold while we connect you to an agent.")
error_msg = flow.play_prompt("I didn't understand your selection. Goodbye.")

disconnect = flow.disconnect()

# Connect the flow
welcome.then(main_menu)

main_menu.when("1", balance_msg) \
    .when("2", payment_msg) \
    .when("3", agent_msg) \
    .otherwise(error_msg) \
    .on_error("InputTimeLimitExceeded", error_msg) \
    .on_error("NoMatchingCondition", error_msg) \
    .on_error("NoMatchingError", error_msg)

balance_msg.then(disconnect)
payment_msg.then(disconnect)
agent_msg.then(disconnect)
error_msg.then(disconnect)

# Generate the flow JSON
flow.compile_to_file("output/account_services.json")
```

---

## Real-World Complex Flow Example

**Requirement:** "Create a burger ordering system where customers can place orders (choosing burger type and size), track existing orders, or speak with an agent."

**Analysis:**
1. **Entry point**: Welcome message
2. **Main menu**: 3 options (order, track, agent)
3. **Order path**: Choose burger type → Choose size → Confirmation
4. **Track path**: Status message → Thank you
5. **Agent path**: Transfer message → Thank you
6. **All paths end at disconnect**

**Key decisions:**
- Create separate disconnect blocks for order vs track vs agent (for reporting clarity)
- Add error handlers to all blocks (production robustness)
- Use intermediate confirmation messages (better UX)

```python
from cxblueprint import Flow

flow = Flow.build("Burger Order Flow", debug=True)

# Entry
welcome = flow.play_prompt("Welcome to Burger Palace! Thank you for calling.")

# Main menu
main_menu = flow.get_input(
    "Press 1 to place an order, 2 to track your order, or 3 to speak with an agent",
    timeout=10
)

# Order path blocks
order_welcome = flow.play_prompt("Great! Let's get your order started.")
burger_menu = flow.get_input(
    "Press 1 for Classic Burger, 2 for Deluxe Burger, or 3 for Veggie Burger",
    timeout=10
)

# Burger size menus (separate for each type)
classic_size = flow.get_input(
    "You selected Classic Burger. Press 1 for Small, 2 for Medium, or 3 for Large",
    timeout=10
)
deluxe_size = flow.get_input(
    "You selected Deluxe Burger. Press 1 for Small, 2 for Medium, or 3 for Large",
    timeout=10
)
veggie_size = flow.get_input(
    "You selected Veggie Burger. Press 1 for Small, 2 for Medium, or 3 for Large",
    timeout=10
)

# Confirmations
classic_confirm = flow.play_prompt("Perfect! Your Classic Burger has been added.")
deluxe_confirm = flow.play_prompt("Excellent! Your Deluxe Burger has been added.")
veggie_confirm = flow.play_prompt("Great! Your Veggie Burger has been added.")
order_thanks = flow.play_prompt("Thank you for your order! You will receive a confirmation text.")

# Track path
track_msg = flow.play_prompt("Please hold while we look up your order status.")
track_result = flow.play_prompt("Your order is being prepared and will be ready in 15 minutes.")
track_thanks = flow.play_prompt("Thank you for calling Burger Palace!")

# Agent path
transfer_msg = flow.play_prompt("Please hold while we connect you to an agent.")
agent_thanks = flow.play_prompt("Thank you for calling. Goodbye.")

# Separate disconnects for tracking
disconnect_order = flow.disconnect()
disconnect_track = flow.disconnect()
disconnect_agent = flow.disconnect()
disconnect_error = flow.disconnect()

# Wire main menu
welcome.then(main_menu)

main_menu.when("1", order_welcome) \
    .when("2", track_msg) \
    .when("3", transfer_msg) \
    .otherwise(disconnect_error) \
    .on_error("InputTimeLimitExceeded", disconnect_error) \
    .on_error("NoMatchingCondition", disconnect_error) \
    .on_error("NoMatchingError", disconnect_error)

# Order flow
order_welcome.then(burger_menu)

burger_menu.when("1", classic_size) \
    .when("2", deluxe_size) \
    .when("3", veggie_size) \
    .otherwise(disconnect_error) \
    .on_error("InputTimeLimitExceeded", disconnect_error) \
    .on_error("NoMatchingCondition", disconnect_error) \
    .on_error("NoMatchingError", disconnect_error)

# Wire each burger type's size selection
# Classic: all three sizes go to same confirmation
classic_size.when("1", classic_confirm) \
    .when("2", classic_confirm) \
    .when("3", classic_confirm) \
    .otherwise(disconnect_error) \
    .on_error("InputTimeLimitExceeded", disconnect_error) \
    .on_error("NoMatchingCondition", disconnect_error)

# Deluxe: all three sizes go to same confirmation
deluxe_size.when("1", deluxe_confirm) \
    .when("2", deluxe_confirm) \
    .when("3", deluxe_confirm) \
    .otherwise(disconnect_error) \
    .on_error("InputTimeLimitExceeded", disconnect_error) \
    .on_error("NoMatchingCondition", disconnect_error)

# Veggie: all three sizes go to same confirmation
veggie_size.when("1", veggie_confirm) \
    .when("2", veggie_confirm) \
    .when("3", veggie_confirm) \
    .otherwise(disconnect_error) \
    .on_error("InputTimeLimitExceeded", disconnect_error) \
    .on_error("NoMatchingCondition", disconnect_error)

# All confirmations lead to thank you message
classic_confirm.then(order_thanks)
deluxe_confirm.then(order_thanks)
veggie_confirm.then(order_thanks)
order_thanks.then(disconnect_order)

# Track path
track_msg.then(track_result)
track_result.then(track_thanks)
track_thanks.then(disconnect_track)

# Agent path
transfer_msg.then(agent_thanks)
agent_thanks.then(disconnect_agent)

flow.compile_to_file("output/burger_order.json")
```

**Key patterns demonstrated:**
- Multi-level nested menus (main → burger type → size)
- Reusing confirmation blocks (all 3 sizes for classic go to same confirmation)
- Separate disconnect blocks for different logical endpoints
- Consistent error handling throughout
- Clear variable naming for complex flows

---

## Pattern: Multi-Level Menu

When creating nested menus, each `get_input()` contains its own prompt:

```python
flow = Flow.build("Department Menu")

# Main menu - prompt is IN the get_input
main = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)

# Sub-menus - each has its own prompt IN the get_input
sales_menu = flow.get_input("Sales: Press 1 for New Accounts, 2 for Existing", timeout=10)
support_menu = flow.get_input("Support: Press 1 for Technical, 2 for Billing", timeout=10)

# Result messages
new_acct = flow.play_prompt("Connecting to New Accounts")
existing = flow.play_prompt("Connecting to Existing Accounts")
technical = flow.play_prompt("Connecting to Technical Support")
billing = flow.play_prompt("Connecting to Billing")
error = flow.play_prompt("Invalid selection")

disconnect = flow.disconnect()

# Wire main menu
main.when("1", sales_menu) \
    .when("2", support_menu) \
    .otherwise(error) \
    .on_error("InputTimeLimitExceeded", error) \
    .on_error("NoMatchingCondition", error)

# Wire sales sub-menu
sales_menu.when("1", new_acct) \
    .when("2", existing) \
    .otherwise(error) \
    .on_error("InputTimeLimitExceeded", error) \
    .on_error("NoMatchingCondition", error)

# Wire support sub-menu
support_menu.when("1", technical) \
    .when("2", billing) \
    .otherwise(error) \
    .on_error("InputTimeLimitExceeded", error) \
    .on_error("NoMatchingCondition", error)

# All endpoints to disconnect
new_acct.then(disconnect)
existing.then(disconnect)
technical.then(disconnect)
billing.then(disconnect)
error.then(disconnect)

flow.compile_to_file("output/department_menu.json")
```

---

## Pattern: Retry Logic

To allow retries on invalid input:

```python
flow = Flow.build("Menu with Retry")

# First attempt
main_menu = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)

# Retry message (only played on retry path)
retry_msg = flow.play_prompt("I didn't catch that. Let me repeat the options.")

# Second attempt - same prompt
retry_menu = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)

# Destinations
sales = flow.play_prompt("Connecting to Sales")
support = flow.play_prompt("Connecting to Support")
final_error = flow.play_prompt("Unable to process your request. Goodbye.")
disconnect = flow.disconnect()

# First menu - on error, go to retry
main_menu.when("1", sales) \
    .when("2", support) \
    .otherwise(retry_msg) \
    .on_error("InputTimeLimitExceeded", retry_msg) \
    .on_error("NoMatchingCondition", retry_msg)

# Retry message leads to second attempt
retry_msg.then(retry_menu)

# Second menu - on error, give up
retry_menu.when("1", sales) \
    .when("2", support) \
    .otherwise(final_error) \
    .on_error("InputTimeLimitExceeded", final_error) \
    .on_error("NoMatchingCondition", final_error)

# Endpoints
sales.then(disconnect)
support.then(disconnect)
final_error.then(disconnect)

flow.compile_to_file("output/menu_with_retry.json")
```

---

## Pattern: Press 9 to Repeat Menu

```python
flow = Flow.build("Repeating Menu")

# Menu introduction (only played once at start)
intro = flow.play_prompt("Welcome to our service.")

# The main menu
menu = flow.get_input("Press 1 for option A, 2 for option B, or 9 to hear this again", timeout=10)

option_a = flow.play_prompt("You selected option A")
option_b = flow.play_prompt("You selected option B")
error = flow.play_prompt("Invalid selection. Goodbye.")
disconnect = flow.disconnect()

# Wire it up
intro.then(menu)

menu.when("1", option_a) \
    .when("2", option_b) \
    .when("9", menu) \
    .otherwise(error) \
    .on_error("InputTimeLimitExceeded", error) \
    .on_error("NoMatchingCondition", error)

option_a.then(disconnect)
option_b.then(disconnect)
error.then(disconnect)

flow.compile_to_file("output/repeating_menu.json")
```

---

## Pattern: Business Hours Check

```python
flow = Flow.build("Hours Check")

hours = flow.check_hours(hours_of_operation_id="${HOURS_OF_OPERATION_ID}")

# Open path
open_menu = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)

# Closed path
closed_msg = flow.play_prompt("We're currently closed. Our hours are 9 AM to 5 PM.")

sales = flow.play_prompt("Connecting to Sales")
support = flow.play_prompt("Connecting to Support")
disconnect = flow.disconnect()

# Hours check routing
hours.when("True", open_menu)   # In hours
hours.when("False", closed_msg) # After hours

# Menu routing
open_menu.when("1", sales).when("2", support)

# Endpoints
sales.then(disconnect)
support.then(disconnect)
closed_msg.then(disconnect)

flow.compile_to_file("output/hours_check.json")
```

---

## Pattern: Lambda Integration

```python
flow = Flow.build("Account Lookup")

# Check account (Lambda returns customer type as attribute)
lookup = flow.invoke_lambda(function_arn="${ACCOUNT_LAMBDA_ARN}")

# Route based on Lambda response
premium = flow.play_prompt("Welcome Premium member. Connecting you to priority support.")
standard = flow.play_prompt("Connecting you to our support team.")
not_found = flow.play_prompt("We couldn't find your account. Please call back with your account number.")

disconnect = flow.disconnect()

# Lambda conditions (based on returned attributes)
lookup.when("Premium", premium) \
    .when("Standard", standard) \
    .on_error("NoMatchingCondition", not_found) \
    .on_error("NoMatchingError", not_found)

premium.then(disconnect)
standard.then(disconnect)
not_found.then(disconnect)

flow.compile_to_file("output/account_lookup.json")
```

---

## Pattern: Store and Use Attributes

```python
flow = Flow.build("Attribute Example")

menu = flow.get_input("Press 1 for Sales, 2 for Support", timeout=10)

# Store selection as attribute
set_sales = flow.update_attributes(department="sales", priority="normal")
set_support = flow.update_attributes(department="support", priority="normal")

sales_msg = flow.play_prompt("Routing to Sales")
support_msg = flow.play_prompt("Routing to Support")
disconnect = flow.disconnect()

menu.when("1", set_sales).when("2", set_support)
set_sales.then(sales_msg)
set_support.then(support_msg)
sales_msg.then(disconnect)
support_msg.then(disconnect)

flow.compile_to_file("output/attributes_example.json")
```

---

## Advanced Blocks (Use with flow.add())

For blocks not covered by convenience methods:

```python
import uuid
from cxblueprint.blocks.contact_actions import TransferContactToQueue
from cxblueprint.blocks.flow_control_actions import DistributeByPercentage, Wait

# Queue transfer
queue = TransferContactToQueue(
    identifier=str(uuid.uuid4()),
    queue_id="${QUEUE_ARN}"
)
flow.add(queue)

# A/B testing
ab_test = DistributeByPercentage(
    identifier=str(uuid.uuid4()),
    percentages=[50, 50]  # 50/50 split
)
flow.add(ab_test)

# Wait/pause
wait = Wait(
    identifier=str(uuid.uuid4()),
    seconds="5"
)
flow.add(wait)
```

---

## Terraform Variable Syntax

Use `${VARIABLE}` for values injected at deploy time:

```python
lambda_block = flow.invoke_lambda(function_arn="${LAMBDA_ARN}")
hours_block = flow.check_hours(hours_of_operation_id="${HOURS_ID}")
```

---

## Translation Checklist

When converting user requirements to code:

1. **Analyze the requirement**
   - What are the user's choices/options? (These become `get_input` blocks)
   - What information is just announcements? (These become `play_prompt` blocks)
   - What are the logical paths through the flow?
   - Where does each path end?
   - Are there nested menus (menu within menu)?
   - Are there conditional branches (business hours, Lambda results)?

2. **Identify all blocks needed**
   - Prompts (play_prompt for announcements only)
   - Menus (get_input with the menu text INSIDE)
   - Endpoints (disconnect, queue, flow transfer)

3. **Identify flow structure**
   - Entry point (first block)
   - Decision points (get_input, check_hours, lambda)
   - Branches (where does each option go?)
   - Exit points (where do paths end?)

4. **Map connections**
   - Sequential: use `.then()`
   - Conditional: use `.when(value, block)`
   - Default: use `.otherwise(block)`
   - Errors: use `.on_error(type, block)`

5. **Verify completeness**
   - Every get_input has all error handlers
   - Every path ends at disconnect or transfer
   - No orphan blocks

---

## Quick Reference

```python
# Initialize
flow = Flow.build("Name", debug=True)

# Basic blocks
msg = flow.play_prompt("text")           # Announcement only
menu = flow.get_input("prompt", timeout) # Menu WITH prompt
dc = flow.disconnect()                   # End call

# Integrations
lam = flow.invoke_lambda(arn)            # Lambda
hrs = flow.check_hours(id)               # Hours check
attrs = flow.update_attributes(k=v)      # Store data

# Connections
block.then(next)                         # Sequential
block.when("value", target)              # Conditional
block.otherwise(fallback)                # Default
block.on_error("Type", handler)          # Error

# Validation (optional but recommended)
flow.validate()                          # Checks for issues, raises error if found

# Output
flow.compile_to_file("path.json")

# Block reuse
disconnect = flow.disconnect()           # Create once
block1.then(disconnect)                  # Reuse
block2.then(disconnect)                  # Reuse again
```

---

## Common Mistakes

| Mistake | Correction |
|---------|------------|
| Separate play_prompt before get_input | Put prompt text IN get_input |
| Missing error handlers on get_input | Add all three: InputTimeLimitExceeded, NoMatchingCondition, NoMatchingError |
| Integer condition values | Use strings: "1" not 1 |
| No disconnect at end of paths | Every path must end |
| Blocks not connected | Use .then() to connect sequential blocks |

---

## Summary

1. **`get_input()` is self-prompting** - it plays its text then waits for input
2. **`play_prompt()` is for announcements** - messages where no response is expected
3. **Always handle errors** - timeout, no match, and catch-all (especially on `get_input`)
4. **Always end paths** - disconnect or transfer
5. **Use strings for DTMF** - "1" not 1
6. **Chain connections** - use method chaining for clean code
7. **Reuse blocks when identical** - create separate blocks when semantically different
8. **Use debug mode** - `Flow.build("Name", debug=True)` helps catch issues early
9. **Set appropriate timeouts** - 8-10 seconds for menus, 5 seconds default is too short
10. **Analyze before coding** - break down requirements into blocks and paths first
