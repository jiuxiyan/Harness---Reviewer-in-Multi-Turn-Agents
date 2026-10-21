# End-to-end actor token-truncation defect and fix (2026-10-21)

## Status
Resolved by a config-only change; first confirmatory batch abandoned as confounded and preserved as partial evidence; a validated re-run is in progress.

## Defect
The first end-to-end confirmatory batch
(`results/workbench-20261020-004/confirmatory/e2e-confirmatory-001`, config
`configs/e2e-confirmatory.json`) ran with a single global
`models.max_completion_tokens = 1024` applied to every role
(`local_experiments/provider.py` builds one payload with
`max_completion_tokens = m['max_completion_tokens']` for actor, reviewer and user).

The actor `sophnet/qwen3.6-plus` is a reasoning model. On the hard multi-fault
fixed-benchmark tasks (prompt ~9,000-9,700 input tokens) it spends the entire
1024-token completion budget on `reasoning_tokens` and emits **zero** content and
**no tool call** (`finish_reason = "length"`, `content_len = 0`,
`reasoning_tokens = 1024`). The native tau2 orchestrator treats an empty
action-less assistant turn as an agent error; after `max_native_errors` such
errors the episode terminates with `termination = "agent_error"` and
`completion = 0`.

## Why it confounds the estimand
The advice-carrying arms (P/R/C) inject the reviewer packet and advice-lifetime
header into the actor context, lengthening prompts and deliberation, while the
bare/receipt-only arm B does not. Truncation therefore correlates with arm:

First 10 outcomes of `-001` (task t0, starts s0/s1, plus t1-s0):

| arm | terminations observed            |
|-----|----------------------------------|
| B   | user_stop x3 (all completion=1)  |
| P   | agent_error x2 (all completion=0)|
| R   | agent_error x2, user_stop x1     |
| C   | agent_error x1, user_stop x1     |

Across the truncated actor responses, `qwen3.6-plus` showed
`{stop: 38, tool_calls: 49, length: 5}` and the reviewer `DeepSeek-V4-Pro-0813`
showed one `length` truncation as well. Had `-001` been run to completion and
analyzed, `J(P)`, `J(R)` and `J(C)` would have been depressed relative to `J(B)`
by a token-budget artifact rather than by advice-lifetime semantics, and
`dJ = J(C) - J(P)` would not estimate the intended contrast. Reporting that as a
confirmatory result would be an artifact-driven conclusion, which the study
integrity rules forbid.

## Decision
`-001` was stopped (SIGTERM to the runner and its `worker.py` subprocess) at 10
recorded outcomes with no `status.json`. Per the no-overwrite rule it is
**preserved as-is** as partial evidence of the defect and is never analyzed as
confirmatory. A fresh numbered output directory is used for the corrected run.

## Fix (config-only, no frozen-source edit)
Raised `models.max_completion_tokens` from 1024 to **8192** in
`configs/e2e-confirmatory.json`. `provider.py` reads this value directly, so no
`local_experiments/*.py` change was required and `source_hashes()` is unchanged.
Because `freeze.binding()` hashes `normalized(config)`, the config change alters
the binding; the freeze was therefore **re-sealed to a new receipt path**
(`configs/freeze/e2e-confirmatory-freeze-v2.json`,
`freeze_sha256 = 90b7123fd2fedce36bda1e2b5b521602730b8a00ffcc29c762bac6a134c92d94`,
8 selected tasks). The prior receipt
(`configs/freeze/e2e-confirmatory-freeze.json`) is retained for history.

## Validation before re-running
A bounded exploratory smoke (`configs/e2e-token-smoke.json`, 8192 cap) ran the
same hard benchmark task (index 0) for arms B and P through the normal runner
(`results/workbench-20261020-004/smoke/e2e-token-smoke-001`):

- 37 responses, **zero** `finish_reason = "length"`; max `completion_tokens`
  observed = **1927** (a call that would have truncated at 1024), confirming the
  actor genuinely needs ~2x the old cap and 8192 leaves ample headroom.
- B: completion=1, `user_stop`, 37 steps.
- P: completion=1, `user_stop`, 33 steps — the advice arm that previously
  agent_error'd 2/2 now terminates naturally.
- `status = completed`, `episode_failures = 0`, `evidence_kind = exploratory_live`.

The corrected confirmatory batch is `e2e-confirmatory-002`
(64 episodes = 8 tasks x 2 starts x 4 arms B/R/P/C), dry-run verified
(64 episodes, all triggered, 0 failures) before the live launch.

## Cost discipline note
No monetary cap (`monetary_cap = null`, `pricing.status = unknown`) per standing
authorization; the abandoned `-001` consumed 162 dispatched requests before the
stop and is recorded as wasted-but-necessary defect discovery. The smoke added 48
physical calls. Consumption is reported, not hidden.
