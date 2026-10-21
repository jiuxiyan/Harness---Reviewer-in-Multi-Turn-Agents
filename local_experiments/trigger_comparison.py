"""Offline comparison of public trigger-rule families over reference-only candidate boundaries.

Development-stage tool (document §6.2/§7.1). Reads one or more reference-only run directories,
replays each candidate rule family over the recorded candidate boundaries, and reports coverage.
Rule selection here uses ONLY public structure (completed assistant tool returns, successful public
WRITEs, user text interactions) plus the offline-measured protection/unmet coverage and a cost proxy.
It never reads hidden goals at trigger time and never selects by which of C-P is more favourable.
"""
import argparse
import json
from pathlib import Path


def load_candidates(run_dirs):
    cands = []
    for d in run_dirs:
        p = Path(d) / 'derived' / 'candidate_boundaries_enriched.jsonl'
        if not p.exists():
            p = Path(d) / 'derived' / 'candidate_boundaries.jsonl'
        if not p.exists():
            raise SystemExit(f'no candidate boundaries in {d}')
        # trajectory_id (t0-s0, ...) is only unique WITHIN a run; tag each candidate with its
        # source run so aggregating multiple runs does not merge distinct trajectories that share
        # the same local id.
        run_tag = Path(d).name
        for line in p.read_text(encoding='utf8').splitlines():
            if line.strip():
                c = json.loads(line)
                c['_run'] = run_tag
                cands.append(c)
    return cands


def by_trajectory(cands):
    traj = {}
    for c in cands:
        traj.setdefault((c['_run'], c['trajectory_id']), []).append(c)
    for v in traj.values():
        v.sort(key=lambda c: c['step'])
    return traj


# Each rule is a predicate over a candidate record. The rule captures the FIRST candidate
# (lowest step) in each trajectory that satisfies the predicate.
def rule_families():
    fams = []
    # Family 1: public call-depth rule (completed assistant tool returns >= D).
    for D in (2, 3, 4, 6, 8):
        fams.append((f'depth>={D}', 'depth',
                     lambda c, D=D: c['completed_assistant_tools'] >= D))
    # Family 2: post-public-change rule (>=1 successful allowed WRITE already returned).
    fams.append(('post_write', 'post_change',
                 lambda c: c.get('prior_successful_writes', 0) >= 1))
    fams.append(('post_write&depth>=4', 'post_change',
                 lambda c: c.get('prior_successful_writes', 0) >= 1 and c['completed_assistant_tools'] >= 4))
    fams.append(('post_write&users>=2', 'post_change',
                 lambda c: c.get('prior_successful_writes', 0) >= 1 and c['user_text_events'] >= 2))
    # Family 3: public interaction-stage rule (user text events >= T).
    for T in (2, 3, 4):
        fams.append((f'users>={T}', 'interaction',
                     lambda c, T=T: c['user_text_events'] >= T))
    # Combined later rules prioritised by §7.1 (rule 2 and later rule 1).
    fams.append(('post_write|depth>=6', 'combined',
                 lambda c: c.get('prior_successful_writes', 0) >= 1 or c['completed_assistant_tools'] >= 6))
    return fams


def evaluate(traj, pred):
    roots = []
    for tid, cs in traj.items():
        for c in cs:
            if pred(c):
                roots.append(c)
                break
    n = len(roots)
    nonempty = [r for r in roots if r['protected_count'] > 0]
    prot_unmet = [r for r in roots if r['protected_count'] > 0 and r['unmet_count'] > 0]
    tasks_nonempty = sorted({r['task_id'] for r in nonempty})
    tasks_prot_unmet = sorted({r['task_id'] for r in prot_unmet})
    subseq = [r.get('subsequent_actor_boundaries', 0) for r in roots]
    steps = [r['step'] for r in roots]
    return {
        'roots': n,
        'trajectories': len(traj),
        'root_coverage': (n / len(traj)) if traj else None,
        'nonempty_protection_roots': len(nonempty),
        'protected_and_unmet_roots': len(prot_unmet),
        'distinct_tasks_nonempty': len(tasks_nonempty),
        'distinct_tasks_protected_unmet': len(tasks_prot_unmet),
        'mean_subsequent_actor_boundaries': (sum(subseq) / n) if n else None,
        'roots_with_subsequent_boundary': sum(1 for s in subseq if s > 0),
        'mean_step': (sum(steps) / n) if n else None,
        'max_step': max(steps) if steps else None,
    }


def main():
    ap = argparse.ArgumentParser(prog='python -m local_experiments.trigger_comparison')
    ap.add_argument('--input-dir', action='append', required=True,
                    help='reference-only run directory (repeatable to aggregate)')
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cands = load_candidates(args.input_dir)
    traj = by_trajectory(cands)
    fams = rule_families()
    results = []
    for name, family, pred in fams:
        r = evaluate(traj, pred)
        r['rule'] = name
        r['family'] = family
        results.append(r)

    payload = {
        'schema_version': 1,
        'input_dirs': args.input_dir,
        'trajectories': len(traj),
        'candidates': len(cands),
        'rules': results,
    }
    (out / 'trigger_comparison.json').write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf8')
    (out / 'trigger_comparison.json').chmod(0o600)

    # Markdown report.
    lines = []
    lines.append('# 公开触发规则族离线比较（文档 §6.2 / §7.1）\n')
    lines.append(f'输入运行目录：{", ".join(args.input_dir)}\n')
    lines.append(f'轨迹数：{len(traj)}；候选边界总数：{len(cands)}\n')
    lines.append('\n规则仅读取公开结构（已完成的 Assistant 工具返回数、已成功返回的公开 WRITE 数、'
                 'User 文本交互数）；保护/未满足覆盖为离线测量，用于开发期选规则，'
                 '**不**按 C−P 哪个更有利选择，也**不**在线读取隐藏目标。\n')
    hdr = ('| 规则 | 族 | 捕获 root | root 覆盖 | 非空保护 root | 保护且未满足 root | '
           '非空保护任务数 | 保护未满足任务数 | 有后续 Actor 边界的 root | 平均后续边界 | 平均步 | 最大步 |')
    sep = '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |'
    lines.append('\n' + hdr + '\n' + sep + '\n')
    for r in results:
        def f(x):
            return '—' if x is None else (f'{x:.2f}' if isinstance(x, float) else str(x))
        lines.append('| `{rule}` | {family} | {roots} | {rc} | {ne} | {pu} | {tne} | {tpu} | {rsb} | {msb} | {ms} | {xs} |\n'.format(
            rule=r['rule'], family=r['family'], roots=r['roots'], rc=f(r['root_coverage']),
            ne=r['nonempty_protection_roots'], pu=r['protected_and_unmet_roots'],
            tne=r['distinct_tasks_nonempty'], tpu=r['distinct_tasks_protected_unmet'],
            rsb=r['roots_with_subsequent_boundary'], msb=f(r['mean_subsequent_actor_boundaries']),
            ms=f(r['mean_step']), xs=f(r['max_step'])))
    # §7.3 engineering coverage target check.
    lines.append('\n## §7.3 初始工程覆盖目标核对\n')
    lines.append('目标：某规则累计 **≥10 个非空保护 root、来自 ≥3 个不同任务、且有未完成工作**'
                 '（即 protected_and_unmet）。该目标是工程覆盖门槛，不代表统计功效，也不证明任务独立。\n\n')
    qualified = [r for r in results if r['protected_and_unmet_roots'] >= 10 and r['distinct_tasks_protected_unmet'] >= 3]
    if qualified:
        lines.append('满足目标的规则：\n')
        for r in qualified:
            lines.append(f"- `{r['rule']}`：protected_and_unmet root={r['protected_and_unmet_roots']}，"
                         f"不同任务={r['distinct_tasks_protected_unmet']}，root 覆盖={r['root_coverage']:.2f}，"
                         f"平均后续 Actor 边界={r['mean_subsequent_actor_boundaries']:.2f}\n")
    else:
        best = max(results, key=lambda r: (r['protected_and_unmet_roots'], r['distinct_tasks_protected_unmet']))
        lines.append('**当前无规则满足 ≥10 非空保护 root 且 ≥3 任务的目标。** '
                     '最接近的规则：`{rule}`（protected_and_unmet root={pu}，不同任务={tpu}）。\n'
                     '按文档 §6.3/§7.3，下一步进入任务/观察边界扩展（§8.4），'
                     '不对同一无信息配置继续增加 suffix，也不用人工续写或隐藏状态补足数量。\n'.format(
                         rule=best['rule'], pu=best['protected_and_unmet_roots'], tpu=best['distinct_tasks_protected_unmet']))
    (out / 'trigger_comparison.md').write_text(''.join(lines), encoding='utf8')
    (out / 'trigger_comparison.md').chmod(0o600)
    print(json.dumps({'trajectories': len(traj), 'candidates': len(cands),
                      'rules_evaluated': len(results),
                      'qualified_rules': [r['rule'] for r in qualified] if qualified else [],
                      'output_dir': str(out)}, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
