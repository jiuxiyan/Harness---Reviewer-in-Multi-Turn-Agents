# Implemented scope and evidence limits

The v2 runner uses official Telecom tools and evaluation from the pinned
`tau2-bench` repository, τ³ release line (`tau2==1.0.1`, commit
`4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`). Offline execution is validated on Linux and native macOS 15.7.9, both arm64
(Apple M1 Virtual) and x86_64 (Intel i7-8700B), with Python 3.12. Mac verification
covered locked dependency installation, 42 outer tests including 27 guarded
engine cases and fresh-process restores, all four historical layers, READ/WRITE
smoke, the two-task/four-root pilot, analysis/export and interrupted/durable
response recovery. See the [exact CI evidence](validation/current_release.json).
User-owned computers, other OS versions and live providers remain untested. Preparation has
made **zero real model calls**. Historical guarded launchers remain offline;
only the new CLI's explicit `--mode live` reads local provider configuration.

## Executable scope

- All eight arms: B_bare (manuscript B_native), B, S, A, P0, P, R, C. S spends
  one actor-model reconsideration request under the configured response budget,
  executes its selected action, and shows no reviewer packet. This matches a
  budget rule, not realized token counts or monetary costs.
- Public roots after two assistant tool returns and a user text event. Roots
  are collected from an unmodified reference trajectory before interventions;
  multiple starts, multiple roots, common-prefix repeats and suffix repeats are
  configurable. No evaluator controls root selection or proposal acceptance.
- READ tools plus the bounded assistant WRITEs `enable_roaming` and
  `disable_roaming`. The roaming fixture changes official carrier state and can
  repair a task assertion. This is a test of an actual mutation, not an estimate
  of natural model repair. Other known assistant WRITEs are explicit capability
  missingness, not silently executed or counted as successes.
- P/R/C share the exact draw, selected action, receipt and first exposure through
  the next actor boundary. Suffixes use fresh objects and fresh logical requests.
  C closes only a declared action-local call after its normal return and one
  valid actor response. Ongoing declarations and errors never close. Closure is
  independent of whether a task goal improved or worsened.
- Native task `ENV_ASSERTION` evaluation with fixed task goals. Initially false
  goals acquired at the root are protected; initially true properties are
  separately recorded. **Dynamic user revocation/change of goals is unsupported.**
- Snapshots bind task/config/source, native histories, routing/counters, RNG,
  environment and consumed intervention state. Restore constructs an uninitialized
  environment and replays initialization plus history exactly once. READ,
  roaming WRITE and non-idempotent suspension initialization have process tests.
- Per-instance pristine VPN defaults for make/restore and all official evaluator
  constructors, preventing the pinned upstream class-level mutable default from
  crossing branches or tasks. The original upstream files and evaluation algorithm
  remain unchanged. bad_vpn is now an exposed regression task.
- Executable `confirmatory-roots` under a locally frozen design/task/source/model
  manifest. Exposed development tasks and near-duplicate fault families are
  excluded; selected confirmation units must share no normalized fault component.
  This is an explicit design assumption, not empirical proof of independence.
  Operator knowledge of other prior exposure is required; software cannot infer it.

## Failure and recovery policy

Received empty, refusal, truncated or malformed model messages become native
AGENT_ERROR/USER_ERROR endpoints (completion zero), with the response retained.
Mixed text/tool messages use the upstream communication-error rule. Multiple or
hallucinated tools are declared model protocol errors. Reviewer received-invalid
output consumes one draw and executes original-action/no-packet fallback; it is
never resampled. Damaged provider envelopes and unknown network results remain
infrastructure missingness. Native step/error limits remain observed failures.

`recovery-plan` and `resume` replay durable responses locally into reconstructed
benchmark state. Unknown dispatches require an explicit per-request abandon or
retry decision; retry acknowledges possible duplicate billing. They never retry
automatically. Confirmed response model identity is checked again. Physical,
per-logical retry and original wall-time budgets persist (wall time includes the
pause). Divergent requests, changed source/config/model, torn journals and
redacted payloads fail closed. In-flight requests may still be billed. No remote
cancellation, idempotency guarantee or arbitrary-provider recovery is claimed.

## Statistics and costs

The primary contrast averages suffixes within common segments, segments within
roots, roots within tasks, then tasks equally. Task-cluster bootstrap preserves
paired contrasts. Shared terminal segments count once. Available-endpoint point
estimates have explicit missingness bounds. Reference failures are reported
separately and prohibit a confirmation verdict; no-trigger reference trajectories
are a different root-conditioned coverage outcome. Equal-family sensitivity is
only a point estimate, not a shared-family cluster interval.

Every physical retry counts once globally. Each arm path includes its reference,
proposal/self-review, common-prefix and own-suffix request ancestry, including
retries. Shared ancestry is repeated only in logical path costs. Absent usage and
prices stay unknown, not zero. Monetary caps and provider-token matched headers
are unsupported. All mock effects remain null / `not_run`.

## Remaining extensions

Episode-start end-to-end utility, arbitrary assistant mutations, voice, streaming,
other domains, dynamic goal masks, semantic declaration auditing, Omega strata,
full delayed/recurrent goal diagnostics, and empirical price/provider calibration
are not implemented. No natural incidence, power, repair effect or efficacy is
established by this offline release. Original research has no specified license.
