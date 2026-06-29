# Impressions: AI Code Evaluation Harness

## Project Summary

Impressions is a lightweight evaluation harness for measuring the correctness and reliability of AI-generated code. The first version focuses on deterministic, reproducible signals: structured coding tasks, model-generated solutions, isolated execution, pytest-based grading, pass@k-style reliability metrics, and versioned run outputs.

The goal is to build a credible MVP that demonstrates production evaluation thinking without over-scoping into tracing, dashboards, LLM-as-judge scoring, or complex qualitative analysis.

## Background: A Study in Impressions

In the development of AI systems, "evaluation" is often conflated with "benchmarking." We treat models like software that can be validated against deterministic unit tests. While deterministic checks are essential for correctness, they fail to capture the fluid, creative, and sometimes ambiguous nature of frontier-model outputs.

AI models don't just "compute"—they express. To truly understand their performance, we need a framework that accommodates both the cold precision of a unit test and the subjective nuance of human judgment.

### Why "Impressions"?
This project is named **Impressions**—a nod to the jazz standard by John Coltrane. Just as a jazz composition provides a structure for improvisation, this harness provides a structure for evaluation. In jazz, a melody can be interpreted differently by every player, and each "impression" reveals something new about the theme.

Similarly, in this framework, an **Impression** is the atomic unit of assessment. It is a polymorphic construct that defines how we "grade" an AI's behavior. An *Impression* could be:

* **Deterministic:** A unit test or regex match for rigid code requirements.
* **Model-Based:** An "LLM-as-a-judge" that analyzes tone, reasoning, or quality.
* **Human-Centric:** An interface for expert-in-the-loop qualitative feedback.

By abstracting these diverse grading methods into a unified "Impression" interface, this harness allows developers to build complex, layered evaluation pipelines. You aren't just running a test; you are gathering a collection of impressions to build a holistic understanding of your model’s capabilities.

## MVP Objective

Build an AI code eval harness that can:

1. Load a curated dataset of Python coding tasks from YAML.
2. Generate prompts from structured task specs.
3. Submit prompts to one or more model providers.
4. Execute generated code inside a Docker sandbox.
5. Grade results with deterministic pytest suites.
6. Calculate task-level and aggregate reliability metrics.
7. Persist every run with config, prompts, outputs, logs, and scores.
8. Report results through a CLI and JSON artifacts.

## Model Strategy

The initial plan referenced Claude Sonnet 4 as the primary model target. That should remain an open implementation decision rather than a hard requirement.

Recommended MVP approach:

- Start with a single model provider to keep the first eval loop simple.
- Design the model layer behind a provider interface so additional models can be added later.
- Treat Claude, OpenAI, local models, or other hosted APIs as interchangeable backends.
- Store model name, provider, temperature, prompt version, and generation config in every run.

MVP default:

- One model provider.
- One model configuration.
- Configurable `k`, with `k=3` as the default.

Future extension:

- Multi-model comparison.
- Prompt variant comparison.
- Provider-specific latency, cost, and reliability tracking.

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

## Explicitly Deferred from MVP

These are useful features, but they should not block the first working version:

- Web dashboard.
- Arize Phoenix or tracing integrations.
- LLM-as-judge scoring.
- Static analysis with linters or security scanners.
- Automated failure clustering.
- Multi-model comparison.
- Large task suites.
- Performance benchmarking.

## MVP Success Criteria

Must-have:

- 9 coding tasks with deterministic tests.
- Docker sandbox executes generated code safely.
- One model provider works through a clean abstraction.
- `k=3` attempts supported.
- Pass@1 and observed pass@k reported.
- Failure types classified.
- JSON results persisted.
- CLI displays task and aggregate summaries.
- README explains setup, architecture, usage, and limitations.

Nice-to-have:

- Prompt baseline comparison.
- Rich terminal formatting.
- Example result folder committed or attached as an artifact.
- Short write-up of findings.
- Blog post or portfolio case study.

## Risk Management

If behind schedule:

- Reduce task count from 9 to 5.
- Keep one prompt variant only.
- Use plain CLI output instead of rich formatting.
- Defer compare command.
- Defer blog post or extended write-up.

If model integration slows progress:

- Mock model responses to finish the sandbox, runner, scoring, and reporting layers.
- Add the live provider once the deterministic pipeline works.

If Docker sandboxing is difficult:

- Keep Docker as the required target.
- Use local subprocess execution only as a temporary development fallback.
- Clearly mark local execution as unsafe and not part of MVP success.

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

## Positioning

Impressions is designed to show careful eval engineering:

- Deterministic scoring before subjective grading.
- Safety through sandboxed execution.
- Reliability measurement through repeated attempts.
- Versioned experiments instead of one-off runs.
- Clear separation between task design, model generation, execution, scoring, and reporting.

This makes the project useful as both a practical tool and a portfolio-quality demonstration of AI evaluation system design.
