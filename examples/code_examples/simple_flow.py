"""
Example: Creating a simple flow from code
"""

from cxblueprint import Flow


def create_simple_flow():
    """Create a simple flow that says 'Created from code' and disconnects."""

    # Create a new flow
    flow = Flow.build("Simple Code Generated Flow")

    # Add blocks
    welcome = flow.play_prompt("Created from code")
    disconnect = flow.disconnect()

    # Wire blocks together using fluent API
    welcome.then(disconnect).on_error("NoMatchingError", disconnect)

    # Compile to file
    flow.compile_to_file("../../src/output/simple.json")

    return flow


if __name__ == "__main__":
    flow = create_simple_flow()
    print(f"Generated flow: {flow.name}")
    print(f"Total blocks: {len(flow.blocks)}")
    print("Blocks created:")
    for block in flow.blocks:
        print(f"  - {repr(block)}")
