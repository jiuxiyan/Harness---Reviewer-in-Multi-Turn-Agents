# Reviewer advice lifetimes in multi-turn agents

An **experiment-preparation release**, with a CPU-local runner and mock-tested
integration of the pinned official τ²-bench Telecom environment. **Formal model
experiments run: zero.** No efficacy or causal improvement is claimed.

The primary proposed comparison is **C versus P**: the same reviewer text,
selected action, factual receipt and shared first exposure; only the later
completion-scope status header changes. R removes the entire packet after one
valid actor response. Earlier persistent feedback is called P0.

![Proposed experiment, not model results](paper/reviewer_advice_overview.png)

## Run locally

Tested on Linux with Python 3.12. Python 3.12–3.13 is the upstream-supported
range; Windows is not supported by these POSIX launchers. No GPU is needed.
Use a checkout and an existing official installation of `uv` on PATH. Setup
uses only the official PyPI lock and hash-pinned wheels; it does not run models.

```sh
python3 tools/public_manifest.py --check
python3 code_inputs/reviewer_pilot/install_locked.py
python3 code_inputs/reviewer_pilot/install_locked.py gap
python3 -m local_experiments validate --config configs/wire-smoke.json
python3 -m local_experiments run --config configs/wire-smoke.json --output-dir results/wire-smoke
python3 -m local_experiments analyze --input-dir results/wire-smoke --output-dir results/wire-smoke-analysis
python3 -m local_experiments export --input-dir results/wire-smoke-analysis --output-dir exports/wire-smoke
```

Output directories must be new. Omitting `--mode` selects `dry-run`: no key or
`.env` is read, no API client is initialized, and guarded mock responses drive
real official tools and evaluation. Fixture analyses report model outcomes as
`not_run`, not effect estimates. `validate` checks configuration, not provider
availability or scientific readiness. This is a run-from-checkout project;
packaging a self-contained wheel is not supported.

Run the tests and regenerate all legacy development fixtures:

```sh
python3 -m unittest discover -s tests -v
python3 tools/offline_checks.py
```

## User-operated live runs

The separate HTTPS Chat Completions transport is real code, tested with mocked
HTTP responses and virtual credentials. It has not been tested against a real
provider in repository preparation. Set the five shell variables named in
[.env.example](.env.example) locally using your normal secret-management method.
No `.env` file is automatically loaded; never put a key in JSON or a command
argument. Endpoint and model selection are entirely yours.

```sh
python3 -m local_experiments run --config configs/wire-smoke.json --mode live --output-dir results/live-smoke-001
python3 -m local_experiments run --config configs/natural-pilot.json --mode live --output-dir results/live-pilot-001
```

Only the explicit `--mode live` flag enables credential reading and model
requests. There is no additional assistant budget approval. Configure request,
step/error, retry, timeout and output-size limits in the JSON. There is no
mandatory total token budget. Token usage is recorded when supplied; prices
and currency costs remain unknown. Monetary caps are explicitly unsupported.
TLS verification stays enabled; redirects are rejected. See the
[local runbook](docs/LOCAL_RUNBOOK.md) before collecting live data.

## Implemented scope and limits

The new runner supports one public-triggered, single assistant READ intervention
per reference start, text half-duplex Telecom, explicit receipt provenance,
public action-local closure, common P/R/C segments, JSON checkpoints restored
into new official objects, and independent actor/user suffix requests. The
included mock path uses exposed task 0. Other exposed tasks can be selected for
exploratory live development, but all assistant mutation, multi-call, streaming
and unsupported evaluator paths fail explicitly. These are method-pipeline
checks, not natural repair evidence or comprehensive benchmark support.

| Arm | New runner capability | Limitation |
| --- | --- | --- |
| B_bare | Original native action/message representation | READ scope only; maps to manuscript B_native |
| B | Original action with factual controller receipt | Instrumentation comparison needs live calibration |
| S | Rejected explicitly | Budget-matched model self-reconsideration not implemented |
| A | Same selected action and receipt, no packet | Different first segment from packet arms |
| P0 | Unwrapped persistent packet | Cross-renderer/provider calibration against historical representation remains unmeasured |
| P | Exact packet plus neutral status sentence | Provider-token equality not assumed |
| R | Common first exposure, then packet/header removed | Separate receipt and native history retained |
| C | Same packet; public-success completion status after one valid response | Syntactic local closure, not proof of correct advice or repair |

`wire-smoke` and `natural-pilot` use the implemented root runner with different
sample sizes. `confirmatory-roots` and `end-to-end` are **rejected**, even in
dry-run. Their configurations and planning documents expose future work,
not implemented studies. See [capabilities and remaining work](docs/CAPABILITIES.md).

All seven Telecom witnesses are **exposed development material**, including the
three originally in upstream test. Confirmation needs a separately frozen,
unseen task/family sample. The final manuscript governs the proposed scientific
study; supported software scope does not redefine that study.

## Research and reproducibility

- [Final pre-experiment manuscript (DOCX)](paper/reviewer_advice_lifetimes_preexperiment.docx), [text](paper/manuscript.txt), [SVG](paper/reviewer_advice_overview.svg)
- [Current scientific protocol](docs/protocol/current_protocol.md) and [experiment plan](docs/planning/EXPERIMENT_PLAN.md)
- [Literature audit](docs/research/related_work_audit.md), [prior art](docs/research/correction_prior_art.md), [research history and decisions](docs/history/RESEARCH_HISTORY.md)
- [Actual validation receipt](docs/validation/current_release.json), [integration migration](docs/reproducibility/public_integration.md)
- [Licensing and data acquisition](docs/reproducibility/licenses.md), [results return/privacy](docs/planning/RESULTS_RETURN.md)

The exact 281-file official source/data allowlist is vendored under
`code_inputs/reviewer_pilot/upstream/`, pinned to
`4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`. Its MIT notices are preserved.
Original research, figures and code have **no specified license grant**; do not
apply the upstream MIT license to original work. Dependencies retain their own
licenses. Excluded historical external datasets require separate license review.

Raw local responses, checkpoints, installation logs and runtime results remain
ignored and private. Export rebuilds a small typed aggregate allowlist locally;
it never uploads, pushes, or publishes. No raw user conversations or private
runtime snapshots are included in this release.
