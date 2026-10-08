# Historical branch decisions

The five branches below informed the project's standards for evidence and its eventual move toward reviewer-advice lifetime. They were exploratory investigations with separate questions and stopping decisions. Their outputs are not experiments on the current P/R/C policies, and their numerical results must not appear as evidence that advice expiry improves a model.

## Contract evidence recovery

### Question and design

Could explicit service-contract information enable safer recovery after an ambiguous tool timeout? An authored simulator varied deduplication retention, status semantics, and processing guarantees. Four hand-written policies faced the same public evidence and initial observations; a full-contract reference received an explicitly privileged extra input.

The grid contained 8 service contracts, 3 initial outcomes, and 5 evidence conditions, producing 120 episodes per policy. Evidence conditions reused the underlying worlds. The 480 policy-episodes were not independent empirical observations or model samples.

### Verified finding

Conservative recovery, immediate same-key retry, and the full-contract reference each produced 90 safe completions, 30 unresolved episodes, and no unsafe episode in the configured grid. The deliberately faulty policy produced 63 unsafe episodes: 16 with duplicate effects and 51 with false-success reports, overlapping in 4 episodes. It had 52 safe completions and 5 unresolved episodes. The captured test record contains 32 passing implementation tests.

Matched-history examples showed that a particular delayed retry or premature success claim could have different consequences in worlds consistent with the observations. They did not show that every available action was unsafe: waiting remained possible, and immediate same-key retry was safe throughout the configured retention grid.

### Decision and rejected interpretation

The branch did not justify a model study claiming an advantage from structured contracts on these fixtures. The strongest simple retry control matched the more informed policies. The faulty policy combined several intentional defects, so its gap was not a causal estimate of a specific omitted guarantee.

The finite diagnostic distinguished objective success from what the observations supported within its bounded model family. It did not establish universal open-world safety. A finite pending continuation was an uncertainty representation, not proof of nontermination. The simulator excluded many real-service complications, including concurrent writers and broad network-failure patterns.

**Retained contribution:** a deterministic measurement/checker example and counterexamples to unsupported success claims. **Unresolved:** whether real models invent guarantees from incomplete evidence. That question was not measured.

Evidence anchors: `contract_evidence/results/summary.json`, the branch's documented simulator semantics, and its captured test record.

## Fixed setup outcome replay

### Question and design

Could lightweight public outcome metadata support an honest no-change instability audit and a small-subset score-estimation replay without downloading traces or embeddings?

Two publicly released metadata files describe a reported OpenHands/Qwen setup. Six disjoint cohorts contain tasks with exactly 5 through 10 retained attempts. The index of an attempt is its position in each task's file-order sequence; it is neither a timestamp nor a synchronized benchmark round. Selection used outcomes at indices 1 and 2. Evaluation used indices 3 through the cohort's final index. The published [grouping implementation](https://github.com/SAILResearch/swe-agent-subset-selection/blob/daed756c5d10aafbc9e4c9b7cbef8d080be43721/pipeline/group_runs.py) establishes this distinction.

### Verified finding

The metadata covered 3,188 tasks, 1,243 repositories, and 25,279 trajectories. Its 50,558 representation entries supplied two representations per trajectory, not twice as many attempts. No missing cells or outcome disagreements were found within the retained rectangular cohorts.

Across all available outcomes, 787 tasks changed pass/fail at least once, 24.69% of tasks. Across task-by-unordered-attempt-pair comparisons, 8,807 of 90,717 differed, 9.71%. Larger-attempt cohorts contributed more pairs, and the pair observations were dependent.

On 33 held-out cohort/index positions, the fixed hash subset had 3.877 percentage-point RMSE; a history-pattern subset had 3.784 unweighted and 3.917 stratum-weighted RMSE. Worst absolute errors were 9.531, 7.350, and 8.871 percentage points, respectively. These were descriptive results from one frozen selection, not a demonstrated method ranking.

Under the illustrative rule of an absolute change strictly greater than 5 percentage points relative to each estimator's own two-index historical mean, the three estimators signaled in 4, 7, and 9 of 33 positions. The full retained cohorts signaled in none. The subsets used 1,893 of 18,903 available held-out task-attempt cells. This was a replay count, not measured execution or monetary savings.

### Correction and limits

An implementation correction replaced floating remainder comparisons with exact integer arithmetic for proportional allocation. In the 10-attempt cohort, the corrected counts for historical patterns 00/01/10/11 were 27/3/2/26 rather than 26/3/3/26. The declared selection rule did not change. The figures above use corrected outputs.

Source metadata did not authenticate immutable model weights, seeds, timestamps, or identical runtime configuration for every retained attempt. The [original collection account](https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b) described invalid-patch filtering and infrastructure failures. Consequently, observed churn cannot be attributed exclusively to model randomness. Separate cross-model cost proxies did not measure this cohort's billed usage.

**Decision:** retain the descriptive audit; reject claims of real-edit regression detection, selector superiority, calibrated real-release false-positive rates, or measured savings. A real harness-change study would require genuine before/after revisions and authenticated paired outcomes.

Evidence anchors: `regression_data_audit/audit_results.json`, `pair_churn.csv`, `heldout_evaluation.csv`, and the correction record. Public input provenance is listed in [Sources and redistribution boundaries](SOURCES_AND_RIGHTS.md).

## Deterministic change replay

### Question and design

Could first-boundary divergence under a harness edit supply a useful test-selection signal beyond component exposure and public capability tags?

The branch used 16 authored tasks, 32 hand-scripted response tapes, 4 local synthetic edits, and 3 controls. Two tapes per task changed wording but shared an action skeleton. The resulting 224 replay units were instrumentation fixtures, not independent agent trajectories.

Replay compared complete serialized model requests, tool dispatches, observations, and termination events. It stopped at the first difference. An old response was never consumed after its request ceased to match, and an old tape tail was never treated as a mutant continuation.

### Verified finding

There were 72 structural divergences: 32 for the global-prompt control and 40 for the local edits. The remaining 152 units matched their complete scripted historical paths. All divergent terminal goals remained unknown. Boundary differences were not labeled as task failures.

A stronger, label-free control evaluated the changed pure functions on valid historical call contexts. It reproduced all 224 divergence-presence decisions and all 72 first-divergence positions. Although replay distinguished some tasks that coarse tags could not, no incremental signal over this direct local-function diagnostic was demonstrated. The captured test record contains 32 passing implementation tests.

### Decision and accounting boundary

The unique replay-selector-advantage hypothesis received a no-go decision on these fixtures. The result does not rule out practical debugging or automation benefits, which were not measured. The direct-function equivalence depends on the fixture's pure immediate-boundary hooks and is not a theorem for arbitrary harnesses.

The cost unit was attempted request boundaries plus tool dispatches. It was neither billed tokens nor runtime. Feature construction was charged rather than treated as free, but the promised separate baseline metadata-work counter was not implemented. The disclosed omission prevents an end-to-end efficiency claim.

**Retained contribution:** exact boundary instrumentation, explicit unknown outcomes after divergence, and a strong null control. **Rejected interpretation:** that replay divergence identifies a model regression or that the candidate selector earned a paid evaluation on a unique-signal premise.

Evidence anchors: `change_replay/results/summary.json`, `local_predicate_diagnostic.json`, the frozen protocol, and the captured test record.

## Constructed decision validity

### Question and design

Could a final bounded audit clarify what observed-drop rules and standard multiplicity corrections mean on small, overlapping task sets?

This branch reused the public outcome matrix, fixing attempts 3 and 4 for every task and keeping prior selectors based only on attempts 1 and 2. There were 307 discordant pairs among 3,188 tasks. In each of 1,000 fixed-seed synthetic replicates, an independent fair orientation assigned each pair to pseudo-old and pseudo-new labels; overlapping views reused the same task orientation.

Six cohorts, three views, and a global test plus four slices produced 90 prespecified hypotheses in 18 five-test families. Empty and zero-discordance tests stayed in their families. Independent fair signs were imposed by construction, not inferred from the original collection.

### Verified finding

Across all 90 tests, at least one positive drop and at least one drop of 5 percentage points or more occurred in all 1,000 synthetic orientations. At least one unadjusted exact p-value was at most .05 in 577 orientations. Audit-wide Holm correction rejected in 6 orientations, 0.6%, with a conditional Monte Carlo Wilson 95% interval of approximately 0.275%–1.303%.

Fifty-six of the 90 tests had at most four discordances and could not attain an unadjusted one-sided exact p-value of .05 even if every discordance was a loss. Seventeen deterministic checker fixtures passed.

### Decision and rejected interpretation

The branch was archived pending a genuine fixed-model, real-edit collection plan. It demonstrated ordinary conditional testing behavior, not a novel method or detector effectiveness. Its observed-drop rules and zero-effect test have different targets and cannot be ranked as competing methods.

The interval quantifies only Monte Carlo uncertainty conditional on these fixed retained pairs and the imposed orientation mechanism. Low rejection frequency, no discordances, or an empty slice does not establish safety, equivalence, or power. The 1,000 orientations are not 1,000 new agent runs. The protocol freeze preceded this analysis but followed earlier access to corpus summaries; it was not an externally registered blind study.

Evidence anchors: `decision_validity_audit/results.json`, its analytical marginal outputs, protocol, and checker fixtures. The public data source is the same as for the fixed-setup audit.

## Natural verification evidence

### Question and design

Could an existing public trace establish a strict chain of stale evidence use: an observed check, a relevant later mutation, explicit subsequent reliance on the older result, and independent final-state falsity of that same claim?

A single deterministic hash-selected sample of 20 tasks was frozen from a 2024-era SWE-agent/GPT-4 submission. The audit read existing artifacts statically; it did not execute benchmark code, collect new trajectories, or expand the sample after observing outcomes. The [pinned submission](https://github.com/SWE-bench/experiments/tree/40f164d5b8f1d249bf95a6df8b74b577fd8e519d/evaluation/lite/20240402_sweagent_gpt4) identifies the collection, but separately hosted assets are mutable independently of the repository commit.

### Verified finding

All 20 trajectories were available. Seventeen records contained an executed diagnostic/check command with observed output, totaling 55 executions. Such commands included drivers that failed or did not actually invoke test methods; execution did not imply valid testing. Eighteen records had a nonempty patch and an evaluator log, and all 18 patches agreed after boundary-whitespace normalization between trajectory submission and prediction.

No record established the full stale-reliance chain. No record established explicit old-check reliance after a relevant mutation. Eight records supplied cleanup-only post-check controls, and one showed misreporting of a fresh execution result. Those are different phenomena.

### Decision and evidence standard

The stale-reliance hypothesis remained unsubstantiated by this sample and was archived. Zero observed positives cannot establish absence or contemporary-agent prevalence. Opportunistically adding examples until a positive appears would not repair that limitation.

A later broad test failure was not accepted as falsification of a narrower successful driver. Deleting a standalone driver after a successful production-state check was not automatically treated as invalidating the production behavior. Fresh-but-insufficient checks, fresh-result misreports, stale evidence, and missing reliance were kept separate.

Exact evaluated-patch equality, full runtime snapshots, and complete agent/evaluator/environment versions were not established. No explicit redistribution license for the separately hosted trajectories and logs was verified. A future causal audit would need licensed snapshot-capable data and a trusted replay of the same claim-specific probe before and after the relevant mutation.

Evidence anchors: `natural_evidence_audit/audit_summary.json` and the recorded aggregate artifact-alignment findings. Raw annotations and trajectory text are excluded from this public history.

## What transfers to the current proposal

The earlier branches supplied evidence standards rather than positive support for a new effect: preserve unknown outcomes, compare against strong simple controls, distinguish public evidence from hidden evaluation, identify the exact claim being checked, preserve negative findings, and charge acquisition costs. The reviewer-advice-lifetime proposal requires its own frozen protocol and fresh behavioral evidence. Its validity cannot be inherited from any of these exploratory results.
