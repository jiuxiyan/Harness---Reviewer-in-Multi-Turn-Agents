import ast
import json
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from contract_sandbox.public import (Action, View, INITIAL_HISTORY, TASK_KEY, PAYLOAD,
                                     canonical, DEADLINE)
from contract_sandbox.evidence import (CONTRACTS, CONDITIONS, Contract, make_evidence)
from contract_sandbox.world import World
from contract_sandbox.policies import Conservative, ImmediateRetry, Overconfident
from contract_sandbox.evaluation import (SCENARIOS, Scenario, run_episode, policy_factories, audit, check_run_integrity)
from contract_sandbox.diagnostic import (all_witnesses, compatible_worlds, assess_claim,
                                         observed)


class WorldTests(unittest.TestCase):
    def test_grid_is_120_distinct_scenarios(self):
        self.assertEqual(len(CONTRACTS), 8)
        self.assertEqual(len(SCENARIOS), 120)
        self.assertEqual(len({s.identity for s in SCENARIOS}), 120)

    def test_retention_boundary_and_replay_does_not_refresh(self):
        world = World(Contract(2, "terminal", None), "accepted_pending")
        world.create_record(PAYLOAD, TASK_KEY)  # tick1 is retained
        self.assertEqual(len(world.generations), 1)
        world.advance(2)
        world.create_record(PAYLOAD, TASK_KEY)  # exact expiry
        self.assertEqual(len(world.generations), 2)
        self.assertEqual([g.accepted for g in world.generations], [0, 2])
        world.drain_accepted_work()
        self.assertEqual([e["tick"] for e in world.ledger], [4, 6])

    def test_pending_retries_within_ttl_never_duplicate(self):
        world = World(Contract(8, "terminal", None), "accepted_pending")
        for tick in range(1, 8):
            world.advance(tick)
            self.assertEqual(world.create_record(PAYLOAD, TASK_KEY), "ACK")
        self.assertEqual(len(world.generations), 1)
        self.assertEqual(len(world.ledger), 1)

    def test_lag_is_full_state_snapshot_and_boundary_is_inclusive(self):
        world = World(Contract(2, "lagging", 2), "accepted_pending")
        self.assertEqual(world.status(TASK_KEY), "ABSENT")  # snapshot -3
        world.advance(4)
        self.assertEqual(world.status(TASK_KEY), "PENDING")  # snapshot 0
        world.advance(5)
        self.assertEqual(world.status(TASK_KEY), "PENDING")  # snapshot 1
        world.advance(6)
        self.assertEqual(world.status(TASK_KEY), "COMMITTED")  # snapshot 2

    def test_terminal_status_survives_expiry(self):
        world = World(Contract(2, "terminal", None), "accepted_pending")
        world.advance(3)
        self.assertEqual(world.status(TASK_KEY), "PENDING")
        world.advance(4)
        self.assertEqual(world.status(TASK_KEY), "COMMITTED")
        world.advance(20)
        self.assertEqual(world.status(TASK_KEY), "COMMITTED")

    def test_same_tick_mutation_is_in_snapshot(self):
        world = World(Contract(2, "lagging", 2), "rejected")
        world.create_record(PAYLOAD, TASK_KEY)
        world.advance(5)
        self.assertEqual(world.status(TASK_KEY), "PENDING")  # accepted tick1

    def test_payload_conflict_even_after_expiry(self):
        world = World(Contract(2, "terminal", 2), "immediate_commit")
        for tick in (1, 2, 10):
            world.advance(tick)
            self.assertEqual(world.create_record("different", TASK_KEY), "CONFLICT")
        self.assertEqual(len(world.generations), 1)

    def test_key_scope_service_tenant_operation(self):
        world = World(Contract(8, "terminal", 2), "immediate_commit")
        for overrides in ({"service": "other"}, {"tenant": "other"}, {"operation": "other"}):
            self.assertEqual(world.create_record("other-payload", TASK_KEY, **overrides), "ACK")
        self.assertEqual(len(world.generations), 4)

    def test_bound_respected_for_every_base_outcome(self):
        for contract in CONTRACTS:
            for outcome in ("rejected", "immediate_commit", "accepted_pending"):
                world = World(contract, outcome)
                world.create_record(PAYLOAD, TASK_KEY)
                if contract.processing_bound:
                    self.assertTrue(all(g.due-g.accepted <= 2 for g in world.generations))

    def test_ack_is_not_commit(self):
        world = World(Contract(8, "terminal", 2), "rejected")
        self.assertEqual(world.create_record(PAYLOAD, TASK_KEY), "ACK")
        self.assertEqual(world.ledger, [])
        self.assertEqual(world.status(TASK_KEY), "PENDING")

    def test_unknown_continuation_stays_pending_at_horizon(self):
        world = World(Contract(8, "terminal", None), "accepted_pending", True)
        world.advance(6)
        self.assertEqual(world.status(TASK_KEY), "PENDING")
        self.assertEqual(world.ledger, [])
        with self.assertRaises(ValueError):
            World(Contract(8, "terminal", 2), "accepted_pending", True)


class EvidenceTests(unittest.TestCase):
    def test_successful_demo_bytes_identical_everywhere(self):
        demos = {canonical(make_evidence(s.contract, s.condition)["successful_demonstrations"]) for s in SCENARIOS}
        self.assertEqual(len(demos), 1)

    def test_demo_is_executable_for_every_contract(self):
        for contract in CONTRACTS:
            world = World(contract, "rejected")
            # Separate run, with its own zero origin, creates the same relative trace.
            world.create_record("demo-value", "demo-key")
            world.advance(9)
            self.assertEqual(world.status("demo-key"), "COMMITTED")

    def test_omissions_remove_discriminating_field(self):
        for condition, field, alternatives in (
            ("retention_omitted", "retention_ticks", [Contract(2,"terminal",2), Contract(8,"terminal",2)]),
            ("status_omitted", "negative_status", [Contract(2,"terminal",2), Contract(2,"lagging",2)]),
            ("processing_omitted", "processing_bound_ticks", [Contract(2,"terminal",2), Contract(2,"terminal",None)]),
        ):
            ea, eb = (make_evidence(c, condition) for c in alternatives)
            self.assertEqual(canonical(ea), canonical(eb))
            self.assertEqual(ea["contract_claims"][field]["state"], "unknown")

    def test_conflict_is_not_resolved_and_candidates_nonempty(self):
        evidence = make_evidence(Contract(2,"terminal",2), "status_contradiction")
        self.assertEqual(evidence["contract_claims"]["negative_status"]["state"], "conflict")
        worlds = compatible_worlds(evidence, INITIAL_HISTORY)
        self.assertEqual({w.contract.negative_status for w in worlds}, {"terminal","lagging"})
        result = assess_claim(evidence, INITIAL_HISTORY, 1)
        self.assertEqual(result["evidence_status"], "UNRESOLVED_CONFLICT")
        self.assertFalse(result["success_supported_in_bounded_model"])

    def test_no_vacuous_proof_for_empty_model(self):
        evidence = make_evidence(Contract(2,"terminal",2), "complete")
        evidence["contract_claims"]["retention_ticks"]["value"] = 99
        result = assess_claim(evidence, INITIAL_HISTORY, 1)
        self.assertEqual(result["compatible_world_count"], 0)
        self.assertFalse(result["success_supported_in_bounded_model"])

    def test_sentinel_prevents_bound_from_success_sample(self):
        evidence = make_evidence(Contract(2,"terminal",None), "processing_omitted")
        world = World(Contract(2,"terminal",None), "accepted_pending")
        history = observed(world, [(1, "status")])
        result = assess_claim(evidence, history, 6)
        self.assertTrue(result["contains_pending_continuation"])
        self.assertTrue(result["success_refuted_in_some_model"])
        self.assertFalse(result["universal_certificate"])

    def test_sentinel_covers_new_acceptance_after_rejection(self):
        evidence = make_evidence(Contract(2,"terminal",None), "complete")
        world = World(Contract(2,"terminal",None), "rejected")
        history = observed(world, [(1, "status"), (2, "create")])
        result = assess_claim(evidence, history, 6)
        self.assertTrue(result["contains_pending_continuation"])
        self.assertTrue(result["success_refuted_in_some_model"])

    def test_all_matched_history_witnesses(self):
        witnesses = all_witnesses()
        self.assertEqual(len(witnesses), 4)
        self.assertTrue(all(w["identical_predecision_bytes"] for w in witnesses))

    def test_policy_module_has_no_evaluator_imports(self):
        source = Path("contract_sandbox/policies.py").read_text()
        tree = ast.parse(source)
        imported = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertEqual(imported, ["public"])
        self.assertFalse(any(isinstance(n, ast.Import) for n in ast.walk(tree)))

    def test_no_private_fields_in_policy_view(self):
        seen = []
        class Capture(Conservative):
            def choose(self, view):
                seen.append(view.public())
                return super().choose(view)
        for scenario in SCENARIOS:
            run_episode(scenario, Capture())
        forbidden = {"scenario_id", "initial_outcome", "seed", "ledger", "contract_id",
                     "generations", "due", "pending_continuation", "abstract_continuation", "condition"}
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for x in value.values(): check(x)
            elif isinstance(value, list):
                for x in value: check(x)
        check(seen)

    def test_mutating_parsed_evidence_cannot_change_view(self):
        view = View(canonical(make_evidence(CONTRACTS[0], "complete")), canonical(INITIAL_HISTORY), 1, True, 6)
        before = canonical(view.public())
        value = view.evidence; value["task"]["key"] = "bad"
        history = view.history; history.clear()
        self.assertEqual(before, canonical(view.public()))


class RunnerAuditTests(unittest.TestCase):
    def test_integrity_checker_detects_missing_scenarios(self):
        failures = check_run_integrity([], [])
        self.assertTrue(failures)
        self.assertTrue(any("120 scenarios" in failure for failure in failures))

    def test_initial_inputs_identical_across_methods(self):
        for scenario in SCENARIOS:
            rows = [run_episode(scenario, factory()) for factory in policy_factories(scenario.contract)]
            self.assertEqual(len({r["initial_input_sha256"] for r in rows}), 1)

    def test_safe_controls_and_immediate_null_baseline(self):
        for scenario in SCENARIOS:
            for factory in policy_factories(scenario.contract):
                policy = factory()
                if policy.name == "overconfident_faulty": continue
                result = run_episode(scenario, policy)
                self.assertFalse(result["metrics"]["unsafe"], (scenario, policy.name))

    def test_complete_conservative_equals_full_reference(self):
        for scenario in SCENARIOS:
            if scenario.condition != "complete": continue
            factories = policy_factories(scenario.contract)
            a,b = run_episode(scenario, factories[0]()), run_episode(scenario, factories[-1]())
            self.assertEqual(a["public_transcript"], b["public_transcript"])
            self.assertEqual(a["metrics"], b["metrics"])

    def test_faulty_control_triggers_each_primary_checker(self):
        results = [run_episode(s, Overconfident())["metrics"] for s in SCENARIOS]
        self.assertTrue(any(r["duplicate_effects"] for r in results))
        self.assertTrue(any(r["false_success"] for r in results))
        self.assertTrue(any(r["duplicate_effects"] and r["false_success"] for r in results))
        self.assertEqual(sum(r["unsafe"] for r in results), sum(r["duplicate_effects"] or r["false_success"] for r in results))

    def test_drain_catches_post_deadline_duplicate(self):
        world = World(Contract(2,"terminal",None), "accepted_pending")
        world.advance(3); world.create_record(PAYLOAD, TASK_KEY)
        world.advance(6)
        self.assertEqual(len(world.ledger), 1)
        world.drain_accepted_work()
        self.assertEqual(len(world.ledger), 2)
        self.assertEqual(world.ledger[-1]["tick"], 7)

    def test_checker_catches_false_report_key_payload_and_deadline(self):
        evidence = make_evidence(CONTRACTS[0], "complete")
        actions = [{"tick":7,"action":Action("create", key="other", payload="other", deadline=7).public()}]
        result = audit(evidence, actions, [{"tick":1}], [], [], 7, 7)
        for flag in ("unsafe", "false_success", "key_violation", "payload_violation", "deadline_violation", "budget_violation"):
            self.assertTrue(result[flag], flag)

    def test_success_truth_uses_report_time_not_drain_time(self):
        evidence = make_evidence(CONTRACTS[0], "complete")
        ledger = [{"scope":["records","example-tenant","create_record",TASK_KEY], "tick":4}]
        result = audit(evidence, [], [{"tick":2}], ledger, [], 2, 1)
        self.assertTrue(result["false_success"])

    def test_checker_reads_json_roundtrip_pending_exports(self):
        world = World(Contract(2,"terminal",None), "accepted_pending", True)
        generations = json.loads(canonical([asdict(g) for g in world.generations]))
        evidence = make_evidence(world.contract, "complete")
        result = audit(evidence, [], [], [], generations, 6, 0)
        self.assertEqual(result["pending_after_drain"], 1)

    def test_outputs_are_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for output in (a,b):
                subprocess.run([sys.executable, "-m", "contract_sandbox.run", "--out", output], check=True, stdout=subprocess.DEVNULL)
            files = sorted(p.name for p in Path(a).iterdir())
            self.assertEqual(files, sorted(p.name for p in Path(b).iterdir()))
            for name in files:
                self.assertEqual((Path(a)/name).read_bytes(), (Path(b)/name).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
