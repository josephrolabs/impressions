from impressions.core.code_extraction import extract_code
from impressions.core.execution import ExecutionResult
from impressions.core.pytest_grader import PytestCodeGrader
from impressions.core.tasks import Task, TaskExecution, TaskExpected, TaskInput


def test_extracts_language_tagged_fence():
    response = "```python\ndef solve():\n    return 1\n```\n"

    assert extract_code(response) == "def solve():\n    return 1\n"


def test_extracts_bare_fence():
    response = "```\nx = 1\n```"

    assert extract_code(response) == "x = 1\n"


def test_extracts_block_surrounded_by_prose():
    response = "Here is the solution:\n\n```python\nx = 2\n```\n\nLet me know!\n"

    assert extract_code(response) == "x = 2\n"


def test_returns_first_block_when_several_present():
    response = "```python\nx = 1\n```\n\nExample:\n\n```python\ny = 2\n```\n"

    assert extract_code(response) == "x = 1\n"


def test_unclosed_fence_yields_block_contents():
    response = "```python\nx = 3\n"

    assert extract_code(response) == "x = 3\n"


def test_unfenced_code_returned_unchanged():
    response = "def solve():\n    return 1\n"

    assert extract_code(response) is response


def test_prose_without_fences_returned_unchanged():
    response = "Call `solve()` with the `value` argument."

    assert extract_code(response) is response


def test_empty_response_returned_unchanged():
    assert extract_code("") == ""


def test_grader_executes_extracted_code_and_flags_extraction(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_add(): assert True\n", encoding="utf-8")
    executor = CapturingExecutor(ExecutionResult("1 passed in 0.01s", "", 0, False))

    result = PytestCodeGrader(executor).grade(
        task, "```python\ndef add(a, b): return a + b\n```\n"
    )

    assert executor.code == "def add(a, b): return a + b\n"
    assert result.metadata["code_extraction_applied"] is True
    assert result.metadata["passed"] is True
    assert result.output == "```python\ndef add(a, b): return a + b\n```\n"


def test_grader_passes_unfenced_code_through_unchanged(tmp_path):
    task = make_task(tmp_path)
    test_file = task.path.parent / "tests/test_solution.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_add(): assert True\n", encoding="utf-8")
    executor = CapturingExecutor(ExecutionResult("1 passed in 0.01s", "", 0, False))

    result = PytestCodeGrader(executor).grade(task, "def add(a, b): return a + b")

    assert executor.code == "def add(a, b): return a + b"
    assert result.metadata["code_extraction_applied"] is False


class CapturingExecutor:
    def __init__(self, result):
        self.result = result
        self.code = None

    def execute(self, code, **kwargs):
        self.code = code
        return self.result


def make_task(tmp_path, execution=TaskExecution("solution.py", "tests/test_solution.py", 30)):
    return Task(
        path=tmp_path / "add.yaml",
        version=1,
        name="add",
        description="Add.",
        input=TaskInput(prompt="Write add."),
        expected=TaskExpected(type="code"),
        execution=execution,
    )
