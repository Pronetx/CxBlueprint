"""
Canvas Layout Engine - Automatic positioning for Amazon Connect flow blocks

This module handles the complex task of automatically positioning flow blocks
on the Amazon Connect canvas using a layered BFS (Breadth-First Search) algorithm.
"""

from typing import Dict, List, Tuple, Optional, Set, TYPE_CHECKING
from collections import deque, defaultdict

if TYPE_CHECKING:
    from .blocks.base import FlowBlock


class CanvasLayoutEngine:
    """Positions flow blocks using layered BFS algorithm.

    The Amazon Connect Canvas X increases to the right and Y increases downwards.
    Block positions represent the top-left corner of the block.

    This algorithm positions blocks in a grid layout:
    - X axis (columns): determined by BFS level from start block
    - Y axis (rows): determined by order of discovery, keeping related branches together
    - Sequential flow (NextAction) goes horizontally (left to right)
    - Branching (Conditions/Errors) fans out vertically (top to bottom)
    """

    # Layout constants based on AWS Connect canvas analysis
    BLOCK_WIDTH = 200  # Estimated block width in pixels
    BLOCK_HEIGHT_BASE = 100  # Base block height (no conditions)
    BLOCK_HEIGHT_PER_BRANCH = 25  # Additional height per condition/error branch
    HORIZONTAL_SPACING = 280  # Pixels between columns (left edge to left edge)
    VERTICAL_SPACING_MIN = 180  # Minimum vertical spacing between rows
    START_X = 150  # X position of first column
    START_Y = 50  # Y position of first row

    def __init__(self, debug: bool = False):
        self.debug = debug

    def calculate_positions(
        self, blocks: List["FlowBlock"], start_action: Optional[str]
    ) -> Dict[str, dict]:
        """Calculate block positions using layered BFS algorithm.

        Returns dict mapping block_id to {"x": int, "y": int}.
        """
        if not start_action:
            return {}

        # Phase 1: Assign levels (columns)
        levels = self._assign_levels(blocks, start_action)

        # Phase 2: Assign rows
        rows = self._assign_rows(blocks, levels)

        # Phase 3: Compact rows to remove gaps
        rows = self._compact_rows(rows)

        # Phase 4: Calculate Y positions based on cumulative heights
        # Group blocks by row to calculate Y offsets
        row_blocks = defaultdict(list)
        for block_id, row in rows.items():
            row_blocks[row].append(block_id)

        # Calculate the maximum height needed for each row
        row_heights = {}
        for row, block_ids in row_blocks.items():
            max_height = self.VERTICAL_SPACING_MIN
            for block_id in block_ids:
                block = self._get_block(blocks, block_id)
                block_height = self._get_block_height(block) + 80  # Add padding
                max_height = max(max_height, block_height)
            row_heights[row] = max_height

        # Calculate cumulative Y positions for each row
        row_y_positions = {}
        current_y = self.START_Y
        for row in sorted(row_heights.keys()):
            row_y_positions[row] = current_y
            current_y += row_heights[row]

        # Phase 5: Convert to pixel positions
        positions = {}
        for block_id in levels:
            level = levels[block_id]
            row = rows[block_id]

            x = self.START_X + level * self.HORIZONTAL_SPACING
            y = row_y_positions[row]

            positions[block_id] = {"x": int(x), "y": int(y)}

        if self.debug:
            self._print_debug_info(positions)

        return positions

    def _get_block(
        self, blocks: List["FlowBlock"], block_id: str
    ) -> Optional["FlowBlock"]:
        """Get block by ID."""
        return next((b for b in blocks if b.identifier == block_id), None)

    def _get_all_targets(self, block: "FlowBlock") -> List[Tuple[str, str]]:
        """Get all target block IDs from a block's transitions.

        Returns list of (target_id, transition_type) tuples.
        transition_type is 'next', 'condition', or 'error'.
        """
        targets = []
        transitions = block.transitions

        # NextAction first (primary path)
        if transitions.get("NextAction"):
            targets.append((transitions["NextAction"], "next"))

        # Then conditions (in order)
        for cond in transitions.get("Conditions", []):
            if cond.get("NextAction"):
                targets.append((cond["NextAction"], "condition"))

        # Then errors (in order)
        for err in transitions.get("Errors", []):
            if err.get("NextAction"):
                targets.append((err["NextAction"], "error"))

        return targets

    def _assign_levels(
        self, blocks: List["FlowBlock"], start_action: str
    ) -> Dict[str, int]:
        """Assign each block to a horizontal level (column) using BFS.

        Level 0 is the start block, level 1 is blocks reachable in 1 step, etc.
        Each block gets assigned to its shortest path level from start.
        """
        levels = {}
        queue = deque([(start_action, 0)])

        while queue:
            block_id, level = queue.popleft()

            # Skip if already assigned (keep shortest path level)
            if block_id in levels:
                continue

            levels[block_id] = level

            block = self._get_block(blocks, block_id)
            if not block:
                continue

            # Add all targets to queue at next level
            for target_id, _ in self._get_all_targets(block):
                if target_id not in levels:
                    queue.append((target_id, level + 1))

        return levels

    def _build_parent_map(self, blocks: List["FlowBlock"]) -> Dict[str, List[str]]:
        """Build a map of block_id -> list of parent block_ids."""
        parents = defaultdict(list)

        for block in blocks:
            for target_id, _ in self._get_all_targets(block):
                parents[target_id].append(block.identifier)

        return parents

    def _get_parent_row(
        self, block_id: str, rows: Dict[str, int], parent_map: Dict[str, List[str]]
    ) -> int:
        """Get the minimum row of this block's parents, or 0 if no parents have rows yet."""
        parent_ids = parent_map.get(block_id, [])
        parent_rows = [rows[pid] for pid in parent_ids if pid in rows]
        return min(parent_rows) if parent_rows else 0

    def _build_next_action_map(self, blocks: List["FlowBlock"]) -> Dict[str, str]:
        """Build a map of block_id -> parent that reaches it via NextAction."""
        next_action_parent = {}

        for block in blocks:
            transitions = block.transitions
            if transitions.get("NextAction"):
                next_action_parent[transitions["NextAction"]] = block.identifier

        return next_action_parent

    def _assign_rows(
        self, blocks: List["FlowBlock"], levels: Dict[str, int]
    ) -> Dict[str, int]:
        """Assign row (Y) positions to blocks within each level.

        Key insight: Blocks reached via NextAction should stay at the same row
        as their parent (horizontal flow). Only branching (conditions/errors)
        creates new rows (vertical fan-out).
        """
        parent_map = self._build_parent_map(blocks)
        next_action_parent = self._build_next_action_map(blocks)

        # Group blocks by level
        level_groups = defaultdict(list)
        for block_id, level in levels.items():
            level_groups[level].append(block_id)

        rows: dict[str, int] = {}
        used_rows_per_level: dict[int, set[int]] = defaultdict(
            set
        )  # Track used rows at each level

        # Process levels in order
        for level in sorted(level_groups.keys()):
            blocks_at_level = level_groups[level]

            # Sort by parent's row to keep related branches together
            blocks_at_level.sort(
                key=lambda bid: self._get_parent_row(bid, rows, parent_map)
            )

            for block_id in blocks_at_level:
                # Check if this block is reached via NextAction
                next_parent = next_action_parent.get(block_id)

                if next_parent and next_parent in rows:
                    # Try to use same row as NextAction parent (horizontal flow)
                    desired_row = rows[next_parent]
                    if desired_row not in used_rows_per_level[level]:
                        rows[block_id] = desired_row
                        used_rows_per_level[level].add(desired_row)
                        continue

                # For branching targets or if desired row is taken, find next available
                min_row = self._get_parent_row(block_id, rows, parent_map)

                # Find first unused row at this level at or after min_row
                row = min_row
                while row in used_rows_per_level[level]:
                    row += 1

                rows[block_id] = row
                used_rows_per_level[level].add(row)

        return rows

    def _compact_rows(self, rows: Dict[str, int]) -> Dict[str, int]:
        """Compact row assignments to remove gaps.

        Renumbers rows to be contiguous starting from 0.
        """
        if not rows:
            return rows

        # Get sorted unique row values
        unique_rows = sorted(set(rows.values()))

        # Create mapping from old row to new compact row
        row_map = {old: new for new, old in enumerate(unique_rows)}

        # Apply mapping
        return {block_id: row_map[row] for block_id, row in rows.items()}

    def _get_block_height(self, block: Optional["FlowBlock"]) -> int:
        """Calculate the visual height of a block based on its branches.

        Blocks with more conditions/errors need more vertical space.
        """
        if not block:
            return self.BLOCK_HEIGHT_BASE

        transitions = block.transitions
        num_conditions = len(transitions.get("Conditions", []))
        num_errors = len(transitions.get("Errors", []))
        num_branches = num_conditions + num_errors

        # Base height + additional height per branch
        height = self.BLOCK_HEIGHT_BASE + (num_branches * self.BLOCK_HEIGHT_PER_BRANCH)
        return height

    def _print_debug_info(self, positions: Dict[str, dict]):
        """Print debug information about the layout."""
        print("\nCanvas Layout Debug")
        print("-" * 30)
        print(f"Blocks positioned: {len(positions)}")

        if positions:
            x_coords = [pos["x"] for pos in positions.values()]
            y_coords = [pos["y"] for pos in positions.values()]

            canvas_width = max(x_coords) - min(x_coords) + 200
            canvas_height = max(y_coords) - min(y_coords) + 100
            print(f"Canvas size: {canvas_width}px × {canvas_height}px")

            unique_x = len(set(x_coords))
            unique_y = len(set(y_coords))
            print(f"Layout: {unique_x} columns, {unique_y} rows")

            # Check for collisions
            pos_set = set()
            collision_count = 0
            for block_id, pos in positions.items():
                pos_tuple = (pos["x"], pos["y"])
                if pos_tuple in pos_set:
                    collision_count += 1
                pos_set.add(pos_tuple)

            if collision_count == 0:
                print("No collisions detected")
            else:
                print(f"WARNING: {collision_count} collisions detected")

        print("-" * 30)
