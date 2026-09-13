from dataclasses import FrozenInstanceError

import pytest

from impressions.core import CodeExecutor as PublicCodeExecutor
from impressions.core import ExecutionError as PublicExecutionError
from impressions.core import ExecutionResult as PublicExecutionResult
from impressions.core.execution import CodeExecutor, ExecutionError, ExecutionResult


def test_execution_result_captures_normalized_process_outcome():
    result = ExecutionResult(
        stdout="hello\n",
        stderr="",
        exit_code=0,
        timed_out=False,
        duration_seconds=0.1,
    )

    assert result.stdout == "hello\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.duration_seconds == 0.1


def test_execution_result_is_immutable():
    result = ExecutionResult(stdout="", stderr="", exit_code=0, timed_out=False)

    with pytest.raises(FrozenInstanceError):
        result.exit_code = 1


def test_execution_api_exports_from_core_package():
    assert PublicCodeExecutor is CodeExecutor
    assert PublicExecutionError is ExecutionError
    assert PublicExecutionResult is ExecutionResult
