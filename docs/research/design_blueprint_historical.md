# Research blueprint: review after its action is complete

Status: pre-experiment proposal, 7 October 2026. No model run, provider-format test, reviewer effect, or method gain is reported here. The frozen implementation directories are read-only evidence. This document proposes a new, separately versioned experiment; it does not amend their protocols.

## 1. Recommendation and claim boundary

The strongest defensible direction is an **empirical systems paper about the lifetime of reviewer feedback**, rather than a claimed invention of goal memory, invariant checking, or critique expiration.

Working title: **When Should Reviewer Feedback Expire? Preserving Achieved Goals in Tool-Agent Continuations**.

Core question: after a reviewer-recommended action has executed successfully, does keeping its critique active in later actor requests change the probability that the workflow ends with an earlier, still-required achievement lost? Can a simple expiration policy improve preservation without sacrificing completion?

The central comparison holds the executed correction and its factual tool result fixed and changes subsequent exposure to the reviewer packet. It measures a total effect of an exposure policy. It is not a new causal estimator, a natural-indirect-effect analysis, proof of an internal cognitive mechanism, or a claim that all earlier work treats reviewing as harmless.

The paper can be valuable if it establishes a practically consequential, reproducible response surface: when persistent advice helps, when it hurts, and whether an inexpensive lifetime choice improves the completion/preservation/cost trade-off. If the evidence does not distinguish this from ordinary context deletion or known feedback disruption, narrow the paper to an honest negative study or stop; renaming old concepts is not a contribution.

### Why this pivot is necessary

- ReinforcedAgent already reports harmful multi-turn configurations. Do not claim the first discovery of multi-turn reviewer harm.
- CAVE-Bench already protects verified correct work, retains supporting history, measures downstream damage, and evaluates evidence rules and gates under false accusations. Our candidate contrast is ordinary model-generated review during an unfinished task, including accepted rather than deliberately false interventions. [Primary source](https://arxiv.org/html/2609.32616v1)
- The Intervention Paradox already separates accurate prediction from effective intervention and compares visible with silent feedback. Consequently, A versus P alone is insufficient novelty. [Primary source, §5.3](https://arxiv.org/html/2602.03338v1)
- PolicyGuide already grounds workflow progress in observed tool results and maintains request state. A goal ledger and a runtime guard are strong baselines, not new principles. [Primary source, §3.4](https://arxiv.org/html/2608.19861v1)
- The parallel literature audit identifies additional overlap in constraint preservation, stale-rule deactivation, authority tracking, and context removal. The final related-work section must use that audit's verified source-level distinctions. Do not make a first-expiration or first-provenance claim.

## 2. Formulation: achievements, requirements, and loss

### 2.1 Two information boundaries

The deployment-facing side observes only the actual public conversation, the actor's available tool descriptions, public tool outputs, and factual controller receipts. It does not observe task IDs, benchmark evaluation criteria, private simulator instructions, hidden database snapshots, future user responses, or executable goal labels.

The evaluator can inspect cloned private state and the benchmark's original grading contract. This privileged access is for labeling and analysis only. Every figure must draw this separation explicitly. The legitimate user simulator may retain its own original private scenario; that does not make the scenario available to the actor or reviewer.

There are three distinct objects:

1. A semantic requirement, such as “restore mobile internet and finish with excellent speed.” Its authority comes from the user's disclosed request or other legitimate public task specification, not from an evaluator field.
2. A public evidence record, such as an observed speed-test output or an exact user report grounded in a device check. This is imperfect evidence that a requirement is currently met.
3. A private predicate used for reproducible scoring. It operationalizes part of the requirement but is not itself a user instruction or deployable sensor.

For each scored predicate, record a pre-run mapping to its semantic requirement, authority source, scope, observability, and temporal mode. Mark weak or disputed mappings. A hidden numeric threshold must never be inserted into a prompt when the user has not disclosed it. Report full official task success separately from the subset of losses that have clear public semantic grounding.

### 2.2 State and goal notation

For task i, let x_t be complete environment state, H_t public interaction history, and p_j(x_t) a fixed evaluator predicate. Let required_j(t) say whether the requirement remains applicable. In a benchmark with fixed user goals, it stays true throughout the run; do not invent a release mechanism the benchmark does not support.

An achieved set at an eligible prefix is:

G_t = {j: required_j(t)=1, p_j(x_t)=1, and p_j was false at an earlier observed state in this episode}.

Require G_t nonempty and at least one still-required goal unmet at t. This studies a genuinely unfinished workflow after progress. Initially true properties form a separately reported “maintained state” stratum rather than being quietly called newly achieved goals. Initially/vacuously true nonexistent-bill predicates do not qualify as achieved progress.

The primary outcome for arm z is terminal unresolved loss:

L_z = 1 if at least one j in G_t remains required at termination and p_j(x_T^z)=0; otherwise 0.

Report per-task fraction lost as a secondary measure. Do not treat nested predicates as independent observations or double-weight one failure because it breaks both connectivity and speed.

Distinguish:

- Immediate loss: a protected predicate is false immediately after the selected tool action and synchronization.
- Delayed unresolved loss: protected predicates hold immediately after that action, but at least one is false at termination.
- Transient loss with recovery: a protected predicate becomes false later but is restored by termination.
- No loss: the protected predicates remain true at evaluated boundaries.
- Legitimate requirement change: an explicitly supported task update releases or changes the obligation; analyze separately, never count silence or a polite goodbye as a release.

For “must always hold” requirements, a temporary violation is already a failure; score those separately. The main terminal-state endpoint must not punish a legitimate temporary restart as if it were permanent damage. Record first loss, recovery, recurrence, and termination cause for interpretation. Native max-step/error termination counts as the observed terminal endpoint, not missing data. Report budget-limited unresolved loss separately from ordinary final completion, because it may be recoverable with more budget.

### 2.3 Local acceptability is not local correctness

Use explicit, nested labels rather than “the reviewer fixed it”:

- Q-format: raw reviewer output parses and follows the public schema.
- Q-scope: proposed action belongs to the declared intervention class.
- Q-executable: the official tool accepts its concrete arguments and returns a non-error outcome.
- V+: on a private isolated shadow execution, all G_t predicates remain true immediately afterward.
- Local repair, optional: a separately predeclared, publicly meaningful defect in a0 is demonstrably fixed by a1. This requires a real defect criterion, not merely successful execution.

V+ is an evaluator-only analytic stratum. It is not a deployment decision rule, and it does not certify the reviewer's prose, future plan, or global correctness. In the currently validated READ slice, immediate physical preservation is largely guaranteed by construction; its V+ rate is not evidence that a safety method works.

## 3. Intervention protocol and estimands

### 3.1 The immutable experimental unit

An experimental root contains task identity for auditing, complete environment snapshot, both participants' original histories/configuration, remaining native budgets, routing, auxiliary tool state, RNG state, and one raw pending actor proposal a0. Actor and user continuations must be fresh model generations; scripted suffixes cannot support behavioral claims.

Generate one raw reviewer packet Q from the allowed public view before any shadow labels or dispatch. Save it unchanged, including invalid outputs. The packet proposes a1 and critique text. Never redraw until an intervention becomes valid, helpful, changed, or V+. Count the following mutually exclusive raw-output classes: invalid, out of scope, unchanged, valid changed. An unchanged action with critique is still an intervention.

For the primary experiment, use at most one prespecified eligible prefix per natural trajectory, selected by a fixed stopping rule. Eligibility is never defined by whether the original continuation succeeds or whether review later harms it. If hidden predicates select scientific diagnostic prefixes, label the sample as evaluator-selected; this cannot establish a deployable trigger rate. In parallel, measure coverage using a frozen public-observation eligibility rule.

### 3.2 Arms

The inherited B/S/A/P controls remain useful:

- **B-bare:** unmodified actor continuation with original action a0 and no receipt instrumentation.
- **B:** execute a0 through the instrumented factual controller receipt format.
- **S:** one matched self-reconsideration opportunity; preserve invalid-format fallback and actual tool errors honestly.
- **A:** execute reviewer action a1; actor sees only the factual override/execution receipt and real result.
- **P:** execute exactly the same a1; the complete frozen reviewer packet is active in every subsequent actor request.
- **R:** execute the same a1; show the same packet at the first subsequent actor generation boundary, then stop re-presenting that packet at later boundaries. The factual receipt, native conversation, actor's own earlier text, and full audit log persist.

P is the frozen adapter's persistent-packet treatment. It is not automatically the default format of every provider or production agent. Describe the role, priority, placement, and lifetime of every packet. A single persistent SystemMessage projected at each request is not a claim that duplicate messages are appended to the official trajectory.

R retires the **whole reviewer-generated prose packet**, not a perfectly separated instruction-only component. The packet may contain useful inferred information as well as directives. All original public observations remain accessible, but an explanatory inference may disappear from active context. That information-loss trade-off is an outcome to evaluate, not a harmless implementation detail.

For malformed or out-of-scope Q, the public deployment policy falls back once to a0, with no critique that pretends a valid revision occurred. A valid-schema official tool error remains a tool error. Do not silently revert after seeing private state or terminal outcomes. All policies use the same predeclared routing for invalid/unchanged cases.

### 3.3 Primary and secondary estimands

Primary deployment question: over all public-triggered roots and all raw Q draws, compare the terminal loss and official task-success rates of R versus P. This policy-level contrast includes invalid and unchanged proposals under their fixed fallbacks. Report cost and latency alongside quality.

Primary mechanistic diagnostic: among the common, pre-dispatch valid-changed Q roots with immediate V+ labels, compare P versus R, and P versus A. This is a selected-population total effect of exposure policy, not the prevalence of reviewer harm on all tasks and not an oracle-free deployment result.

Additional contrasts:

- B-bare versus B: instrumentation effect.
- A versus B: effect of using the revised action plus honest override provenance, not a “pure action effect” detached from required representation.
- P versus A: effect of adding the whole critique package to the same executed action/result.
- P versus R: effect of sustained versus one-boundary packet exposure.
- R versus A: value or harm of one explanatory exposure.
- S versus B: additional reconsideration rather than reviewer identity.

Average first within each task across roots/proposals/replicates, then across tasks. Publish task-level effects, domain effects, and raw counts. Do not label one pair with B success and P failure as proven individual causal harm: stochastic suffixes can differ without treatment. Repeated fresh suffixes estimate risk differences, with uncertainty clustered above the suffix level.

### 3.4 Shared first-exposure segment for P/R

P and R have identical request distributions until the second post-intervention actor boundary. For an efficient and cleaner contrast, execute their common first exposed actor/user segment once, snapshot immediately before the next actor generation, then fork P and R there. Both branches inherit the same new actor text and user response. After that boundary use fresh actor and user stochastic generations.

If the common segment terminates before a second boundary, both policies have the same observed result; keep it in the all-root policy denominator. Do not silently select only long continuations. A secondary landmark analysis may condition on reaching that second boundary, clearly labeled. Shared-prefix costs are logged once physically and assigned to each policy's logical deployment cost.

Preserving RNG state at a clone does not guarantee common random numbers from a remote API. Do not promise identical randomness when prompts differ. Randomize/interleave arm execution order in provider-time blocks, record model version and sampling configuration, and treat unseedable API randomness honestly.

## 4. Concrete policy: slot-scoped reviewer-packet exposure

This is a minimal no-training controller policy proposed for testing, not a novel general memory algorithm. It needs no hidden predicates, no environment clone in deployment, no trajectory oracle, no new model, and no per-turn extra reviewer calls.

### Controller state

Each accepted intervention stores:

- immutable intervention ID and pending slot ID;
- hashes of raw a0 and Q;
- actual selected action a1 with honest fresh call ID if changed;
- executed outcome/result hash, including errors;
- packet state: pending execution / eligible for one exposure / retired;
- the actor generation boundary where exposure was attempted and whether a valid response was received.

An exposure consumes the slot only after a valid actor response is returned. A transport error does not expire the packet or create a new reviewer draw. Retries of the same request obey the fixed block retry cap. Actor-produced copies or paraphrases of critique in the native history remain; R is not memory erasure.

### Pseudocode

```text
At the declared reviewable slot:
    preserve raw pending proposal a0
    Q := one reviewer call(public_actor_view, public_tools, a0)
    record Q before any shadow evaluation
    if Q is invalid or outside public study scope:
        selected := a0
        packet := none
    else:
        selected := exact action from raw Q
        packet := exact critique/revision payload from raw Q
    execute selected through the unchanged official environment
    record actual result/error and factual override provenance
    if packet exists:
        exposure_state := eligible_for_one_exposure

At each later actor generation request:
    request := official public history + factual controller receipts
    if policy is P and packet exists:
        request := request + exact packet
    if policy is R and exposure_state is eligible_for_one_exposure:
        request := request + exact packet
    if policy is A:
        do not add the packet
    actor_response := invoke fixed actor API(request, unchanged tool catalog)
    on a valid response under R:
        exposure_state := retired
    append only actual actor/user/tool events to native history
    continue with native remaining budgets and termination rules
```

Keep each policy's request projection fully serialized and hashable. Never relabel controller action a1 as an observed actor generation. A canceled a0 must not receive a1's result under its old call ID. The private raw log and derived official replay trajectory have different purposes and must remain separately identifiable.

### Essential minimal implementation tests

1. P and R have identical first-exposure requests, tools, receipts, and selected action.
2. After exposure, P/R differ only in the declared packet-lifetime projection; no public tool observation or native message is lost.
3. An unchanged a1 still follows the chosen packet lifetime.
4. Public errors do not trigger oracle-informed fallback.
5. Serialized restart preserves expiry state and never gives R another first exposure.
6. Retries cannot spend a packet twice or obtain a fresh Q.
7. All actor/user continuations inherit exact remaining native budgets.
8. Canary and structural tests exclude hidden labels and source IDs from actor/reviewer payloads.

The existing frozen renderer cannot be presumed to satisfy these new lifetime semantics. Implement a new version only after its own protocol freeze and approval. Existing READ checks are not validation of mutating actions, participant-message intervention, multi-call proposals, or voice.

## 5. Hypotheses, discriminating controls, and failure conditions

### Predeclared hypotheses

- H1, diagnostic: some locally executable, immediately preserving reviewer interventions are followed by higher terminal unresolved-loss risk than their same-prefix controls. The effect must survive repeated suffix sampling rather than rely on selected anecdotes.
- H2, lifetime: at fixed a1 and shared first exposure, P and R have meaningfully different preservation/completion outcomes on held-out tasks. Direction is an empirical question; the directional method hypothesis is that R lowers loss in the prespecified vulnerable subset.
- H3, useful mitigation: R reduces loss relative to P while official completion is noninferior within a predeclared margin, and does not merely avoid action or spend more resources.
- H4, heterogeneity: lifetime effects depend on whether reviewer content is genuinely action-local versus contains still-useful cross-step information. This requires annotation before inspecting arm outcomes; do not discover a favorable label afterward.

The paper need not “confirm” all four. A consistent finding that persistence helps, or that expiration loses important diagnostic context, is informative and should be reported as such.

### Strong controls and baselines

**Scope tag, same words.** Retain the exact packet at all P boundaries but label it as advice for the already executed slot, not a new user goal or permanent policy. Use a neutral wrapper of similar size as a presentation control. This tests framing without removal; it still changes an instruction, so it is not a semantically inert placebo.

**Matched retirement.** Retire a matched-size, similarly positioned non-review summary rather than the reviewer packet. If arbitrary context shortening explains the gain, do not claim a reviewer-specific lifetime phenomenon. Padding itself can affect models; disclose that exact semantic/token matching is impossible.

**Plain task/achievement reminder.** Give the actor a compact public-evidence-linked goal checklist, with no hidden labels. Compare one-shot and persistent forms under matched context budgets. This is the simple baseline reviewers will rightly demand.

**Evidence refresh/final verification.** Use available ordinary public reads to recheck stale achieved-goal evidence before completion, with an explicit read budget. A future write does not automatically license an extra private state probe. User-side checks in Telecom must be requested through the user, not executed by the assistant under a fabricated role.

**Immediate public guard.** Reject only demonstrable public violations of stated constraints or tool preconditions. Add an oracle predicate guard solely as an explicitly privileged diagnostic upper reference, never as a practical competitor.

**Bounded rollout selector.** On a subset where a deployment-faithful sandbox/model of the tools is actually available, compare a compute-matched short rollout with a public scoring rule. A clone with private true state and hidden predicates is an oracle diagnostic and must be labeled accordingly. Do not claim that a rollout is deployable simply because the evaluator can fork the benchmark.

**No-review and self-reconsideration.** B-bare/B/S are necessary to show whether the full review system creates value at all. A cheaper policy that merely undoes an unnecessary reviewer is not enough for a broad “better agent” claim.

### Falsifiers and stop criteria

- If B-bare and B differ materially, the adapter is an active intervention. Report all main effects conditional on the instrumented setup; investigate the format before attributing a broad reviewer effect.
- If natural/publicly detectable eligible prefixes are too rare, the setting has poor practical yield. Stop broad collection and report feasibility, rather than manufacturing selected harmful cases and calling them prevalence.
- If all evidence is from seven staged READ roots with nested goals, stop any broad preservation/method claim. These are infrastructure and narrow information-path witnesses only.
- If P and R are equivalent to a practically meaningful precision bound, the expiration hypothesis is unsupported. A nonsignificant wide interval is inconclusive, not equivalence.
- If R's preservation gain is paid for by lower completion, more abandonment, or materially more unmet new goals, do not declare success. Show the trade-off.
- If R helps no more than arbitrary shortening or a basic goal reminder, do not claim a review-specific policy advance.
- If the effect disappears with a lower-priority/ordinary message role, frame it as a harness-delivery effect rather than a universal property of review.
- If losses occur only in hand-authored examples, label them constructed stress tests and do not infer natural incidence.
- Any oracle leakage, contradictory raw/executed action records, or nonfaithful restore invalidates the affected block. Repeated structural failures stop collection for repair; they are not model errors.

## 6. Coverage plan: what must extend beyond the current seven tasks

### Existing evidence, exactly

The frozen backend reports seven scripted live runs and fourteen fresh-process restores, with original pending customer lookup and terminal official ENV reward 1. It also reports 84 concrete READ transitions across six tools. The intervention layer reports 36 offline tests; the receipt adapter reports 37 tests and six restart checks. All are scripted, with zero actual model calls. They establish bounded readiness, not natural eligibility or harm. See the local REPORT.md files listed below.

The seven base Telecom candidates involve restoring connectivity while speed remains inadequate. Those predicates are nested, so the slice is one family of staged progress rather than independent multi-goal diversity. The 45 full-split static candidates are not 45 already validated tasks or independent task families.

### Necessary extensions, in priority order

1. **Natural READ-to-later-WRITE continuations in the current slice.** Fresh actor and user APIs must actually reach eligible prefixes; score any subsequent public/device actions. This can test feedback-lifetime effects through information and dialogue, but cannot demonstrate a mutation guard's ability to admit/reject destructive corrections.
2. **Validated single assistant WRITE slots.** Start with exact official Telecom operations that have narrow inspectable effects, such as enable_roaming/disable_roaming and resume_line/suspend_line, on synthetic benchmark accounts only. Verify full official orchestration, copied state, errors, replay, timestamp behavior, and future actor/user routing for each concrete proposal/revision family. These tools are source-inspected candidates, not validated extensions. Charges/policy permissions must remain part of the simulated task contract. Do not patch original tools or remove native policy requirements.
3. **User-mediated device actions.** Toggle operations and troubleshooting resets can create temporary or unresolved connectivity loss. They are user-side tools; changing an assistant instruction requires a separately declared message-level intervention interface. Never pretend they belong to the already validated assistant READ slot.
4. **Independent goal interactions.** Audit at least one additional task family/domain where an achieved requirement is not logically entailed by the remaining goal: for example, completing two distinct authorized account updates; preserving a document section while fixing another; or retaining an existing reservation while completing a different allowed change. These are candidate task designs, not asserted official coverage. First identify real source tasks with public goals and observable results; only then decide whether an explicitly labeled synthetic stress suite is necessary.
5. **Legitimate transient-change controls.** Include workflows where temporarily breaking a state is necessary and recovered. A controller that simply forbids every decrease can look safe while preventing task completion.

Keep natural benchmark evaluation and constructed mechanism stress tests in separate result tables. A constructed fixture may show that the harness can express a pathway, but not that models take it naturally. Split related templates/personas/fault variants together when assigning development versus test sets.

## 7. Power, clustering, budget, and staged execution

### Statistical unit and precision

Suffixes from one prefix are repeated draws, not new independent tasks. Prefixes from one task, persona variants, and generated fault combinations may be strongly dependent. Use task-macro point estimates, task-cluster intervals, and a sensitivity aggregation by the prespecified task family. With very few families, avoid grand population claims even if thousands of suffixes make a naive confidence interval narrow.

Before the confirmatory run, specify the smallest worthwhile absolute loss reduction and the acceptable completion loss. An illustrative planning target is 5 percentage points for preservation and a 2-point completion noninferiority margin; these are proposed design choices, not established domain standards. The user/researcher should fix them before observing confirmatory outcomes.

For an independent paired Bernoulli contrast with discordant-pair probability q and target difference delta, the rough screening calculation n ≈ (1.96+0.84)^2 q / delta^2 illustrates the scale. At q=0.20 and delta=0.05, that is about 628 independent paired units before clustering. This is an order-of-magnitude calculation, not a justified sample-size recommendation for the hierarchical experiment.

Estimate task/prefix variance and pair discordance from an explicitly separate feasibility sample; simulate power under a hierarchical task/prefix/suffix model, including exclusions and realistic reviewer-change rates. Prefer more task families to many repeats on seven tasks. A small feasible budget can support an informative pilot, but it cannot be advertised as a powered top-conference confirmatory study.

Preregister one primary policy contrast (P versus R), one utility noninferiority constraint, and secondary diagnostics. Use simultaneous intervals or a declared multiplicity correction for confirmatory secondary contrasts. Model-pair and domain analyses are heterogeneity estimates with intervals, not a search for whichever cell is positive.

### Stage 0: current pre-experiment work

Freeze the formulation, source mapping, proposed policy, public/evaluator boundary, outcome schemas, and decision criteria. Keep this incomplete paper honest about missing results. No model/API calls are authorized by writing a plan.

### Stage 1: tiny provider-format gate, separately authorized

After explicit provider/model/budget approval, test the exact supported role/receipt format on a few non-behavioral requests. Verify raw effective request, returned call IDs, tool serialization, usage reporting, and restart. This gate is not an experiment and must not be called evidence of causality or provider-wide reliability. If SDK rewriting prevents the promised request contrasts, repair and refreeze before behavioral collection.

### Stage 2: feasibility sample

Use held-out-from-confirmation tasks to estimate public and oracle-selected eligibility rates, Q class frequencies, average actor/user cost, and suffix length. Validate the first narrow write/message extensions before using them. A provisional small schedule might be 12–20 task roots, one Q per root and two fresh continuation replicates, but its purpose is feasibility, not significance. Stop at the approved ceiling; do not increase the budget because a trend is almost significant.

### Stage 3: confirmatory design decision

Use the feasibility estimates to choose a fixed task count, repeats, model pairs, and dollar cap. Lock task/family split and all primary analyses. Decide whether a multi-domain confirmatory study is affordable. If not, keep the project a bounded pilot or seek approval for a larger scope; do not imply that cheap infrastructure has removed inference costs.

### Stage 4: main conditional experiment

Run complete pre-reserved arm blocks, with randomized time-blocked schedules and fresh actor/user suffixes. Include B-bare/B calibration, B/S/A/P/R core contrasts, and focused lifetime ablations. It may be cheaper to run the most expensive baselines on a prespecified subset rather than every root; distinguish those samples. Save every raw Q and exact request projection. No best-of-n hidden selection.

### Stage 5: public-trigger end-to-end validation

Run the frozen P and R policies from ordinary episode starts, under the same total deployment resource ceiling. This checks whether an effect on evaluator-selected roots translates to usable improvement and whether detection/extra context costs erase it. Do not claim end-to-end benefit from a conditional slice alone.

### Cost ledger and missingness

Maintain separate physical charges and logical per-policy cost. Charge prefix generation, reviewer/self calls, both actor and user continuations, repeated receipt tokens, failed calls, retries, and readback/rollout baselines. Shared captured Q must not be billed four times in the physical ledger or zero times in a deployed review policy's cost. Prices remain unknown until the approved provider/model is selected and its current pricing is verified.

Reserve worst-case budget for a complete comparison block before launch, including one declared retry allowance. Do not start whichever cheap arms fit and silently drop the rest. Native task failures remain outcomes. Provider/infrastructure failures are reported separately, with their frequencies by arm, complete-block analysis, and conservative missing-outcome bounds. Predefine structural-failure thresholds that pause the study for debugging, never a significance-based early stop.

## 8. Explicitly synthetic worked example

This is an authored illustration, not an observed or model-generated trajectory. Its successful and failing suffixes are invented to explain the estimand.

The user wants working mobile data and excellent speed. The agent has already restored connectivity, supported by a user device check; speed is still poor. Thus G_t contains working connectivity, while excellent speed remains unmet.

The pending actor proposal repeats a customer lookup. The reviewer recommends get_details_by_id for the already known line and says to inspect the carrier line before changing device settings. The actual READ returns an active line. It is executable and leaves connectivity intact. This is a locally acceptable lookup substitution, not proof that the entire critique is optimal.

P and R receive the same factual receipt and the same critique for the next actor response. The actor asks which network mode the phone is using; the user reports 2G-only. The two policies are then cloned at the next actor boundary, preserving that shared conversation.

- Under a hypothetical P suffix, the old “inspect carrier settings first” advice remains active. The actor restarts troubleshooting, asks the user to toggle mobile data, and later ends without turning it back on. The evaluator observes connectivity=false at termination: delayed unresolved loss.
- Under a hypothetical R suffix, the packet is no longer re-presented. The factual line result and 2G observation remain. The actor asks for the preferred faster network mode, then checks the result and ends with both requirements met.
- In a third hypothetical suffix, mobile data is briefly off but is restored before termination. That is transient loss with recovery, not the primary terminal-loss endpoint.

One such story proves nothing about causality or frequency. The experiment asks whether repeated fresh P/R suffix distributions differ over predeclared roots. If P instead uses the critique productively and R forgets an important diagnostic constraint, the method has failed on that case and the study must count it.

## 9. What the incomplete paper may and may not say

It may present the question, distinction from close prior work, formal endpoints, policy pseudocode, validated infrastructure boundary, synthetic illustration, budget/power plan, and preregistered result-table shells.

It may not say that reviewers caused measured delayed loss, that expiration improves success, that any method is state-of-the-art, that the current seven tasks establish diversity, or that provider behavior has been verified. Avoid a “Results” section that substitutes unit-test counts for behavioral evidence; title that part “Offline infrastructure readiness.”

The strongest possible eventual contribution is empirical: a controlled characterization of post-action feedback lifetime, together with a low-cost operating rule whose value and limits are demonstrated against credible alternatives. If that evidence does not materialize, the correct paper is narrower or remains unfinished.

## 10. Final novelty amendment: applicability must be tested, not assumed

This amendment follows the completed parallel novelty audit, particularly AgentSentry's matched-runtime evidence-preserving context interventions. Merely changing an adversarial source to a legitimate reviewer does **not** by itself establish a substantial new contribution. The stronger scientific target is **feedback applicability calibration**: preserving useful continuing advice while recognizing when a local recommendation has already been discharged.

### Add the exact-text status arm C

Add C to the pre-experiment design before any protocol freeze. C retains the exact reviewer prose in the same role and position as P, but supplies a factual scope/status header identifying its target slot and whether that slot's prescribed action has completed. A neutral-status wrapper of comparable length is a control. No semantic rewriting or supposedly perfect fact/directive splitter is permitted.

For the narrow initial study, the reviewer is explicitly contracted to advise only on the pending single-action slot. Every arm uses that same reviewer contract and raw Q. The scope comes from the public review interface, not from hidden task predicates. A controller may label that slot consumed after the exact accepted action has an ordinary public success result. It must not infer that a broader user goal is fulfilled. If the call errors or returns a public failure, the slot remains unresolved. State changes necessary to establish success must use ordinary public tool evidence already available to the policy.

Example consumed header, to freeze verbatim with its neutral control:

> This reviewer output concerned decision slot {slot_id}. The selected action {call_id} has returned successfully. Its recommendation for that slot is complete. The text below remains historical reviewer reasoning; it is not a new continuing user requirement. The user's original requirements and all actual tool results remain in force.

This header is an intervention, not an innocuous annotation. Its effect is precisely what C versus P measures. A public success response establishes that the specified call completed, not that the reviewer was substantively right or that its diagnostic explanation is true. For stronger “useful correction” claims, require the independently declared local-repair stratum as well.

Recommended role of arms in a high-standard paper:

- P/A measures information-plus-guidance exposure and has substantial prior overlap.
- P/R measures persistence versus a fixed one-generation TTL; it is a context-exposure treatment.
- **P/C is the indispensable applicability-status contrast with reviewer words retained.**
- C/R tests whether status marking retains useful explanatory information that deletion loses.

R remains the concrete cheap baseline specified above; it should not be renamed an event-aware scope-calibration algorithm. C is also a simple inference-time design, not a claimed new architecture. Before live study registration, select one primary deployment comparison based on the precisely supported review interface. If C's action-local contract can be faithfully implemented, prefer C versus P as the primary policy comparison and retain R as the fixed-TTL baseline. If it cannot, keep the planned P/R comparison but narrow the scientific claim to exposure management. This is a pre-experiment design decision, never an outcome-dependent choice.

### What would make the question substantive

Require evidence for the following pattern, rather than only a positive expiration effect:

1. The review action is genuinely useful on a declared local defect, not just an accepted READ; alternatively state clearly that the study covers accepted proposals only.
2. The same correction, outcome, factual history, and user goals precede each lifetime/status treatment.
3. A same-word scope/status treatment changes preservation/completion, ruling out the claim that only deletion has been shown useful.
4. Benefits are specific to guidance whose local purpose has completed; they do not arise indiscriminately when unresolved or durable guidance is suppressed.
5. Simple task reminders, fixed TTL, ordinary context shortening, and public readback baselines fail to explain the entire benefit.

These criteria are demanding because the close prior art is strong. Failure to satisfy them does not make a careful experiment worthless, but it prevents the stronger mechanism claim.

### Bounded mixed-scope extension

Do not build a broad memory system now. In a second, explicitly separate experiment, annotate reviewer statements before reading outcomes using only their public context:

- Local action: “look up this line instead of that customer.” Discharge event is that exact public call's successful result.
- Until-condition: “check identity before changing the service.” It remains applicable until the ordinary public transcript contains the prescribed evidence. Unsupported or ambiguous conditions remain unresolved; no hidden database truth decides this.
- Continuing guidance: a still-relevant diagnostic strategy or a restatement of an existing user constraint. The underlying user constraint is never retired with the review packet.

Record source provenance separately from temporal applicability. A reviewer cannot create permission to disregard user instructions, and an echo of a user rule does not own that rule. In the initial study, keep original user requirements equally accessible in every arm. Include a matched persistent-reminder baseline to test whether a benefit is merely better recall of those requirements.

For a later selective policy, use only caller-declared, publicly checkable scopes; default to keeping ambiguous guidance. A model-inferred scope policy would be a separate, costed condition with its own errors. Compare it to always-retain, fixed-TTL, always-drop, and exact-text consumed-status baselines. A policy that prevents loss by prematurely suppressing unresolved useful guidance must pay for the resulting task failures.

Do not interpret the observational difference among scope categories as a randomized causal effect of “being fulfilled.” Categories can differ in difficulty and content. The randomized contrast is the exposure/status policy within each predeclared category. A synthetic factorial suite can isolate scope conditions, but its results remain constructed mechanism evidence rather than natural prevalence.

### Specific new kill condition

If scope/status effects are absent at useful precision, or any gain is reproduced by generic context shortening without a completion advantage, the project does not support a special consumed-reviewer mechanism. The fallback is the narrower surrogate-validity question in the novelty audit: whether local review acceptance changes the ranking of reviewer configurations once delayed preservation, completion, and cost are evaluated. That fallback requires its own predeclared held-out ranking experiment; it must not be improvised after unsuccessful hypothesis tests.

## Local evidence read for this blueprint

- reviewer_pilot/REPORT.md and INDEPENDENT_REVIEW.md
- reviewer_pilot/task_audit.json and selected_task.json
- reviewer_pilot/upstream/src/tau2/domains/telecom/tools.py and user_tools.py, source inspection only
- reviewer_interventions/SPEC.md, REPORT.md, DEVIATIONS.md
- controller_receipt_adapter/PLAN.md and REPORT.md

All paths above are internal research provenance, not public download links. Frozen source and evidence were not modified.
