# 全量实验续执行最终报告（advice-lifetimes-local-v4，2026-10-21）

本文件记录按 `Harness_全量实验续执行流程_20261020.md` 续执行全量实验的最终结果、
途中发现并解决的具体问题、以及诚实的结论与局限。所有数字均来自真实模型运行或
冻结源码的离线分析，未做任何粉饰；原始私有记录（`results/.../private/`）不随仓库分发。

---

## 0. 一句话结论

在固定的前瞻性基准（8 个 telecom 任务、每任务 2 个独立 start、4 条建议生命周期臂
B/R/P/C，共 64 个 end-to-end episode）上，**确认性主对比 ΔJ = J(C) − J(P) = 0.0，
95% 任务簇 bootstrap 区间 [0, 0]，缺失端点插补界 [0, 0]，`claim_status = not_established`**。
根本原因不是统计功效不足，而是**机制缺口**：48 次 reviewer draw 中 `valid_changed = 0`
——reviewer 从未提出与 actor 原动作不同的动作；同时所有臂的完成率 J 都触顶（≈1.0），
没有可供区分臂间差异的余量。根层次的主端点 L 此前已被证明在该冻结任务池中**不可测**
（§13 有界负发现）。因此本研究如实报告"未建立正向效应"，而非制造显著性。

---

## 1. 确认性 end-to-end 批次（主交付物）

- 运行目录：`results/workbench-20261020-004/confirmatory/e2e-confirmatory-003`
- 配置：`configs/e2e-confirmatory.json`（`study_label=confirmatory`，`stage=end-to-end`，
  `protocol_id=advice-lifetimes-local-v4`）
- 冻结回执：`configs/freeze/e2e-confirmatory-freeze-v3.json`，
  `freeze_sha256 = 67fc480d5c56358f5cb998b76287ad8defeffaa819e509524f64589e5ce99252`（8 个任务）
- 分析 protocol_hash：`55d7fde2fccdd8513ebce027749f78a2e8442a27258b7202989572ddca57319f`
- `evidence_kind = confirmatory_live`，`formal_experiments = 1`，`status = completed_with_missing`

### 1.1 主端点

| 量 | 值 |
|---|---|
| J(P) 持久建议 | 1.0（16/16 计分） |
| J(C) 消费式建议 | 1.0（16/16 计分） |
| **ΔJ = J(C) − J(P)** | **0.0** |
| ΔJ 95% 区间（任务簇 bootstrap，2000 次） | [0.0, 0.0] |
| ΔJ 缺失端点最坏/最好插补界 | [0.0, 0.0] |
| 判定 delta | 0.0（ criteria_met 需区间下界 > delta 且 missing==0 ） |
| **claim_status** | **not_established** |

### 1.2 各臂完成率 J（task-macro，含未触发 episode）

| 臂 | 语义 | J | 计分/总 | 自然终止 | 触发率 |
|---|---|---|---|---|---|
| B | 仅回执（receipt-only） | 1.0 | 14/16 | 14 | 0.9375 |
| R | 一次有效响应后移除 packet+header | 0.9375 | 15/16 | 14 | 1.0 |
| P | 持久 packet+中性 header | 1.0 | 16/16 | 16 | 1.0 |
| C | header 中性→消费，packet 保留 | 1.0 | 16/16 | 16 | 1.0 |

- 总触发率 0.984（64 个 episode 中 63 个触发；1 个 B episode 未触发）。
- `ever_achieved_then_lost = 0`（所有臂均无"达成后丢失"）。

### 1.3 机制诊断（为何 ΔJ=0）

- `draw_classifications = {invalid: 0, out_of_scope: 0, unchanged: 48, valid_changed: 0}`。
  48 次 reviewer draw **全部为 unchanged**：reviewer 选定的动作与 actor 原本就要执行的
  动作一致，packet 只是复述既有意图。因此 P/R/C 三种"建议生命周期"操纵作用在**内容相同**
  的建议上，无法产生臂间差异。
- 完成率触顶（除 R 因 1 次 agent_error 略低外，其余 J=1.0），没有可区分效应的动态范围。
- 该机制缺口在**两个独立批次**（-002 与 -003，各 48 draw）以及此前的 integration 运行
  （6 draw）中一致复现，`valid_changed` 恒为 0。

### 1.4 缺失端点（3 个，诚实记录）

| episode | 臂 | 状态 | 性质 |
|---|---|---|---|
| 2 个 | B / R | `provider_result_unknown` | 瞬时（网关未知结果，重试耗尽；2 次 request_failed） |
| 1 个 | R | `agent_error` | 单 episode 原生错误累积 |

缺失由 `missingness_bounds` 处理：ΔJ 插补界 [0.0, 0.0]，不改变结论。
注意：本批**未**出现 -002 中的 `unsupported_known_write_capability`（任务需要 roaming 之外
的写能力、超出冻结的 `allowed_writes` 范围）；该范围是协议边界，扩张它属于 task-setting
变更，未被执行。

### 1.5 资源消耗（如实记录，定价未知）

- 物理调用 1921 次；上报 input tokens 13,635,722；output tokens 455,634。
- `cost = null`，`cost_status = unknown`，`monetary_cap = null`（按既有授权不设金额上限，
  按有限批次执行并记录消耗）。
- **0 个 length 截断 / 1916 个响应**（见 §3 的 token 缺陷修复）。

### 1.6 确认范围（confirmation_scope，原文）

> fixed benchmark task set; episode-start policies; conditional on the fixed task list,
> not unseen-family generalization; offline freeze is not external preregistration

即：结论条件于这份**固定已知**基准任务列表，用**新的独立 start** 重采样；推断针对该任务集，
不外推到未见任务族；离线冻结**不是**外部预注册。

---

## 2. 根层次主端点 L：不可测（§13 有界负发现）

详见 `docs/planning/root_estimand_measurability_finding.md`。要点：

- 在冻结的 telecom 任务池中，约 57 条轨迹、288 个候选根里，**仅 1 个**"受保护且未满足"
  （protected-and-unmet）根，且只来自 1 个任务。
- §8.4 的扩张复现得到 **0** 个可分离根。
- 触发规则对比中，没有任何规则满足 §7.3 的覆盖/分离要求（最佳"depth≥2"规则覆盖 1.00，
  但只对应 1 个根 / 1 个任务）。
- 因此根层次 8 臂实验（B_bare/B/S/A/P0/P/R/C 对 L 的因果对比）在该池上**无法产生可测的 L 分离**。
  这是有证据的负发现，**不是**通过推理错误过早宣称不可能。

研究据此把主交付物转向**end-to-end 的 J / ΔJ**（§1），它不依赖稀有根分离即可测量。

---

## 3. 途中发现并解决的具体问题

### 3.1 致命混淆：actor 在 1024 token 上限下被 reasoning 吃光（已修）

- 现象：首个确认批次 `-001` 中，推理型 actor `sophnet/qwen3.6-plus` 在硬基准任务
  （prompt ~9,000–9,700 input tokens）上把全部 1024 token 完成预算花在 `reasoning_tokens`
  （=1024），content 长度 0、无 tool call、`finish_reason=length`。原生 tau2 把这种空动作
  回合记为 agent error，累积到 `max_native_errors` 后 episode 以 `agent_error` 终止、completion=0。
- 为何是混淆：携带建议的臂（P/R/C）会注入 packet 与生命周期 header，prompt 更长、actor 推理更多，
  而 B 臂只注入回执。于是截断与臂相关：`-001` 前 10 个 outcome 中 **B 完成 3/3，P 失败 2/2**，
  R/C 多数失败。若跑完并分析，J(P)/J(R)/J(C) 会被 token 预算伪影系统性压低，ΔJ 将估计的不是
  建议生命周期语义。按完整性规则，这属于伪影结论，禁止上报。
- 处置：停掉 `-001`（对 runner 及其 `worker.py` 子进程发 SIGTERM），在 10 个 outcome、无 status.json
  处停止；按"不覆盖/不删除失败目录"规则**原样保留**为缺陷证据，绝不作为确认批次分析。
- 修复（仅配置，未改冻结源码逻辑）：`configs/e2e-confirmatory.json` 的 `models.max_completion_tokens`
  由 1024 升至 **8192**（`provider.py` 直接读取该值，无需改 `local_experiments/*.py`）。
- 验证：bounded smoke（`configs/e2e-token-smoke.json`，同一硬任务 idx0，臂 B/P，8192 上限）
  经正常 runner 跑通：37 个响应 **0 个 length 截断**，最大 completion_tokens=1927（在 1024 下必被截断），
  B 与 P 均自然完成（user_stop）。随后 `-002`（64 episode）与 `-003`（64 episode）整批 **0 截断**。
- 详见 `docs/planning/e2e_token_truncation_defect.md`。

### 3.2 harness 标注 bug：end-to-end 确认批次被误标为 exploratory_live（已修）

- 现象：`local_experiments/storage.py:25` 原本只在 `stage=='confirmatory-roots'` 时给
  `confirmatory_live`，`end-to-end` 阶段即使 `study_label=='confirmatory'` 也落到 `exploratory_live`。
  于是 `-002` 虽按冻结的确认配置执行，却被标为 exploratory，确认分析分支（`verify_freeze` +
  `criteria_met` 判定）不会触发。
- 修复：把判定改为
  `confirmatory_live if (stage=='confirmatory-roots' or (stage=='end-to-end' and study_label=='confirmatory'))`。
- 验证：56 项回归测试全过；`-003` 的 `run_manifest.json` 正确显示 `evidence_kind=confirmatory_live`，
  确认分析分支正常触发并给出 `claim_status=not_established`。
- 因 `freeze.binding()` 对 `normalized(config)` 与 `source_hashes()` 取哈希，上述源码/配置改动改变了绑定，
  故**重新冻结**到新回执 `configs/freeze/e2e-confirmatory-freeze-v3.json`（旧 v1/v2 回执保留为历史）。
  `-002` 在 exploratory 分支下分析（不调用 verify_freeze），其结果作为验证 token 修复的探索性先导保留。

### 3.3 其他

- 凭据/模型/网关均按既有授权工作，无需更换模型或提供商，无需新增付费基础设施。
- 全程未要求用户介入（除本次进度询问外）。

---

## 4. §11.2 消融矩阵 A–H：可行性与处置

详见 `docs/planning/e2e_ablation_matrix.md`。核心判断：

- **机制缺口使多数消融失去发力点**：`valid_changed=0` 意味着 reviewer 从不改变动作，
  因此"建议内容/生命周期"类消融（A 八臂、B、C、E、F、H 等）在该基准上无法产生可区分信息——
  所有臂都会落在完成率天花板且建议内容相同。这是**经验证据**（两批各 48 draw + integration 6 draw
  一致 `valid_changed=0`），不是推理臆断。
- **A（八臂 end-to-end）**：实现路径已明确（扩展 `config.py` 的 `END_TO_END_ARMS` 与
  `engine.py` 的 `run_episode` 路由以支持 B_bare/S/A/P0）。但鉴于上述机制缺口与天花板，
  执行一次多小时、数千次调用的八臂 live 运行只会复现"各臂 J≈1.0、无区分"的既有结论，
  不会增加新信息；且它会改动确认冻结所依赖的源码，使被推送源码与产生 `-003` 的 v3 冻结源发散。
  故本研究**记录其可行性与实现路径，但不执行 live 八臂运行**，作为诚实的局限而非过早宣称不可能。
- **D-1（TTL=1 ≡ R）与单槽"保留最新"≡ 持久**：给出等价性论证（见消融矩阵文档）。
- **G（declaration 审计）**：可行，已作为分析完成——所有 integration/确认 draw 的 declaration 均为
  `{scope: action_local, instruction: execute_target_call, close_condition: normal_tool_return}`、
  classification=unchanged，故 C 的"消费"只是撤销一条已返回的 action-local 建议，无实质杠杆。
- **根层次八臂**：因 L 不可测（§2）而 moot。

---

## 5. 交付物与复现

- 确认性结果（聚合，允许分发）：
  `results/workbench-20261020-004/confirmatory/e2e-confirmatory-003-export/summary.json`
  与 `disclosure.json`（仅聚合标量，无原始文本，`upload_performed=false`）。
  注意 `results/` 整体被 `.gitignore` 排除，不随仓库分发；此处分发的是 `configs/`、`docs/`、
  `tools/`、`tests/`、`PUBLIC_MANIFEST.json` 等可公开产物。
- 冻结配置与回执：`configs/e2e-confirmatory.json`、`configs/freeze/e2e-confirmatory-freeze-v3.json`。
- 设计记录：`docs/planning/e2e_study_design.json`、`docs/planning/e2e_sample_size_plan.md`、
  `docs/planning/manifests/tasks_e2e_fixed_benchmark_v4.json`、
  `docs/planning/root_estimand_measurability_finding.md`、`docs/planning/e2e_ablation_matrix.md`、
  `docs/planning/e2e_token_truncation_defect.md`。
- 复现命令（离线，mock）：`python3 -m local_experiments validate --config configs/e2e-confirmatory.json`；
  `... run --mode dry-run ...`（64 episode，0 失败）。

---

## 6. 诚实声明

- 完成实验 ≠ 得到正向结果。本研究的主对比 ΔJ 的确认性判定为 **not_established**，
  根层次 L **不可测**。两者均有数据支撑，未制造显著性、未篡改分母、未手改 status.json。
- 失败/缺失端点如实记录（3 个缺失，含瞬时 provider 未知结果与 1 次 agent_error）。
- 被放弃的 `-001` 批次原样保留为缺陷证据，未被删除、覆盖或重新标注为完成。
- 定价未知、不设金额上限；实际 token 消耗如实上报（§1.5）。
