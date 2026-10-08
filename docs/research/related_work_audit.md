# Primary-source novelty audit: reviewer intervention and preservation

**Audit cutoff and retrieval date:** 7 October 2026 (UTC).  
**Status:** pre-experiment research assessment. Public paper metadata and the relevant full-text sections were inspected; reported paper results were not independently reproduced.

## 1. Decision

**The original broad proposal does not clear novelty.** “Reviewers can hurt multi-turn agents,” “a locally plausible correction can damage correct work,” “preserve established constraints,” and “use an evidence ledger plus a gate” are already substantially covered. The particularly important collisions are Reinforced Agent [R1], The Intervention Paradox [N1], CAVE-Bench [N2], PolicyGuide [R5], and When “Must” Becomes “Maybe” [N3]. The earlier claim that reviewer harm had only been examined on BFCL is too strong: the specific helpfulness/harmfulness table in [R1] is BFCL-only, but its multi-turn section explicitly discusses reviewer-induced failure categories and worse outcomes in some configurations.

**A narrower candidate question survives this bounded search, with significant uncertainty:**

> After a reviewer-directed local action has already executed, does continuing to present its directive as active advice change the probability of later losing an achieved, still-required environment goal, compared with marking that directive consumed while preserving the same factual execution evidence?

This is a candidate **empirical question about the temporal scope of a particular source of guidance**, not a claim to have invented context management, instruction expiration, state restoration, causal contrasts, or preservation gates. A high-level conference contribution would require a reproducible effect or a useful sharply bounded negative result, credible natural incidence, strong controls, and a practical policy that retains useful feedback. The current offline software establishes none of those empirical claims.

The bounded literature review did not locate a directly matching experiment that simultaneously (i) begins after an identical reviewer-directed action and result, (ii) changes only the subsequent lifetime/status of its directive, (iii) keeps execution evidence and user goals available, and (iv) measures later unresolved loss of currently achieved environment predicates. **This is a search finding, not proof of absence or a justified “first” claim.** The nearest remaining overlaps are feedback-memory governance [N5], feedback-visible versus silent control [N1], consumable authority [N7], source-linked stale-context reconciliation [N8], replay-paired context diagnostics [N6], and especially evidence-preserving directive purification at matched runtime states [N15].

## 2. Evidence boundaries and search method

- Verified nine initial arXiv identifiers against their primary abstract pages and inspected the corresponding full text. All nine matched the reviewed subject, although several initial abbreviations were not the paper titles.
- Used explicit versioned HTML links. Notable updates before the cutoff: AgentProcessBench v2 (1 June); RECAP v4 (31 August); Counterfactual Rollout Replay v3 (3 October); Concord v2 (6 October). Initial release and consulted-version dates are distinguished below.
- Extended searching across harmful correction, critique contamination, operational constraint preservation, persistent advice, context scope, stale observations, memory governance, and authority consumption. Citation-following surfaced additional close work that was absent from the initial list.
- An author’s arXiv comment about venue acceptance is not independent venue verification. References below are safely citable as preprints unless a publisher record is separately checked.
- “Not studied” below means no corresponding experiment or object was located in the inspected sections, not that an algorithm could never address it.
- The source-grounded descriptions report what the papers actually define or test. The assessment of whether an extension is valuable, and the proposed designs, are this audit’s inferences.

## 3. Related-work matrix: nine initial candidates

| Reference and inspected evidence | What is already covered | Precise boundary for this project |
|---|---|---|
| **[R1] Reinforced Agent**. §§2.1, 4.1–4.3; Tables 2–4; Appendix A.4. | Separate reviewer inspects provisional calls, returns feedback, or selects candidates without retraining the actor. Formal help/harm table uses BFCL. Multi-turn τ² results and error analysis already describe negative effects of review. | No located same-prefix, repeated-continuation study of an immediately acceptable intervention followed by unresolved loss of an achieved goal. Feedback lifetime is not isolated. Do not claim multi-turn harm itself is new. |
| **[R2] SEVRA**. §3; §§4–5; Appendices C–E. | Accept/continue/active-verify allocation, correct-to-wrong transitions, recoverability-aware gates, shared initial attempts, cost accounting, and stronger initial-budget controls. Uses a frozen solver, but trains gates. | Answer revision rather than an evolving tool environment; not an achieved-state preservation endpoint. “Frozen base model” alone is not a novelty distinction, and its gate-training recipe violates a strict no-training project constraint. |
| **[R3] SAVeR**. §§3.1, 3.4–3.5; §4.1; Table 1. | Audits evidence support of reasoning steps, localizes violations, performs constrained minimal repairs, keeps unaffected reasoning stable, and checks explicit acceptance criteria before commitment. | The six reported datasets are QA/fact-verification tasks. “Minimal repair preserves unaffected content” is occupied; external-state predicate survival after later tool interactions is a different measurement object. A new belief-repair label would not be enough. |
| **[R4] AgentProcessBench**. §§3.1–3.3, 4.2–4.3; Tables 2, 5. | Human-labeled correct/neutral/incorrect tool-agent steps, error-propagation rules, first-error evaluation, and process-assisted trajectory selection. Includes τ² trajectories. | Annotated process quality is not randomized reviewer effect. Existing trajectories alone cannot establish outcomes under an unexecuted intervention or its effect on future goal survival. |
| **[R5] PolicyGuide**. §§3.1–3.4; Algorithm 1; Appendix A. | Policy workflow graphs, code-owned persistent request state, tool-result grounding, request reconciliation, per-turn verification and remediation, and explicit action-local versus workflow-level coverage. | An obligation ledger, persistent verifier state, or “look beyond one call” is insufficient novelty. The inspected work does not isolate the lifespan of a consumed reviewer directive or reviewer-induced reversal of an achieved predicate. |
| **[R6] How Do Agent Harnesses Create Value?** §§3.1–3.5, 4.3, 6.4, 8.2; Appendices D–F. | Separates planning information, completion correctness, release acceptance, and cost. Fixed–Sham guidance comparison and read-only terminal verification reveal false rejection as well as avoided false pass. | Terminal rejection is not necessarily environmental damage. Its proposed follow-up on repair after rejection underscores that a reject/repair/preserve trajectory is a different endpoint; component isolation and liability tradeoffs already exist. |
| **[R7] CVT-RL**. §3.2, Eq. 4; §3.4; Tables 4–5. | Frozen-policy counterfactual continuation, distinct intervention families, pre-rollout validity gates, selection correction, uncertainty and leakage diagnostics, used for RL credit. | No new estimator should be claimed for paired intervention rollouts. The applicable contribution here would be a new treatment and endpoint with fixed APIs, not relabeling counterfactual credit. |
| **[R8] Counterfactual Rollout Replay (CRR)**. Consulted v3: §§3, 4.1–4.3; Proposition 1; Appendix P. | Executable state forks, alternative-action continuations, proposal-dependent return contrasts, explicit future-sampling uncertainty and total replay cost, used in SWE-agent training. | Restore/fork/replay is infrastructure, not scientific novelty. Deterministic environment replay does not make stochastic actor/user continuations deterministic or identify individual harm from one pair. |
| **[R9] Risk-aware intrinsic self-correction**. §§2.2–2.3, 3.2, 4. | Transition accounting separates recovery from harmful flips, shows net gain can hide damage to correct answers, and compares unconditional versus gated revision. | Static answer correctness, not persistent multi-goal tool state. A proposed gain-minus-harm decomposition is algebra already covered, not a theorem contribution. |

## 4. Additional collisions and lifetime-specific prior art

| Reference and inspected evidence | Overlap and boundary |
|---|---|
| **[N1] The Intervention Paradox**. §3; §5.3; §6; Appendix B. | Critic-triggered rollback/append can disrupt successful trajectories. Crucially, §5.3 compares visible warning text with the same control action performed silently, and also tests richer feedback. Thus an action-held-fixed “with versus without critique” ablation is already anticipated. A post-fulfillment lifetime treatment with unchanged evidence and later predicate survival is narrower. |
| **[N2] CAVE-Bench**. §§3–5, especially §5.2 and §5.4; Appendix B.1. | Verified correct work, retained supporting history, later false accusation, downstream replayed damage, and harness mitigation. Strong collision for “preserve correct work against harmful correction.” Its deliberately opaque false-accusation setting differs from naturally generated, useful reviewer guidance whose immediate correction has already executed. Avoid implying that all destructive corrections begin with locally false feedback. |
| **[N3] When “Must” Becomes “Maybe”**. §§3–4, 6.2–6.3; Tables 2–3. | Conditions on correct upstream blocker identification, changes the handoff artifact, and measures operational preservation separately from forbidden endpoint action. Restores structured fields and holds artifacts fixed during containment comparisons. This occupies generic state-preservation and representation-versus-execution claims. Its controlled single-action blocker relay does not establish ongoing achieved-goal survival after consumed advice. |
| **[N4] Why Retrying Fails**. §§2.2, 3.3, 7.2–8. | Models a worse error rate after failed context-bearing attempts, recommends clean restarts, and fits aggregate retry outcomes. It does not randomize otherwise identical histories to identify contamination. Treat as a modeling precedent, not evidence that retaining a particular critique causes harm. The full text also contains inconsistent inequality signs in §3.3; do not import its theorems uncritically. |
| **[N5] Closing the Feedback Loop**. §§3.1–3.3. | Governs cross-episode verbal insights: keeps evidence, deprecates stale rules rather than deleting their history, and injects active rules. This strongly overlaps “retain evidence but retire instructions.” Its adaptation criterion uses accumulated experience, whereas this proposal would test a directive’s consumed local purpose after one execution. That narrower empirical distinction needs direct experiments. |
| **[N6] Plans Don’t Persist**. §3.3. | Replay pairing holds action/observation history fixed while removing plan content for representation diagnostics; stripped-branch outputs do not drive the environment. Paired context removal is established. The prospective outcome here is independently sampled subsequent behavior under different directive lifetime policies. |
| **[N7] ACG**. §3.2; Appendix A. | Separates evidence from authority, scopes approved execution, consumes allowances on dispatch, and prevents new candidate IDs/fresh evidence from restoring spent permission. Single-use authority is already a concrete agent runtime concept. Reviewer advice is ordinarily not user authorization: any contribution must concern its lingering linguistic influence and utility, not merely add a consumable token. |
| **[N8] Concord**. §§3.1–3.4, 4.1–4.4. | Source-linked observations have validity metadata and may be refreshed, annotated, suppressed, or re-read after changes. This defeats a broad “expire stale context” novelty claim. The paper explicitly leaves revision of derived summaries/plans/decisions outside its prototype. Here a directive can be consumed even when its original factual premise remains true; world-state freshness and instruction applicability must be separated. |
| **[N9] SARA**. §§4.2–4.4, 5.3. | Preserves action-origin provenance across steps, separates authorized successful execution evidence from authority, and prevents history from laundering an external instruction into permission. Its ablations test persistent-origin and no-history-promotion mechanisms under attacks. A benign reviewer-lifetime study has a different treatment, but generic provenance separation is established. |
| **[N10] RECAP**. Consulted v4: §§2–4; Appendices H, L. | Constraint-level forgetting under add/edit/delete schedules, including rule-only validators and active-constraint information controls. Regression under changing instructions and prompt adaptation is established. Its object is prompt-level compliance on new interactions, not survival of environment goals achieved during an unfinished episode. |
| **[N11] MRMS**. §§4.1–4.3, 5–6. | Memory objects carry scope, provenance, revision status and temporal commitments; storage and selection are distinct. Controlled pre-generation memory selection is the primary diagnostic. A typed receipt with scope and status is therefore an engineering choice, not an independently new abstraction. |
| **[N12] Cordon**. §§2–4, 6.5. | Task-scoped semantic transactions bind lineage, local state, staged effects and delegated authority before commit. Per-call validity need not establish valid composed execution. The system does not claim complete semantic correctness outside mediated effects. A broad local-checks-versus-global-effects framing would overlap heavily. |
| **[N13] Helpful Agent Meets Deceptive Judge / WAFER-QA**. §§3.1–3.4, 4.4–5.2. | Correct-answer corruption under misleading critique, feedback intent/knowledge, and repeated feedback precede the current proposal. QA answer corruption differs from persistent environmental loss, but contamination by critique is not a new phenomenon. |
| **[N14] AgentBoard**. §3.1. | Fine-grained multi-turn progress measurement is established. Its maximum-so-far progress definition is monotone, making current predicate survival a potentially useful complementary endpoint. Do not claim that intermediate goal tracking itself is new. |
| **[N15] AgentSentry**. §§4.2–4.6; Appendices B.2–B.4. | Counterfactual dry runs hold dialogue/runtime prefix fixed and change mediator context; instruction-bearing spans become non-actionable while factual content is retained. Online purification enables continued execution. Thus matched context interventions and evidence-preserving purification already exist. The prospective distinction is legitimate useful advice becoming consumed after an identical successful repair, rather than malicious tool content and next-action takeover. |

## 5. What may be claimed in the pre-experiment draft

### Safe present-tense claims

1. The project proposes to study **post-fulfillment feedback lifetime** in fixed-model tool workflows.
2. It distinguishes successful execution of a local recommendation from the continued applicability of that recommendation as advice.
3. It proposes paired treatment-policy comparisons from the same saved state, with explicit repeated continuations and private evaluation.
4. It measures **unrecovered terminal loss of a previously achieved, still-required goal**, alongside official terminal success, temporary loss, recovery, cost, and task completion.
5. It has narrowly tested offline serialization, replay, representation, and receipt infrastructure. Those tests establish implementation properties only.

### Claims that must wait

- That natural reviewer corrections frequently cause delayed loss.
- That a particular context treatment is causally harmful across tasks or models.
- That expiring advice improves performance, is cost-effective, or beats a competent preservation baseline.
- That the effect is specifically caused by normative authority rather than information removal, length, salience, role, or position.
- That the project is the first to study any broad class of harmful feedback, scope control, or correct-work preservation.

### Rejected contribution labels

“A novel helpfulness–harmfulness metric,” “a novel causal fork estimator,” “the first multi-turn reviewer harm study,” “the first preservation ledger,” “a general guarantee from local checks,” and “the first context expiration mechanism” are not defensible from this audit.

## 6. Narrow formulation A: after the correction, retire the directive?

**Question.** Once a local reviewer directive has been fulfilled, does its continued active status affect later goal preservation independently of the already executed local action?

**Scientific object.** A directive is a recommendation tied to a particular action, evidence item, task scope and discharge condition. It can be historically accurate yet no longer applicable. Do not conflate its discharge with factual invalidation or user-goal deletion.

**Minimal treatment controls.** Start comparisons from an identical post-action checkpoint, including user state, tool results, remaining budgets and executed history. Use the same captured reviewer packet and immutable evidence. Compare:

- Persistent packet, in its normal actor-visible role and position.
- The exact same packet marked consumed after its declared target, with its text still present. This tests an applicability/status policy without deleting information.
- Directive omitted from future actor requests after fulfillment, while retaining the same factual receipt and provenance. This changes information exposure and must be described as such.
- An equally long neutral wrapper/status control, plus an unrelated-packet expiry control, to probe instruction length and generic context cleanup.
- Cases where the advice remains relevant or its discharge condition has not occurred. A policy that drops useful continuing guidance must pay for the resulting losses.

If the current architecture exposes advice only after executing the replacement action, say exactly that. Do not call it a natural actor-followed correction without an arm in which the actor actually receives and follows it. If “one-slot exposure” is introduced, define the slot and branch after it; otherwise differing pre-checkpoint actor text can contaminate the comparison.

**What would distinguish the result from simple history ablation?** Status-only effects with the same words; specificity to fulfilled versus unresolved directives; actual event-triggered benefits beyond fixed TTL or generic truncation; failures traceable to reuse outside the directive’s declared scope; and an effect on ongoing external-state goals under independent continuations. These are empirical requirements, not assumptions.

**Failure criterion.** If gains appear only when text is deleted, match ordinary context-pruning baselines and report an exposure-management result. If gains vanish with exact-message/position controls or there is no natural eligible mass, reject the stronger lifetime mechanism. If persistent advice wins, report the retention benefit instead of redefining success.

**Publication assessment.** Best available candidate, but conditional. The conceptual machinery is familiar; the value must come from a convincing, useful empirical separation and a validated deployment policy.

## 7. Bounded formulation B: when are local acceptance scores misleading?

**Question.** Do reviewer configurations that look better under immediate executable validity or local repair success rank differently under later preservation and complete-task utility?

This is a measurement paper, not a claim that a local validator guarantees the future. Freeze prefixes, proposal draws, local checks and treatment candidates before observing suffixes. Report the joint distribution of immediate validity, achieved-goal survival, unmet-goal completion, official terminal success and cost. Test reviewer/prompt rankings on held-out task families and models, with uncertainty. Compare simple no-review, matched self-revision, ordinary review, and the strongest feasible preservation-aware baseline.

The useful result would be a reproducible, practically consequential surrogate failure or rank reversal that changes reviewer selection, not merely discovering a nonzero error rate. The empirical comparator is both [R1] and [N1]; the preservation endpoint must add predictive or decision value beyond their aggregate disruption/recovery accounting. This route remains viable even if directive expiration is not the mechanism.

**Kill condition:** later preservation is almost fully explained by immediate invalidity, insufficient budget, or ordinary task failure, or the extra endpoint does not change any well-powered reviewer selection conclusion. A single constructed witness is inadequate.

## 8. Bounded formulation C: useful feedback retention under scope changes

**Question.** Can a non-trained controller keep reviewer evidence and useful durable guidance while expiring only directives whose local obligations have been discharged, and outperform both always-retain and always-drop policies across mixed scope conditions?

This formulation makes the hard part the **utility–preservation tradeoff**, not adding a field named “scope.” Include mixed directive types: next-action only, until a public postcondition, and truly task-wide. Compare explicit caller-declared scope, model-inferred scope, fixed expiry, no expiry, status-only labeling, and a standard workflow/obligation ledger. Charge scope extraction, check calls and any readbacks. Discharge detection must use public tool evidence; the private benchmark predicate cannot decide what the deployed controller sees.

The main novelty burden is to show generalization to unseen tools/goal compositions and robustness to wrong scope declarations while preserving useful feedback. This overlaps [N5], [N7], [N8], [N15] and [R5] as a systems composition. It warrants a paper only if the empirical policy tradeoff is substantial and the simpler baselines genuinely fail. It is not cleared as a new general memory architecture.

## 9. Local infrastructure: exact scientific limits

Read: `reviewer_pilot/PHASE1_REPORT.md`, `reviewer_pilot/REPORT.md`, `reviewer_interventions/REPORT.md`, and `controller_receipt_adapter/REPORT.md`.

- The current backend is pinned τ³ Telecom code, package namespace `tau2`, commit `4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699`. Naming it simply historical τ² risks confusing benchmark versions.
- Seven scripted backend witnesses demonstrate staged predicate transitions and fresh restoration. They do not estimate natural prefix frequency, reviewer behavior, or population effects. Connectivity/speed predicates are nested, so the slice cannot establish independent multi-goal interference.
- The intervention and receipt adapters use scripted proposals and continuations. Current A/P branches share a changed READ and differ in actor-visible captured critique. That is useful instrumentation, but [N1] already motivates feedback-visible versus silent effects.
- The receipt adapter reports 37 named tests and six fresh-process restart checks. Its persistence check spans two scripted actor boundaries; no provider serialization or actual model behavior is established.
- The currently inspected system has no tested event-based directive-expiration policy and no real-model estimate of any proposed endpoint. A paper must not convert fixture assertions into scientific findings.

## 10. Bibliographic record: nine initial candidates

These exact primary links and dates were verified on the source pages. All records below use 2026 as publication year and `arXiv` as the safe publication container.

- **[R1]** Anh Ta, Junjie Zhu, Shahin Shayandeh. *Reinforced Agent: Inference-Time Feedback for Tool-Calling Agents*. arXiv:2604.27233v1. First/consulted version: 29 April 2026. [Metadata](https://arxiv.org/abs/2604.27233); [full text](https://arxiv.org/html/2604.27233v1).
- **[R2]** Sajib Acharjee Dip, Dawei Zhou, Liqing Zhang. *Think Again or Think Longer? Selective Verification for Budget-Aware Reasoning*. arXiv:2606.19808v1. 18 June 2026. [Metadata](https://arxiv.org/abs/2606.19808); [full text](https://arxiv.org/html/2606.19808v1).
- **[R3]** Wenhao Yuan, Chenchen Lin, Jian Chen, Jinfeng Xu, Xuehe Wang, Edith Cheuk Han Ngai. *Verify Before You Commit: Towards Faithful Reasoning in LLM Agents via Self-Auditing*. arXiv:2604.08401v1. 9 April 2026. [Metadata](https://arxiv.org/abs/2604.08401); [full text](https://arxiv.org/html/2604.08401v1). ArXiv comments state ACL 2026 Main acceptance; not independently venue-verified here.
- **[R4]** Shengda Fan, Xuyan Ye, Yupeng Huo, Zhi-Yuan Chen, Yiju Guo, Shenzhi Yang, Wenkai Yang, Shuqi Ye, Jingwen Chen, Haotian Chen, Xin Cong, Yankai Lin. *AgentProcessBench: Diagnosing Step-Level Process Quality in Tool-Using Agents*. arXiv:2603.14465v2. First: 15 March 2026; consulted revision: 1 June 2026. [Metadata](https://arxiv.org/abs/2603.14465); [full text](https://arxiv.org/html/2603.14465v2).
- **[R5]** Seongjae Kang, Taehyung Yu, Sung Ju Hwang. *PolicyGuide: From Guarding One Action to Guiding the Whole Workflow for Policy-Compliant LLM Agents*. arXiv:2608.19861v1. 20 August 2026. [Metadata](https://arxiv.org/abs/2608.19861); [full text](https://arxiv.org/html/2608.19861v1).
- **[R6]** Yukun Zhang, Kemu Xu, Yishen Chen. *How Do Agent Harnesses Create Value? Planning Information and Release Control in Stateful LLM Agents*. arXiv:2609.20474v1. 17 September 2026. [Metadata](https://arxiv.org/abs/2609.20474); [full text](https://arxiv.org/html/2609.20474v1).
- **[R7]** Renwei Meng. *Policy-Conditioned Counterfactual Credit for Verifiable Reinforcement Learning of Long-Horizon Language Agents*. arXiv:2606.05263v1. 3 June 2026. [Metadata](https://arxiv.org/abs/2606.05263); [full text](https://arxiv.org/html/2606.05263v1).
- **[R8]** Yuanhao Li, Hongbo Wang, Xuhong Chen, Yiming Cao, Xunzhu Tang. *Counterfactual Rollout Replay: Forkable Environments as Free Process Rewards for Software Engineering Agents*. arXiv:2609.33875v3. First: 27 September 2026; consulted revision: 3 October 2026. [Metadata](https://arxiv.org/abs/2609.33875); [full text](https://arxiv.org/html/2609.33875v3). ArXiv comments state NeurIPS 2026 acceptance; not independently venue-verified here.
- **[R9]** Tianzhu Zhang. *When Should LLMs Trust Their Own Revisions? A Risk-Aware Study of Intrinsic Self-Correction*. arXiv:2609.35832v1. Source-reported submission date: 23 September 2026. [Metadata](https://arxiv.org/abs/2609.35832); [full text](https://arxiv.org/html/2609.35832v1).

## 11. Bibliographic record: additional primary papers

- **[N1]** Rakshith Vasudev, Melisa Russak, Dan Bikel, Waseem Alshikh. *Accurate Failure Prediction in Agents Does Not Imply Effective Failure Prevention*. arXiv:2602.03338v1. 3 February 2026. The versioned full text prefixes the title with “The Intervention Paradox.” [Metadata](https://arxiv.org/abs/2602.03338); [full text](https://arxiv.org/html/2602.03338v1).
- **[N2]** Xutao Mao, Rui Qian, Longxiang Wang, Xinjian Yi, Mingxuan Li, Linghan Chen, Yudong Gao, Xiang Zheng, Cong Wang. *“You’re Right, Let Me Fix It”: How LLM Agents Damage Correct Work When Falsely Accused*. arXiv:2609.32616v1. 26 September 2026. [Metadata](https://arxiv.org/abs/2609.32616); [full text](https://arxiv.org/html/2609.32616v1).
- **[N3]** Yiheng Sun, Huifei Wang, Yancheng Zhu, Zhenyu Li, Zebin Zhao, Yifan Yuan. *When “Must” Becomes “Maybe”: Constraint Weakening in LLM Agent Workflows*. arXiv:2608.24569v1. 25 August 2026. [Metadata](https://arxiv.org/abs/2608.24569); [full text](https://arxiv.org/html/2608.24569v1).
- **[N4]** Zhanfu Yang. *Why Retrying Fails: Context Contamination in LLM Agent Pipelines*. arXiv:2605.08563v1. 8 May 2026. [Metadata](https://arxiv.org/abs/2605.08563); [full text](https://arxiv.org/html/2605.08563v1).
- **[N5]** Yanwei Cui, Xing Zhang, Yulong Zhang, Li Shao, Xiaofeng Shi, Guanghui Wang, Peiyang He. *Closing the Feedback Loop: From Experience Extraction to Insight Governance in Verbal Reinforcement Learning*. arXiv:2606.17591v1. 16 June 2026. [Metadata](https://arxiv.org/abs/2606.17591); [full text](https://arxiv.org/html/2606.17591v1). ArXiv comments state ICML 2026 RLxF Workshop acceptance.
- **[N6]** Aman Mehta, Anupam Datta. *Plans Don’t Persist: Why Context Management Is Load Bearing for LLM Agents*. arXiv:2606.22953v1. 22 June 2026. [Metadata](https://arxiv.org/abs/2606.22953); [full text](https://arxiv.org/html/2606.22953v1).
- **[N7]** Qingzhuo Wang, CaiYi Wang, Jinglu Meng, Ruiyang Qin, Kunyu Peng, Zhihua Wei, Wen Shen. *Authorization Closure Graph: Minimal Repair for LLM Agents with Evolving User Instructions*. arXiv:2609.32428v1. 26 September 2026. [Metadata](https://arxiv.org/abs/2609.32428); [full text](https://arxiv.org/html/2609.32428v1).
- **[N8]** Yingying Liu, Junzhou Fang, Chenxiong Qian. *When Agent Context Goes Stale: Incoherence in Volatile Agent Context*. arXiv:2610.05281v2. First: 4 October 2026; consulted revision: 6 October 2026. [Metadata](https://arxiv.org/abs/2610.05281); [full text](https://arxiv.org/html/2610.05281v2). ArXiv comments state AgenticOS Workshop at SOSP 2026 acceptance.
- **[N9]** Xiaokun Guo, Zhen Xu, Dongdong Huo, Yanqiu Zhang, Wei Wang, Qinfu Yang, Dongjin Yu, Yu Wang. *When Tool Outputs Become Commands: Separating Action Induction from Runtime Authorization in Tool-Augmented LLM Agents*. arXiv:2608.27146v1. 27 August 2026. [Metadata](https://arxiv.org/abs/2608.27146); [full text](https://arxiv.org/html/2608.27146v1).
- **[N10]** Harsh Deshpande, Kushal Chawla, Sangwoo Cho, William Campbell, Sambit Sahu. *RECAP: Regression Evaluation for Continual Adaptation of Prompts*. arXiv:2606.06698v4. First: 4 June 2026; consulted revision: 31 August 2026. [Metadata](https://arxiv.org/abs/2606.06698); [full text](https://arxiv.org/html/2606.06698v4). Earlier search snippets omit the fifth author and describe four rather than five backbones; use the consulted version.
- **[N11]** Jizhizi Li, Amy Shi-Nash. *MRMS: A Multi-Resolution Memory Substrate for Long-Lived AI Agents*. arXiv:2607.04617v1. 6 July 2026. [Metadata](https://arxiv.org/abs/2607.04617); [full text](https://arxiv.org/html/2607.04617v1).
- **[N12]** Zheng Chen, Hanqing Liu, Duling Xu, Dong Dong, Jialin Li, Bangzheng Pu, Jidong Zhai. *Cordon: Semantic Transactions for Tool-Using LLM Agents*. arXiv:2606.17573v1. 16 June 2026. [Metadata](https://arxiv.org/abs/2606.17573); [full text](https://arxiv.org/html/2606.17573v1). The manuscript displays a 2027 EuroSys template; that is not treated as independently verified acceptance.
- **[N13]** Yifei Ming, Zixuan Ke, Xuan-Phi Nguyen, Jiayu Wang, Shafiq Joty. *Helpful Agent Meets Deceptive Judge: Understanding Vulnerabilities in Agentic Workflows*. arXiv:2506.03332v1. 3 June 2025. [Metadata](https://arxiv.org/abs/2506.03332); [full text](https://arxiv.org/html/2506.03332v1). WAFER-QA is its benchmark name; an alternate venue title has not been primary-source verified in this audit.
- **[N14]** Chang Ma, Junlei Zhang, Zhihao Zhu, Cheng Yang, Yujiu Yang, Yaohui Jin, Zhenzhong Lan, Lingpeng Kong, Junxian He. *AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents*. arXiv:2401.13178v2. First: 24 January 2024; consulted revision: 23 December 2024. [Metadata](https://arxiv.org/abs/2401.13178); [full text](https://arxiv.org/html/2401.13178v2). ArXiv comments state NeurIPS 2024 Oral.
- **[N15]** Tian Zhang, Yiwei Xu, Juan Wang, Keyan Guo, Xiaoyang Xu, Bowen Xiao, Quanlong Guan, Jinlin Fan, Jiawei Liu, Zhiquan Liu, Hongxin Hu. *AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification*. arXiv:2602.22724v1. 26 February 2026. [Metadata](https://arxiv.org/abs/2602.22724); [full text](https://arxiv.org/html/2602.22724v1).

## 12. Bottom line for the paper writer

Lead with the question and planned discriminating experiment, not with an asserted discovery. The strongest current sentence is:

> We study whether reviewer guidance should remain active after its local recommendation has been fulfilled, by varying directive lifetime from matched post-execution states and measuring subsequent preservation of still-required goals.

Use “we propose/test/will evaluate” until real experiments exist. Present state restoration, receipts, field schemas and accounting as enabling methods. Cite the close prior art directly and acknowledge that harmful intervention, governance of stale context, and preservation of correct work are already established research topics.

## 13. Foundational references verified for the draft

These records were additionally checked on primary abstract pages. They support general background; this audit does not use them to claim the narrow gap is absent from all early literature.

- Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank Gupta, Bodhisattwa Prasad Majumder, Katherine Hermann, Sean Welleck, Amir Yazdanbakhsh, Peter Clark. *Self-Refine: Iterative Refinement with Self-Feedback*. arXiv:2303.17651v2. First: 30 March 2023; revision: 25 May 2023. [Primary metadata](https://arxiv.org/abs/2303.17651).
- Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao. *Reflexion: Language Agents with Verbal Reinforcement Learning*. arXiv:2303.11366v4. First: 20 March 2023; revision: 10 October 2023. [Primary metadata](https://arxiv.org/abs/2303.11366).
- Victor Barres, Honghua Dong, Soham Ray, Xujie Si, Karthik Narasimhan. *τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment*. arXiv:2506.07982v1. 9 June 2025. [Primary metadata](https://arxiv.org/abs/2506.07982). Cite this 2025 paper separately from the 2026 pinned τ³ implementation.
