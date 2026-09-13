import pytest

from impressions.core.failure_classification import (
    FailureCategory,
    classify_failure,
)


@pytest.mark.parametrize(
    ("metadata", "category"),
    [
        ({"timed_out": True, "stderr": "SyntaxError"}, FailureCategory.TIMEOUT),
        ({"output_limit_exceeded": True}, FailureCategory.FORMAT_ERROR),
        ({"stderr": "SyntaxError: invalid syntax"}, FailureCategory.SYNTAX_ERROR),
        ({"stderr": "ModuleNotFoundError"}, FailureCategory.SYNTAX_ERROR),
        ({"failed_tests": 1, "exit_code": 1}, FailureCategory.TEST_FAILURE),
        ({"exit_code": 1, "stderr": "ValueError"}, FailureCategory.RUNTIME_ERROR),
        ({"exit_code": None}, FailureCategory.OTHER),
    ],
)
def test_classify_failure_uses_documented_precedence(metadata, category):
    assert classify_failure(metadata).category is category


def test_classify_failure_returns_none_for_successful_result():
    assert classify_failure({"passed": True, "exit_code": 0}) is None
