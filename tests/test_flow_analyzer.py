"""
Tests for FlowAnalyzer validation logic.

These tests verify the structural validation of flows without requiring AWS credentials.
"""

import sys
from pathlib import Path
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from flow_analyzer import FlowAnalyzer, FlowValidationError


def test_find_orphaned_blocks_detects_unreachable(orphaned_flow):
    """Test that orphaned blocks are detected correctly."""
    analyzer = FlowAnalyzer(orphaned_flow.blocks, orphaned_flow._start_action)
    orphaned = analyzer.find_orphaned_blocks()

    assert len(orphaned) == 1
    assert "orphaned-block-123" in orphaned


def test_find_orphaned_blocks_none_when_all_connected(simple_flow):
    """Test that fully connected flows have no orphaned blocks."""
    analyzer = FlowAnalyzer(simple_flow.blocks, simple_flow._start_action)
    orphaned = analyzer.find_orphaned_blocks()

    assert len(orphaned) == 0


def test_missing_error_handlers_detects_incomplete(missing_error_handlers_flow):
    """Test that GetParticipantInput missing error handlers are detected."""
    analyzer = FlowAnalyzer(
        missing_error_handlers_flow.blocks, missing_error_handlers_flow._start_action
    )
    missing = analyzer.find_missing_error_handlers()

    assert len(missing) > 0
    # Should have one block with missing handlers
    block_id = list(missing.keys())[0]
    missing_handlers = missing[block_id]

    # Should be missing all three required handlers
    assert "InputTimeLimitExceeded" in missing_handlers
    assert "NoMatchingCondition" in missing_handlers
    assert "NoMatchingError" in missing_handlers


def test_missing_error_handlers_none_when_complete(menu_flow):
    """Test that flows with complete error handlers pass validation."""
    analyzer = FlowAnalyzer(menu_flow.blocks, menu_flow._start_action)
    missing = analyzer.find_missing_error_handlers()

    assert len(missing) == 0


def test_unterminated_paths_detects_blocks_without_exit(unterminated_flow):
    """Test that blocks without exits are detected."""
    analyzer = FlowAnalyzer(unterminated_flow.blocks, unterminated_flow._start_action)
    unterminated = analyzer.find_unterminated_paths()

    assert len(unterminated) == 1


def test_unterminated_paths_none_for_valid_flow(simple_flow):
    """Test that properly terminated flows pass validation."""
    analyzer = FlowAnalyzer(simple_flow.blocks, simple_flow._start_action)
    unterminated = analyzer.find_unterminated_paths()

    assert len(unterminated) == 0


def test_has_issues_integration(orphaned_flow, simple_flow):
    """Test combined validation with has_issues() method."""
    # Orphaned flow should have issues
    analyzer_bad = FlowAnalyzer(orphaned_flow.blocks, orphaned_flow._start_action)
    assert analyzer_bad.has_issues() is True

    # Simple flow should have no issues
    analyzer_good = FlowAnalyzer(simple_flow.blocks, simple_flow._start_action)
    assert analyzer_good.has_issues() is False


def test_generate_report_formatting(orphaned_flow):
    """Test that generate_report() produces human-readable output."""
    analyzer = FlowAnalyzer(orphaned_flow.blocks, orphaned_flow._start_action)
    report = analyzer.generate_report()

    assert isinstance(report, str)
    assert len(report) > 0
    assert "Orphaned blocks" in report or "orphaned-block-123" in report


def test_flow_validation_error_with_error_code():
    """Test FlowValidationError with error code includes suggestions."""
    error = FlowValidationError(
        "Flow has orphaned blocks",
        error_code=FlowValidationError.ORPHANED_BLOCKS,
        details={"block_ids": ["block-1", "block-2"]},
    )

    error_str = str(error)
    assert "orphaned blocks" in error_str.lower()
    assert "Suggestion:" in error_str
    assert "reachable from the start action" in error_str


def test_flow_validation_error_details_preserved():
    """Test that error details are preserved in exception."""
    details = {"missing_handlers": {"block-1": ["InputTimeLimitExceeded"]}}
    error = FlowValidationError(
        "Missing error handlers",
        error_code=FlowValidationError.MISSING_ERROR_HANDLERS,
        details=details,
    )

    assert error.error_code == FlowValidationError.MISSING_ERROR_HANDLERS
    assert error.details == details


def test_flow_validation_error_without_code():
    """Test FlowValidationError works without error code."""
    error = FlowValidationError("Generic validation error")

    error_str = str(error)
    assert "Generic validation error" in error_str
    # Should not have suggestion if no error code
    assert "Suggestion:" not in error_str
