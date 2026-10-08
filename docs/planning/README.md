> Integration status: the CLI and bounded official Telecom mock path are implemented and exercised. The current executable commands and exact remaining limitations are in [the tested runbook](../LOCAL_RUNBOOK.md) and [capability report](../CAPABILITIES.md). This document retains the full planned-study requirements; it is not a claim that every requirement is implemented.

# Local experiment handoff

This is a pre-experiment protocol for **Reviewer Advice Lifetimes and Goal Preservation in Multi Turn Agents**, aligned to the final 13-page manuscript dated 7 October 2026. It prepares CPU-based local orchestration with remote model APIs. No model training or local GPU is required.

**Real model experiments completed: zero. Real effectiveness results available: none.** Historical passing tests are scripted engineering evidence. They are not performance observations, natural reviewer samples, or an experimental sample size.

The immediate release goal is a reproducible repository that the researcher can run locally, inspect, and update with reviewed results. Repository preparation does not itself authorize API calls or collect any experiment. All new runner commands default to dry-run; live execution must be deliberately enabled on the researcher's computer with local configuration and explicit operational limits. An optional monetary ceiling can be set when reliable pricing is available.

## Read in this order

1. [Experiment plan](EXPERIMENT_PLAN.md): hypotheses, arms, dataset gates, sampling, analysis, and claim limits.
2. [Runner contract](RUNNER_CONTRACT.md): CLI and minimum implementation requirements.
3. [Local runbook](LOCAL_RUNBOOK.md): staged commands and safe configuration.
4. [Return results checklist](RESULTS_RETURN.md): reproducibility and privacy review before a repository update.
5. [Implementation checklist](IMPLEMENTATION_CHECKLIST.md): acceptance criteria for the repository implementation.

The JSON manifests contain actual source-derived identifiers and explicitly proposed extensions. Configuration templates deliberately leave provider choice, prices, optional spend limits, and confirmatory sample sizes unresolved. Missing required model or scientific-design fields block the relevant stage; unknown prices do not block token-accounted local runs.

## Version and evidence precedence

- The final manuscript defines the scientific contrasts: **C versus P is primary**; P is a persistent exact packet with a neutral header; **P0** is the legacy raw persistent packet. `B_bare` in the CLI is the manuscript's `B_native`.
- The older method blueprint used P for legacy persistence and prioritized R/P. Those naming and priority choices are superseded. Do not copy them into the new runner.
- The later frozen `advice_lifetime_controls` report establishes scripted P/R/C serialization, all-draw fallback, and bounded shared-prefix restore checks. This advances engineering readiness beyond the manuscript's older implementation-status paragraph. It does not change the scientific design or add model results.
- Frozen directories must remain unchanged. New tests and experiments write to new versioned output directories.

## Implementation status

The CLI in these planning documents is a **proposed interface until matched to the implementing repository's verified commands**. A command being specified here does not mean its live backend exists. The release must ship a capability report with each stage marked `implemented_and_tested`, `implemented_not_live_tested`, or `blocked_not_implemented`; no fictitious runner or placeholder success is acceptable.

The requested release must include an implemented local API path and at least one complete small multi-turn execution path tested with mock responses. It must not substitute permanently blocked live placeholders for that functionality. Calling the release ready for formal experiments additionally requires the scientific gates in the plan. The current seven scripted READ fixtures do not clear those gates.
