> Integration status: the CLI and bounded official Telecom mock path are implemented and exercised. The current executable commands and exact remaining limitations are in [the tested runbook](../LOCAL_RUNBOOK.md) and [capability report](../CAPABILITIES.md). This document retains the full planned-study requirements; it is not a claim that every requirement is implemented.

# Local runbook

The researcher runs these commands on their own computer. No GPU or training is needed. The harness runs on CPU and live inference uses the researcher-selected model API. Repository preparation makes no API requests.

Use the tested release runbook and validation receipt for actual command evidence. Historical offline bundle launchers are dependency-bound and are not a substitute for the new local runner.

## 1 Prepare a clean local environment

Clone the published repository, record its commit, and follow its tested installation command and lockfile. The implementation should document the supported Python version and OS. Do not copy a cloud virtual environment or install from an unpinned personal machine path. No installation has been performed by this planning task.

First run:

```sh
python -m local_experiments --help
python -m local_experiments validate --config configs/wire-smoke.json
python -m local_experiments run --config configs/wire-smoke.json --output-dir results/wire-smoke-dry
python -m local_experiments analyze --input-dir results/wire-smoke-dry --output-dir results/wire-smoke-dry-analysis
python -m local_experiments export --input-dir results/wire-smoke-dry-analysis --output-dir exports/wire-smoke-dry
```

Omitting `--mode` means dry-run. This must work without a key and without network. Expected evidence is a fixture/plumbing result and `real_model_calls=0`; no model success estimate is expected.

The config files in this planning directory are proposed schema templates. The implementing release must install schema-compatible files at `configs/` before these commands are advertised as runnable. Validate failures should identify missing values or unsupported stages rather than manufacture successful outputs.

## 2 Configure your own API locally

Copy the release's `.env.example` to an ignored `.env` file and replace the placeholders on your own machine, or export those environment variables through your normal local method. Use the implementation's explicit env-file loading option if one exists; automatic dotenv search is forbidden in dry-run. Do not commit `.env`, paste keys into issue reports, or pass keys on shell command lines.

Set the provider protocol/base URL, API key, actor model, reviewer model, and user-simulator model. The three roles may initially use the same supported API model, but must be recorded separately. This is a setup convenience, not a model-strength comparison. No real gateway or model is preselected by this plan.

Review maximum requests, native steps/errors, retry count and concurrency. There is no required total token limit or additional approval from an assistant. An optional monetary cap can be selected when current prices are known; otherwise report tokens and unknown cost honestly. Running a local live command may incur charges from the configured provider.

## 3 Verify wire behavior first

After local values are complete:

```sh
python -m local_experiments validate --config configs/wire-smoke.json
python -m local_experiments run --config configs/wire-smoke.json --mode live --output-dir results/wire-smoke-live-001
python -m local_experiments analyze --input-dir results/wire-smoke-live-001 --output-dir results/wire-smoke-live-001-analysis
```

Inspect actual payload role/order, tool-call/result bindings, P/R/C equality and differences, packet integrity, request IDs, retries, and usage. Confirm the model/transport supports the required format. Do not interpret a successful wire test as an experimental method improvement.

## 4 Run the natural development pilot

Use only a validated runtime/task scope. The initial seven exposed tasks are development material. The configuration should contain one reference start per task, one public-triggered root at most, one q draw per root, two common-segment repeats and two suffix repeats for P/R/C, with four independent continuations for other root controls. These proposed values are a small plumbing/coverage starting point and may require adjustment for the implemented scope before any data are collected.

```sh
python -m local_experiments validate --config configs/natural-pilot.json
python -m local_experiments run --config configs/natural-pilot.json --mode dry-run --output-dir results/pilot-dry
python -m local_experiments run --config configs/natural-pilot.json --mode live --output-dir results/pilot-live-001
python -m local_experiments analyze --input-dir results/pilot-live-001 --output-dir results/pilot-live-001-analysis
```

All starts and draws stay in the report. Zero useful roots is a valid finding about coverage, not permission to replay the authored successful path or redraw the reviewer. Inspect missingness and infrastructure failures before interpreting differences.

Expand task families and validated mutating workflows before a formal repair claim. Complete outcome-blind goal/scope/local-repair mappings and estimate task-family variance and cost. Choose formal sample sizes, delta/epsilon, budgets, and stopping rules from this development work. Freeze a new protocol before evaluating held-out outcomes.

## 5 Confirmatory root and episode-start studies

These commands are the target interface. They must be rejected as confirmatory until the scientific design and relevant capability receipts are complete:

```sh
python -m local_experiments validate --config configs/confirmatory-roots.json
python -m local_experiments run --config configs/confirmatory-roots.json --mode dry-run --output-dir results/roots-dry
python -m local_experiments run --config configs/confirmatory-roots.json --mode live --output-dir results/roots-live-001
python -m local_experiments analyze --input-dir results/roots-live-001 --output-dir results/roots-live-001-analysis

python -m local_experiments validate --config configs/end-to-end.json
python -m local_experiments run --config configs/end-to-end.json --mode dry-run --output-dir results/episodes-dry
python -m local_experiments run --config configs/end-to-end.json --mode live --output-dir results/episodes-live-001
python -m local_experiments analyze --input-dir results/episodes-live-001 --output-dir results/episodes-live-001-analysis
```

C/P remains primary. R/P or a favorable hidden-label subgroup cannot replace it after results. Use new directories and preserve failures. If provider behavior or code changes, record the change and create a new protocol/run; do not overwrite the prior results.

## 6 Return results to the repository

Run the export command for a completed analysis directory, inspect the staged files using [RESULTS_RETURN.md](RESULTS_RETURN.md), and commit only the reviewed shareable subset with the source/configuration hash and limitations. Raw responses/checkpoints stay private by default. Export does not push anything. Update the repository yourself after review; do not use `git add .` over runtime output.
