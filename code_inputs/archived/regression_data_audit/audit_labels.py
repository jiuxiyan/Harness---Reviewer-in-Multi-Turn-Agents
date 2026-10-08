"""Independent stdlib-only descriptive audit. Does not import/execute repository code."""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import statistics

ROOT = Path(__file__).resolve().parent
INPUT_SHA256 = {
    "single_setup_vectors.md5": "d4c03560181ed4f024bcf607150808eb7ff7a8dd687d332c3fe0ef67ace755d4",
    "single_setup_repository_map.json": "65b5aaf7b258dff691b3e012cb98a78e8cec5a79be38db1798571bc027fa91f8",
}
for filename, expected in INPUT_SHA256.items():
    actual = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"Input checksum mismatch for {filename}: {actual}")
PLAN = json.loads((ROOT / "audit_plan.json").read_text())
MAP = json.loads((ROOT / "single_setup_repository_map.json").read_text())
RX = re.compile(r"vectors/(pooled|timeseries)/(\d+)_runs/run_(\d+)/(SUCCESS|FAIL)_(.*?)_(chatcmpl-[^_]+)_(pooled|ts)\.npy$")
rows = []
for line in (ROOT / "single_setup_vectors.md5").read_text().splitlines():
    digest, path = line.split(maxsplit=1)
    match = RX.fullmatch(path)
    assert match, path
    mode, group, run, label, repo_name, tid, suffix = match.groups()
    info = MAP[tid]
    assert (suffix == "pooled") == (mode == "pooled")
    assert (label == "SUCCESS") == info["outcome"]
    rows.append(dict(mode=mode, group=int(group), run=int(run), label=int(label == "SUCCESS"),
                     repository=info["repo"], instance=info["instance_id"], trajectory=tid,
                     digest=digest, path=path))

assert len({r["path"] for r in rows}) == len(rows)
paired = defaultdict(dict)
mat = defaultdict(lambda: defaultdict(dict))
repos = {}
for row in rows:
    key = (row["group"], row["run"], row["trajectory"])
    assert row["mode"] not in paired[key]
    paired[key][row["mode"]] = row
    if row["mode"] == "pooled":
        g, iid, run = row["group"], row["instance"], row["run"]
        assert run not in mat[g][iid]
        mat[g][iid][run] = row["label"]
        repos[iid] = row["repository"]
assert all(set(v) == {"pooled", "timeseries"} for v in paired.values())
assert set(MAP) == {r["trajectory"] for r in rows}
assert len(paired) == len(MAP)
assert len({iid for tasks in mat.values() for iid in tasks}) == sum(map(len, mat.values()))
assert sorted(mat) == PLAN["groups"]
for g, tasks in mat.items():
    assert all(set(v) == set(range(1, g+1)) for v in tasks.values())

def h(iid):
    return hashlib.sha256((PLAN["hash_salt"] + ":" + iid).encode()).hexdigest()

# Freeze selections before the held-out metrics below are calculated.
selections = {}
for g, tasks in sorted(mat.items()):
    ids = sorted(tasks)
    n = len(ids)
    k = max(1, round(n * PLAN["subset_fraction"]))
    strata = defaultdict(list)
    for iid in ids:
        pattern = ''.join(str(tasks[iid][r]) for r in PLAN["training_runs"])
        strata[pattern].append(iid)
    # Integer quotients/remainders preserve exact ties; float subtraction can break them.
    allocation = {s: (k * len(ss)) // n for s, ss in strata.items()}
    remainders = {s: (k * len(ss)) % n for s, ss in strata.items()}
    for s in sorted(strata, key=lambda s: (-remainders[s], s))[:k-sum(allocation.values())]:
        allocation[s] += 1
    chosen_by_stratum = {s: sorted(ss, key=h)[:allocation[s]] for s, ss in sorted(strata.items())}
    assert all(allocation[s] > 0 for s in strata), "Cannot compute unbiased stratified estimator with absent sampled stratum"
    selections[g] = {
        "n": n, "k": k,
        "stratum_sizes": {s: len(v) for s, v in sorted(strata.items())},
        "allocation": allocation,
        "hash_uniform": sorted(ids, key=h)[:k],
        "history_stratified": [iid for selected in chosen_by_stratum.values() for iid in selected],
        "history_stratified_by_stratum": chosen_by_stratum,
    }
selection_bytes = (json.dumps(selections, sort_keys=True, indent=2) + '\n').encode()
(ROOT / "frozen_selections.json").write_bytes(selection_bytes)
selection_sha = hashlib.sha256(selection_bytes).hexdigest()

def mean(values):
    return statistics.mean(values)

def metric(values):
    return {"rmse": math.sqrt(mean(v*v for v in values)), "max_abs_error": max(map(abs, values)),
            "mean_error": mean(values), "n_heldout_runs": len(values)}

summary = {"verdict": "feasible label-only no-change offline replay; not real revision regression evaluation",
           "plan_sha256": hashlib.sha256((ROOT / "audit_plan.json").read_bytes()).hexdigest(),
           "frozen_selections_sha256": selection_sha,
           "manifest_entries": len(rows), "map_entries": len(MAP), "trajectories": len(paired),
           "instances": sum(map(len, mat.values())), "repositories": len(set(repos.values())),
           "missing_map_ids": 0, "duplicate_trajectory_ids": 0, "duplicate_task_run_pairs": 0,
           "missing_task_run_cells": 0, "map_filename_label_disagreements": 0,
           "vector_hash_duplicates": {}, "groups": {}}
for mode in ("pooled", "timeseries"):
    counts = Counter(r["digest"] for r in rows if r["mode"] == mode)
    summary["vector_hash_duplicates"][mode] = {
        "distinct_hashes": len(counts), "duplicate_hash_buckets": sum(v > 1 for v in counts.values()),
        "extra_records_sharing_hash": sum(v-1 for v in counts.values()),
        "largest_hash_bucket": max(counts.values())}

eval_rows = []
pair_rows = []
for g, tasks in sorted(mat.items()):
    n = len(tasks)
    runs = range(1, g+1)
    rates = {r: mean(t[r] for t in tasks.values()) for r in runs}
    success_hist = Counter(sum(t.values()) for t in tasks.values())
    churn = []
    adjacent = []
    for a,b in combinations(runs, 2):
        fail_to_pass = sum(t[a] == 0 and t[b] == 1 for t in tasks.values())
        pass_to_fail = sum(t[a] == 1 and t[b] == 0 for t in tasks.values())
        rate = (fail_to_pass + pass_to_fail)/n
        churn.append(rate)
        if b == a+1:
            adjacent.append(rate)
        pair_rows.append(dict(group=g, earlier_index=a, later_index=b, task_count=n,
                              fail_to_pass=fail_to_pass, pass_to_fail=pass_to_fail, churn_rate=rate))
    chosen = selections[g]
    errors = defaultdict(list)
    alarms = defaultdict(list)
    baseline_est = {}
    full_base = mean(rates[r] for r in (1,2))
    for r in runs:
        estimates = {method: mean(tasks[iid][r] for iid in chosen[method])
                     for method in ("hash_uniform", "history_stratified")}
        estimates["history_stratified_weighted"] = sum(
            chosen["stratum_sizes"][s]/n * mean(tasks[iid][r] for iid in ids)
            for s, ids in chosen["history_stratified_by_stratum"].items())
        if r in (1,2):
            for method, estimate in estimates.items():
                baseline_est.setdefault(method, []).append(estimate)
            continue
        for method, estimate in estimates.items():
            err = estimate-rates[r]
            delta = estimate-mean(baseline_est[method])
            full_delta = rates[r]-full_base
            errors[method].append(err)
            alarms[method].append(abs(delta) > 0.05)
            eval_rows.append(dict(group=g, heldout_run_index=r, method=method, full_rate=rates[r],
                                  estimate=estimate, error=err, estimated_delta_from_training=delta,
                                  full_delta_from_training=full_delta, noop_alarm_gt_5pp=abs(delta)>0.05))
    summary["groups"][g] = {
        "tasks": n, "trajectories": n*g, "repositories": len({repos[iid] for iid in tasks}),
        "subset_size": chosen["k"], "subset_fraction_actual": chosen["k"]/n,
        "training_pattern_counts": chosen["stratum_sizes"], "training_pattern_selection": chosen["allocation"],
        "pass_rates_by_run_index": rates, "pass_rate_range": max(rates.values())-min(rates.values()),
        "pass_rate_population_std": statistics.pstdev(rates.values()),
        "always_fail": success_hist[0], "always_pass": success_hist[g],
        "ever_changed_tasks": n-success_hist[0]-success_hist[g],
        "task_success_count_histogram": dict(sorted(success_hist.items())),
        "all_pair_mean_churn": mean(churn), "all_pair_min_churn": min(churn), "all_pair_max_churn": max(churn),
        "adjacent_pair_mean_churn": mean(adjacent),
        "heldout_metrics": {m: {**metric(err), "noop_alarm_gt_5pp_count": sum(alarms[m]),
                                 "noop_alarm_gt_5pp_fraction": mean(alarms[m])} for m, err in errors.items()},
        "full_benchmark_noop_alarm_gt_5pp_count": sum(abs(rates[r]-full_base)>0.05 for r in range(3,g+1)),
    }
for filename, data in [("heldout_evaluation.csv",eval_rows),("pair_churn.csv",pair_rows)]:
    with (ROOT/filename).open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
summary["total_ever_changed_tasks"] = sum(x["ever_changed_tasks"] for x in summary["groups"].values())
summary["total_always_fail"] = sum(x["always_fail"] for x in summary["groups"].values())
summary["total_always_pass"] = sum(x["always_pass"] for x in summary["groups"].values())
summary["task_pair_weighted_churn"] = sum((r["fail_to_pass"]+r["pass_to_fail"]) for r in pair_rows)/sum(r["task_count"] for r in pair_rows)
summary["heldout_overall_macro_metrics"] = {
    m: metric([r["error"] for r in eval_rows if r["method"] == m])
    for m in sorted({r["method"] for r in eval_rows})}
(ROOT/"audit_results.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+'\n')
print(json.dumps(summary, indent=2, sort_keys=True))
