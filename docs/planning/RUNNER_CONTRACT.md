> Integration status: the CLI and bounded official Telecom mock path are implemented and exercised. The current executable commands and exact remaining limitations are in [the tested runbook](../LOCAL_RUNBOOK.md) and [capability report](../CAPABILITIES.md). This document retains the full planned-study requirements; it is not a claim that every requirement is implemented.

# Expected local runner interface

Status: validate/run/analyze/export are implemented for the bounded scope described in the capability report. This contract prepares local CPU orchestration and remote model inference. It does not authorize or execute an API call during repository preparation.

## 1 Public CLI

From the repository root:

```sh
python -m local_experiments validate --config configs/wire-smoke.json
python -m local_experiments run --config configs/wire-smoke.json --mode dry-run --output-dir results/wire-smoke
python -m local_experiments analyze --input-dir results/wire-smoke --output-dir results/wire-smoke-analysis
python -m local_experiments export --input-dir results/wire-smoke-analysis --output-dir exports/wire-smoke
```

`run` defaults to `--mode dry-run` when omitted. Live requests require the command-line flag `--mode live`; an environment variable or configuration file cannot silently enable live mode. A dry-run must not initialize an API client, load credentials, discover `.env` files, contact a provider, or fetch a cost map. Validate and analyze/export also require no credentials or network.

The stage comes from the JSON configuration, with these names:

- `wire-smoke`: actual request mapping, role/packet audits, tiny response/usage checks.
- `natural-pilot`: fresh multi-turn actor/reviewer/user execution and coverage accounting.
- `confirmatory-roots`: frozen all-draw checkpoint comparison.
- `end-to-end`: episode-start P/C task utility.

A stage requiring missing implementation must exit with an explicit unsupported-capability error. It must not write success, real model outcomes, or mock data under a live label. The requested initial implementation must include a real local API transport plus at least one complete small multi-turn path validated through deterministic mock provider responses. Scientific generality and mutation-readiness may remain narrowly scoped and explicitly gated.

The release records its actual tested command lines, exit codes, code hash, and capabilities. Update only the implementation-status statement after verification; do not reinterpret the planned studies as completed.

## 2 Configuration contract

Use JSON, stable schema versioning, rejection of unknown fields, and checked path resolution. Required sections:

- `schema_version`, `protocol_id`, `stage`, `evidence_kind` and `study_label`.
- `source`: repository revision, pinned benchmark commit, task/data hashes.
- `dataset`: manifest path, permitted population, split/family grouping, selected IDs or deterministic selector; no hidden metadata may flow from it into model payloads.
- `models`: actor, reviewer and user identifiers; API protocol/transport; sampling parameters; provider seed support; per-response bounds if configured. The local endpoint and credential are read from explicit local environment variable names only in live mode.
- `arms`: allowed ordered arm IDs and frozen projection/prompt version identifiers.
- `review`: one slot; one raw draw per root; public trigger; declaration contract; predetermined fallback; public close rule.
- `sampling`: task-start repeats, root cap, common-prefix repeats, suffix repeats, independent control continuations, task/family allocation and seed namespaces.
- `limits`: maximum physical requests, native steps/errors, concurrency, retry count/backoff, optional wall-clock stop, optional monetary ceiling and currency. There is no mandatory total token limit. Defaults must be explicit, configurable and appropriate to a smoke test.
- `pricing`: optional per-model price snapshot and date; `unknown` is permitted and must remain unknown in reports. Unsupported cached/reasoning pricing cannot be silently treated as free.
- `analysis`: endpoints, primary C/P contrast, task-macro weighting, interval level/resampling seed, delta/epsilon, missingness sensitivity, secondary adjustment, and planned sample size where confirmatory.
- `gates`: verified capability receipts and research-evidence receipts. These have separate meanings.
- `output`: private raw directory, shareable export directory, retention/redaction policy, and overwrite policy.

For any published sample configuration, include an explicit `planning_template` status if its schema has not yet been matched to code. Validate must report all missing required stage fields, not silently infer a model, install dependency, choose a gateway, or obtain credentials. A required confirmatory sample/margin field of null is an honest blocker. Unknown pricing alone is not a live-execution blocker unless the selected monetary cap depends on knowing it.

## 3 Local API behavior

A generic API implementation may initially support one explicitly named wire protocol, such as an OpenAI-compatible chat-completions transport, while remaining provider-neutral about endpoint and model IDs. Compatibility must be documented and tested; do not claim every API or reasoning model works. Unsupported native roles, tool formats, streaming, or authentication mechanisms fail clearly.

Load the API base URL and key from the researcher's shell or an explicitly chosen ignored `.env` file. Never require credentials in JSON, on a command line, in Git, or in a report. Do not attempt browser login, remote account setup, token generation, credential testing, or cloud configuration. The local user supplies whatever their own provider needs.

Capture outgoing payloads after adapter/SDK transformation but before transport, excluding all authorization headers. Persist each incoming response and parsed output privately. Keep immutable raw request/response identities, packet bytes, selected action, and native tool return distinct. Reject mismatched call IDs and duplicate or missing tool-result bindings. Do not claim server-side behavior was observed when only the outgoing wire body is visible.

Save completed responses durably before continuation. Retry only declared retryable failures within the configured cap. Record every attempt and uncertainty. A malformed model-generated reviewer packet remains one observation and uses the fallback; it is not a transport retry. Unknown response validity/charge after network loss requires an explicit unresolved status. Use a stable local request identity but do not claim it is provider idempotency unless the protocol actually guarantees that.

## 4 Runtime modules and trust boundaries

The implementation may choose its structure, but must expose these responsibilities:

1. Config and capability validator with dry-run/live separation.
2. Versioned provider transport and usage/retry journal.
3. Official environment adapter with native actor/user routing and budget accounting.
4. Public-view builder with evaluator metadata structurally excluded.
5. Raw proposal/reviewer capture, schema/scope gate and fixed fallback.
6. Receipt renderer plus B_bare/B/S/A/P0/P/R/C projection state machine.
7. Checkpoint serializer/restorer including participants, histories, queues, routing, tools, auxiliary state, native counters, clocks when supported, RNG, usage, and packet exposure state.
8. Reference trajectory/root collector, common-segment sampler and independent branch scheduler.
9. Isolated offline evaluator and official finalization, preserving every required reward component.
10. Analysis/export paths that distinguish fixtures, exploratory data and confirmatory data.

The public gate/renderer must not accept an evaluator callback, goal vector, terminal reward, or future branch text. A private evaluator process or rigorously isolated object boundary can implement shadow labels; its use must not mutate the live world. Class names alone are not proof of isolation: tests must alter private canaries and verify unchanged public requests.

## 5 Required event schema

Use append-only JSONL for journal records, with a schema per event and content hashes. At minimum retain:

- `run_id`, `protocol_hash`, `event_id`, parent event IDs, timestamp, `evidence_kind`.
- Private evaluator-side task/family IDs and hashes; `trajectory_id`, `root_id`, `draw_id`, `common_prefix_repeat_id`, `suffix_repeat_id`, `arm_id` as applicable.
- `physical_call_id`, logical request ID, retry attempt number, provider-returned request ID where available, actor/reviewer/user role, model/config digest and payload digest.
- a0 raw proposal; q raw output and declaration; validation/scope classification; unchanged/changed state; selected action identity; actual result/error; source provenance.
- Packet and receipt digests, neutral/consumed header state, exposure attempts and valid-response count, public closure evidence, first and later request audits.
- Checkpoint and restore digests, source/config versions, RNG identifiers, remaining native budgets, routing/participant state versions.
- Termination/disposition reason, evaluation availability, official full success, acquired-goal membership and offline labels in evaluator-only records.
- Input/output/cached/reasoning token counts when reported, latency, known/unknown price, currency, physical cost, logical cost attribution and any TEST_UNITS label for historical fixtures.

Never put secrets or authorization headers in any event. Raw actor/user text, simulator instructions and full snapshots remain in ignored private output by default. Use references to private files rather than embedding everything in shareable records. Public aggregate exports use a narrow allowlist; a regex secret scan alone is insufficient.

## 6 Run output layout

An illustrative layout under the requested output directory:

```text
run_manifest.json
capabilities.json
status.json
source_hashes.json
config.public.json
journal/events.jsonl
journal/calls.jsonl
private/raw_requests/
private/raw_responses/
private/checkpoints/
private/evaluation/
derived/dispositions.jsonl
derived/root_outcomes.jsonl
derived/coverage.json
```

An analysis directory contains `analysis_manifest.json`, per-task/family summaries, contrasts, intervals, missingness bounds, costs, request-format audits, and a concise report. Empty real-data tables are valid before experiments. Any demonstrative rows require `evidence_kind=scripted_fixture` and may not be pooled with live rows.

`export` copies only allowlisted analysis artifacts into a new staging directory, with a disclosure manifest and hashes. It does not upload, push, or publish. It must refuse to overwrite a distinct run or silently mix protocol hashes. New runs get new IDs/directories. A rerun must not replace frozen prior evidence.

## 7 Acceptance tests

Tests must run offline with scripted/mock responses unless the researcher explicitly chooses local live mode:

- Default/omitted mode and any config-only live setting cause zero network and zero credential reads.
- Real provider client construction and JSON request/response parsing are exercised against a mock transport.
- A complete small multi-turn run includes actor, reviewer, actual benchmark tool dispatch, legitimate user simulation, next actor boundary, branch termination and official evaluation. A single chat completion does not satisfy this requirement.
- All eight arms are either supported and tested or truthfully rejected; S cannot use an authored answer while labeled model self-reconsideration.
- First P/R/C requests match; second/later P/C differ only in permitted header bytes; R removes only the packet/header; P0 has no new wrapper; B_bare preserves native format.
- Valid/error/malformed/out-of-scope/unchanged/semantic-violation draws all remain logged and follow frozen behavior.
- Public-success closure requires matching action/result and one valid response; tool errors and unresolved conditions leave C equal to P.
- Failed render/transport/invalid response do not consume R; restart cannot repeat exposure; raw q cannot redraw after failure.
- Full common-segment user/tool state restores in a fresh process; post-fork actor/user futures do not cross branches; early terminal shared segments are retained.
- Native max-step/error outcomes are scored, while missing infrastructure endpoints remain missing; unsupported mutations fail visibly.
- No raw private evaluator metadata can enter actor/reviewer/user projections. Public disclosed requirements remain intact.
- Every physical attempt is counted once; logical costs include proper shared preparation and exclude reviewer calls from B/S where appropriate.
- Unknown pricing stays unknown; optional monetary caps fail clearly when unenforceable; request/step caps terminate with full partial-run logs.
- Analysis accepts a hand-calculated fixture with nested dependencies and missing endpoints, produces correct task macro averages, and refuses mixed fixture/live pooling or mixed protocol IDs.
- Export excludes private text/state, keys, endpoint/account details, absolute home paths, and raw provider headers. Git ignore checks cover local credentials and runtime outputs.

## 8 Implementation versus scientific eligibility

Implemented local execution can be enabled without claiming a confirmatory study is scientifically ready. A natural development run may proceed on the validated narrow scope with explicit limitations. Only a run labeled confirmatory requires the complete design freeze, valid held-out sample, mutation/repair evidence appropriate to its claim, provider mapping receipt, and analysis settings.

Conversely, filling a configuration or setting a gate to true cannot create missing functionality. Capability receipts must identify tested code and supported scope. Do not remove frozen guards from historical packages: implement the new explicitly live-capable entry point separately.
