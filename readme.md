# Contact Flow Compiler / Decompiler

## Goal

Build a simple DSL for creating and editing Amazon Connect contact flows safely.

**Current Phase:** Decompiling and compiling contact flows through Python objects  
**Next Phase:** Generate valid contact flows programmatically from Python code

---

## Current Status

- [DONE] Decompile AWS Connect JSON into block-level Python objects
- [DONE] Recompile Python objects back to valid AWS JSON
- [DONE] Validate flows against AWS API
- [TODO] Programmatic flow generation API (see design below)

---

## Future API Design (Programmatic Flow Generation)

When generating flows from Python code instead of JSON, the API will use **explicit block references with direct routing**:

```python
# Create a new flow
flow = ContactFlow("Customer Support IVR")

# Create blocks - each returns a reference
welcome = flow.play_prompt("Welcome to support. Press 1 for Billing, 2 for Tech Support.")
menu = flow.get_user_input(
    text="Press 1 for Billing, press 2 for Technical Support.",
    timeout_seconds=5
)

# Wire the linear path
welcome.next(menu)

# Handle branching - get branch contexts
option_1 = menu.on_input("1")
option_2 = menu.on_input("2")
timeout = menu.on_timeout()
invalid = menu.on_invalid()

# Build out each branch
billing_msg = option_1.play_prompt("Transferring you to Billing.")
billing_queue = billing_msg.transfer_to_queue("billing_queue")

tech_msg = option_2.play_prompt("Transferring you to Technical Support.")
tech_queue = tech_msg.transfer_to_queue("tech_support_queue")

timeout_msg = timeout.play_prompt("No input received. Goodbye.")
timeout_msg.disconnect()

retry_msg = invalid.play_prompt("Invalid selection. Please try again.")
retry_msg.next(menu)  # Loop back

# Compile to AWS JSON
flow.compile_to_file("output/customer_support.json")
```

### Key Design Principles

1. **Auto-generate UUIDs** - Blocks automatically get unique identifiers when created
2. **Auto-set entry point** - First block added becomes StartAction by default (can override)
3. **Auto-position blocks** - Flow calculates block positions for Connect UI visualization
4. **Blocks manage their own transitions** - Each block maintains its Transitions dict
5. **Flow is a container** - Tracks all blocks, handles compilation, validates structure
6. **Link by reference, store by ID** - API uses block references, internally links via `block.identifier`
7. **Validate at compile time** - Check for orphaned blocks, missing transitions, unreachable paths

---

## Use Case (Original YAML Vision)

Suppose you want to create an IVR menu where a customer can choose between Billing and Technical Support.  
Instead of manually writing AWS JSON, you can represent the flow in YAML:

```yaml
contact_flow: Customer Support Menu
blocks:
  - id: start
    type: PlayPrompt
    text: "Welcome to support. Press 1 for Billing, 2 for Tech Support."
    next: get_user_input

  - id: get_user_input
    type: GetCustomerInput
    options:
      "1": billing_branch
      "2": tech_support_branch
    invalid: invalid_response
    timeout: timeout_response

  - id: billing_branch
    type: PlayPrompt
    text: "Transferring you to Billing."
    next: transfer_billing

  - id: tech_support_branch
    type: PlayPrompt
    text: "Transferring you to Technical Support."
    next: transfer_tech

  - id: transfer_billing
    type: TransferToQueue
    queue_name: billing_queue

  - id: transfer_tech
    type: TransferToQueue
    queue_name: tech_support_queue

  - id: invalid_response
    type: PlayPrompt
    text: "Invalid selection. Please try again."
    next: get_user_input

  - id: timeout_response
    type: PlayPrompt
    text: "No input received. Transferring you to an agent."
    next: transfer_support

  - id: transfer_support
    type: TransferToQueue
    queue_name: general_support_queue
```

Using this YAML, your tool can:

- Parse it into Python objects for validation or modification
- Generate AWS-compatible JSON for deployment
- Allow AI or humans to edit flows safely without worrying about UUIDs or metadata

## Why This Is Useful

- AWS contact flow JSON is complex and easy to break
- Working with block-level representations makes editing flows safe, repeatable, and human-readable
- Enables AI-assisted generation or automated modifications of flows


# Block Implementation Status

## Implemented Blocks (21 total)

- CheckHoursOfOperation
- CheckMetricData
- Compare
- CreateCallbackContact
- CreateTask
- DisconnectParticipant
- DistributeByPercentage
- EndFlowExecution
- GetParticipantInput
- InvokeLambdaFunction
- MessageParticipant
- MessageParticipantIteratively
- TransferContactToQueue
- TransferToFlow
- UpdateContactAttributes
- UpdateContactCallbackNumber
- UpdateContactEventHooks
- UpdateContactRecordingBehavior
- UpdateContactRoutingBehavior
- UpdateContactTargetQueue
- Wait

## Validation Results

- Total flows processed: 12
- Successfully validated: 12
- Failed validation: 0

## Status: COMPLETE

All CONTACT_FLOW type flows can be decompiled and recompiled to valid AWS Connect JSON.
