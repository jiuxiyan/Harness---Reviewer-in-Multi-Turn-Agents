"""Label-blind rankings. CLI accepts one sanitized JSON file, emits one file.

Only standard-library imports; no access to fixture, checker, or replay modules.
The runner starts this program in an isolated temporary working directory that
contains only this file and the allowlisted view. This is an auditable data-flow
boundary, not an operating-system security sandbox.
"""
import hashlib
import json
import sys
from fractions import Fraction


def tie(task_id):
    return hashlib.sha256(("change-replay-tie-v1:" + task_id).encode()).hexdigest()


def validate_view(view):
    assert set(view) == {"structural_diff_ids", "tasks"}
    for diff in view["structural_diff_ids"]:
        assert set(diff) == {"diff_id", "component_id"}
    for task in view["tasks"]:
        assert set(task) == {"task_id", "old_exposures", "public_capability_tags", "historical_scripted_costs", "first_valid_divergence_features"}
        assert task["historical_scripted_costs"] > 0
        for exposure in task["old_exposures"]:
            assert set(exposure) == {"component_id", "boundary_kind"}
        for feature in task["first_valid_divergence_features"]:
            assert set(feature) == {"tape_id", "status", "boundary_index", "old_kind", "new_kind"}


def features(task, view, method):
    exposed = {item["component_id"] for item in task["old_exposures"]}
    touched = {item["diff_id"] for item in view["structural_diff_ids"] if item["component_id"] in exposed}
    if method == "changed_component_coverage":
        return {("changed", item) for item in touched}
    if method == "diff_plus_capability":
        return {("contract", item, tag) for item in touched for tag in task["public_capability_tags"]}
    if method == "candidate_replay":
        signatures = {(f["old_kind"], f["new_kind"]) for f in task["first_valid_divergence_features"] if f["status"] == "diverged_unknown"}
        unknown = any(f["status"] == "unsupported_unknown" for f in task["first_valid_divergence_features"])
        if unknown:
            signatures.add(("unknown", "unknown"))
        return {("first_boundary", item, old, new, tag) for item in touched for old, new in signatures for tag in task["public_capability_tags"]}
    return set()


def rank(view, method):
    validate_view(view)
    remaining, covered, output = list(view["tasks"]), set(), []
    while remaining:
        def key(task):
            gain = len(features(task, view, method) - covered)
            return (-Fraction(gain, task["historical_scripted_costs"]), task["historical_scripted_costs"], tie(task["task_id"]))
        selected = min(remaining, key=key)
        evidence = features(selected, view, method)
        gain = len(evidence - covered)
        score = Fraction(gain, selected["historical_scripted_costs"])
        output.append({"task_id": selected["task_id"], "historical_scripted_costs": selected["historical_scripted_costs"], "new_structural_features": gain, "score_numerator": score.numerator, "score_denominator": score.denominator, "stable_tie_sha256": tie(selected["task_id"])})
        covered |= evidence
        remaining.remove(selected)
    return output


def all_rankings(view):
    return {method: rank(view, method) for method in ("cheapest_first", "changed_component_coverage", "diff_plus_capability", "candidate_replay")}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as source:
        view = json.load(source)
    with open(sys.argv[2], "w", encoding="utf-8") as destination:
        json.dump(all_rankings(view), destination, indent=2, sort_keys=True)
        destination.write("\n")
