"""Metadata-only builder for the end-to-end prospective_fixed_benchmark manifest (doc §8.2/§11.1).

The end-to-end estimand J(P)/J(C)/ΔJ runs each policy from the official initial state over a FIXED,
KNOWN benchmark task list with NEW independent starts (v4 identity). This builder selects that fixed
list from the already-verified roaming-protectable development manifest using STRUCTURAL attributes
only (fault-token count and persona difficulty) -- never model outcomes, completion labels, or any
result observed in a live run. Selecting for higher structural difficulty is a design prior (more
faults / harder persona => plausibly more room for completion to vary), not an outcome-based choice.

Selection rule (deterministic, reproducible):
  - Stratify the roaming-protectable tasks by fault-token count.
  - Per-stratum quota: {2:1, 3:2, 4:2, 5:2, 6:1} = 8 tasks, spanning the complexity spectrum and
    weighting toward higher complexity where completion headroom is plausible.
  - Within a stratum, rank by (persona difficulty DESC [Hard>Easy>None], tasks_json_index ASC) and
    take the top-k. Ties are fully broken by index, so the output is deterministic.

Every row's task_sha256 is recomputed as freeze.sha over the canonical pinned task object and
verified against the official pinned tasks.json; tasks_json_index is verified to point at that task.
Each selected row is marked research_partition='prospective_fixed_benchmark'.

Usage:
  python -m tools.build_e2e_benchmark --out docs/planning/manifests/tasks_e2e_fixed_benchmark_v4.json
"""
import argparse
import json
from pathlib import Path

from local_experiments.config import ROOT, PIN
from local_experiments.freeze import sha, fault_set

OFFICIAL = ROOT / 'code_inputs/reviewer_pilot/upstream/data/tau2/domains/telecom/tasks.json'
SOURCE = ROOT / 'docs/planning/manifests/tasks_development_roaming_protectable.json'
QUOTA = {2: 1, 3: 2, 4: 2, 5: 2, 6: 1}


def persona_rank(task_id):
    if '[PERSONA:None]' in task_id:
        return 0
    if '[PERSONA:Easy]' in task_id:
        return 1
    return 2


def select(source_rows):
    enriched = []
    for row in source_rows:
        nf = len(fault_set(row['task_id']))
        enriched.append((nf, persona_rank(row['task_id']), row['tasks_json_index'], row))
    chosen = []
    for nf in sorted(QUOTA):
        cand = [r for r in enriched if r[0] == nf]
        cand.sort(key=lambda r: (-r[1], r[2]))
        chosen.extend(cand[:QUOTA[nf]])
    chosen.sort(key=lambda r: r[2])
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    source = json.loads(SOURCE.read_text())
    official_list = json.loads(OFFICIAL.read_text())
    official = {t['id']: t for t in official_list}

    chosen = select(source['tasks'])
    rows = []
    for nf, pr, idx, src_row in chosen:
        task = official.get(src_row['task_id'])
        if task is None:
            raise SystemExit('selected task absent from pinned official tasks.json: ' + src_row['task_id'])
        if official_list[idx]['id'] != src_row['task_id']:
            raise SystemExit(f'tasks_json_index {idx} does not point at the selected task')
        recomputed = sha(task)
        if recomputed != src_row['task_sha256']:
            raise SystemExit('task_sha256 mismatch vs pinned official object: ' + src_row['task_id'])
        rows.append({
            'task_id': src_row['task_id'],
            'task_sha256': recomputed,
            'family_id': '|'.join(sorted(fault_set(src_row['task_id']))),
            'research_partition': 'prospective_fixed_benchmark',
            'tasks_json_index': idx,
            'fault_token_count': nf,
            'persona_rank': pr,
            'assistant_side_env_assertion': bool(src_row.get('assistant_side_env_assertion')),
            'regressible_protected_goal': bool(src_row.get('regressible_protected_goal')),
            'protectable_coupled_user_goal': bool(src_row.get('protectable_coupled_user_goal')),
        })

    out = {
        'schema_version': 'planning-manifest-v1',
        'evidence_kind': 'not_run',
        'source_commit': PIN,
        'tasks_file_sha256': source['tasks_file_sha256'],
        'task_hash_encoding': 'freeze.sha over canonical pinned task object',
        'population': 'prospective_fixed_benchmark',
        'notes': 'End-to-end (doc §11.1) prospective_fixed_benchmark task list for the J(P)/J(C)/ΔJ '
                 'estimand under the v4 identity. A FIXED, KNOWN benchmark: inference conditions on '
                 'this exact task set using NEW independent starts resampled by start; it does NOT '
                 'claim unseen-family generalization (operator_attests_unseen stays false) and the '
                 'exposure ledger is bound at freeze. Selected outcome-blind from the verified '
                 'roaming-protectable pool by structural complexity only.',
        'selection_rule': 'complexity-stratified across fault-token count with per-stratum quota '
                          '{2:1,3:2,4:2,5:2,6:1}=8; within stratum rank by (persona difficulty DESC, '
                          'tasks_json_index ASC); structural attributes only, no model outcomes consulted',
        'tasks': rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print('wrote', args.out, 'with', len(rows), 'tasks')
    for r in rows:
        print('  idx=%3d nfault=%d persona=%d %s' % (r['tasks_json_index'], r['fault_token_count'], r['persona_rank'], r['family_id']))


if __name__ == '__main__':
    main()
