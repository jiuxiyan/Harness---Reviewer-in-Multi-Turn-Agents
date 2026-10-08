# Evolution of the reviewer advice lifetime proposal

This document explains the historical narrowing of the question. The final manuscript in `paper/manuscript.txt` and [current protocol](../protocol/current_protocol.md) govern the current design.

The current project is a pre-experiment proposal about a narrow empirical question: after a reviewer-recommended local action has executed, does the continuing applicability or exposure of that review change later preservation of still-required goals?

No reviewer-harm rate, lifetime-policy benefit, cost advantage, or formal LLM result has been established. The historical branches in [Research history](RESEARCH_HISTORY.md) address different questions. Their failures and negative findings motivate tighter controls; they do not validate this hypothesis.

## Why the question narrowed

Broad contribution claims were rejected. Harmful criticism, correct-to-incorrect revision, multi-turn reviewer disruption, preservation of constraints, and evidence-backed workflow control already have substantial prior art. State restoration, paired continuation, provenance receipts, goal ledgers, and expiring context are enabling techniques, not sufficient novelty claims.

The narrower distinction is between three things that need not change together:

1. A user requirement that remains in force.
2. Factual evidence from an executed action.
3. A reviewer's recommendation whose local purpose may already be complete.

An instruction can be inapplicable after execution while the facts that originally justified it remain accurate. Marking that recommendation consumed must not retire the user's requirement, erase actual tool observations, or imply that the reviewer had authority to change the task.

The intended comparison holds the same accepted reviewer action, its actual result, environment state, original requirements, and remaining budgets fixed before varying later review exposure or status. Successful execution alone is weaker than a useful repair: the tool may accept an action without that action correcting a genuine defect. Any stronger repair claim requires an independently declared local-defect criterion.

## The proposed P R C comparison

The planning record developed from a persistent-versus-retired packet comparison into a stronger design that also preserves the exact reviewer wording while changing its declared status.

- **P, persistent:** the captured reviewer packet continues to appear in subsequent actor requests in the declared role and position.
- **R, fixed exposure:** the same packet is shown for one post-intervention actor generation, then ceases to be re-presented. Factual receipts, original observations, and native conversation remain. R removes the whole packet, including potentially useful explanatory information, and is therefore an exposure-management treatment.
- **C, consumed status:** the exact reviewer text remains present, with a factual header identifying the local decision slot and whether its specified action has completed. A comparable neutral header controls part of the presentation change. C tests the effect of explicitly marking applicability while retaining the words.

C does not amount to a semantically inert annotation: its status header is the treatment. A public success response can establish that the specified call completed; it cannot prove the recommendation was substantively right or a broader user goal was satisfied. Failed or unresolved calls cannot simply be marked consumed.

The final protocol fixes C versus P as the primary comparison, with R as the whole-packet removal baseline. An earlier P/R-first possibility is historical design context, not an interchangeable current endpoint. Any future change requires a separate prospectively declared protocol revision.

## Outcomes and information boundaries

The primary preservation endpoint is terminal unresolved loss of a previously achieved requirement that remains applicable. Temporary loss followed by restoration is reported separately unless the requirement explicitly must hold continuously. Initially true properties are a distinct maintained-state stratum, rather than automatically counted as achieved progress. Nested predicates must not turn one failure into multiple independent observations.

Completion, unmet remaining goals, recovery, error termination, latency, and cost are necessary companion outcomes. A policy that avoids loss by abandoning the task cannot be declared beneficial solely from a preservation score.

The actor and reviewer receive public conversation and tools, actual tool results, and factual controller receipts. Private goal predicates and cloned benchmark state belong to the evaluator. They must not silently become a deployment trigger, a discharge signal, or an oracle fallback. Evaluator-selected diagnostic prefixes and public-triggered end-to-end episodes answer different questions and need separate reporting.

Repeated continuations from one task are clustered observations, not new independent tasks. A single successful control and failed treatment pair cannot establish individual causal harm under stochastic continuation. Captured raw reviewer proposals must be retained, including malformed, unchanged, and out-of-scope outputs, under prespecified fallback rules rather than redrawn until useful.

## Necessary controls and stopping decisions

A useful study must compare against no review, matched self-reconsideration, and a same-action factual receipt without the full critique. Uninstrumented and instrumented no-review arms check whether the receipt format itself changes behavior. Other controls include generic context shortening, a public task reminder, matched role/position/length wrappers, ordinary evidence refresh, and continued-validity cases where the advice should remain active.

P/R/C share the exact first exposed actor request, one valid actor response and intervening native events, then restore freshly at the next actor boundary. C changes only the matched status header after the declared target call actually returned successfully and that valid actor response occurred. P retains the neutral header and R stops reattaching both packet and header. Remote API randomness is not made identical merely by cloning local state. Provider format and restart behavior require their own checks before a behavioral claim is possible.

A strong result would show a useful preservation/completion trade-off under the same correction and evidence, a status-only effect beyond deletion, and specificity to genuinely completed local guidance. If ordinary shortening or a task reminder explains the entire effect, the conclusion should be narrower. If retaining review helps, that benefit must be reported. A wide nonsignificant interval is inconclusive rather than evidence of equivalence.

Stop or narrow the claim if natural eligible prefixes are too rare; if results depend only on authored stress fixtures; if the intervention loses useful unresolved guidance; if instrumentation or hidden-state leakage compromises the comparison; or if practical precision is insufficient. Any alternative study of whether local reviewer scores misrank downstream utility requires its own held-out, predeclared design. It is not a post hoc rescue of the lifetime hypothesis.

## Closest related work and limits on originality

The following distinctions come from the recorded primary-source audit through 7 October 2026. They describe inspected versions and do not prove absence of an equivalent experiment elsewhere.

- [Reinforced Agent](https://arxiv.org/html/2604.27233v1) already studies inference-time review for tool calling and discusses harmful multi-turn configurations. Reviewer harm beyond a single call is not a new discovery proposed here.
- [Accurate Failure Prediction in Agents Does Not Imply Effective Failure Prevention](https://arxiv.org/html/2602.03338v1), titled with “The Intervention Paradox” in its full text, separates recovery from disruption and compares visible feedback with silent control actions. An action-held-fixed critique/no-critique ablation alone is insufficient distinction.
- [CAVE-Bench](https://arxiv.org/html/2609.32616v1) studies damage to verified correct work under false accusations and evaluates evidence rules and gates. The candidate distinction here is a legitimate local recommendation after its execution, rather than an unsupported accusation. Changing only the kind of feedback would not establish a substantial contribution.
- [Closing the Feedback Loop](https://arxiv.org/html/2606.17591v1) deactivates stale verbal rules while retaining their evidence. Its cross-episode governance strongly overlaps the separation of retained knowledge and active guidance. The proposed question instead concerns local completion within an unfinished episode.
- [Plans Don't Persist](https://arxiv.org/html/2606.22953v1) uses paired replay with fixed action/observation histories to study plan removal. Context-removal pairing is established. Independently sampled behavioral continuations after an identical completed recommendation are the proposed measurement setting here.
- [Authorization Closure Graph](https://arxiv.org/html/2609.32428v1) separates evidence from authorization and consumes execution allowances. Single-use authority is existing machinery. Reviewer advice is not authenticated user permission; the current proposal concerns its continuing linguistic effect and utility.
- [AgentSentry](https://arxiv.org/html/2602.22724v1) compares context interventions from matched runtime states and makes instruction-bearing content non-actionable while preserving factual content. This is a particularly strong overlap. A useful new study must isolate the transition of legitimate advice from applicable to completed and measure later preservation, rather than claim matched context purification itself as new.
- [PolicyGuide](https://arxiv.org/html/2608.19861v1) uses grounded persistent workflow state and verification. A goal ledger or runtime guard is therefore a credible baseline, not a distinctive contribution by itself.
- [Concord](https://arxiv.org/html/2610.05281v2) manages source-linked observations when world state changes. Factual freshness differs from completed instructional scope: a consumed recommendation need not contain stale facts. This distinction is a hypothesis to test, not an established mechanism.
- [AgentBoard](https://arxiv.org/html/2401.13178v2) already tracks intermediate goal progress. Current predicate survival can complement peak progress, but per-step subgoal measurement is not new.

The proposal should therefore be presented as a bounded empirical study of applicability and retention, with credible negative outcomes allowed. It cannot claim to invent harmful-feedback analysis, evidence-preserving purification, consumed authority, causal replay, goal tracking, or general context expiry.
