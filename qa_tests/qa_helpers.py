"""Shared QA reporting utilities for CxBlueprint gap analysis."""

import json
import sys
import traceback
from dataclasses import dataclass, field


@dataclass
class Finding:
    category: str  # "success", "friction", "missing", "error", "discoverability"
    message: str
    detail: str = ""


class QAReport:
    """Structured report for a single QA test."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.findings: list[Finding] = []
        self.compiled = False
        self.block_count = 0
        self.validation_passed = False

    def success(self, message: str, detail: str = ""):
        self.findings.append(Finding("success", message, detail))

    def friction(self, message: str, detail: str = ""):
        self.findings.append(Finding("friction", message, detail))

    def missing(self, message: str, detail: str = ""):
        self.findings.append(Finding("missing", message, detail))

    def error(self, message: str, exception: Exception | None = None):
        detail = ""
        if exception:
            detail = f"{type(exception).__name__}: {exception}"
        self.findings.append(Finding("error", message, detail))

    def discoverability(self, tried: str, correct: str, detail: str = ""):
        msg = f"Tried `{tried}` - correct is `{correct}`"
        self.findings.append(Finding("discoverability", msg, detail))

    def probe_method(self, obj, method_name: str, correct_name: str):
        """Probe whether an intuitive method name exists."""
        exists = hasattr(obj, method_name)
        if not exists:
            self.discoverability(
                f"flow.{method_name}()",
                f"flow.{correct_name}()",
                f"AttributeError: '{type(obj).__name__}' has no attribute '{method_name}'",
            )
        return exists

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "compiled": self.compiled,
            "block_count": self.block_count,
            "validation_passed": self.validation_passed,
            "findings": [
                {"category": f.category, "message": f.message, "detail": f.detail}
                for f in self.findings
            ],
        }


def print_report(report: QAReport):
    """Print a single test report."""
    status = "PASS" if report.compiled else "FAIL"
    print(f"\n{'=' * 60}")
    print(f"  [{status}] {report.test_name}")
    print(f"  Blocks: {report.block_count} | Validated: {report.validation_passed}")
    print(f"{'=' * 60}")

    for f in report.findings:
        icon = {
            "success": "+",
            "friction": "~",
            "missing": "!",
            "error": "X",
            "discoverability": "?",
        }.get(f.category, " ")
        print(f"  [{icon}] {f.message}")
        if f.detail:
            print(f"      {f.detail}")


def print_aggregate_report(reports: list[QAReport]):
    """Print consolidated gap analysis across all tests."""
    print("\n" + "=" * 70)
    print("  CXBLUEPRINT QA GAP ANALYSIS REPORT")
    print("=" * 70)

    # Summary
    total = len(reports)
    compiled = sum(1 for r in reports if r.compiled)
    validated = sum(1 for r in reports if r.validation_passed)
    print(f"\n  Tests: {total} | Compiled: {compiled}/{total} | Validated: {validated}/{total}")

    # Collect all findings by category
    by_category: dict[str, list[tuple[str, Finding]]] = {}
    for r in reports:
        for f in r.findings:
            by_category.setdefault(f.category, []).append((r.test_name, f))

    # Print each category
    category_labels = {
        "missing": "MISSING FEATURES / CONVENIENCE METHODS",
        "friction": "API FRICTION POINTS",
        "discoverability": "DISCOVERABILITY GAPS",
        "error": "ERRORS ENCOUNTERED",
        "success": "WORKING FEATURES",
    }

    for cat, label in category_labels.items():
        items = by_category.get(cat, [])
        if not items:
            continue
        print(f"\n  --- {label} ({len(items)}) ---")
        for test_name, f in items:
            print(f"  [{test_name}] {f.message}")
            if f.detail:
                print(f"      {f.detail}")

    # Summary counts
    print(f"\n  --- SUMMARY ---")
    for cat, label in category_labels.items():
        count = len(by_category.get(cat, []))
        if count:
            print(f"  {label}: {count}")

    print("\n" + "=" * 70)


def run_test_safely(test_func, test_name: str) -> QAReport:
    """Run a test function with error handling, return its report."""
    try:
        return test_func()
    except Exception as e:
        report = QAReport(test_name)
        report.error(f"Test crashed: {e}", e)
        traceback.print_exc()
        return report
