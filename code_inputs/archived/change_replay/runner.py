"""Reproducible local validation runner. Run: python runner.py."""
import csv
from copy import deepcopy
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from itertools import combinations
from common import ROOT, canonical, component_id, digest, file_hash, save_json, verify_freeze
from fixtures import public_tasks, tapes
from replay import Harness, local_predicate_probe
from variant_source import BASE, VARIANTS, load_source, structural_diff, write_sources

METHODS = ("cheapest_first", "changed_component_coverage", "diff_plus_capability", "candidate_replay")


def frozen_plan():
    return {
        "stage": "implementation_rules_before_first_replay_comparison",
        "tie_rule": "sha256('change-replay-tie-v1:' + task_id), ascending",
        "historical_cost": "maximum of the two old tape request-boundary-plus-actual-dispatch counts",
        "cheapest_first": "ascending historical cost, then hash",
        "changed_component_coverage": "greedy new (actual AST diff ID) exposure count / historical cost",
        "diff_plus_capability": "greedy new (actual AST diff ID, frozen public capability) pairs / historical cost",
        "candidate_replay": "greedy new (actual AST diff ID, first old/new boundary kind, frozen public capability) tuples / historical cost; absent divergence contributes no detection feature; unknown remains unknown",
        "all_methods": "full 16-task ranking, no dropping unexposed or equivalent-path tasks; zero marginal gain falls back to cheapest/hash",
        "selector_view": "only opaque diff/component IDs, old exposure categories, public capabilities, old scripted costs, first valid divergence kind/index; no raw requests, tool payloads, answers, edit names, checker results",
        "predicate_diagnostic": "iterate old hook calls in order; only evaluate changed pure hook functions on old arguments, stop at first return difference; unexposed changed hook is unknown",
        "predicate_limit": "valid only for these small immediate-boundary pure hooks, not arbitrary harness code",
        "comparison_budgets": "0, 5, 10, 20, 40, 80, and total historical task cost; stop at first unaffordable ranked task",
        "inclusive_accounting": "candidate first-divergence feature acquisition is charged its attempted request boundaries plus actual dispatches for both tapes/all tasks; baseline metadata processing and local-predicate hook evaluations reported in their own deterministic work counters, never converted to currency",
        "decision": "Any structural distinction vs coarse coverage/tags is explicitly reported. If all replay distinctions are reproduced by the direct-local-predicate control, report NO-GO for unique replay-selector advantage; ranking changes do not override this gate.",
        "hidden_evaluation_order": "all selector outputs and hashes persisted before importing the independent hidden checker",
        "not_preregistration": "local content-hash freeze, no independent timestamp service",
    }


def structural_feature(run):
    detail = run["detail"] or {}
    return {"tape_id": run["tape_id"], "status": run["status"], "boundary_index": detail.get("boundary_index"), "old_kind": detail.get("old_kind"), "new_kind": detail.get("new_kind")}


def exposures(recordings):
    found = set()
    for record in recordings:
        for hook in record["hook_calls"]:
            index = hook["next_boundary_index"]
            kind = record["events"][index]["kind"] if index < len(record["events"]) else "end_of_tape"
            found.add((hook["component_id"], kind))
    return [{"component_id": comp, "boundary_kind": kind} for comp, kind in sorted(found)]


def selector_view(tasks, recordings, runs, diffs):
    return {
        "structural_diff_ids": [{k: diff[k] for k in ("diff_id", "component_id")} for diff in diffs],
        "tasks": [{"task_id": task["id"], "old_exposures": exposures([r for r in recordings if r["task_id"] == task["id"]]), "public_capability_tags": task["capabilities"], "historical_scripted_costs": max(r["scripted_synthetic_units"] for r in recordings if r["task_id"] == task["id"]), "first_valid_divergence_features": [structural_feature(run) for run in runs if run["task_id"] == task["id"]]} for task in tasks],
    }


def isolated_selection(view):
    # The isolated interpreter cannot import neighboring harness/checker files.
    # It retains ordinary process filesystem privileges: not an OS sandbox.
    with tempfile.TemporaryDirectory(prefix="change_replay_selector_") as directory:
        folder = __import__("pathlib").Path(directory)
        shutil.copyfile(ROOT / "selection_probe.py", folder / "selection_probe.py")
        save_json(folder / "input.json", view)
        subprocess.run([sys.executable, "-I", str(folder / "selection_probe.py"), str(folder / "input.json"), str(folder / "output.json")], check=True, cwd=folder, capture_output=True, text=True)
        assert sorted(path.name for path in folder.iterdir()) == ["input.json", "output.json", "selection_probe.py"]
        return json.loads((folder / "output.json").read_text())


def prefix_at_budget(ranking, budget):
    used, selected = 0, []
    for item in ranking:
        if used + item["historical_scripted_costs"] > budget:
            break
        used += item["historical_scripted_costs"]
        selected.append(item["task_id"])
    return selected, used


def compare(change, view, rankings, runs, predicates):
    total = sum(task["historical_scripted_costs"] for task in view["tasks"])
    overhead = sum(run["scripted_synthetic_units"] for run in runs)
    differing_tasks = {run["task_id"] for run in runs if run["status"] == "diverged_unknown"}
    signature_by_task = {task["task_id"]: {(f["old_kind"], f["new_kind"]) for f in task["first_valid_divergence_features"] if f["status"] == "diverged_unknown"} for task in view["tasks"]}
    budget_rows = []
    for budget in sorted({0, 5, 10, 20, 40, 80, total}):
        for method in METHODS:
            for accounting in ("selection_only", "including_feature_construction"):
                acquisition = overhead if accounting == "including_feature_construction" and method == "candidate_replay" else 0
                chosen, used = prefix_at_budget(rankings[method], max(0, budget - acquisition))
                if acquisition > budget:
                    chosen, used = [], 0
                signatures = set().union(*(signature_by_task[task] for task in chosen)) if chosen else set()
                budget_rows.append({"change": change, "method": method, "accounting": accounting, "budget_scripted_units": budget, "required_feature_acquisition_units": acquisition, "acquisition_affordable": acquisition <= budget, "selected_task_ids": chosen, "selected_execution_units": used, "selected_boundary_different_tasks": len(set(chosen) & differing_tasks), "distinct_boundary_kind_pairs": len(signatures)})
    # Same simple coverage/capability evidence, ignoring cost as a ranking aid.
    # A cost difference is not declared a new mechanism signal.
    collisions = []
    def simple_evidence(task):
        exposed = {e["component_id"] for e in task["old_exposures"]}
        touched = sorted(d["diff_id"] for d in view["structural_diff_ids"] if d["component_id"] in exposed)
        return touched, sorted(task["public_capability_tags"])
    for left, right in combinations(view["tasks"], 2):
        if simple_evidence(left) == simple_evidence(right) and signature_by_task[left["task_id"]] != signature_by_task[right["task_id"]]:
            collisions.append([left["task_id"], right["task_id"]])
    agreements = 0
    position_agreements = 0
    for run, probe in zip(runs, predicates):
        divergence = run["status"] == "diverged_unknown"
        if divergence == (probe["status"] == "changed_local_return"):
            agreements += 1
        if divergence and run["detail"].get("boundary_index") == probe["next_boundary_index"]:
            position_agreements += 1
    summary = {
        "unit_count": len(runs), "statuses": dict(Counter(run["status"] for run in runs)),
        "first_boundary_kind_pairs": dict(Counter((run["detail"]["old_kind"] + " -> " + run["detail"]["new_kind"]) for run in runs if run["status"] == "diverged_unknown")),
        "differing_task_ids": sorted(differing_tasks),
        "same_coverage_and_capability_pairs_with_distinct_replay": collisions,
        "predicate_divergence_presence_agreements": agreements,
        "predicate_first_boundary_position_agreements": position_agreements,
        "predicate_hook_evaluations": sum(probe["hook_evaluations"] for probe in predicates),
        "candidate_feature_construction_scripted_units": overhead,
        "candidate_feature_boundary_comparisons": sum(run["boundaries_attempted"] for run in runs),
        "all_task_historical_execution_scripted_units": total,
        "distinct_rankings": len({tuple(item["task_id"] for item in ranking) for ranking in rankings.values()}),
        "global_degenerate": bool(differing_tasks) and len(differing_tasks) == len(view["tasks"]) and all(run["detail"].get("boundary_index") == 0 for run in runs),
    }
    return summary, budget_rows


def main():
    verify_freeze()
    if "hidden_checker" in sys.modules:
        raise RuntimeError("Hidden checker must not be loaded before selection freeze")
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    save_json(ROOT / "implementation_plan.json", frozen_plan())
    tasks = public_tasks()
    base = load_source(BASE)
    recordings = [Harness(task, base, tape).run() for task in tasks for tape in tapes(task["id"])]
    assert len(recordings) == 32 and all(r["status"] == "complete" for r in recordings)
    save_json(out / "h0_request_bound_tapes.json", recordings)
    save_json(out / "tape_freeze.json", {"source_kind": "HANDSCRIPTED", "tape_hashes": {r["tape_id"]: digest(r) for r in recordings}, "artifact_sha256": file_hash(out / "h0_request_bound_tapes.json"), "all_16_tape_pairs_share_action_skeleton": True, "old_model_response_count": sum(r["responses_consumed"] for r in recordings)})
    variant_manifest = write_sources()
    save_json(out / "before_comparisons_freeze.json", {"protocol_manifest_sha256": file_hash(ROOT / "freeze_manifest.json"), "implementation_plan_sha256": file_hash(ROOT / "implementation_plan.json"), "tape_freeze_sha256": file_hash(out / "tape_freeze.json"), "variant_manifest_sha256": file_hash(ROOT / "variant_manifest.json")})
    all_runs, all_predicates, views, selections, summaries, budget_rows = {}, {}, {}, {}, {}, []
    by_task = {task["id"]: task for task in tasks}
    for change, source in VARIANTS.items():
        hooks, diffs = load_source(source), structural_diff(source)
        runs = [Harness(by_task[old["task_id"]], hooks, {"tape_id": old["tape_id"], "responses": []}, reference=old).run() for old in recordings]
        probes = [local_predicate_probe(old, hooks, diffs) for old in recordings]
        view = selector_view(tasks, recordings, runs, diffs)
        rankings = isolated_selection(view)
        all_runs[change], all_predicates[change], views[change], selections[change] = runs, probes, view, rankings
        summaries[change], rows = compare(change, view, rankings, runs, probes)
        budget_rows.extend(rows)
    # Persist all pre-outcome evidence and rank choices before evaluator import.
    save_json(out / "selector_views.json", views)
    save_json(out / "frozen_rankings.json", selections)
    save_json(out / "selection_freeze.json", {"hidden_checker_loaded": "hidden_checker" in sys.modules, "selector_views_sha256": file_hash(out / "selector_views.json"), "frozen_rankings_sha256": file_hash(out / "frozen_rankings.json"), "view_hashes": {name: digest(view) for name, view in views.items()}, "selector_program_sha256": file_hash(ROOT / "selection_probe.py")})
    save_json(out / "local_predicate_diagnostic.json", all_predicates)
    save_json(out / "replay_traces.json", all_runs)
    checker = importlib.import_module("hidden_checker")
    hidden = {"h0": {r["tape_id"]: checker.check(r["task_id"], r["answer"], r["state"], r["events"]) for r in recordings}, "h1": {change: {r["tape_id"]: checker.check(r["task_id"], r["answer"], r["state"], r["events"]) if r["status"] == "historical_path_equivalent" else {"passed": None, "reason": "unknown_diverged_or_unsupported_replay"} for r in runs} for change, runs in all_runs.items()}}
    save_json(out / "hidden_goal_view.json", hidden)
    assert all(result["passed"] for result in hidden["h0"].values())
    predicate_agreement = sum(s["predicate_divergence_presence_agreements"] for s in summaries.values())
    result = {"title": "Synthetic boundary instrumentation validation, not Agent performance", "fixture_task_count": 16, "HANDSCRIPTED_tape_count": 32, "crossed_replay_units": sum(len(runs) for runs in all_runs.values()), "changes": summaries, "decision": "NO-GO for unique replay-selector advantage" if predicate_agreement == 224 else "INCONCLUSIVE: inspect differences from direct-local-predicate diagnostic", "decision_reason": "All observed divergence-presence distinctions are reproduced by direct evaluation of changed pure local hooks on valid old boundary contexts. Replay can add signal beyond coarse coverage/capability tags, but no unique mechanism signal beyond this simple diagnostic is established.", "api_calls": 0, "actual_billed_currency_not_measured": True, "currency_savings_claim": False, "historical_cost_unit": "scripted_synthetic_units", "checker_scope": "Only complete H0 scripts and fully boundary-equivalent replay are checked. All diverged replay goals remain unknown.", "selection_integrity": "Whitelisted structural view, separate isolated Python interpreter in a temporary directory, no checker import or raw payload; not an OS security sandbox.", "public_schema_and_checker_freeze_verified": True, "plan_deviations": [{"id": "D1", "description": "The implementation plan promised separate baseline metadata-processing work counters. These were not implemented; baseline CPU/metadata work remains unmeasured. Candidate boundary/scripted counters and local-predicate hook evaluations are reported. Original plan and before-comparison hash are preserved. No end-to-end runtime or monetary advantage is claimed.", "impact": "Does not affect replay correctness, selected rankings, structural counts, or the NO-GO conclusion."}], "limitations": ["All fixtures, tool environments, mutations, and response tapes are authored synthetic data.", "Two tapes per task vary wording but share the same action skeleton; they are not independent trajectories.", "No live-model performance, regression rate, monetary saving, significance, novelty, or external validity is measured.", "Predicate equivalence here depends on pure, immediate-boundary hooks and does not generalize to arbitrary programs.", "Matched historical path does not establish untested-path safety or model stability.", "The local freeze is content-addressed, not externally preregistered."]}
    save_json(out / "summary.json", result)
    save_json(out / "budget_comparisons.json", budget_rows)
    with (out / "replay_matrix.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["change", "task_id", "tape_id", "status", "first_boundary_index", "old_kind", "new_kind", "responses_consumed", "actual_tool_dispatches", "prefix_committed_writes", "scripted_synthetic_units", "goal_outcome"])
        writer.writeheader()
        for change, runs in all_runs.items():
            for run in runs:
                detail = run["detail"] or {}
                writer.writerow({"change": change, **{key: run[key] for key in ("task_id", "tape_id", "status", "responses_consumed", "actual_tool_dispatches", "scripted_synthetic_units", "goal_outcome")}, "first_boundary_index": detail.get("boundary_index"), "old_kind": detail.get("old_kind"), "new_kind": detail.get("new_kind"), "prefix_committed_writes": run["state"]["committed_writes"]})
    with (out / "budget_comparisons.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(budget_rows[0]))
        writer.writeheader()
        for row in budget_rows:
            writer.writerow({**row, "selected_task_ids": ";".join(row["selected_task_ids"])})
    verify_freeze()
    print(json.dumps({"decision": result["decision"], "replay_units": 224, "h0_checker_passes": 32, "predicate_presence_agreements": predicate_agreement, "changes": summaries}, indent=2))


if __name__ == "__main__":
    main()
