# Impressions: AI Code Evaluation Harness

## Project Summary

Impressions is an evaluation harness for measuring the correctness and reliability of AI-generated code. The first version focuses on deterministic, reproducible signals: structured coding tasks, model-generated solutions, isolated execution, pytest-based grading, pass@k-style reliability metrics, and versioned run outputs.

Future versions will explore tracing, dashboards, LLM-as-judge scoring and complex qualitative analysis.

## Background: A Study in Impressions

AI systems are inherently non-deterministic. Their outputs often manifest as fluid, unstructured prose that resists traditional unit testing. Much like a jazz performance, an AI model may explore a unique melody every time it is invoked, making it difficult to capture performance with rigid, binary assessments.

AI models do not merely "compute"—they express. To truly measure their performance, we need a framework that reconciles the cold precision of deterministic testing with the subjective nuance of human judgment

### Why "Impressions"?
This project is named **Impressions**—a nod to the jazz standard by John Coltrane. Just as a jazz composition provides a structural framework for improvisation, this harness provides a structure for evaluation. In jazz, a theme is interpreted differently by every musician, and each "impression" reveals a unique dimension of the melody.

In this framework, an **Impression** is the atomic unit of assessment—a polymorphic construct that defines how we measure AI behavior. An Impression serves as a unified interface for disparate grading methods::

* **Deterministic:** A unit test or regex match for rigid code requirements.
* **Model-Based:** An "LLM-as-a-judge" that analyzes tone, reasoning, or quality.
* **Human-Centric:** An interface for expert-in-the-loop qualitative feedback.

By abstracting diverse grading methodologies into a unified interface, Impressions allows developers to build layered evaluation pipelines. You are not merely running a test suite; you are gathering a collection of impressions to develop a holistic, multi-faceted understanding of your model’s capabilities.

## Core Architecture

```text
Problem Dataset
    |
    v
Prompt Builder
    |
    v
Model Layer
    |
    v
Execution Sandbox
    |
    v
Test Runner
    |
    v
Scoring Engine
    |
    v
Results Store
    |
    v
Analysis and Reporting
```

## Component Design

### 1. Task Dataset

Tasks are defined as structured YAML files. Each task should include enough information to reproduce the prompt, execute the generated code, and grade the result.

Recommended dataset for MVP:

- 9 total tasks.
- 3 easy tasks.
- 4 medium tasks.
- 2 hard tasks.
- 3–5 test cases per task.

Recommended categories:

- Bug fix.
- Function generation.
- Refactor.
- Test writing.
- Error handling.
- Small multi-file repair.

Example YAML shape:

```yaml
id: bug_fix_001
title: Fix duplicate detection
difficulty: easy
category: bug_fix
timeout_seconds: 10
entrypoint: solution.py
prompt: |
  Fix the function so it returns duplicate values in order of first repeated occurrence.
starter_code: |
  def find_duplicates(values):
      return []
tests: tests/test_solution.py
```

### 2. Prompt Builder

The prompt builder turns task specs into reproducible model inputs.

Responsibilities:

- Apply a versioned system prompt.
- Inject task instructions, starter code, and output constraints.
- Record the exact rendered prompt for every attempt.
- Support prompt variants for baseline comparisons.

MVP prompt variants:

- `baseline`: minimal coding assistant prompt.
- `engineered`: stricter output format and test-focused instructions.

### 3. Model Layer

The model layer isolates provider-specific API details from the rest of the harness.

Responsibilities:

- Submit prompts to the configured provider.
- Retry transient failures.
- Capture response text, model metadata, token usage, latency, and errors.
- Support repeated attempts per task for pass@k analysis.

Suggested interface:

```python
class ModelClient:
    def generate(self, prompt: str, config: ModelConfig) -> ModelResponse:
        ...
```

### 4. Execution Sandbox

Generated code must execute in a Docker sandbox.

Responsibilities:

- Run generated code in an isolated Python container.
- Disable network access.
- Enforce per-task timeouts.
- Mount only temporary task files.
- Capture stdout, stderr, exit code, and timeout status.

Default timeout policy:

- Easy tasks: 10 seconds.
- Medium tasks: 30 seconds.
- Hard tasks: 60 seconds.

### 5. Test Runner

The test runner grades generated code using pytest.

Responsibilities:

- Materialize the generated solution and task tests inside the sandbox.
- Run pytest.
- Parse pass/fail results.
- Capture test-level output.
- Return a normalized execution result.

### 6. Scoring Engine

The scoring engine prioritizes objective correctness.

Primary metrics:

- Test pass rate: `passing_tests / total_tests`.
- Task success: all required tests passed.
- First-attempt success rate.
- Observed pass@k: whether at least one of `k` attempts succeeded.
- Mean attempts to success.

Note on pass@k:

For the MVP, report an observed pass@k result based on the configured number of attempts. If the project later samples more than `k` attempts per task, implement the standard HumanEval estimator:

```text
pass@k = 1 - comb(n - c, k) / comb(n, k)
```

Where `n` is the number of generated samples and `c` is the number of correct samples.

### 7. Failure Classification

Each failed attempt should be assigned a simple failure type.

Initial taxonomy:

- `syntax_error`: generated code cannot parse or import.
- `runtime_error`: code crashes during execution.
- `test_failure`: code runs but fails assertions.
- `timeout`: execution exceeds the task timeout.
- `format_error`: response cannot be extracted into runnable code.
- `other`: fallback category for unknown failures.

### 8. Run Registry

Every eval run should be saved as a versioned experiment.

Each run should capture:

- Run ID.
- Timestamp.
- Git commit SHA, if available.
- Task set version.
- Prompt version.
- Model provider and model name.
- Generation config.
- Per-task attempts.
- Generated code.
- Execution logs.
- Scores and aggregate metrics.

Suggested output structure:

```text
results/
  2026-06-26_001/
    run.json
    config.json
    prompts/
    outputs/
    logs/
```

### 9. CLI Reporter

The CLI is the primary MVP interface.

Required commands:

```bash
impressions init
impressions run --tasks tasks/ --model default --k 3
impressions report results/2026-06-26_001
impressions compare results/baseline results/engineered
```

Required output:

- Task-level status.
- Attempts per task.
- Test pass counts.
- Failure types.
- Pass@1 and observed pass@k.
- Aggregate summary.
- Path to JSON results.

### Project Initialization

Create a new Impressions project scaffold with:

```bash
impressions init
```

By default, this initializes the current directory. You can also pass a target directory:

```bash
impressions init path/to/project
```

The command creates:

```text
.
├── impressions.toml
├── tasks/
│   └── example.yaml
└── reports/
```

Existing scaffold files are not overwritten unless you confirm the prompt or pass `--force`.

## Scoring Philosophy

The core principle is: **correctness first, nuance later**.

The MVP should favor objective, reproducible scoring over subjective quality judgments. If a signal cannot be measured deterministically in v1, defer it.

### Tier 1: Functional Correctness

Question: does the code do what it is supposed to do?

Method:

- Run generated code against predefined pytest suites.
- Record binary test outcomes.
- Treat deterministic test success as the primary ground truth.

### Tier 2: Failure Mode Classification

Question: when the code fails, why does it fail?

Method:

- Classify failures using parser errors, exit codes, pytest output, exceptions, and timeout status.
- Track failure distributions across tasks and runs.

### Tier 3: Behavioral Quality

Question: how reliably and efficiently does the model solve the task?

Method:

- Track first-attempt success.
- Track attempts to success.
- Track token usage and latency where provider metadata is available.
- Optionally compare code variability across attempts.


## Future Roadmap

Version 2 candidates:

- Multi-model comparison.
- LLM-as-judge for readability and explanation quality.
- Static analysis with Ruff, Bandit, or Semgrep.
- Web dashboard.
- Failure clustering.
- Cost and latency dashboards.
- Larger benchmark suites.
- Task authoring UI.
- CI integration for scheduled eval runs.
