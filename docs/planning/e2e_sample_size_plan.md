# 端到端样本量与设计计划（文档 §8.5 / §11.1 / §12）

状态：**已冻结设计，待执行确认批次**。campaign：workbench-20261020-004。协议：advice-lifetimes-local-v4。
更新：2026-10-21。

## 1 估计量与为何转向端到端

根实验主终点 **L(P)−L(C)**（终止时受保护目标丢失之差）已被证实**在冻结 Telecom 池中不可测**：
约 66 条真实 reference 轨迹、288 个候选边界中，仅出现 **1 个 protected-and-unmet root、来自 1 个任务**
（round-1 t6-s0/idx70）；针对性 §8.4 扩展（6 个 ≥2 仅降速故障家族 ×4 start）**复现 0 次分离**，
且 idx70 本身 4 个 start 全 0——证明 round-1 的单次命中是稀有随机排序，非可复现结构
（详见 `reports/coverage_structure_finding.md` §13 有边界可测性负结果）。

端到端估计量 **J(P)/J(C)/ΔJ**（文档 §11.1）**不依赖**这种稀有的中途目标分离：每个策略从官方初始状态
跑自己的自然轨迹，公开规则至多触发一次 review，无触发 episode 正常运行至终止并进入分母。因此
**J/ΔJ 是当前可达的主交付物**，也是文档对旧 G3/G4 终端判断（含事实错误）的纠正。

- **J(arm)** = 该臂所有 episode 完成任务宏平均（官方 ENV_ASSERTION 奖励）。
- **ΔJ = J(C) − J(P)**：正值代表“一次履行后关闭建议生命周期”(C) 相对“持续建议”(P) 提高完成率。
- **独立性单元 = 任务簇**（不相交故障组件）；ΔJ 按任务配对，bootstrap 重采任务簇而非 episode。

## 2 固定基准（prospective_fixed_benchmark）

| 项 | 值 |
| --- | --- |
| 清单 | `docs/planning/manifests/tasks_e2e_fixed_benchmark_v4.json`（8 任务） |
| 构建器 | `tools/build_e2e_benchmark.py`（仅元数据、可复现） |
| 来源池 | 32 个已核验 roaming-protectable 任务 |
| 选择规则 | 按故障 token 数分层，配额 {2:1,3:2,4:2,5:2,6:1}=8；层内按（persona 难度 DESC，index ASC） |
| 是否读取结局 | **否**（outcome-blind：仅用故障数与 persona 等结构属性，未看任何模型结局/完成标签） |
| sha 核验 | 每行 `task_sha256=freeze.sha(canonical pinned task)`，对官方 `tasks.json`@4ce7c03 核验；index 核验 |
| 选中官方 index | 18, 41, 44, 106, 111, 182, 184, 232 |

**难度先验（非结局选择）**：2 任务真实联调（idx70/71，3 故障）显示 B/P/R 完成率饱和于 J=1，且
Reviewer 从未改变 Actor 动作（0 个 valid_changed draw）。故基准**结构化地**偏向更高故障数与更难 persona，
以给完成率留出变动空间（headroom），给 Reviewer 留出杠杆。这是设计先验，不是按观测结局挑任务。

## 3 样本量

| 项 | 值 |
| --- | --- |
| 任务数（簇） | 8 |
| starts_per_task | 2 |
| task-start 单元 | **16** = `confirmatory_sample_size` |
| 臂 | B, R, P, C |
| episode 总数 | **64** |
| 每 episode review 槽 | 1（至多一次触发） |
| allocation_seed | 20261021 |

**功效限制（诚实声明）**：bootstrap 独立性单元是**任务簇**，本设计仅 **8 个簇**。增大 `starts_per_task`
只降低任务内方差，**不增加独立簇数**，因此无法靠加 start 修复“簇受限”的功效。预期 ΔJ 区间较宽，
将如实报告。本批次是**有边界的可行性 + 预注册零检验**，非高功效试验。若需更高功效，须扩展**不同任务**
（更多簇），受 roaming-protectable 池（32 任务）与算力约束。

## 4 判定规则（冻结前统一不等号）

- 主判据：`claim_status='criteria_met'` 当且仅当——全部基准任务单元均被代表、`missing_endpoints==0`、
  且 ΔJ 的 95% 任务簇 bootstrap **下界 > delta**。否则 `not_established`。
- **delta = 0.0**、**epsilon = 0.0**、confidence 0.95、bootstrap 2000 次、seed 20261021。
- **诚实预期**：鉴于联调暴露的机制空档（roaming 任务上 Reviewer 极少改变动作），预注册的中性阈值
  delta=0 预期得到 `not_established`。这是合法的预注册零检验，按原样报告；**阈值未被调参以制造阳性声明**。

## 5 成本与执行纪律

- `monetary_cap=null`、`pricing.status=unknown`（未知价格/用量从不记零）。
- `concurrency=1`、真实运行**串行**；用户已授权不设总金额上限，按有限批次执行并记录消耗。
- 每 episode 至多 1 次 review；触发器 outcome-blind、结构化，不读隐藏目标、不按 C−P 有利性选择。
- 联调批次（`development/e2e-live-integration-001`，idx70/71）先于冻结，用于验证 run→analyze→export
  全链路；其任务**不同于**本基准，记录 `used_for_formal_analysis=false`，基准任务集与 delta/epsilon
  **均未**据其结局选择。

## 6 与根实验/消融的关系

- 根实验 8 臂（文档 §11.2 A 项）在当前池中**对主终点 L 不可执行**（§13 负结果），将如实记录为
  “不可执行 + 证据”，不静默丢弃、不伪造覆盖。
- 端到端 4 臂（B/R/P/C）本身即构成 §11.2 A 项“回执/额外思考/Reviewer 动作/原包与状态头”的**端到端版本**
  对照：B（回执+包+头，从不关闭）、R（一次履行后移除包、无生命周期头）、P（持续中性头+包）、
  C（一次履行后关闭）。其余 B–H 消融项的可行性与限制见 §11.2 消融矩阵记录。
