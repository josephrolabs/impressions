"""Deterministic classification of normalized evaluation failures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class FailureCategory(str, Enum):
    """Initial taxonomy for unsuccessful evaluation attempts."""

    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    TEST_FAILURE = "test_failure"
    TIMEOUT = "timeout"
    FORMAT_ERROR = "format_error"
    OTHER = "other"


@dataclass(frozen=True)
class FailureClassification:
    """Machine-readable failure category with a deterministic explanation."""

    category: FailureCategory
    reason: str


def classify_failure(metadata: Mapping[str, Any]) -> FailureClassification | None:
    """Classify a normalized unsuccessful execution/grading result.

    Precedence is timeout, response/materialization format, syntax/import,
    pytest assertion failure, generic runtime failure, then an explicit fallback.
    """
    if metadata.get("passed") is True:
        return None
    if metadata.get("timed_out") is True:
        return FailureClassification(FailureCategory.TIMEOUT, "Execution exceeded its timeout.")
    if metadata.get("format_error") is True or metadata.get("output_limit_exceeded") is True:
        return FailureClassification(
            FailureCategory.FORMAT_ERROR,
            "Generated output could not be safely materialized for evaluation.",
        )

    output = "\n".join(
        str(metadata.get(field, "")) for field in ("stdout", "stderr")
    )
    if any(token in output for token in ("SyntaxError", "IndentationError", "ImportError", "ModuleNotFoundError")):
        return FailureClassification(
            FailureCategory.SYNTAX_ERROR,
            "Python could not parse or import the generated solution.",
        )
    if _positive_int(metadata.get("failed_tests")):
        return FailureClassification(
            FailureCategory.TEST_FAILURE,
            "One or more pytest assertions failed.",
        )
    if metadata.get("exit_code") not in (None, 0):
        return FailureClassification(
            FailureCategory.RUNTIME_ERROR,
            "Execution exited unsuccessfully outside a pytest assertion failure.",
        )
    return FailureClassification(FailureCategory.OTHER, "Failure did not match a known category.")


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
