# Simple Counter Example

Minimal Amazon Connect + Lambda example showing how CxBlueprint's handles a scenario with a dynamic parameter.

## What It Does

1. Caller hears: "Thank you for calling"
2. Lambda increments counter stored in /tmp
3. Caller hears: "You are caller number X"
4. Call disconnects


## Quick Start

```bash
python flow_generator.py
cd terraform
terraform init
terraform apply
```

## Cleanup

```bash
cd terraform
terraform destroy
```

## Files

- `flow_generator.py` - Uses CxBlueprint as library
- `counter_flow.json` - Generated flow (4 blocks)
- `lambda/counter.py` - /tmp-backed counter (40 lines)
- `terraform/` - Infrastructure code (110 lines)

