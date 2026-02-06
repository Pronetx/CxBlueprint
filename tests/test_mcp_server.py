"""Tests for the CxBlueprint MCP server."""

import json

import pytest

from cxblueprint.mcp_server import (
    _read_bundled_doc,
    _run_user_code,
    _find_flow,
    mcp,
)


class TestResources:
    """Test MCP resource loading."""

    def test_model_instructions_loads(self):
        content = _read_bundled_doc("MODEL_INSTRUCTIONS.md")
        assert len(content) > 1000
        assert "CxBlueprint" in content

    def test_api_reference_loads(self):
        content = _read_bundled_doc("API_REFERENCE.md")
        assert len(content) > 500
        assert "API" in content or "Flow" in content

    def test_missing_doc_raises(self):
        with pytest.raises(Exception):
            _read_bundled_doc("nonexistent.md")

    def test_resources_registered(self):
        resources = list(mcp._resource_manager._resources.keys())
        assert "cxblueprint://model-instructions" in resources
        assert "cxblueprint://api-reference" in resources


class TestCompileFlow:
    """Test the compile_flow tool's code execution."""

    def test_simple_flow(self):
        result = _run_user_code(
            'flow = Flow.build("Test")\n'
            'w = flow.play_prompt("Hi")\n'
            "d = flow.disconnect()\n"
            "w.then(d)"
        )
        assert "error" not in result
        assert result["flow_name"] == "Test"
        assert result["total_blocks"] == 2
        assert "Actions" in result["contact_flow_json"]

    def test_menu_flow(self):
        result = _run_user_code(
            'flow = Flow.build("Menu")\n'
            'menu = flow.get_input("Press 1 or 2", timeout=10)\n'
            'opt1 = flow.play_prompt("Option 1")\n'
            'opt2 = flow.play_prompt("Option 2")\n'
            "d = flow.disconnect()\n"
            'menu.when("1", opt1).when("2", opt2).otherwise(d)\n'
            'menu.on_error("InputTimeLimitExceeded", d)\n'
            'menu.on_error("NoMatchingCondition", d)\n'
            'menu.on_error("NoMatchingError", d)\n'
            "opt1.then(d)\n"
            "opt2.then(d)"
        )
        assert "error" not in result
        assert result["flow_name"] == "Menu"
        assert result["total_blocks"] == 4

    def test_no_flow_instance(self):
        result = _run_user_code("x = 1 + 2")
        assert "error" in result
        assert "No Flow instance" in result["error"]

    def test_syntax_error(self):
        result = _run_user_code("def foo(")
        assert "error" in result
        assert "SyntaxError" in result["error"]

    def test_runtime_error(self):
        result = _run_user_code("x = 1 / 0")
        assert "error" in result
        assert "ZeroDivisionError" in result["error"]

    def test_import_blocked(self):
        result = _run_user_code("import os")
        assert "error" in result

    def test_subprocess_blocked(self):
        result = _run_user_code("import subprocess")
        assert "error" in result

    def test_dunder_import_blocked(self):
        result = _run_user_code("__import__('os')")
        assert "error" in result

    def test_open_blocked(self):
        result = _run_user_code("f = open('/etc/passwd')")
        assert "error" in result

    def test_empty_code(self):
        result = _run_user_code("")
        assert "error" in result
        assert "No Flow instance" in result["error"]

    def test_compiled_json_is_valid(self):
        result = _run_user_code(
            'flow = Flow.build("JSON Test")\n'
            'w = flow.play_prompt("Hello")\n'
            "d = flow.disconnect()\n"
            "w.then(d)"
        )
        flow_json = result["contact_flow_json"]
        assert flow_json["Version"] == "2019-10-30"
        assert len(flow_json["Actions"]) == 2
        assert "StartAction" in flow_json
        assert "Metadata" in flow_json


class TestServerRegistration:
    """Test MCP server tool and resource registration."""

    def test_server_name(self):
        assert mcp.name == "cxblueprint"

    def test_compile_flow_tool_registered(self):
        tools = list(mcp._tool_manager._tools.keys())
        assert "compile_flow" in tools

    def test_resources_count(self):
        resources = list(mcp._resource_manager._resources.keys())
        assert len(resources) == 2
