"""
Contact Flow Builder - Programmatic flow generation
"""
from pathlib import Path
import json
from typing import List, Optional, Dict, Set, Tuple
from collections import deque
import uuid
from blocks.base import FlowBlock
from blocks.message_participant import MessageParticipant
from blocks.disconnect_participant import DisconnectParticipant
from blocks.get_participant_input import GetParticipantInput
from blocks.transfer_to_flow import TransferToFlow


class ContactFlowBuilder:
    """Build contact flows programmatically with BFS-based layout."""
    
    # Layout constants
    BLOCK_SIZE = 180
    HORIZONTAL_SPACING = 50  # Left-to-right spacing between sibling blocks
    VERTICAL_SPACING = 250   # Top-to-bottom spacing between levels
    COLLISION_PADDING = 200  # Minimum safe distance (block + spacing)
    START_X = 150
    START_Y = 40
    
    def __init__(self, name: str, debug: bool = False):
        self.name = name
        self.version = "2019-10-30"
        self.blocks: List[FlowBlock] = []
        self._start_action: Optional[str] = None
        self.debug = debug
    
    def _register_block(self, block: FlowBlock) -> FlowBlock:
        """Register a block with the flow."""
        self.blocks.append(block)
        
        # Set start action to first block if not set
        if self._start_action is None:
            self._start_action = block.identifier
        
        return block
    
    def play_prompt(self, text: str) -> MessageParticipant:
        """Create a play prompt block."""
        block = MessageParticipant(
            identifier=str(uuid.uuid4()),
            text=text
        )
        return self._register_block(block)
    
    def get_input(self, text: str, timeout: int = 5) -> GetParticipantInput:
        """Create a get participant input block."""
        block = GetParticipantInput(
            identifier=str(uuid.uuid4()),
            text=text,
            input_time_limit_seconds=str(timeout),
            store_input="False"
        )
        return self._register_block(block)
    
    def disconnect(self) -> DisconnectParticipant:
        """Create a disconnect block."""
        block = DisconnectParticipant(
            identifier=str(uuid.uuid4())
        )
        return self._register_block(block)
    
    def transfer_to_flow(self, contact_flow_id: str) -> TransferToFlow:
        """Create a transfer to flow block."""
        block = TransferToFlow(
            identifier=str(uuid.uuid4()),
            contact_flow_id=contact_flow_id
        )
        return self._register_block(block)
    
    # ============================================================
    # BFS-BASED LAYOUT ALGORITHM
    # ============================================================
    
    def _get_block(self, block_id: str) -> Optional[FlowBlock]:
        """Get block by ID."""
        return next((b for b in self.blocks if b.identifier == block_id), None)
    
    def _has_collision(self, positions: Dict[str, dict], x: int, y: int, exclude_id: str = None) -> bool:
        """Check if position collides with existing blocks."""
        for block_id, pos in positions.items():
            if exclude_id and block_id == exclude_id:
                continue
            
            x_dist = abs(x - pos["x"])
            y_dist = abs(y - pos["y"])
            
            # Check if within collision zone
            if x_dist < self.COLLISION_PADDING and y_dist < self.COLLISION_PADDING:
                return True
        
        return False
    
    def _find_safe_position(self, positions: Dict[str, dict], start_x: int, start_y: int) -> Tuple[int, int]:
        """Find safe position starting from given coordinates, moving right."""
        x = start_x
        y = start_y
        
        # Keep moving right until we find a safe spot
        max_attempts = 50
        for _ in range(max_attempts):
            if not self._has_collision(positions, x, y):
                return (x, y)
            x += self.HORIZONTAL_SPACING
        
        # If still colliding, try next row
        return (start_x, y + self.VERTICAL_SPACING)
    
    def _calculate_positions_bfs(self) -> Dict[str, dict]:
        """Calculate positions using breadth-first search.
        
        BFS ensures all blocks at same depth are positioned before going deeper.
        This creates a level-by-level layout.
        """
        if not self._start_action:
            return {}
        
        positions = {}
        visited = set()
        queued = set()  # Track what's already in queue
        
        # BFS queue: (block_id, suggested_x, level)
        queue = deque([(self._start_action, self.START_X, 0)])
        queued.add(self._start_action)
        
        while queue:
            # Process entire level at once
            level_size = len(queue)
            current_level = queue[0][2] if queue else 0
            level_y = self.START_Y + (current_level * self.VERTICAL_SPACING)
            
            for _ in range(level_size):
                block_id, suggested_x, level = queue.popleft()
                
                if block_id in visited:
                    continue
                
                visited.add(block_id)
                
                # Find safe position for this block
                x, y = self._find_safe_position(positions, suggested_x, level_y)
                
                # Round to grid
                x = round(x / 10) * 10
                y = round(y / 10) * 10
                
                positions[block_id] = {"x": x, "y": y}
                
                # Get children for next level
                block = self._get_block(block_id)
                if not block:
                    continue
                
                transitions = block.transitions
                
                # Collect all unique children
                children = []
                if "NextAction" in transitions and transitions["NextAction"]:
                    child = transitions["NextAction"]
                    if child not in visited and child not in queued and child not in children:
                        children.append(child)
                
                if "Conditions" in transitions and transitions["Conditions"]:
                    for condition in transitions["Conditions"]:
                        if "NextAction" in condition:
                            child = condition["NextAction"]
                            if child not in visited and child not in queued and child not in children:
                                children.append(child)
                
                if "Errors" in transitions and transitions["Errors"]:
                    for error in transitions["Errors"]:
                        if "NextAction" in error:
                            child = error["NextAction"]
                            if child not in visited and child not in queued and child not in children:
                                children.append(child)
                
                # Queue children for next level, all start at same X as parent
                for child_id in children:
                    queue.append((child_id, x, level + 1))
                    queued.add(child_id)
        
        if self.debug:
            self._print_debug_info(positions)
        
        return positions
    
    def _print_debug_info(self, positions: Dict[str, dict]):
        """Print debug information about the layout."""
        print("\n" + "="*60)
        print("BFS LAYOUT DEBUG INFO")
        print("="*60)
        
        print(f"\nTotal blocks positioned: {len(positions)}")
        
        # Position summary
        if positions:
            x_coords = [pos["x"] for pos in positions.values()]
            y_coords = [pos["y"] for pos in positions.values()]
            print(f"\nCanvas dimensions:")
            print(f"  X: {min(x_coords)} to {max(x_coords)} ({max(x_coords) - min(x_coords)}px)")
            print(f"  Y: {min(y_coords)} to {max(y_coords)} ({max(y_coords) - min(y_coords)}px)")
            
            # Check for collisions
            collision_count = 0
            block_ids = list(positions.keys())
            for i, id1 in enumerate(block_ids):
                for id2 in block_ids[i+1:]:
                    pos1 = positions[id1]
                    pos2 = positions[id2]
                    x_dist = abs(pos1["x"] - pos2["x"])
                    y_dist = abs(pos1["y"] - pos2["y"])
                    if x_dist < 200 and y_dist < 200:
                        collision_count += 1
            
            print(f"\nCollision check (<200px): {collision_count} potential overlaps")
        
        print("="*60 + "\n")
    
    # ============================================================
    # COMPILATION
    # ============================================================
    
    def _build_metadata(self) -> dict:
        """Build metadata including block positions."""
        metadata = {
            "entryPointPosition": {"x": 0, "y": 0},
            "snapToGrid": False,
            "ActionMetadata": {},
            "Annotations": []
        }
        
        # Calculate positions using BFS layout
        positions = self._calculate_positions_bfs()
        
        for block_id, position in positions.items():
            metadata["ActionMetadata"][block_id] = {
                "position": position
            }
        
        return metadata
    
    def compile(self) -> dict:
        """Compile flow to AWS Connect JSON format."""
        return {
            "Version": self.version,
            "StartAction": self._start_action or "",
            "Metadata": self._build_metadata(),
            "Actions": [block.to_dict() for block in self.blocks]
        }
    
    def compile_to_json(self, indent: int = 2) -> str:
        """Compile flow to JSON string."""
        return json.dumps(self.compile(), indent=indent)
    
    def compile_to_file(self, filepath: str):
        """Compile flow and save to file."""
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(self.compile_to_json())
        
        print(f"Flow compiled to: {filepath}")