# Implemented scope and evidence limits

The new `local_experiments` runner is distinct from the four historical guarded
packages. Their live entrypoints remain blocked. Only the new explicit local
transport can call a provider when the user chooses `--mode live`.

## Implemented and exercised offline

- Strict versioned configuration, all missing-field reporting, unknown-field
  rejection, default dry-run, fresh private run directories, bounded append-only
  request journals and response persistence before parsing.
- HTTPS, bearer-authenticated, nonstreaming Chat Completions with system/user/
  assistant/tool roles, one tool call per generated message, temperature and
  optional provider seeds, bounded requests/retries/time/output. Redirects are
  denied rather than forwarded. HTTP 429/500/502/503/504 may retry; an uncertain
  connection result does not retry. Malformed response content is not redrawn.
- Official Telecom tools, native participant ownership, environment replay,
  native counters, full required ENV_ASSERTION reward basis through official
  `EvaluationType.ALL`, and native max-step failure scoring. No LLM judge runs.
- Single public trigger: at least two completed assistant tool returns, at least
  one user text event, and a pending single READ. No hidden success predicate
  controls eligibility. All raw reviewer draws remain private evidence; invalid
  format/out-of-scope draws fall back to original action without a packet.
- Public completion binds a predeclared deterministic ID of the root's selected
  call to the actual normal return plus one valid actor response. Failed calls,
  unresolved declarations and failed generations do not consume closure.
- P/R/C first response and intervening tool/user events sampled once per common
  segment, then restored into independent official objects. Suffix actors/users
  issue fresh requests. A/P0/B/B_bare get independent first segments. Early
  shared terminal outcomes count once per common segment, not cloned suffixes.
- JSON checkpoints preserve histories, participant states, environment replay
  assertions, native routing/counters, exposure, RNG and elapsed start metadata.
  A fresh-process save/restore check exercises continuation and evaluation.
- Initial-false acquired protected goals and separately stored initially-true
  membership. Task-macro aggregation averages suffixes within common segment,
  common segments within root, roots within task, then tasks equally. Cluster
  bootstrap resamples task contrasts. Missing endpoint worst/best bounds are
  separate from exploratory available-endpoint point estimates.
- Local aggregate export has a typed allowlist; no raw files/text/identities
  are copied. Known client credentials and authorization fields are redacted
  if echoed into a response. Full response evidence is therefore redacted when
  necessary, not claimed byte-identical to secret-bearing input.

## Explicitly not delivered as implemented capabilities

- S fixed-budget self-reconsideration; confirmatory-root execution; episode-start
  end-to-end policy utility; unseen/frozen confirmation data or sample allocation.
- Arbitrary assistant WRITE tools, multiple tool calls, voice, streaming,
  timeout-aware native checkpoints, other domains, persistent automatic resume
  of a partially dispatched provider request, or idempotency guarantees.
- Real-provider acceptance, price snapshots/currency ceilings, physical-to-logical
  cost allocation, provider token-matched headers, or historical P0 byte parity
  across different renderer versions. Current usage counts can be unknown.
- Automated semantic truth checks of reviewer declarations, Omega shadow
  stratification, complete delayed/recurrent/per-goal diagnostics, a separately
  analyzed initially-true maintained-state stratum, and full negative-control
  battery. These remain preconditions for the corresponding scientific claims.
- Independently replicated natural incidence, meaningful repair effects,
  statistical power, or broad task/family generality. No live model run was made.

The default smoke fixture is authored and can reach official success. That
checks routing and evaluation, not the natural probability of success.
`natural-pilot --mode dry-run` remains `scripted_fixture`; changing stage labels
never turns fixture data into model evidence. All seven input tasks are exposed.

## Failures and interpretation

Completed runs may contain explicit missing endpoints. Analyses refuse runs
without a settled journal/status because omitted assignments would invalidate
bounds. Native max-step/error terminations remain observed endpoints; transport,
restore, output-budget and implementation errors do not become successes.
A stopped run's private files remain available for diagnosis, but the CLI does
not automatically replay unknown-billed requests. Start a new run after a fix.

A whole-run wall limit is checked before each model dispatch; a single in-flight
request can additionally consume its per-request timeout. Output limits apply
to evidence writes, not total process RAM or tool execution time. These are
operational controls, not a kernel sandbox or hard currency cap.
