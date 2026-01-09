import os
from pathlib import Path
from decompiler import FlowDecompiler


def process_flow(input_path: str, output_path: str):
    """Decompile and recompile a contact flow."""
    print(f"Processing: {input_path}")
    
    # Decompile
    flow, has_unknown_blocks = FlowDecompiler.decompile_from_file(input_path)
    print(f"  Decompiled {len(flow.actions)} blocks:")
    for action in flow.actions:
        print(f"    - {action.type} (ID: {action.identifier[:8]}...)")
    
    # Skip output if unknown blocks found
    if has_unknown_blocks:
        print(f"  [SKIP] Skipping output due to unknown blocks\n")
        return False
    
    # Recompile
    recompiled_json = flow.to_json()
    
    # Write to output
    with open(output_path, 'w') as f:
        f.write(recompiled_json)
    print(f"  [OK] Written to: {output_path}\n")
    return True


if __name__ == "__main__":
    # Setup paths
    project_root = Path(__file__).parent.parent
    input_dir = project_root / "input"
    output_dir = project_root / "output"
    
    success_count = 0
    skipped_count = 0
    
    for input_file in input_dir.glob("*.json"):
        # Create output filename with Cx_ prefix
        output_filename = f"Cx_{input_file.name}"
        output_path = output_dir / output_filename
        
        if process_flow(str(input_file), str(output_path)):
            success_count += 1
        else:
            skipped_count += 1
    
    print("=" * 60)
    print(f"Processed: {success_count + skipped_count} flows")
    print(f"Success: {success_count}")
    print(f"Skipped: {skipped_count}")
    print("=" * 60)
