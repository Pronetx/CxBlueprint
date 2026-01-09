#!/bin/bash

# Validate a contact flow by attempting to create it in Amazon Connect
# Usage: ./validate_flow.sh <flow_file.json>

INSTANCE_ID="082e847c-8736-4d4d-b74b-2ca68376897a"
PROFILE="cxforge"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <flow_file.json>"
    exit 1
fi

FLOW_FILE="$1"

if [ ! -f "$FLOW_FILE" ]; then
    echo "Error: File '$FLOW_FILE' not found"
    exit 1
fi

echo "============================================================"
echo "Contact Flow Validator"
echo "============================================================"
echo "File: $FLOW_FILE"
echo ""

# Generate a test flow name with timestamp
TIMESTAMP=$(date +%s)
TEST_FLOW_NAME="test_validation_${TIMESTAMP}"

echo "Attempting to create test flow: $TEST_FLOW_NAME"

# Read the flow content
FLOW_CONTENT=$(cat "$FLOW_FILE" | jq -c '.')

# Always use CONTACT_FLOW type for validation
FLOW_TYPE="CONTACT_FLOW"

echo "Flow type: $FLOW_TYPE"

# Attempt to create the contact flow
result=$(aws connect create-contact-flow \
  --instance-id "$INSTANCE_ID" \
  --name "$TEST_FLOW_NAME" \
  --type "$FLOW_TYPE" \
  --content "$FLOW_CONTENT" \
  --profile "$PROFILE" \
  --output json 2>&1)

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "[VALID] Flow is valid and can be created in Connect"
    
    # Extract the flow ID and ARN
    flow_id=$(echo "$result" | jq -r '.ContactFlowId')
    flow_arn=$(echo "$result" | jq -r '.ContactFlowArn')
    
    echo " FLOWlow ID: $flow_id"
    echo ""
    
    # Clean up - delete the test flow
    echo "Cleaning up test flow..."
    aws connect delete-contact-flow \
      --instance-id "$INSTANCE_ID" \
      --contact-flow-id "$flow_id" \
      --profile "$PROFILE" \
      --output json 2>&1 > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "[OK] Test flow deleted"
    else
        echo "[WARNING] Could not delete test flow $flow_id"
        echo "   You may need to delete it manually"
    fi
    
    exit 0
else
    echo "[INVALID] Flow validation failed"
    echo ""
    echo "Error details:"
    echo "$result" | grep -A 10 "error"
    
    # Check for specific error types
    if echo "$result" | grep -q "InvalidContactFlowException"; then
        echo ""
        echo "This is an InvalidContactFlowException - the flow structure is invalid"
    elif echo "$result" | grep -q "InvalidParameterException"; then
        echo ""
        echo "This is an InvalidParameterException - check parameter values"
    fi
    
    exit 1
fi
