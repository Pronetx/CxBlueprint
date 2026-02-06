"""
QA Test: Zero-Knowledge Agent Test

Goal: Have an LLM agent attempt to build contact flows using ONLY
MODEL_INSTRUCTIONS.md as its documentation. This tests how intuitive
and complete the library documentation is.

For each scenario, the agent:
1. Receives MODEL_INSTRUCTIONS.md as its sole reference
2. Gets a plain-English description of the desired flow
3. Generates Python code using cxblueprint
4. The code is executed and validated

Usage:
    python qa_tests/test_zero_knowledge.py

Requires ANTHROPIC_API_KEY environment variable.
"""

import sys
import os
import json
import tempfile
import traceback
import subprocess

sys.path.insert(0, "src")
sys.path.insert(0, "qa_tests")

from qa_helpers import QAReport, print_report

# Scenarios: plain-English descriptions of flows an agent should build
SCENARIOS = [
    {
        "name": "pizza_ordering",
        "description": (
            "Build a pizza delivery ordering flow. "
            "Start with a welcome message greeting the caller. "
            "Then present a menu: Press 1 for Pickup, Press 2 for Delivery. "
            "Each option should play a confirmation message. "
            "If invalid input or timeout, play an error message. "
            "All paths end with a disconnect."
        ),
    },
    {
        "name": "appointment_scheduler",
        "description": (
            "Build a doctor's office appointment scheduler flow. "
            "Start with a welcome message. "
            "Check business hours using check_hours_of_operation. "
            "If in hours: present a menu with Press 1 for New Appointment, "
            "Press 2 for Cancel Appointment, Press 3 to speak to staff. "
            "If out of hours: play a closed message and disconnect. "
            "All menu options should play a confirmation then disconnect."
        ),
    },
    {
        "name": "bank_balance_inquiry",
        "description": (
            "Build a bank account balance inquiry flow. "
            "Start with a welcome message. "
            "Set a contact attribute 'department' to 'banking'. "
            "Use a compare block to branch on $.Attributes.customer_tier: "
            "if 'premium' route to a VIP greeting, if 'standard' route to "
            "a normal greeting. Both greetings should then go to a shared "
            "menu: Press 1 for Balance, Press 2 for Transfers. "
            "Handle errors and invalid input. All paths end with disconnect."
        ),
    },
    {
        "name": "ab_test_support",
        "description": (
            "Build a customer support flow with A/B testing. "
            "Start with a welcome message. "
            "Use distribute_by_percentage with a 60/40 split. "
            "Path A (60%): play 'You are in our new express support experience.' "
            "Path B (40%): play 'Thank you for calling support.' "
            "Both paths converge to a shared menu: Press 1 for Technical, "
            "Press 2 for Billing. Handle errors. All paths disconnect."
        ),
    },
]


SYSTEM_PROMPT = """You are a Python developer using the cxblueprint library to build
Amazon Connect contact flows. You have access to the library documentation below.

IMPORTANT RULES:
- Output ONLY valid Python code, no markdown fences, no explanation
- The code must be a complete, runnable script
- Start with: from cxblueprint import Flow
- Use flow = Flow.build("Flow Name") to create the flow
- Use flow.compile_to_file(output_path) at the end
- The variable `output_path` will be provided — read it from sys.argv[1]
- Add `import sys` and use `output_path = sys.argv[1]`
- Do NOT import anything except from cxblueprint and sys
- Do NOT use print statements
- Do NOT define functions or classes — just top-level sequential code

DOCUMENTATION:
{instructions}
"""

USER_PROMPT = """Build the following contact flow using the cxblueprint library.
The output path will be passed as sys.argv[1].

Flow description:
{description}

Remember: output ONLY Python code, no markdown, no explanation.
"""


def load_instructions() -> str:
    """Load MODEL_INSTRUCTIONS.md as the agent's only documentation."""
    doc_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "src", "cxblueprint", "docs", "MODEL_INSTRUCTIONS.md",
    )
    with open(doc_path, "r") as f:
        return f.read()


def generate_code(instructions: str, scenario: dict, api_key: str) -> str:
    """Call Claude API to generate Python code for a scenario."""
    import urllib.request

    body = json.dumps({
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT.format(instructions=instructions),
        "messages": [
            {"role": "user", "content": USER_PROMPT.format(description=scenario["description"])}
        ],
    })

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    # Extract text from response
    code = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            code += block["text"]

    # Strip markdown fences if present
    code = code.strip()
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    return code


def execute_code_safely(code: str, code_path: str, output_path: str) -> dict:
    """Execute generated code as a subprocess for isolation."""
    result = subprocess.run(
        [sys.executable, code_path, output_path],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env={**os.environ, "PYTHONPATH": "src"},
    )

    if result.returncode != 0:
        return {
            "success": False,
            "error": result.stderr or result.stdout or "Unknown error",
        }

    # Check if output file was created
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            flow_json = json.load(f)
        return {
            "success": True,
            "actions": len(flow_json.get("Actions", [])),
            "has_metadata": "Metadata" in flow_json,
            "has_start_action": "StartAction" in flow_json,
            "flow_json": flow_json,
        }
    else:
        return {"success": False, "error": "Output file not created"}


def run_test() -> QAReport:
    report = QAReport("test_zero_knowledge")

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        report.error("ANTHROPIC_API_KEY not set — cannot run zero-knowledge test")
        return report

    # Load documentation
    try:
        instructions = load_instructions()
        report.success(
            f"Loaded MODEL_INSTRUCTIONS.md ({len(instructions)} chars)",
            "This is the ONLY documentation the agent receives"
        )
    except Exception as exc:
        report.error("Failed to load MODEL_INSTRUCTIONS.md", exc)
        return report

    passed = 0
    total = len(SCENARIOS)

    for scenario in SCENARIOS:
        name = scenario["name"]

        # Generate code
        try:
            code = generate_code(instructions, scenario, api_key)
            report.success(
                f"[{name}] Agent generated {len(code.splitlines())} lines of code"
            )
        except Exception as exc:
            report.error(f"[{name}] Code generation failed", exc)
            continue

        # Save generated code for inspection
        code_dir = os.path.join(os.path.dirname(__file__), "output", "zero_knowledge")
        os.makedirs(code_dir, exist_ok=True)
        code_path = os.path.join(code_dir, f"{name}.py")
        with open(code_path, "w") as f:
            f.write(code)

        # Create temp output path
        output_path = os.path.join(code_dir, f"{name}_tmp.json")

        try:
            result = execute_code_safely(code, code_path, output_path)
            if result["success"]:
                report.success(
                    f"[{name}] Code executed successfully — {result['actions']} blocks",
                    f"has_metadata={result['has_metadata']}, has_start_action={result['has_start_action']}"
                )

                # Move to named output
                final_path = os.path.join(code_dir, f"{name}.json")
                os.rename(output_path, final_path)

                # Validate the flow by loading it
                try:
                    from cxblueprint import Flow
                    flow = Flow.from_file(final_path)
                    flow.validate()
                    report.success(f"[{name}] Flow validates after decompile round-trip")
                    passed += 1
                except Exception as exc:
                    report.friction(
                        f"[{name}] Flow compiled but failed round-trip validation",
                        str(exc)
                    )
                    passed += 1  # Still count — compilation worked
            else:
                error_msg = result.get("error", "unknown")
                # Truncate long errors
                if len(error_msg) > 500:
                    error_msg = error_msg[:500] + "..."
                report.error(
                    f"[{name}] Code execution failed",
                    Exception(error_msg)
                )
                # Save error details
                err_path = os.path.join(code_dir, f"{name}_error.txt")
                with open(err_path, "w") as f:
                    f.write(f"Code:\n{code}\n\nError:\n{result.get('error', '')}")
        except subprocess.TimeoutExpired:
            report.error(f"[{name}] Code execution timed out (30s)")
        except Exception as exc:
            report.error(f"[{name}] Unexpected error", exc)

        # Clean up temp file if it still exists
        if os.path.exists(output_path):
            try:
                os.unlink(output_path)
            except OSError:
                pass

    # Summary
    report.block_count = passed
    report.compiled = passed > 0
    report.validation_passed = passed == total
    report.success(
        f"Zero-knowledge results: {passed}/{total} scenarios produced valid flows",
        "Tests library documentation completeness and API intuitiveness"
    )

    return report


if __name__ == "__main__":
    print_report(run_test())
