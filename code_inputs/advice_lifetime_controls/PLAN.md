# Bounded operational protocol, declared before execution

This new offline stage implements matched neutral-header P, same-exact-packet
status C, and whole-packet one-valid-response R over the frozen V1 adapter.
The frozen adapter's old persistent packet arm is named P0 here and is unchanged.
All fixtures are authored scripts. No model/API calls or effectiveness estimates are reported.

## Frozen public rule

Before the selected action executes, capture a single immutable raw draw and its
public declaration: target_action_id, scope, instruction, close_condition.
Supported closure is scope=action_local, instruction=execute_target_call, and
close_condition=normal_tool_return. The target ID must be the deterministic ID of
the actual selected action. Only the captured actual public ToolMessage with
error=false fulfils this call requirement. It does not establish task/goal repair.
C remains exactly P when the scope is mixed, ongoing, unresolved, the target is
unresolved, the condition is unknown, the call fails, or no valid actor response
has yet returned. No hidden evaluator, semantic classifier, or future trajectory
is consulted. Prose-level scope violations are separately logged blind to outcome;
they never cause exclusion, resampling, or hindsight changes to the declared rule.
A dishonest action-local declaration can therefore close: this limitation is
explicit rather than covered by an imagined perfect classifier.

The body is the unchanged canonical UTF-8 packet captured by the frozen adapter.
P and C use the same role, position, fields, public receipt and raw packet bytes.
Only the fixed-width ASCII status sentence differs. This is character/byte length
matching, not a claim of provider-token equivalence. A separate neutral-rewording
render probe checks wrapper perturbation bookkeeping, not an extra outcome arm.
R removes both the packet and its dedicated header after one valid actor response;
it leaves the independent factual receipt, native history and user constraints.
Repeated render attempts and failed generation attempts do not consume exposure.

Malformed/action-out-of-scope draws are retained once and use the original-action,
no-packet fallback in every arm. Valid format tool failures remain tool failures.
Declared scope negative controls remain in the draw ledger and retain their packet.
No invalid draw is resampled. Original task/persistent user constraints never expire.
This is not a semantic mixed-scope extension or new benchmark.

## Shared prefix and restoration

P/R/C share exactly the first exposed request and valid actor response, plus all
subsequent native tool/user events up to the next actor boundary. Fresh restores
fork only there. Common-prefix repetition and suffix repetition IDs are distinct;
provider seed determinism is never assumed. Terminal common prefixes remain in the
ledger with no fork. Each fork has its own actor/user queues and fresh restoration.
Two and three actual scripted actor boundaries are tested, including a user event.
Physical fixture costs are pooled by capture identity; common/reviewer records are
counted once physically and once within each deployment branch logically.
TEST_UNITS are not actual tokens, prices, savings, or model calls.

## Verification and stopping condition

Use the existing guarded private venv launcher pattern, guard before imports,
-I -B, sanitized environment, and read-only frozen dependencies. Check complete
source/manifests before and after. Add failure/ongoing/semantic-violation controls,
byte-level contrasts, retry/state roundtrips, fresh-process second/third-boundary
restores and cost de-duplication. Obtain independent read-only code/test review,
resolve material findings, run a stable final suite, and report readiness limits.
Stop at this operational fixture deliverable; provider wire and natural behavior
remain separately authorized future work.
