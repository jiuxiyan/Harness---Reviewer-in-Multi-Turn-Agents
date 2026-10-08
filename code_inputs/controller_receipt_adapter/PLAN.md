# ControllerReceiptRendererV1 implementation scope

Frozen scope before implementation: offline scripted fixtures only. No model calls,
provider setup, network, install, credentials, external publication or causal claims.
Existing reviewer_pilot and reviewer_interventions are read-only dependencies.

Implement four separate artifacts: immutable observed fixture/model-output record;
controller decision; derived executed-only official replay history; exact actor-only
request projection using supported SystemMessage receipts at every actor boundary.
Attach controller provenance to derived native calls for offline replay, without
claiming those calls are observed actor outputs. No fake cancellation result.

Use the full original catalog/configuration and native budgets, routing, queues,
actual tool response and error counters. Restrict the intervention slot to one
public-schema-valid assistant READ. Persist the renderer registry with checkpoints;
reject missing spans, missing registry, modified results and ambiguous identifiers.
All actor continuations in this implementation are scripted. Provider runtime fails
closed unconditionally pending separately approved provider/model/format/budget work.

Verify B/no-op A exact effective bytes and tools/config, A/P packet-only difference,
a distinct bare-vs-instrumented B control, two actor boundaries, restart persistence,
strict official replay, native termination, privacy canaries, immutable provenance,
deduplicated fixture usage accounting and unchanged frozen files. Request independent
read-only review and fix verified defects before packaging.

Timeout-bearing checkpoints are out of scope: fail closed rather than refund elapsed
wall time. Future model studies must predeclare charging receipt context on every
continuation and whether timeout includes controller/reviewer/self-revision work.
