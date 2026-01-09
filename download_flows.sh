#!/bin/bash

INSTANCE_ID="082e847c-8736-4d4d-b74b-2ca68376897a"
PROFILE="cxforge"
OUTPUT_DIR="./input"

echo "============================================================"
echo "Amazon Connect - Contact Flow Downloader"
echo "============================================================"
echo "Instance ID: $INSTANCE_ID"
echo "Profile: $PROFILE"
echo ""

# Get list of contact flows
echo "Fetching contact flows..."
flows=$(aws connect list-contact-flows \
  --instance-id "$INSTANCE_ID" \
  --profile "$PROFILE" \
  --output json)

# Extract flow IDs and names
flow_ids=$(echo "$flows" | jq -r '.ContactFlowSummaryList[] | .Id')
total=$(echo "$flow_ids" | wc -l | tr -d ' ')

echo "Found $total contact flows"
echo ""

count=0
for flow_id in $flow_ids; do
  count=$((count + 1))
  
  # Get flow details
  flow_data=$(aws connect describe-contact-flow \
    --instance-id "$INSTANCE_ID" \
    --contact-flow-id "$flow_id" \
    --profile "$PROFILE" \
    --output json)
  
  flow_name=$(echo "$flow_data" | jq -r '.ContactFlow.Name')
  flow_type=$(echo "$flow_data" | jq -r '.ContactFlow.Type')
  
  echo "[$count/$total] Downloading: $flow_name ($flow_type)"
  
  # Extract and save content
  content=$(echo "$flow_data" | jq -r '.ContactFlow.Content')
  
  if [ "$content" == "null" ] || [ -z "$content" ]; then
    echo "  [WARNING] No content found"
    continue
  fi
  
  # Create safe filename
  safe_name=$(echo "$flow_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | sed 's/[^a-z0-9_-]/_/g')
  
  # Skip non-CONTACT_FLOW types
  if [ "$flow_type" != "CONTACT_FLOW" ]; then
    echo "  [SKIP] Skipping (type: $flow_type)"
    continue
  fi
  
  output_file="$OUTPUT_DIR/${safe_name}.json"
  
  # Save formatted JSON - no modifications
  echo "$content" | jq '.' > "$output_file"
  
  echo "  [OK] Saved to: $output_file"
  
  # Create safe filename
  safe_name=$(echo "$flow_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | sed 's/[^a-z0-9_-]/_/g')
  output_file="$_with_typeOUTPUT_DIR/${safe_name}.json"
  
  # Save formatted JSON
  echo "$content" | jq '.' > "$output_file"
  
  echo "  ✓ Saved to: $output_file"
done

echo ""
echo "[DONE] Downloaded $total contact flows to $OUTPUT_DIR"
