# Impressions: AI Code Evaluation Harness

## Project Summary

Impressions is an evaluation harness for measuring the correctness and reliability of AI-generated code. The first version focuses on deterministic, reproducible signals: structured coding tasks, model-generated solutions, isolated execution, pytest-based grading, pass@k-style reliability metrics, and versioned run outputs.

Future versions will explore tracing, dashboards, LLM-as-judge scoring and complex qualitative analysis.

## Current Project Status

Impressions is in pre-alpha. The repository now contains the working foundation for a Python package and CLI, with task discovery, validation, and a deterministic evaluation path. The broader AI-code-evaluation system described later in this README remains the long-term architecture.

Implemented:

- Python package with `impressions` CLI entry point.
- Project initialization via `impressions init`.
- Project configuration loading from `impressions.toml`.
- Task discovery from configured YAML task directories.
- YAML task parsing and schema validation.
- `EvaluationEngine` orchestration primitive.
- `Evaluator` protocol and structured `EvaluationResult`.
- Built-in `EchoEvaluator` for deterministic local pipeline verification.
- CLI commands for version, config inspection, task listing, task validation, and evaluation.
- Unit tests covering CLI behavior, configuration, task parsing, task discovery, and evaluation orchestration.

In progress:

- Expanding evaluator backends beyond the deterministic echo evaluator.
- Connecting the evaluation framework to model generation, execution, and scoring components.
- Persisting evaluation reports under the configured reports path.

Planned:

- Prompt rendering and prompt-version tracking.
- Provider-agnostic model clients.
- Sandboxed execution of generated code.
- Pytest-based grading of generated solutions.
- Failure classification and aggregate scoring.
- Run registry, comparison reports, and pass@k metrics.
- Dashboard, CI integration, and qualitative evaluation extensions.

## Design Principles

Impressions is being built around a few practical engineering principles:

- Deterministic-first evaluation: objective, reproducible checks are the foundation before subjective scoring is added.
- Composable architecture: configuration, task loading, evaluation orchestration, evaluator backends, and reporting are separate concerns.
- Provider-agnostic interfaces: model and evaluator integrations should be swappable behind stable local interfaces.
- Incremental development: each milestone should leave behind a working CLI and tested package surface.
- Test-first engineering: new behavior should be covered by focused unit tests before the system grows more complex.

## Installation

Clone the repository:

```bash
git clone https://github.com/josephrolabs/impressions.git
cd impressions
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the package in editable mode with development dependencies:

```bash
pip install -e . --group dev
```

Run the test suite:

```bash
pytest
```

## Quick Start

Create a new Impressions project scaffold:

```bash
impressions init
```

This creates:

```text
.
├── impressions.toml
├── tasks/
│   └── example.yaml
└── reports/
```

By default, `impressions init` initializes the current directory. You can also pass a target directory:

```bash
impressions init path/to/project
```

Existing scaffold files are not overwritten unless you confirm the prompt or pass `--force`.

Inspect the loaded project configuration:

```bash
impressions config show
```

List discovered and validated tasks:

```bash
impressions tasks list
```

Validate all discovered task files:

```bash
impressions tasks validate
```

Run the current deterministic evaluation workflow:

```bash
impressions evaluate
```

Today, `impressions evaluate` loads validated tasks and runs them through `EvaluationEngine` with the built-in `EchoEvaluator`. This verifies the local evaluation pipeline without calling an external model provider.

## Current Architecture

The implemented architecture is intentionally small:

```text
Task YAML
    |
    v
impressions.toml
    |
    v
Task Discovery
    |
    v
Task Validation
    |
    v
EvaluationEngine
    |
    v
Evaluator
    |
    v
CLI Output
```

This foundation is designed to grow into the target architecture below. The current CLI proves that projects can be initialized, configured, discovered, validated, and evaluated through a stable package interface.

## Repository Structure

```text
.
├── impressions/
│   ├── __init__.py
│   ├── cli.py
│   └── core/
│       ├── __init__.py
│       ├── config.py
│       ├── evaluation.py
│       └── tasks.py
├── tests/
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_evaluation.py
│   └── test_tasks.py
├── pyproject.toml
└── README.md
```

Key modules:

- `impressions.cli`: command-line parser and command handlers.
- `impressions.core.config`: `impressions.toml` loading and validation.
- `impressions.core.tasks`: YAML task discovery, parsing, and validation.
- `impressions.core.evaluation`: evaluator protocol, result object, `EvaluationEngine`, and `EchoEvaluator`.
- `tests`: unit tests for current package behavior.

## Task Format

Current task files use schema version 1 and are stored as `.yaml` or `.yml` files in the configured tasks directory.

```yaml
version: 1
name: example-task
description: Summarize the supplied article.

input:
  prompt: |
    Write a concise summary of the supplied article.

expected:
  type: text
```

Required fields:

- `version`: task schema version. Currently `1`.
- `name`: non-empty task name displayed by the CLI.
- `description`: non-empty human-readable task description.
- `input.prompt`: non-empty prompt text.
- `expected.type`: non-empty expected output type.

## Background: A Study in Impressions

AI systems are inherently non-deterministic. Their outputs often manifest as fluid, unstructured prose that resists traditional unit testing. Much like a jazz performance, an AI model may explore a unique melody every time it is invoked, making it difficult to capture performance with rigid, binary assessments.

AI models do not merely "compute" - they express. To truly measure their performance, we need a framework that reconciles the cold precision of deterministic testing with the subjective nuance of human judgment.

### Why "Impressions"?

This project is named **Impressions** - a nod to the jazz standard by John Coltrane. Just as a jazz composition provides a structural framework for improvisation, this harness provides a structure for evaluation. In jazz, a theme is interpreted differently by every musician, and each "impression" reveals a unique dimension of the melody.

In this framework, an **Impression** is the atomic unit of assessment - a polymorphic construct that defines how we measure AI behavior. An Impression serves as a unified interface for disparate grading methods:

- **Deterministic:** A unit test or regex match for rigid code requirements.
- **Model-Based:** An "LLM-as-a-judge" that analyzes tone, reasoning, or quality.
- **Human-Centric:** An interface for expert-in-the-loop qualitative feedback.

By abstracting diverse grading methodologies into a unified interface, Impressions allows developers to build layered evaluation pipelines. You are not merely running a test suite; you are gathering a collection of impressions to develop a holistic, multi-faceted understanding of your model's capabilities.

## Target Architecture

The following diagram represents the long-term architecture, not the complete current implementation:

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

## Target Component Design

The components below describe the intended system as Impressions grows beyond the current package and CLI foundation.

### 1. Task Dataset

Tasks are defined as structured YAML files. Each task should include enough information to reproduce the prompt, execute the generated code, and grade the result.

Recommended dataset for MVP:

- 9 total tasks.
- 3 easy tasks.
- 4 medium tasks.
- 2 hard tasks.
- 3-5 test cases per task.

Recommended categories:

- Bug fix.
- Function generation.
- Refactor.
- Test writing.
- Error handling.
- Small multi-file repair.

Future coding-task YAML shape:

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

Generated code must execute in a sandbox.

Responsibilities:

- Run generated code in an isolated Python environment.
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

The current CLI already supports initialization, config inspection, task listing, task validation, and deterministic evaluation. The target CLI will expand that surface into full model-backed runs and report comparison.

Target commands:

```bash
impressions init
impressions run --tasks tasks/ --model default --k 3
impressions report results/2026-06-26_001
impressions compare results/baseline results/engineered
```

Target output:

- Task-level status.
- Attempts per task.
- Test pass counts.
- Failure types.
- Pass@1 and observed pass@k.
- Aggregate summary.
- Path to JSON results.

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
