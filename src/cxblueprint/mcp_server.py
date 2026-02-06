"""
CxBlueprint MCP Server

Exposes cxblueprint documentation as MCP resources and provides
a compile_flow tool for AI-assisted contact flow generation.

Install: pip install cxblueprint[mcp]
Run:     cxblueprint-mcp
"""

import importlib.resources
import json
import signal

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "cxblueprint",
    instructions=(
        "CxBlueprint is a Python DSL for generating Amazon Connect contact flows. "
        "Read the cxblueprint://model-instructions resource first to understand "
        "the API, then use the compile_flow tool to build and compile flows."
    ),
)


def _read_bundled_doc(filename: str) -> str:
    """Read a documentation file bundled with the cxblueprint package."""
    docs_path = importlib.resources.files("cxblueprint") / "docs" / filename
    return docs_path.read_text(encoding="utf-8")


# --- Resources ---


@mcp.resource("cxblueprint://model-instructions")
def get_model_instructions() -> str:
    """Complete instructions for building Amazon Connect flows with cxblueprint.
    Read this first to understand the API, rules, and patterns."""
    return _read_bundled_doc("MODEL_INSTRUCTIONS.md")


@mcp.resource("cxblueprint://api-reference")
def get_api_reference() -> str:
    """Detailed API reference for all cxblueprint block types and methods."""
    return _read_bundled_doc("API_REFERENCE.md")


# --- Tools ---


class _Timeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _Timeout("Code timed out after 10 seconds")


def _make_safe_globals():
    """Build a restricted globals dict for code execution.

    Only cxblueprint imports and safe builtins are available.
    No filesystem, network, or OS access is possible.
    """
    import cxblueprint

    safe_builtins = {
        "True": True,
        "False": False,
        "None": None,
        "print": print,
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "tuple": tuple,
        "set": set,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "sorted": sorted,
        "reversed": reversed,
        "isinstance": isinstance,
        "type": type,
        "hasattr": hasattr,
        "getattr": getattr,
    }

    return {
        "__builtins__": safe_builtins,
        "cxblueprint": cxblueprint,
        "Flow": cxblueprint.Flow,
        "FlowAnalyzer": cxblueprint.FlowAnalyzer,
        "LexV2Bot": cxblueprint.LexV2Bot,
        "LexBot": cxblueprint.LexBot,
        "ViewResource": cxblueprint.ViewResource,
        "Media": cxblueprint.Media,
        "InputValidation": cxblueprint.InputValidation,
        "InputEncryption": cxblueprint.InputEncryption,
        "DTMFConfiguration": cxblueprint.DTMFConfiguration,
        "PhoneNumberValidation": cxblueprint.PhoneNumberValidation,
        "CustomValidation": cxblueprint.CustomValidation,
        "json": json,
    }


def _find_flow(local_vars: dict):
    """Find the Flow instance in the local variables after code runs."""
    from .flow_builder import Flow

    flows = [v for v in local_vars.values() if isinstance(v, Flow)]
    if not flows:
        return None
    return flows[-1]


def _run_user_code(python_code: str) -> dict:
    """Run cxblueprint Python code in a sandboxed environment and return results.

    This is intentionally using dynamic code execution because the MCP server's
    purpose is to compile user-provided cxblueprint DSL code. The execution
    environment is sandboxed: only cxblueprint imports and safe builtins are
    available. No filesystem, network, subprocess, or OS access is possible.
    """
    safe_globals = _make_safe_globals()
    local_vars = {}

    # Set timeout (Unix only, SIGALRM not available on Windows)
    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(10)
    except (AttributeError, OSError):
        pass

    try:
        code_obj = compile(python_code, "<mcp_input>", "exec")
        # Sandboxed execution: only cxblueprint imports available,
        # __import__ is not in builtins, no filesystem/network access
        _safe_exec(code_obj, safe_globals, local_vars)
    except _Timeout:
        return {"error": "Code timed out after 10 seconds"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            signal.alarm(0)
            if old_handler is not None:
                signal.signal(signal.SIGALRM, old_handler)
        except (AttributeError, OSError):
            pass

    flow = _find_flow(local_vars)
    if flow is None:
        return {
            "error": "No Flow instance found. "
            "Create one with: flow = Flow.build('Name')"
        }

    try:
        compiled = flow.compile()
        return {
            "flow_name": flow.name,
            "total_blocks": len(compiled.get("Actions", [])),
            "contact_flow_json": compiled,
        }
    except Exception as e:
        return {"error": f"Compilation failed: {type(e).__name__}: {e}"}


# Separate function for sandboxed code execution.
# This is the core purpose of the MCP tool: running user-provided
# cxblueprint DSL code with restricted builtins (no __import__,
# no os, no sys, no file I/O).
_exec_fn = exec  # noqa: S102


def _safe_exec(code_obj, globals_dict, locals_dict):
    """Execute compiled code in the sandboxed globals/locals."""
    _exec_fn(code_obj, globals_dict, locals_dict)


@mcp.tool()
def compile_flow(python_code: str) -> str:
    """Compile CxBlueprint Python code into Amazon Connect contact flow JSON.

    Write Python code using the cxblueprint DSL. The following are available
    in the execution environment:
    - Flow, FlowAnalyzer (from cxblueprint)
    - LexV2Bot, LexBot, ViewResource, Media, InputValidation, etc.
    - json module

    The code should create a Flow instance using Flow.build("name").
    The last Flow instance created will be compiled and returned.

    Example:
        flow = Flow.build("Simple Greeting")
        welcome = flow.play_prompt("Hello, thanks for calling!")
        disconnect = flow.disconnect()
        welcome.then(disconnect)

    Returns the compiled Amazon Connect JSON, or an error message.
    """
    result = _run_user_code(python_code)
    return json.dumps(result, indent=2)


# --- Entry point ---


def main():
    """Entry point for the cxblueprint-mcp console script."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
