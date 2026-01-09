"""
Shows how to define related flows with template placeholders that get
resolved during Terraform/CDK deployment.
"""
import sys
sys.path.insert(0, '../src')
from flow_builder import ContactFlowBuilder
import json
from pathlib import Path


def create_hello_goodbye_flows():
    """Create both hello and goodbye flows with template references."""
    
    
    # 1. Define Goodbye Flow (target of transfer)
    print("1. Creating Goodbye Flow...")
    goodbye_flow = ContactFlowBuilder("Goodbye Flow")
    goodbye_msg = goodbye_flow.play_prompt("Goodbye! Thank you for calling. Have a great day!")
    disconnect = goodbye_flow.disconnect()
    goodbye_msg.then(disconnect)
    
    # 2. Define Hello Flow (references goodbye flow via template)
    print("2. Creating Hello Flow with template reference...")
    hello_flow = ContactFlowBuilder("Hello Flow")
    hello_msg = hello_flow.play_prompt("Hello! Welcome to our system.")
    
    # Use template placeholder - will be resolved during deployment
    transfer = hello_flow.transfer_to_flow("{{GOODBYE_FLOW_ARN}}")
    hello_msg.then(transfer)
    
    return hello_flow, goodbye_flow


def save_flows_with_templates():
    """Save flows showing template approach."""
    hello_flow, goodbye_flow = create_hello_goodbye_flows()
    
    # Compile both flows
    hello_compiled = hello_flow.compile()
    goodbye_compiled = goodbye_flow.compile()
    
    # Save with template names
    output_dir = Path(__file__).parent.parent / "src" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    hello_path = output_dir / "template_hello_flow.json"
    goodbye_path = output_dir / "template_goodbye_flow.json"
    
    with open(hello_path, 'w') as f:
        json.dump(hello_compiled, f, indent=2)
    
    with open(goodbye_path, 'w') as f:
        json.dump(goodbye_compiled, f, indent=2)
    
    print(f"\n3. Generated Template Files:")
    print(f"   Hello: {hello_path}")
    print(f"   Goodbye: {goodbye_path}")
    
    # Show the template reference
    transfer_block = next(a for a in hello_compiled['Actions'] if a['Type'] == 'TransferToFlow')
    template_ref = transfer_block['Parameters']['ContactFlowId']
    print(f"   Template reference: {template_ref}")
    
    return hello_compiled, goodbye_compiled




def main():
    hello_data, goodbye_data = save_flows_with_templates()
    
    


if __name__ == "__main__":
    main()