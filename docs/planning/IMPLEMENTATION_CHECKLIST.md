> Integration status: the CLI and bounded official Telecom mock path are implemented and exercised. The current executable commands and exact remaining limitations are in [the tested runbook](../LOCAL_RUNBOOK.md) and [capability report](../CAPABILITIES.md). This document retains the full planned-study requirements; it is not a claim that every requirement is implemented.

# Minimum implementation and release checklist

This checklist is for the implementation that accompanies the pre-experimental repository. It is not a record that these items have passed.

## Required for the local-run handoff

- [ ] `python -m local_experiments` exposes validate/run/analyze/export and helpful error messages.
- [ ] `run` defaults to dry-run and never reads credentials or makes network requests in that mode.
- [ ] `--mode live` is a command-line-only opt-in using the researcher's generic local API configuration. No assistant approval, existing private gateway, or cloud secret setup is required.
- [ ] At least one real supported API transport is implemented, including request/response recording, parsing, usage and retry errors, and tested against a mock transport.
- [ ] At least one complete small official-environment multi-turn path works with mock actor/reviewer/user responses, real tool dispatch, native continuation, terminal evaluation and output analysis. A fake single-request example is insufficient.
- [ ] The supported task/tool/checkpoint scope is explicit. Unimplemented paths return unsupported-capability errors rather than placeholder success.
- [ ] All eight arm semantics are implemented or individually labeled unsupported. Formal full-paper comparisons cannot be claimed until the missing arms work.
- [ ] Natural generation is structurally separate from historical scripted witness trajectories. Authored suffixes are never labeled natural API outcomes.
- [ ] P0 remains the frozen raw persistent treatment; P has a neutral header; C/P remains primary; R is whole-packet one-valid-response exposure.
- [ ] No historical guard is disabled. The new live-capable runner is separate from frozen no-API packages.
- [ ] Single q capture, malformed/out-of-scope fallback, unchanged draws, errors and semantic violations all remain in an immutable ledger.
- [ ] Shared P/R/C first segments and fresh independent suffixes preserve all native user/tool state and exposure counters across restart.
- [ ] Factual receipts remain separate from packet projection and raw model provenance; actor/user role ownership is preserved.
- [ ] Public projection excludes task IDs, fault labels, evaluator/answer fields, private databases and future branch text; legitimate public requirements are retained.
- [ ] Configurable request/step/retry limits exist; total token limits are not mandatory; pricing may be unknown; any optional currency cap is truthfully enforceable or explicitly rejected.
- [ ] Every attempted call and run status is recorded, including unknown billing/response outcomes and unfinished blocks.
- [ ] Analysis produces task-macro aggregates with explicit dependencies and missingness. It never pools fixtures with live data.
- [ ] Export is local-only and allowlist-based; `.env`, raw text/state, private outputs and caches are ignored.
- [ ] A generic `.env.example`, tested dependency instructions, source pins, licenses and public zero-real-results statement are present.
- [ ] Fresh output directories protect frozen evidence. No unrelated local files, personal context, or historical credentials are packaged.
- [ ] Actual tested commands, exit codes and code hashes replace proposed status only after verification.

## Required before a confirmatory repair claim

- [ ] Actual chosen provider wire behavior and token-matching limitations verified locally.
- [ ] Natural coverage pilot completed, including a full all-start/all-draw funnel.
- [ ] Mutating workflow/checkpoint support validated, including native participant ownership and side-effect replay/restore.
- [ ] Goal mappings and local-repair labels grounded in public requirements and annotated blind to terminal outcomes.
- [ ] Independent task/family coverage extends beyond the seven nested-goal READ fixtures; known development tasks remain excluded from held-out confirmation.
- [ ] Confirmatory protocol frozen before held-out outcomes: task sample, models/prompts, public trigger, repeated-sampling units, endpoints, delta/epsilon, interval/multiplicity method and stopping condition.
- [ ] P/C all-root estimate, official completion constraint, native B_bare/B control, P0/P wrapper calibration and necessary information/context controls available.
- [ ] Ordinary episode-start P/C utility evaluation completed before a deployable overall-benefit claim.
- [ ] Insufficient power, low incidence, failed gates, missing blocks, negative controls and unfavorable results reported honestly.

## Integration notes

Copy/adapt planning manifests and templates into the implementation's public layout. Preserve task/source hashes and scientific semantics. Schema names here are a contract proposal; the release must reconcile them with its actual code and update the runbook to working paths. Do not mark an unfinished stage complete merely to keep a command example passing.

Keep engineering status separate from science status: a mock-tested local runner can be delivered while natural experiments remain not run. The repository must make both facts easy to see.
