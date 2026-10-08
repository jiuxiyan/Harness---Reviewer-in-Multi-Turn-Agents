# Frozen plan: offline reviewer intervention wire dry-run v0.1

Frozen before implementation/test results. This is a small fixture integration check, not an effectiveness experiment or a full sampler. Runtime mode is `scripted_fixture`; actual API calls are zero. No installs, credentials, clients, provider calls, price tables or paid resources.

## Dependency and scope

Read-only dependency: sibling `reviewer_pilot`, official tau2 1.0.1 / current τ³ commit `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`. Use exactly checkpoint 0. Verify its full raw state, pending action, original timestamps/turn indexes, effective official model projection, budgets, routing and RNG before interventions. Reuse guarded imports only; set no-bytecode to avoid changing the frozen dependency.

The public intervention study constraint allows a single assistant READ from the six names verified in `results/read_tool_summary.json`. The full actor future catalog stays intact. The positive alternative fixture is get_details_by_id(id="L1002"). Six concrete argument sets have environment-transition coverage; only original customer-by-phone has prior full-orchestrator continuation coverage. Unknown arguments do not inherit that fidelity evidence. Mutating, user-side or multi-call proposals are out of scope, logged once, excluded before outcomes, and never resampled.

## Immutable records and privacy

Typed frozen Root, Proposal, Arm, InputViews, Receipt and Usage records; nested data stored as immutable canonical JSON strings. Hash sorted, compact, UTF-8 JSON, reject nonfinite values and duplicate JSON keys. The original raw actor proposal stays separate from reviewer Q and execution events. Root is private, never a model payload. Actor/reviewer views use explicit official actor projection plus full tool catalog and public study constraint. The user view retains legitimate original simulator instructions/state; no extra evaluation predicates, source IDs, or hidden checks. Unique canary and structural forbidden-field tests must pass, including tests that ordinary public goal words are allowed.

## Arms and honest rendering

B executes original a0. S uses one fixed self-reconsider packet and one fixture response; only parse/public-schema invalidity falls back to a0, with an honest neutral receipt and logical preparation charges. Valid-schema official-tool rejection remains an outcome. A executes one frozen Q action a1 and a minimal factual receipt. P executes the same a1, adding a frozen critique/revision packet. A and B have byte-identical internal actor input when a1=a0 and no extra packet. Unchanged action with P critique is not a noop.

Shared receipts preserve original and executed call IDs, actual action/result/error, and explicit override provenance. No replacement is relabelled as the actor's original proposal; no a1 result is fed under a0's ID. Raw result metadata remains in audit evidence; public tool-response projection uses the unchanged official converter. Provider continuation stays fail-closed because official message roles lack an explicit reviewer-origin override event. Static internal serialization is not provider-format verification.

## Proposal and outcome order

One raw Q draw is recorded before any shadow execution or arm dispatch. Classify unchanged / invalid / valid_changed with public parse/schema checks, plus explicit out_of_scope. Count every draw before conditioning. Public tool errors are recorded without oracle feedback or fallback. Shadow checks restore a fresh isolated environment and cannot mutate root or other arms. Optional private goal preservation is an analysis-only V+ stratum, never a model input or eligibility oracle. No natural model continuation exists in this dry-run; terminal results stay unmeasured and no causal HARM label is assigned.

## Budget and live safety

TEST_UNITS and fixture logical usage only. Record root preparation, proposal/reviewer, self, shadow, per-arm actor/user/tool preparation and retry categories separately. Reserve a complete four-arm block atomically before any arm starts; insufficient funds start zero arms. Retry cap is one for the entire block and explicitly reserved/charged. Live mode raises MissingApproval before any client; provider adapter raises ProviderConfigError regardless of a local config file. No configuration file supplies user authorization.

## Verification plan

Use stdlib unittest under the existing private venv, guarded before upstream imports. Verify: exact checkpoint restore; baseline output against frozen original-live evidence; original/proposal immutability; canonical hash/RNG ID reproducibility; full tool catalog retention; no-op B/A input and state equality; A/P only declared package differences; unchanged P remains non-noop; actual override IDs/history; privacy canaries/structural exclusions; S parse/schema fallback and domain-error preservation; Q invalid/out-of-scope one-draw exclusion; fresh isolated shadows; atomic budget reserve, fees and retry cap; network/model/dotenv negative probes; live/provider failure before client creation; explicit fixture flags and no terminal/causal result. Freeze dependency evidence hash before and after. Package only this layer's own source, results and README after checks, excluding venv/cache/dependencies/private roots/proxy data.
