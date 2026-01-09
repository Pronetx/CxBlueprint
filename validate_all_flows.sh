#!/bin/bash

# Validate all flows in the output directory
# Usage: ./validate_all_flows.sh

OUTPUT_DIR="./output"
VALIDATOR="./validate_flow.sh"

echo "============================================================"
echo "Batch Contact Flow Validator"
echo "============================================================"
echo ""

if [ ! -f "$VALIDATOR" ]; then
    echo "Error: Validator script not found at $VALIDATOR"
    exit 1
fi

# Make sure validator is executable
chmod +x "$VALIDATOR"

# Count total files
total=$(find "$OUTPUT_DIR" -name "*.json" | wc -l | tr -d ' ')
echo "Found $total flow(s) to validate"
echo ""

# Track results
valid_count=0
invalid_count=0

# Process each JSON file
for flow_file in "$OUTPUT_DIR"/*.json; do
    if [ -f "$flow_file" ]; then
        filename=$(basename "$flow_file")
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Validating: $filename"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        "$VALIDATOR" "$flow_file"
        
        if [ $? -eq 0 ]; then
            valid_count=$((valid_count + 1))
        else
            invalid_count=$((invalid_count + 1))
        fi
        
        echo ""
        
        # Add a small delay to avoid API throttling
        sleep 1
    fi
done

echo "============================================================"
echo "Validation Summary"
echo "============================================================"
echo "Total:   $total"
echo "Valid:   $valid_count"
echo "Invalid: $invalid_count"
echo ""

if [ $invalid_count -eq 0 ]; then
    echo "[SUCCESS] All flows are valid!"
    exit 0
else
    echo "[WARNING] Some flows failed validation"
    exit 1
fi
