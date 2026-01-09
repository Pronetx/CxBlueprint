#!/usr/bin/env python3
"""
Test hierarchical layout with debug output
"""
import sys
sys.path.insert(0, '../src')

from flow_builder import ContactFlowBuilder

# Create flow with debug enabled
flow = ContactFlowBuilder("Layout Test Flow", debug=True)

# Build a complex flow to test all layout features
welcome = flow.play_prompt("Welcome to our service")

# Main menu with 3 options
main_menu = flow.get_input("Press 1 for Sales, 2 for Support, or 3 for Billing", timeout=10)
welcome.then(main_menu)

# Sales path
sales_msg = flow.play_prompt("Connecting you to Sales")
sales_submenu = flow.get_input("Press 1 for New Customers, 2 for Existing", timeout=5)
sales_msg.then(sales_submenu)

sales_new = flow.play_prompt("New customer sales team")
sales_existing = flow.play_prompt("Existing customer sales team")
sales_disconnect = flow.disconnect()

sales_submenu.when("1", sales_new).when("2", sales_existing).otherwise(sales_disconnect)
sales_new.then(sales_disconnect)
sales_existing.then(sales_disconnect)

# Support path
support_msg = flow.play_prompt("Connecting you to Support")
support_disconnect = flow.disconnect()
support_msg.then(support_disconnect)

# Billing path  
billing_msg = flow.play_prompt("Connecting you to Billing")
billing_submenu = flow.get_input("Press 1 for Payments, 2 for Invoices", timeout=5)
billing_msg.then(billing_submenu)

billing_payments = flow.play_prompt("Payment department")
billing_invoices = flow.play_prompt("Invoice department")
billing_disconnect = flow.disconnect()

billing_submenu.when("1", billing_payments).when("2", billing_invoices).otherwise(billing_disconnect)
billing_payments.then(billing_disconnect)
billing_invoices.then(billing_disconnect)

# Wire up main menu
error_disconnect = flow.disconnect()
main_menu.when("1", sales_msg).when("2", support_msg).when("3", billing_msg).otherwise(error_disconnect)

# Error handling - goes to disconnect
main_menu.on_error("InputTimeLimitExceeded", error_disconnect)
main_menu.on_error("NoMatchingCondition", error_disconnect)

# Compile and analyze
print("Compiling flow with hierarchical layout...\n")
flow.compile_to_file("../src/output/debug_test_flow.json")

# Analyze positions
import json
with open("../src/output/debug_test_flow.json") as f:
    data = json.load(f)

print("\n" + "="*60)
print("COLLISION ANALYSIS")
print("="*60)

metadata = data['Metadata']['ActionMetadata']
positions = [(id, meta['position']) for id, meta in metadata.items()]

# Check for overlaps
overlaps = []
for i, (id1, pos1) in enumerate(positions):
    for j, (id2, pos2) in enumerate(positions[i+1:], i+1):
        x_dist = abs(pos1['x'] - pos2['x'])
        y_dist = abs(pos1['y'] - pos2['y'])
        if x_dist < 200 and y_dist < 200:
            overlaps.append((id1[:8], pos1, id2[:8], pos2, x_dist, y_dist))

if overlaps:
    print(f'\nFound {len(overlaps)} potential overlaps:')
    for id1, pos1, id2, pos2, x_dist, y_dist in overlaps:
        print(f"  {id1}... ({pos1['x']:4},{pos1['y']:4}) <-> {id2}... ({pos2['x']:4},{pos2['y']:4}) - dist: X={x_dist}, Y={y_dist}")
else:
    print('\n✓ No overlaps detected! All blocks have sufficient spacing.')

print("="*60)
