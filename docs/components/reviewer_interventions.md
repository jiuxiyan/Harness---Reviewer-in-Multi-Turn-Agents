> Historical component documentation. See the current integration notes before running. Referenced runtime results and old internal reports are not transferred; bounded aggregate validation is in docs/validation.

# Reviewer intervention wire dry-run

**Offline internal-event implementation; model/provider continuation remains blocked.**

This small layer consumes the frozen sibling `reviewer_pilot` backend without editing it. It is a wire-correctness fixture, not an effectiveness experiment, sampler, natural trajectory collector, or live API runner. Every record is marked `mode: scripted_fixture`; actual API calls are zero.

## What it does

- Restores checkpoint 0 exactly before every actual READ, including original pending proposal, raw history metadata, official actor/user prompt projections, routing, budgets and RNG.
- Preserves immutable original proposal and reviewer Q separately. A changed execution has its own deterministic tool-call ID, and its actual result never resolves the suppressed original call.
- Uses unchanged official Telecom tools on fresh isolated restored environments. The demo alternative is `get_details_by_id(id="L1002")`.
- Preserves the full future actor tool catalog. The intervention slot has an explicit public restriction to one assistant READ from the six previously checked diagnostic tool names.
- Serializes truthful shared receipts in a separate internal event format. It never fabricates an assistant message claiming the original actor proposed the replacement.
- Creates explicit actor, reviewer and user input views by allowlist. The user simulator retains its original legitimate instructions and source projection. Private checkpoint/oracle fields and source IDs are not added to those views.

## Four arms

- B: execute the original pending customer lookup.
- S: prepare one fixed self-reconsideration packet and one scripted draft. The demo draft is malformed, so it honestly falls back to the original action. Only parse/public-schema failures trigger this fallback. A valid-format official tool rejection remains an error outcome.
- A: execute the fixed valid reviewer action and return a minimal neutral factual receipt.
- P: execute exactly the same action as A, with the same factual receipt, plus a fixed critique/actor-revision packet.

When a1=a0 and A has no extra packet, B/A internal actor input bytes and resulting environment state match. P with an unchanged action and nonempty critique remains a distinct intervention. A/P changed-action inputs differ only in the declared additional packet.

The actor/user response fields are explicit ungenerated fixture placeholders. This code does not generate any stochastic model continuation. Any future experiment must generate fresh actor and user continuations separately for each branch.

## Proposal gating and private analysis

One raw Q is recorded before shadow execution or branch outcomes. Public syntax/schema checks classify unchanged, invalid or valid_changed; non-assistant/unknown tool names, mutation tools and multi-call requests are outside the public intervention scope. All classifications are counted before conditioning. Excluded proposals are not redrawn.

A private copy-based shadow check can record goal preservation as an analysis-only V+ stratum. It is never an eligibility gate, fallback signal, or actor/reviewer/user-simulator feedback. Its actual tool error is retained as a public behavior outcome. The shadow restores fresh state and cannot mutate the root or another arm.

## Budget semantics

The ledger uses invented, explicitly labelled TEST_UNITS and fixture logical slots. These are neither provider token counts nor prices, monetary charges or savings.

The complete fixture block costs 30 units plus one reserved retry unit. Root/proposal/reviewer preparation costs six units even when Q is excluded. Self preparation adds three units when reached. These prepaid costs form part of the whole 31-unit block; its remaining reserve is acquired atomically before any shadow or arm dispatch. Insufficient funds start no arms. One global retry slot is reserved; no retries are silently performed. The demo leaves that unit unused.

Root, proposal, reviewer, self, shadow, actor, user, tool execution and retries have separate usage categories. Actor/user charges represent logical fixture slots, not executed generations. An injected backend failure marks an incomplete infrastructure block, records attempted fixture costs, and aborts without retry. A partial block is never labelled a valid completed block.

## Verification and precise limits

Run from the existing prepared environment:

```sh
python code_inputs/reviewer_interventions/launch.py
```

The launcher uses the already-installed sibling `.venv`, a new private runtime directory inside this layer, a whitelist-only environment, `-I -B`, and the existing `no_api_guard` before upstream imports. No packages are installed. The unittest suite is stdlib-based. The launcher verifies the recorded commit and all 281 official source/fixture hashes, and compares non-runtime dependency file inventories/hashes before and after execution, including added/deleted files.

Final test details and results are in `results/tests.json` and `results/suite_stderr.txt`. The final passing demo is `results/dryrun.json`. The guard’s negative model/network/dotenv probes are expected blocked attempts; unexpected attempts remain empty. These are process-local application guards, not a claim of a kernel network sandbox.

Evidence boundaries:

1. The sibling backend previously established seven original live **scripted** witnesses and fourteen fresh-process restorations, with full orchestration only for the original pending customer lookup. “Live” there means the original running Python object, not model inference.
2. Its six READ tools with concrete arguments have 42 checkpoint/tool pairs and 84 environment transitions. This layer rechecks one checkpoint and uses one of those concrete alternative calls.
3. This layer proves internal serialization, provenance, privacy gates, TEST_UNIT accounting and isolated READ transitions. Changed-action full orchestration and provider-facing formatting are not validated here.
4. The official converter has no implemented lossless reviewer-override adapter in this layer. A separate, explicitly validated standard-role/controller-receipt adapter may be possible. This code’s `provider_request` always raises `ProviderConfigError`; live mode raises `MissingApproval` before preparation or callbacks. A local config file cannot authorize execution.
5. Raw tool-result metadata is retained in audit receipts. Actor-visible result projection uses the unchanged official converter, which omits timestamps/turn indexes. The exact root is compared without metadata removal. Fresh response timestamps are not falsified to make arm inputs equal.
6. Terminal results and causal HARM are unmeasured (`null`), not zero. Equal scripted states do not imply a reviewer lacks an effect.

## Files

- `SPEC.md`, `plan_freeze.json`: specification/hash frozen before implementation and test outcomes
- `DEVIATIONS.md`: review findings and corrections, without retroactively changing the frozen plan
- `interventions.py`: immutable records, public gate, internal renderer, safety stubs and ledger
- `offline_backend.py`: exact frozen-checkpoint restore and isolated official READ execution
- `launch.py`, `worker.py`: sanitized guarded entrypoint and final fixture demonstration
- `test_interventions.py`: wire/privacy/provenance/budget/guard regression checks
- `results/`: final test summary, demo, source-pin and dependency-immutability evidence
- `BUNDLE_MANIFEST.json`: packaged files and hashes

The bundle contains only this layer's source, documentation and results. It excludes the backend, dependencies, virtual environment, runtime homes/caches, private whole checkpoints and proxy data. Reproduction requires the separately prepared frozen sibling backend. Nothing in the bundle starts paid work, reads API keys or enables model calls.
