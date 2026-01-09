"""
Example: Creating a simple flow from code
"""
import sys
sys.path.insert(0, '../src')
from flow_builder import ContactFlowBuilder


def create_simple_flow():
    """Create a simple flow that says 'Created from code' and disconnects."""
    
    # Create a new flow
    flow = ContactFlowBuilder("Simple Code Generated Flow")
    
    # Add blocks
    welcome = flow.play_prompt("Created from code")
    disconnect = flow.disconnect()
    
    # Wire blocks together using fluent API
    welcome.then(disconnect).on_error("NoMatchingError", disconnect)
    
    # Compile to file
    flow.compile_to_file("../src/output/code_generated_simple.json")
    
    return flow


if __name__ == "__main__":
    print("Creating simple flow from code...")
    flow = create_simple_flow()
    
    print(f"\nFlow details:")
    print(f"  Name: {flow.name}")
    print(f"  Blocks: {len(flow.blocks)}")
    print(f"  Start action: {flow._start_action}")
    
    for block in flow.blocks:
        print(f"    - {block.type} (ID: {block.identifier[:8]}...)")
