"""
Tests for CanvasLayoutEngine positioning logic.

Tests the layered BFS layout algorithm for positioning flow blocks.
"""

import sys
from pathlib import Path
import pytest

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from canvas_layout import CanvasLayoutEngine


def test_canvas_engine_initialization():
    """Test CanvasLayoutEngine initialization."""
    engine = CanvasLayoutEngine(debug=False)
    assert engine.debug is False
    assert engine.BLOCK_WIDTH == 200
    assert engine.HORIZONTAL_SPACING == 280

    debug_engine = CanvasLayoutEngine(debug=True)
    assert debug_engine.debug is True


def test_calculate_positions_empty_flow():
    """Test positioning with empty flow."""
    engine = CanvasLayoutEngine()
    positions = engine.calculate_positions([], None)
    assert positions == {}


def test_calculate_positions_single_block(simple_flow):
    """Test positioning with single block."""
    engine = CanvasLayoutEngine()

    # Create a single isolated block for testing
    from flow_builder import Flow

    single_flow = Flow.build("Single Block Test")
    block = single_flow.play_prompt("Single block")

    positions = engine.calculate_positions([block], block.identifier)

    assert len(positions) == 1
    assert block.identifier in positions
    assert positions[block.identifier]["x"] == engine.START_X
    assert positions[block.identifier]["y"] == engine.START_Y


def test_calculate_positions_linear_flow(simple_flow):
    """Test positioning with linear flow (two blocks)."""
    engine = CanvasLayoutEngine()
    positions = engine.calculate_positions(
        simple_flow.blocks, simple_flow._start_action
    )

    assert len(positions) == len(simple_flow.blocks)

    # Check that blocks are positioned horizontally
    x_positions = [pos["x"] for pos in positions.values()]
    assert len(set(x_positions)) > 1  # Should have different X positions

    # First block should be at start position
    start_block_pos = positions[simple_flow._start_action]
    assert start_block_pos["x"] == engine.START_X
    assert start_block_pos["y"] == engine.START_Y


def test_calculate_positions_branching_flow(branching_flow):
    """Test positioning with branching flow."""
    engine = CanvasLayoutEngine()
    positions = engine.calculate_positions(
        branching_flow.blocks, branching_flow._start_action
    )

    assert len(positions) == len(branching_flow.blocks)

    # Check that we have multiple columns and rows for branching
    x_positions = [pos["x"] for pos in positions.values()]
    y_positions = [pos["y"] for pos in positions.values()]

    assert len(set(x_positions)) >= 2  # Multiple columns
    assert len(set(y_positions)) >= 1  # At least one row


def test_assign_levels_bfs_ordering(simple_flow):
    """Test that BFS level assignment works correctly."""
    engine = CanvasLayoutEngine()
    levels = engine._assign_levels(simple_flow.blocks, simple_flow._start_action)

    assert levels[simple_flow._start_action] == 0  # Start block at level 0

    # Check that all blocks have valid levels
    for level in levels.values():
        assert level >= 0


def test_compact_rows_removes_gaps():
    """Test that row compaction removes gaps."""
    engine = CanvasLayoutEngine()

    # Test with gaps in row numbers
    rows_with_gaps = {
        "block1": 0,
        "block2": 2,  # Gap at row 1
        "block3": 5,  # Gap at rows 3-4
    }

    compacted = engine._compact_rows(rows_with_gaps)

    # Should be compacted to consecutive rows
    expected_rows = {0, 1, 2}
    actual_rows = set(compacted.values())
    assert actual_rows == expected_rows


def test_get_block_height_calculation(simple_flow):
    """Test block height calculation based on branches."""
    engine = CanvasLayoutEngine()

    # Block with no conditions/errors
    simple_block = simple_flow.blocks[0]
    height = engine._get_block_height(simple_block)
    assert height == engine.BLOCK_HEIGHT_BASE

    # Test with None block
    none_height = engine._get_block_height(None)
    assert none_height == engine.BLOCK_HEIGHT_BASE


def test_debug_output(simple_flow, capsys):
    """Test that debug output is produced when enabled."""
    engine = CanvasLayoutEngine(debug=True)
    engine.calculate_positions(simple_flow.blocks, simple_flow._start_action)

    captured = capsys.readouterr()
    assert "Canvas Layout Debug" in captured.out
    assert "Blocks positioned:" in captured.out


def test_no_debug_output(simple_flow, capsys):
    """Test that no debug output is produced when disabled."""
    engine = CanvasLayoutEngine(debug=False)
    engine.calculate_positions(simple_flow.blocks, simple_flow._start_action)

    captured = capsys.readouterr()
    assert "Canvas Layout Debug" not in captured.out
