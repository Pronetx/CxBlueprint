"""
Flow Graph Analysis & Validation

Analyzes flow structure to detect common issues before deployment.
"""

from typing import Set, List, Dict
from blocks.base import FlowBlock


class FlowAnalyzer:
    """Analyze flow structure for problems."""

    def __init__(self, blocks: List[FlowBlock], start_action: str):
        self.blocks = blocks
        self.start_action = start_action
        self.block_map = {b.identifier: b for b in blocks}

    def find_orphaned_blocks(self) -> List[str]:
        """Find blocks not reachable from start."""
        reachable = set()
        to_visit = [self.start_action]

        while to_visit:
            block_id = to_visit.pop()
            if block_id in reachable:
                continue
            reachable.add(block_id)

            block = self.block_map.get(block_id)
            if block:
                for target_id in self._get_all_targets(block):
                    to_visit.append(target_id)

        all_blocks = set(self.block_map.keys())
        return list(all_blocks - reachable)

    def find_missing_error_handlers(self) -> Dict[str, List[str]]:
        """Find GetParticipantInput blocks missing required error handlers."""
        missing = {}
        required_errors = {
            "InputTimeLimitExceeded",
            "NoMatchingCondition",
            "NoMatchingError",
        }

        for block in self.blocks:
            if block.type == "GetParticipantInput":
                errors = block.transitions.get("Errors", [])
                handled = {e["ErrorType"] for e in errors}
                unhandled = required_errors - handled
                if unhandled:
                    missing[block.identifier] = list(unhandled)

        return missing

    def find_unterminated_paths(self) -> List[str]:
        """Find blocks that don't end in disconnect/transfer."""
        terminal_types = {
            "DisconnectParticipant",
            "EndFlowExecution",
            "TransferToFlow",
            "TransferContactToQueue",
        }

        unterminated = []
        for block in self.blocks:
            if block.type in terminal_types:
                continue

            # Check if this block has no outgoing transitions
            transitions = block.transitions
            has_next = bool(transitions.get("NextAction"))
            has_conditions = bool(transitions.get("Conditions"))
            has_errors = bool(transitions.get("Errors"))

            if not (has_next or has_conditions or has_errors):
                unterminated.append(block.identifier)

        return unterminated

    def _get_all_targets(self, block: FlowBlock) -> List[str]:
        """Get all target block IDs from transitions."""
        targets = []
        trans = block.transitions

        if trans.get("NextAction"):
            targets.append(trans["NextAction"])

        for cond in trans.get("Conditions", []):
            if cond.get("NextAction"):
                targets.append(cond["NextAction"])

        for err in trans.get("Errors", []):
            if err.get("NextAction"):
                targets.append(err["NextAction"])

        return targets

    def generate_report(self) -> str:
        """Generate human-readable analysis report."""
        orphaned = self.find_orphaned_blocks()
        missing_errors = self.find_missing_error_handlers()
        unterminated = self.find_unterminated_paths()

        report = []

        if orphaned:
            report.append(f"  Orphaned blocks ({len(orphaned)}):")
            for block_id in orphaned:
                block = self.block_map[block_id]
                report.append(f"    - {block.type} ({block_id[:8]})")

        if missing_errors:
            report.append(f"  Missing error handlers ({len(missing_errors)} blocks):")
            for block_id, missing in missing_errors.items():
                block = self.block_map[block_id]
                report.append(f"    - {block.type} ({block_id[:8]})")
                report.append(f"      Missing: {', '.join(missing)}")

        if unterminated:
            report.append(f"  Unterminated paths ({len(unterminated)}):")
            for block_id in unterminated:
                block = self.block_map[block_id]
                report.append(f"    - {block.type} ({block_id[:8]})")

        return "\n".join(report) if report else "  No issues found"

    def has_issues(self) -> bool:
        """Check if there are any validation issues."""
        orphaned = self.find_orphaned_blocks()
        missing_errors = self.find_missing_error_handlers()
        unterminated = self.find_unterminated_paths()

        return bool(orphaned or missing_errors or unterminated)


class FlowValidationError(Exception):
    """Raised when flow validation fails."""

    pass
