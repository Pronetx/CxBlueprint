"""
Generate the counter flow - Simple example using Flow as a library
"""
import sys
sys.path.insert(0, '../src')

from flow_builder import Flow
import json
from pathlib import Path


def generate_counter_flow():
    """Generate a flow that invokes a counter Lambda and speaks the result."""
    
    # Create the flow builder
    flow = Flow.build("Counter Flow")
    
    # Step 1: Welcome message (entry point)
    welcome = flow.play_prompt("Thank you for calling!")
    
    # Step 2: Invoke Lambda (template placeholder - resolved by Terraform)
    invoke_counter = flow.invoke_lambda(
        function_arn="${COUNTER_LAMBDA_ARN}",
        timeout_seconds=8
    )
    welcome.then(invoke_counter)
    
    # Step 3: Say the count back (using Lambda's return value)
    say_count = flow.play_prompt("You are caller number $.External.count")
    invoke_counter.then(say_count)
    
    # Step 4: Ask for feedback rating
    rating_menu = flow.get_input("Please rate your experience. Press 1 for excellent, 2 for good, or 3 for poor", timeout=10)
    say_count.then(rating_menu)
    
    # Step 5: Handle rating responses
    thanks_excellent = flow.play_prompt("Thank you for your excellent rating!")
    thanks_good = flow.play_prompt("Thank you for your feedback!")
    thanks_poor = flow.play_prompt("We apologize. Your feedback helps us improve.")
    
    # Step 6: Disconnect (end of flow)
    disconnect = flow.disconnect()
    
    # Wire rating menu branches
    rating_menu.when("1", thanks_excellent) \
        .when("2", thanks_good) \
        .when("3", thanks_poor) \
        .otherwise(disconnect) \
        .on_error("InputTimeLimitExceeded", disconnect) \
        .on_error("NoMatchingCondition", disconnect) \
        .on_error("NoMatchingError", disconnect)
    
    # All thank you messages lead to disconnect
    thanks_excellent.then(disconnect)
    thanks_good.then(disconnect)
    thanks_poor.then(disconnect)
    
    # Handle Lambda errors
    invoke_counter.on_error("NoMatchingError", disconnect)
    
    return flow


def main():
    """Generate the flow JSON file for Terraform deployment."""
    
    print("Generating Counter Flow")
    print("="*60)
    
    flow = generate_counter_flow()    
    compiled = flow.compile()   
    output_path = Path(__file__).parent / "counter_flow.json"
    
    with open(output_path, 'w') as f:
        json.dump(compiled, f, indent=2)
    
    print(f"Flow generated: {output_path}")
    print(f"Total blocks: {len(compiled['Actions'])}")
    print("Next: cd terraform && terraform apply")


if __name__ == "__main__":
    main()
