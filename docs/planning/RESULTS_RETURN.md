# Returning local results safely

The researcher owns local execution and the subsequent repository update. The runner's export step prepares files; it does not upload, commit, push, open issues, or contact any external service.

## Keep private by default

Never commit `.env`, API keys, cookies, authentication headers, connection strings with credentials, raw provider headers, full local environment dumps, raw prompts/responses, hidden simulator instructions, full database snapshots, checkpoints, local home paths, or provider account/billing identifiers. Public benchmark data being synthetic does not make every surrounding log safe.

Keep original raw evidence locally in an ignored, access-restricted directory with hashes. Redact a copy rather than destroying the evidence needed to audit the run. Ordinary SHA-256 hashes verify file identity but are not anonymization for easily guessable sensitive content.

## Commit after reviewing

A shareable result bundle may contain:

- Protocol/source/task/prompt hash manifest and benchmark citation/license notices.
- Sanitized non-secret configuration, model identifiers and date/version, sampling and retry settings.
- Run counts, coverage funnel, termination/error classes, deviations and missing-data counts.
- Per-task or suitably grouped family-level numeric outcomes for public synthetic tasks, after inspecting free-text fields and identifiers.
- Aggregate estimates, intervals, sensitivity bounds, and clearly labeled exploratory versus confirmatory comparisons.
- Actual usage counts and known/unknown cost fields without provider account details.
- A capability/request-audit summary rather than raw authenticated requests.
- A reproducibility note explaining planned versus achieved sample, unsupported paths, and exact commands.

Raw excerpts or complete traces require a separate content/privacy/license review and a specific reason to release them. The default exporter must not include them. Any derived data whose redistribution is unclear remains local until resolved.

## Review sequence

1. Analyze a single completed or honestly partial run; preserve its source/configuration identity.
2. Export only the analysis allowlist into a new directory.
3. Inspect every staged filename and all text fields. Scan for credential patterns, provider headers, user/machine paths, hidden states, source answers, and unexpected large files. A clean scanner result is only a check, not a guarantee.
4. Confirm there are no fixture rows in live outcome tables and no silently dropped starts/draws/failures.
5. Confirm all estimates identify the population, denominator, task/family unit, protocol, and evidence status.
6. Check `.gitignore` covers `.env*` except the generic example, private results, raw traces, checkpoints, caches, virtual environments, and runtime output.
7. Inspect `git status --short`, then stage explicit reviewed files only. Inspect `git diff --cached --stat` and `git diff --cached` before committing. Do not use `git add .` over results.
8. Commit the reviewed export and limitations note. Publish only the intended repository changes.

Never remove an unfavorable arm, malformed draw, cost, or unfinished block to make the paper table cleaner. Update an existing report through a new version or documented correction, retaining enough provenance to identify superseded results.

## Before there are real results

Use this baseline status:

```json
{
  "evidence_kind": "preexperiment_plan",
  "real_model_calls": 0,
  "real_experiment_runs": 0,
  "effectiveness_result": "not_run",
  "natural_coverage_estimate": "not_run",
  "causal_estimate": "not_run"
}
```

Historical fixture counts belong in a readiness section. Do not convert them to a success percentage in a model-results section.
