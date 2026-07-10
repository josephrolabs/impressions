# Impressions: AI Code Evaluation Harness

## Project Summary

Impressions is an evaluation harness for measuring the correctness and reliability of AI-generated code. The first version focuses on deterministic, reproducible signals: structured coding tasks, model-generated solutions, isolated execution, pytest-based grading, pass@k-style reliability metrics, and versioned run outputs.

Future versions will explore tracing, dashboards, LLM-as-judge scoring and complex qualitative analysis.

## Project Status

Impressions is early-stage. The project scaffold, configuration system, task pipeline, and a minimal evaluation engine are implemented; the model layer, sandboxed execution, pytest-based grading, and the run registry described in the original design are not yet built.

**Implemented**

- Project scaffolding via `impressions init`
- TOML-based project configuration (`impressions.toml`) with loading and validation
- YAML task definition discovery, parsing, and schema validation
- A minimal `EvaluationEngine` with a deterministic `EchoEvaluator` for pipeline verification
- CLI commands: `version`, `init`, `config show`, `tasks list`, `tasks validate`, `evaluate`
- Unit test coverage for config, tasks, evaluation, and the CLI

**In Progress**

- Real evaluator backends beyond the echo/no-op implementation
- Structured evaluation output and reporting

**Planned** (see [Core Architecture (Target)](#core-architecture-target) and [Future Roadmap](#future-roadmap))

- Prompt builder with versioned system prompts and prompt variants
- Model layer / provider-agnostic `ModelClient` interface
- Docker-based execution sandbox
- Pytest-based test runner and pass@k scoring
- Failure mode classification
- Versioned run registry and `impressions run` / `report` / `compare` commands

## Background: A Study in Impressions

AI systems are inherently non-deterministic. Their outputs often manifest as fluid, unstructured prose that resists traditional unit testing. Much like a jazz performance, an AI model may explore a unique melody every time it is invoked, making it difficult to capture performance with rigid, binary assessments.

AI models do not merely "compute"—they express. To truly measure their performance, we need a framework that reconciles the cold precision of deterministic testing with the subjective nuance of human judgment

### Why "Impressions"?
This project is named **Impressions**—a nod to the jazz standard by John Coltrane. Just as a jazz composition provides a structural framework for improvisation, this harness provides a structure for evaluation. In jazz, a theme is interpreted differently by every musician, and each "impression" reveals a unique dimension of the melody.

In this framework, an **Impression** is the atomic unit of assessment—a polymorphic construct that defines how we measure AI behavior. An Impression serves as a unified interface for disparate grading methods::

* **Deterministic:** A unit test or regex match for rigid code requirements.
* **Model-Based:** An "LLM-as-a-judge" that analyzes tone, reasoning, or quality.
* **Human-Centric:** An interface for expert-in-the-loop qualitative feedback.

By abstracting diverse grading methodologies into a unified interface, Impressions allows developers to build layered evaluation pipelines. You are not merely running a test suite; you are gathering a collection of impressions to develop a holistic, multi-faceted understanding of your model's capabilities.

## Design Principles

- **Deterministic-first evaluation.** Objective, reproducible signals (schema validation, deterministic evaluators) come before subjective or model-based judgment.
- **Composable architecture.** Each stage of the pipeline (config, task discovery, task parsing, evaluation) is a small, independently testable module connected through explicit interfaces.
- **Provider-agnostic interfaces.** The `Evaluator` protocol is designed so real model/grading backends can be swapped in without changing the engine or CLI.
- **Incremental development.** Functionality ships as thin, working vertical slices (e.g., an echo evaluator before a real one) rather than large speculative builds.
- **Test-first.** Each module (`config`, `tasks`, `evaluation`, `cli`) has direct unit test coverage before new functionality is layered on top.

## Installation

Impressions targets Python 3.10+.

```bash
git clone https://github.com/josephrolabs/impressions.git
cd impressions
python -m venv .venv
source .venv/bin/activate
pip install -e . --group dev
```

This installs the `impressions` package in editable mode along with development dependencies (currently `pytest`).

## Quick Start

Initialize a new project scaffold:

```bash
impressions init
```

This creates `impressions.toml`, a `tasks/` directory with an example task, and an empty `reports/` directory in the current directory. Pass a path to initialize elsewhere, or `--force` to overwrite existing scaffold files.

Inspect the loaded project configuration:

```bash
impressions config show
```

List discovered, validated task definitions:

```bash
impressions tasks list
```

Validate task definitions without running an evaluation:

```bash
impressions tasks validate
```

Run the evaluation pipeline against all discovered tasks:

```bash
impressions evaluate
```

The MVP evaluation pipeline currently runs tasks through a deterministic `EchoEvaluator`, which returns the task's prompt as its output. This exists to exercise and verify the full config → discovery → validation → evaluation → CLI pipeline ahead of a real, provider-backed evaluator.

## Core Architecture (Current)

```text
Task YAML
    |
    v
Project Config (impressions.toml)
    |
    v
Task Discovery
    |
    v
Task Validation / Parsing
    |
    v
EvaluationEngine
    |
    v
Evaluator (EchoEvaluator)
    |
    v
CLI Output
```

## Core Architecture (Target)

The diagram below reflects the original, long-term design. It is the direction the project is building toward, not the current implementation — see [Project Status](#project-status) for what exists today.

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

## Repo Structure

```text
.
├── impressions/
│   ├── __init__.py        # Package version
│   ├── cli.py              # argparse-based CLI: version, init, config, tasks, evaluate
│   └── core/
│       ├── config.py       # impressions.toml loading and validation
│       ├── evaluation.py   # Evaluator protocol, EvaluationEngine, EchoEvaluator
│       └── tasks.py        # Task discovery, YAML parsing, schema validation
├── tests/
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_evaluation.py
│   └── test_tasks.py
├── pyproject.toml
└── README.md
```

## Component Design

Each component below is labeled with its current status. Sections without a status label describe target design that has not been implemented yet.

### 1. Task Dataset *(implemented, schema simplified from original design)*

Tasks are defined as structured YAML files, discovered from the directory configured in `impressions.toml` (`[paths] tasks`). Each task file is parsed and validated against a small required schema before it can be evaluated.

Current required task schema:

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

`impressions tasks validate` reports missing or malformed fields per file. The richer task shape from the original design (below) — including difficulty, category, timeouts, starter code, and a linked test file — is planned but not yet implemented:

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

Target YAML shape:

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

### 2. Prompt Builder *(planned)*

The prompt builder turns task specs into reproducible model inputs.

Responsibilities:

- Apply a versioned system prompt.
- Inject task instructions, starter code, and output constraints.
- Record the exact rendered prompt for every attempt.
- Support prompt variants for baseline comparisons.

MVP prompt variants:

- `baseline`: minimal coding assistant prompt.
- `engineered`: stricter output format and test-focused instructions.

### 3. Model Layer *(planned)*

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

### 4. Execution Sandbox *(planned)*

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

### 5. Test Runner *(planned)*

The test runner grades generated code using pytest.

Responsibilities:

- Materialize the generated solution and task tests inside the sandbox.
- Run pytest.
- Parse pass/fail results.
- Capture test-level output.
- Return a normalized execution result.

### 6. Evaluation Engine *(implemented, minimal)*

The current `EvaluationEngine` coordinates evaluation of validated tasks through a pluggable `Evaluator`. It validates that each evaluator returns a structured `EvaluationResult`, then runs the configured evaluator across all discovered tasks in order.

The only evaluator implemented today is `EchoEvaluator`, a deterministic backend that returns the task's prompt as its output — useful for exercising the pipeline end-to-end, but not a real correctness signal. The scoring behavior described below (pytest-based pass/fail grading and pass@k) is the target design once a real, code-executing evaluator exists.

Target primary metrics:

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

### 7. Failure Classification *(planned)*

Each failed attempt should be assigned a simple failure type.

Initial taxonomy:

- `syntax_error`: generated code cannot parse or import.
- `runtime_error`: code crashes during execution.
- `test_failure`: code runs but fails assertions.
- `timeout`: execution exceeds the task timeout.
- `format_error`: response cannot be extracted into runnable code.
- `other`: fallback category for unknown failures.

### 8. Run Registry *(planned)*

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

### 9. CLI Reporter *(partially implemented)*

Implemented commands:

```bash
impressions version
impressions init [path] [--force]
impressions config show
impressions tasks list
impressions tasks validate
impressions evaluate
```

Target commands from the original design, not yet implemented:

```bash
impressions run --tasks tasks/ --model default --k 3
impressions report results/2026-06-26_001
impressions compare results/baseline results/engineered
```

Target output for a full run (once the model layer, sandbox, and scoring engine exist):

- Task-level status.
- Attempts per task.
- Test pass counts.
- Failure types.
- Pass@1 and observed pass@k.
- Aggregate summary.
- Path to JSON results.

### Project Initialization *(implemented)*

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

> Note: the scoring tiers above describe the target scoring engine. Today, `impressions evaluate` runs the pipeline with a deterministic echo evaluator and does not yet produce pass/fail or tiered scores.

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
