> Historical component documentation. See the current integration notes before running. Referenced runtime results and old internal reports are not transferred; bounded aggregate validation is in docs/validation.

# ControllerReceiptRendererV1

**OFFLINE SCRIPTED FIXTURES ONLY. No real actor, reviewer or self-revision was
sampled. No provider wire compatibility, effectiveness or causal effect is claimed.**

This separate adapter consumes the frozen `reviewer_pilot` and
`reviewer_interventions` directories read-only. It does not alter either package.
The official source pin is `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`.

## What is implemented

Four artifacts remain distinct:

1. `ObservedModelOutput`: immutable canonical full captured text message, original
   ID/timestamps/usage/cost/raw metadata and digest. In this build its mode is always
   `scripted_fixture`, actual model calls are zero, and raw provider response is
   `None` because none exists. Reviewer recommendations have their own immutable
   fixture records, including the available critique/revision packet.
2. `InterventionDecision`: explicit controller choice, immutable source recommendation,
   classification, target proposal digest and emitted packet digest. A and P can
   share the same recommendation while only P emits its unchanged recorded packet.
3. Derived official execution history: the original pending slot is copied into a
   controller-authored selected call, followed by its actual official tool response.
   The native assistant/requestor role is toolkit routing. `raw_data` labels the
   call as `derived_intervention_execution`; it is never relabeled as observed
   actor generation. Synthetic calls carry no generation usage or cost.
4. `ActorRequestProjection`: the exact local generic-converter request, full original
   tool schemas, and model/config arguments. Each derived call/result pair is
   replaced by one native supported `SystemMessage` containing a fixed controller
   receipt. The original proposal, disposition, executed action/ID and exact public
   result/error are visible. No unresolved canceled call, selected synthetic native
   call, fake cancellation result, audit source, arm label or private evaluator is
   placed in that projected span.

`ReceiptAwareOfflineAgent` extends the official LLMAgent protocol and renders before
**every** scripted actor continuation. `ReceiptAwareState` requires the serialized
registry. Missing, modified, duplicated or ambiguous spans fail closed. A separate
pending-proposal renderer represents a0 as labeled data for reviewer/self requests.
Those requests can be logged, but no real reviewer or self generator is implemented.

## Scope and controls

- One original intervention slot only; checkpoint 0 is the sole validated input. Exactly one text-only assistant
  READ from the previously declared six-name public scope. Unknown/mutating tools,
  invalid arguments, multiple intervention slots, audio/voice/streaming, and unknown
  message shapes are rejected.
- Positive fixtures use `get_customer_by_phone(phone_number="555-123-2002")` and
  `get_details_by_id(id="L1002")`. These are public-fake benchmark data.
- Selective execution calls official `step()` exactly once. Native routing, step and
  error counts, queues, user state, full actor tool catalog, model configuration,
  environment state and RNG are checked. Tool errors remain actual outcomes.
- B/no-op A equality means exact canonical effective request bytes, including tools
  and config. It is checked at two actor boundaries. It does not imply equal hidden
  provider state or equal future random generations.
- A/P equality after removing the actual emitted packet is checked at both actor
  boundaries. Executed action/history, public result, receipt, tools and config are
  held fixed. This identifies only a possible conditional message-package comparison
  under this instrumented representation, not natural mediation or model-brain state.
- Bare B is explicitly a different native-message request from instrumented B.
  Both retain the same full tool catalog/config. A future experiment needs this
  separately specified instrumentation control; no-op equality does not remove it.
- Receipts exist only in actor projections. The official trajectory, user simulator
  state/projection and routed tool message never receive these SystemMessages.

## Replay, persistence and timing

`checkpoint()` returns immutable canonical JSON containing the base checkpoint,
complete official branch state, mandatory registry, usage ledger, RNG, queues,
counters, routing and elapsed timing. `restore()` constructs a fresh official
orchestrator and replays only the derived completed history exactly once using
strict `Environment.set_state`. No live action is rerun to manufacture a READ result.
The captured READ result is independently bound to its immutable record because
upstream replay deliberately skips READ outputs.

Timestamp policy: preserve the observed proposal timestamp for the derived slot and
preserve the actual response timestamp. Reject a backwards response or any sorted
trajectory that changes event order. Equal timestamps rely on Python's stable sort
and are tested. Observed raw times are never rewritten to conceal ordering problems.

Timeout-bearing checkpoints are rejected. For the supported `timeout=None` fixture,
restart preserves elapsed perf time and adds wall-clock downtime; a backwards wall
clock fails closed. This elapsed duration begins when the frozen fixture is restored,
not at a historical real model episode. Future studies must predeclare wall-time and
all reviewer/self/controller work. No native steps or errors are refunded.

## Privacy and accounting

Actor payload construction is allowlisted. Private root/evaluator fields and raw
model metadata are never serialized through the receipt. Packet structural checks
and caller-supplied canaries supplement that boundary. Public tool content is copied
exactly; unknown secrets embedded in otherwise allowed public text cannot be detected
by a finite canary set. The user input and legitimate public goal words are preserved.

`RawUsageLedger` is authoritative for the adapter's **fixture** output/request records.
The shared original a0 capture is keyed independently of branch, so pooling B/A/P
records deduplicates it. The same frozen reviewer output has the same identity in
A and P; different branch continuations have distinct logical identities. Conflicting
identity reuse is rejected. Do not sum separate branch ledgers as a deduplicated total.
An integration test keeps the frozen four-arm TEST_UNITS reservation/charge policy
unchanged by pure rendering. TEST_UNITS are logical fixture accounting, not token
estimates, dollars, real generations or real charges. Actual future costs must come
from deduplicated raw provider calls, including every repeated receipt-context token;
the official derived-history `get_cost` is not a complete study cost ledger.

## Running and evidence

From this directory, run `python launch.py`. It uses the already installed sibling
private venv and a sanitized environment, installs existing no-network/no-model
process guards before upstream imports, suppresses bytecode, verifies the pinned
source and both frozen dependency bundle manifests, and checks frozen files before/after.
Do not invoke upstream or `worker.py` directly; do not install anything.

- `results/run_status.json`: authoritative latest aggregate run status
- `results/tests.json`: named stdlib unittest suite summary
- `results/process_restart.json`: fresh-process disk checkpoint verification
- `results/stderr.txt`: complete named test output
- `results/demonstration.json`: clearly labeled B/no-op A/A/P fixture artifacts,
  both actor requests, observed/decision/derived artifacts and ledger records
- `results/integrity.json`: frozen-file and tested-source hashes with subprocess exit
- `REVIEW.md`: independent review and resolved findings

A failed latest launch replaces old PASS markers before starting. Adapter source
changes during a run invalidate the aggregate result. SHA-256 detects corruption or
accidental mismatch; it is not authentication against an adversary who can rewrite
both data and hashes.

## Remaining hard gate

`provider_request()` and `generate_live()` always raise before creating any client,
regardless of supplied approval/config flags. The official converter accepting native
message objects is not a provider format test. Late SystemMessage handling, SDK/LiteLLM
rewrites, provider-specific placement/merging, complete request retention, natural
continuations and generated critique/revision behavior remain unverified. Advancing
requires separate approval of a tiny format test, exact model/provider and total
budget, followed by a separately implemented and frozen provider mapping.
