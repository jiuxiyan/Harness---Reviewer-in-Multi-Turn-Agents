"""Reproduce deterministic local artifacts: python -m contract_sandbox.run"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from .evaluation import SCENARIOS, run_episode, policy_factories, summarize, check_run_integrity
from .diagnostic import all_witnesses, assess_claim
from .public import canonical


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for scenario in SCENARIOS:
        episode_rows = []
        for factory in policy_factories(scenario.contract):
            row = run_episode(scenario, factory())
            transcript = row["public_transcript"]
            row["bounded_model_claim_diagnostic"] = (
                assess_claim(transcript["evidence"], transcript["history"], transcript["claims"][0]["tick"])
                if transcript["claims"] else None)
            episode_rows.append(row)
        assert len({r["initial_input_sha256"] for r in episode_rows}) == 1
        rows.extend(episode_rows)
    summary = summarize(rows)
    for group in summary:
        subset = [r for r in rows if r["method"] == group["method"] and
                  (group["condition"] == "ALL" or r["condition"] == group["condition"])]
        group["reported_success_count"] = sum(bool(r["public_transcript"]["claims"]) for r in subset)
        group["success_claims_refuted_in_bounded_model"] = sum(
            bool(r["bounded_model_claim_diagnostic"] and r["bounded_model_claim_diagnostic"]["success_refuted_in_some_model"]) for r in subset)
    witness = all_witnesses()
    integrity_failures = check_run_integrity(rows, witness)
    if integrity_failures:
        write_json(args.out/"integrity_failures.json", integrity_failures)
        raise AssertionError("Scenario integrity checks failed; see integrity_failures.json")
    metadata = {
        "stage": "API-free feasibility and measurement integrity only",
        "llm_calls": 0, "api_calls": 0, "network_calls": 0,
        "base_scenarios": len(SCENARIOS), "methods": len({r["method"] for r in rows}),
        "method_episodes": len(rows), "horizon_ticks": 6, "max_tool_calls": 6,
        "scenario_integrity_failures": integrity_failures,
        "full_contract_reference": "Privileged contract control, not an optimal oracle or performance ceiling; no hidden-outcome access",
        "diagnostic": "Finite model family plus unknown-processing continuation; never a universal safety certificate",
        "limitations": ["No actual LLM was called", "No model performance measured", "No novelty established",
                        "Single initial fault; subsequent calls reliable; no concurrency",
                        "Immediate same-key retry is safe on all configured retention values; omission is not unavoidable failure",
                        "Successful demonstrations are reset runs and do not advance the challenge clock",
                        "Objective truth and evidential support are reported separately"],
    }
    write_json(args.out/"metadata.json", metadata)
    write_json(args.out/"episodes.json", rows)
    write_json(args.out/"summary.json", summary)
    write_json(args.out/"witnesses.json", witness)
    with (args.out/"summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0]))
        writer.writeheader(); writer.writerows(summary)
    with (args.out/"episodes.csv").open("w", newline="") as handle:
        flattened = [{"scenario_id": r["scenario_id"], "method": r["method"],
                      "condition": r["condition"], **r["metrics"]} for r in rows]
        writer = csv.DictWriter(handle, fieldnames=list(flattened[0]))
        writer.writeheader(); writer.writerows(flattened)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.out.iterdir())
              if p.is_file() and p.name in {"metadata.json", "episodes.json", "summary.json", "witnesses.json", "summary.csv", "episodes.csv"}}
    write_json(args.out/"sha256.json", hashes)
    print(canonical(metadata))
    for group in summary:
        if group["condition"] == "ALL":
            print(canonical(group))


if __name__ == "__main__":
    main()
