# Reviewer correction, delayed harm, and advice lifetime: primary-source audit

Research cutoff: 2026-10-07. Full primary HTML/PDF text inspected for every main entry. Dates below are first arXiv submission dates unless a venue date is specified. No new empirical model experiments or training were performed.

## Verdict

A generic claim that criticism can damage correct work, that good critics can hurt agents, or that persistent context can cause delayed harm is already substantially covered. The narrower prospective question is more defensible: **after the exact same legitimate correction has executed and its result is verified, does retaining its directive force cause later loss of independently still-required state, compared with consuming the directive while preserving identical factual evidence?** This is a candidate gap, not a verified first. Its strongest challenges are AgentSentry's evidence-preserving directive purification and Closing the Feedback Loop's deactivated-rule/preserved-evidence separation.

Do not claim novelty for paired replay, evidence-preserving purification, single-use permission, inactive-but-retained knowledge, or per-step goal metrics. The prospective contribution needs a specifically post-success, post-repair intervention: same corrected action and readback, unchanged world and user goal, valid original critique, then a controlled change to the critique's continuing applicability followed by independent behavioral rollouts. These are our proposed distinctions, not findings of the cited works.

## Six closest papers

### 1. CAVE-Bench: direct collision with damage to correct state

**Xutao Mao, Rui Qian, Longxiang Wang, Xinjian Yi, Mingxuan Li, Linghan Chen, Yudong Gao, Xiang Zheng, and Cong Wang. “You're Right, Let Me Fix It”: How LLM Agents Damage Correct Work When Falsely Accused. 2026-09-26.** [Abstract](https://arxiv.org/abs/2609.32616); [full text](https://arxiv.org/html/2609.32616v1).

Verified locations: §§3.1–3.4, §4, §5.4, Appendix B.1. Each scored run starts from verified correct state; later accusations may enter through messages, project context, misleading environment, or fabricated history. Future-event replay measures terminal damage against workflow invariants. The paper also tests evidence rules and destructive-action gates.

**Overlap:** later feedback, retained history, correct-state preservation, executable downstream harm, and harness effects.

**Remaining distinction:** false unsupported accusations versus legitimate local repairs whose instructions outlive completion. CAVE does not hold a shared corrected action fixed and manipulate only post-repair directive lifetime. Its conclusion explicitly leaves warranted accusations as an extension, so the extension alone is insufficient novelty.

### 2. Intervention Paradox: direct collision with critic-induced regression

**Rakshith Vasudev, Melisa Russak, Dan Bikel, and Waseem Alshikh. Accurate Failure Prediction in Agents Does Not Imply Effective Failure Prevention. 2026-02-03.** Full-text heading prefixes “The Intervention Paradox.” [Abstract](https://arxiv.org/abs/2602.03338); [full text](https://arxiv.org/html/2602.03338v1).

Verified locations: §3; §§5.3–5.5; Appendices D–F. Compares baseline/intervention matched task outcomes, decomposing recovery and disruption. ROLLBACK restores the previous environment state; APPEND executes the action and appends a warning. It examines richer feedback and repeated-intervention cascades. Appendix E reports its observed regressions concentrate at already-correct steps 0–1.

**Overlap:** critic accuracy does not imply useful control; feedback can cause downstream failure; explicit harmful/beneficial transition accounting.

**Remaining distinction:** episode-level outcomes and intervention policies, rather than a matched successful repair followed by controlled expiry of its advice. Critic training uses Qwen3-0.6B LoRA (§3); that training is not suitable for a no-training prospective implementation.

### 3. Closing the Feedback Loop: closest lifecycle concept

**Yanwei Cui, Xing Zhang, Yulong Zhang, Li Shao, Xiaofeng Shi, Guanghui Wang, and Peiyang He. Closing the Feedback Loop: From Experience Extraction to Insight Governance in Verbal Reinforcement Learning. 2026-06-16.** [Abstract](https://arxiv.org/abs/2606.17591); [full text](https://arxiv.org/html/2606.17591v1).

Verified locations: §2.2 R2–R4; §§3.1–3.3; §4.1; §5 limitations. Rules have conditions and corrective actions. Deprecation disables a rule while retaining its knowledge and append-only evidence. A critic/proposer/curator loop uses cross-episode outcomes to govern active context. Models remain parameter-frozen. The empirical setting is nonstationary financial forecasting.

**Overlap:** stale advice harms; evidence should survive deactivation; applicability differs from retention; context-only interventions.

**Remaining distinction:** cross-episode rule reliability learned from accumulated outcomes versus an episode-local correction becoming consumed immediately after verified execution. No same-repair causal fork or predicate-survival analysis is shown. Evidence is treated uniformly over time; temporal discounting is future work. No numeric deprecation threshold was verified; do not invent one.

### 4. Plans Don't Persist: closest paired-prefix method

**Aman Mehta and Anupam Datta. Plans Don't Persist: Why Context Management Is Load Bearing for LLM Agents. 2026-06-22.** [Abstract](https://arxiv.org/abs/2606.22953); [full text](https://arxiv.org/html/2606.22953v1).

Verified locations: §§3.3–3.5, §8, §9. Replay pairing feeds identical actions and observations with versus without the plan; stripped-run outputs are discarded. Primary outcomes concern hidden-state distances. The work explicitly notes confounds from history length, token positions, discourse structure, and reasoning traces that restate removed content. Separate compression experiments measure behavioral success.

**Overlap:** fixed trajectory replay, contextual persistence, history removal, and contamination through later restatements.

**Remaining distinction:** action/observation replay for representations rather than a shared repair followed by freely diverging behavioral continuations; plan presence rather than instruction applicability. Do not reuse a trained probe if the project excludes training. The paper's requested length/content-matched controls should be included in any new context experiment.

### 5. Authorization Closure Graph: closest consumed authority semantics

**Qingzhuo Wang, CaiYi Wang, Jinglu Meng, Ruiyang Qin, Kunyu Peng, Zhihua Wei, and Wen Shen. Authorization Closure Graph: Minimal Repair for LLM Agents with Evolving User Instructions. 2026-09-26.** [Abstract](https://arxiv.org/abs/2609.32428); [full text](https://arxiv.org/html/2609.32428v1).

Verified locations: §§3.1–3.2; Appendices A.1, A.3–A.4. Separates evidence availability from authorization; grants are scoped to approved actions/arguments. Changed source versions invalidate dependent authority while preserving unaffected nodes. Dispatch consumes execution allowance, which a refreshed observation or new candidate identifier cannot replenish.

**Overlap:** evidence is not authority, action scope, non-reusable consumed grants, versioned context, and selective preservation.

**Remaining distinction:** deterministic enforcement of authenticated user authorization versus measuring a model's continuing interpretation of reviewer advice after a valid repair. No evidence that it isolates the linguistic effect of retained corrective text after matched action execution. Single-use semantics alone would be an incremental adaptation of this established design.

### 6. AgentSentry: closest causal/context-purification method

**Tian Zhang, Yiwei Xu, Juan Wang, Keyan Guo, Xiaoyang Xu, Bowen Xiao, Quanlong Guan, Jinlin Fan, Jiawei Liu, Zhiquan Liu, and Hongxin Hu. AgentSentry: Mitigating Indirect Prompt Injection in LLM Agents via Temporal Causal Diagnostics and Context Purification. 2026-02-26.** [Abstract](https://arxiv.org/abs/2602.22724); [full text](https://arxiv.org/html/2602.22724v1).

Verified locations: §§4.2–4.6; Appendices B.2–B.4, C.1–C.3. Holds dialogue prefix/runtime snapshot fixed; substitutes mediator context in counterfactual dry runs; preserves factual fields while making instruction-bearing spans non-actionable. Online mitigation purifies context, revises the next action, and resumes. It needs no retraining.

**Overlap:** delayed context-mediated harm, state-matched causal comparisons, directive/evidence separation, and safe continuation.

**Remaining distinction:** malicious indirect injection and next-action takeover versus legitimate reviewer advice that was useful, executed, and then became inapplicable. A candidate novelty claim requires isolating that transition and later predicate loss. Context purification or matched snapshots alone are not new. Reported diagnostics are mainly next-action dry runs, not same-corrected-action post-repair survival curves.

## Additional verified sources and useful leads

- **Yifei Ming, Zixuan Ke, Xuan-Phi Nguyen, Jiayu Wang, Shafiq Joty. Helpful Agent Meets Deceptive Judge: Understanding Vulnerabilities in Agentic Workflows. 2025-06-03.** [Full text](https://arxiv.org/html/2506.03332v1), §§3.1–3.4, §§4.4–5.2. WAFER-QA varies critic intent and knowledge, including web-supported misleading critiques; it tracks four-round correctness patterns and recovery. Strong antecedent for critique contamination, but outcomes are QA answers, not persistent world predicates. Verify latest venue title separately: a secondary index calls the ICLR 2026 version “WAFER-QA: Evaluating Vulnerabilities of Agentic Workflows with Agent-as-Judge.”

- **Chang Ma, Junlei Zhang, Zhihao Zhu, Cheng Yang, Yujiu Yang, Yaohui Jin, Zhenzhong Lan, Lingpeng Kong, Junxian He. AgentBoard: An Analytical Evaluation Board of Multi-turn LLM Agents. 2024-01-24; NeurIPS 2024.** [Full text v2](https://arxiv.org/html/2401.13178v2), §3.1. Progress explicitly records the highest state-matching score attained. Thus current predicate survival can be distinguished from peak progress; do not claim per-step subgoal evaluation is new.

- **Sanjana Pedada, Aditya Dhavala, Neelraj Patil. Shared Selective Persistent Memory for Agentic LLM Systems. 2026-07-10.** [Full text](https://arxiv.org/html/2607.09493v1), §§3.2–3.4, §6.2, future work. Persists specifications/schemas/tool configuration/output constraints while dropping prior-session reasoning/tool traces; compares selective memory, full history, and none. Prior-session pruning and stale-trace anchoring, not within-episode consumed critique.

- **Zhaohui Wang. Persistent Semantic Entities in Tool-Augmented LLM Systems. arXiv 2026-08-08.** [Full text](https://arxiv.org/html/2608.07952v1), §§4.6–4.7, §6, Appendix I.5. Studies persistence/propagation of instruction, preference, persona, and factual contamination; context-isolated verification. Name-binding/injection setting, not legitimate correction lifecycle. [PMLR page](https://proceedings.mlr.press/v306/wang26gf.html) uses author name Zhaohui Geoffrey Wang and ICML 2026 venue metadata; preserve source-specific bibliographic distinction.

- **SLIFT: Different Feedback, Different Updates: Selective Self-Learning from User Interactions for Large Language Models. 2026-08-10.** [Full text](https://arxiv.org/html/2608.09109v1), §§3.1–3.4. Explicitly separates necessary fixes, conditional specifications, and unsupported feedback; warns against turning local refinements into defaults. It trains two LoRA adapters, so it is conceptual prior art, not a no-training method. Author list not extracted in this pass.

## Older harm/faithfulness background, full texts inspected

- **Jie Huang, Xinyun Chen, Swaroop Mishra, Huaixiu Steven Zheng, Adams Wei Yu, Xinying Song, Denny Zhou. Large Language Models Cannot Self-Correct Reasoning Yet. 2023-10-03; ICLR 2024.** [PDF](https://arxiv.org/pdf/2310.01798), §§3.2–3.3, §§4–5. Correct-to-incorrect transitions, oracle-stopping confound, inference-budget fairness, and prompt-design controls are established.
- **Philippe Laban, Lidiya Murakhovs'ka, Caiming Xiong, Chien-Sheng Wu. Are You Sure? Challenging LLMs Leads to Performance Drops in The FlipFlop Experiment. 2023-11-14.** [Full text v2](https://arxiv.org/html/2311.08596v2), §§3.1–3.2 and §5.3. User challenge corrupts classifications; no persistent tool state. Its fine-tuning mitigation is outside the prospective scope.
- **Qingjie Zhang, Han Qiu, Di Wang, Haoting Qian, Yiming Li, Tianwei Zhang, Minlie Huang. Understanding the Dark Side of LLMs' Intrinsic Self-Correction. 2024-12-19; ACL 2025.** [Full text](https://arxiv.org/html/2412.14959v1), §5.2 and Appendix D.3. Feedback/history overload can obscure original task details, with programming and household-agent examples. Causal labels such as cognitive overload are interpretations, not definitive latent-mechanism evidence.
- **Yingming Wang and Pepa Atanasova. Self-Critique and Refinement for Faithful Natural Language Explanations. EMNLP, November 2025.** [PDF](https://aclanthology.org/2025.emnlp-main.427.pdf), §5.3/Figure 4. Measures faithful-to-unfaithful and reverse transitions under iterative feedback. This is post-hoc explanation faithfulness; avoid treating narrative agreement as a substitute for executable state validity.

## Engineering lead, not a verified paper claim

Search-indexed official agentfootprint strict-output documentation describes ephemeral retry feedback that never enters persistent history and disappears when the validation gate exits, while accepted exchanges are retained. [Documentation](https://agentfootprint.dev/docs/build/strict-output/). Direct page open failed in this pass; publication date was not verified. This is a practical prior-art warning against claiming ephemeral correction messages as an unprecedented implementation technique.

## Minimum distinguishing experiment (proposal)

1. Fork only after a legitimate reviewer-requested repair has executed identically, with matching environment state and independent readback.
2. Preserve original task, still-applicable requirements, factual correction evidence, source provenance, tool outputs, token budget, and available tools. The only intended treatment is whether the consumed directive remains applicable.
3. Include persistent raw critique, same-content explicitly consumed critique, evidence-only receipt, and length/role/placebo-matched controls. Removing history alone cannot identify directive lifetime.
4. Resume independent rollouts, measuring current still-required predicate loss, loss latency, recovery, final task completion, and additional cost. Not every achieved subgoal is an invariant; define persistence obligations before examining outcomes.
5. Demonstrate the result under non-adversarial, factually correct critique and unchanged world state. Otherwise the experiment reduces toward CAVE-Bench, WAFER-QA, AgentSentry, or ordinary stale-evidence handling.
6. Do not use visible reasoning as causal ground truth. Executable predicates and controlled context manipulations should carry the claim.
