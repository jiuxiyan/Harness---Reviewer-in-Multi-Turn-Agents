"""stdlib tests: offline wire checks, not model behavior/effectiveness tests."""
import copy
import dataclasses
import hashlib
import json
import pathlib
import unittest
from unittest.mock import patch

import no_api_guard as guard
import backend_checks as backend
from interventions import (
    MODE, SOURCE_COMMIT, FrozenJSON, Classification, ArmKind, Usage, Ledger,
    BudgetError, MissingApproval, ProviderConfigError, WHOLE_BLOCK, PREPARATION,
    canonical, digest, parse_json, original_action, classify_q, make_views,
    check_privacy, execution_id, make_arm, run_block, require_mode, provider_request,
)
from offline_backend import load_root, restore_checkpoint, execute_read, shadow_analysis, PILOT

HERE = pathlib.Path(__file__).resolve().parent


class DryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root, cls.catalog, cls.names = load_root()
        cls.same = classify_q(cls.root, canonical(original_action(cls.root)), cls.catalog, cls.names)
        cls.changed = classify_q(cls.root, canonical({"name": "get_details_by_id", "arguments": {"id": "L1002"}}), cls.catalog, cls.names)
        cls.execute = lambda action, call_id: execute_read(cls.root, action, call_id)

    def proposal(self, action):
        return classify_q(self.root, canonical(action), self.catalog, self.names)

    def run_arms(self, q=None, s=None, units=WHOLE_BLOCK):
        ledger = Ledger(units)
        arms = run_block(self.root, q or self.changed, s or self.same,
                         type(self).execute, ledger, "SCRIPTED FIXTURE critique about line details.",
                         shadow=lambda action: shadow_analysis(self.root, action))
        return arms, ledger

    def test_01_plan_frozen_before_results(self):
        frozen = json.loads((HERE / "plan_freeze.json").read_text())
        self.assertEqual(frozen["spec_sha256"], hashlib.sha256((HERE / "SPEC.md").read_bytes()).hexdigest())
        self.assertEqual(frozen["stage"], "PRE_IMPLEMENTATION_PRE_TEST")

    def test_02_checkpoint_exact_boundary_and_metadata(self):
        o, _ = restore_checkpoint(self.root.private_checkpoint.copy())
        expected = self.root.private_checkpoint.copy()
        self.assertEqual(backend.orch_state(o, False), expected["raw_checkpoint"])
        self.assertEqual(digest(backend.orch_state(o, False)), self.root.raw_checkpoint_sha256)
        self.assertEqual(backend.dump(o.message), self.root.original_proposal.copy())
        self.assertEqual(o.message.tool_calls[0].id, "pending-shared-proposal")
        self.assertEqual(self.root.source_commit, SOURCE_COMMIT)

    def test_03_source_effective_projection_preserved(self):
        o, _ = restore_checkpoint(self.root.private_checkpoint.copy())
        actual = backend.effective_views(o)
        self.assertEqual(self.root.actor_projection.copy(), actual["agent"])
        self.assertEqual(self.root.user_projection.copy(), actual["user"])
        views = make_views(self.root)
        self.assertEqual(views.user.copy()["source_effective_user_messages"], actual["user"])
        self.assertEqual(views.actor.copy()["source_effective_actor_messages"], actual["agent"])

    def test_04_frozen_nested_objects_and_raw_proposal_separate(self):
        before = self.root.original_proposal.text
        changed = self.root.original_proposal.copy()
        changed["tool_calls"][0]["arguments"]["phone_number"] = "edited"
        self.assertEqual(self.root.original_proposal.text, before)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self.root.seed = 8
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self.changed.raw_q = "edited"
        self.assertNotEqual(digest(self.changed.action), self.root.original_proposal_sha256)
        self.assertEqual(digest(self.root.original_proposal), self.root.original_proposal_sha256)

    def test_05_canonical_hash_rejects_lossy_json(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))
        self.assertNotEqual(digest([1, 2]), digest([2, 1]))
        with self.assertRaises(ValueError): canonical({"a": float("nan")})
        with self.assertRaises(TypeError): canonical({1: "a"})
        with self.assertRaises(ValueError): parse_json('{"a":1,"a":2}')
        with self.assertRaises(ValueError): parse_json('{"a":NaN}')

    def test_06_deterministic_execution_ids_from_public_inputs(self):
        action = self.changed.action.copy()
        self.assertEqual(execution_id(self.root, action), execution_id(self.root, copy.deepcopy(action)))
        self.assertNotEqual(execution_id(self.root, action), execution_id(dataclasses.replace(self.root, seed=1), action))
        self.assertEqual(execution_id(self.root, original_action(self.root)), "pending-shared-proposal")
        self.assertNotEqual(execution_id(self.root, action), "pending-shared-proposal")
        o, _ = restore_checkpoint(self.root.private_checkpoint.copy())
        self.assertEqual(backend.rng_state(), self.root.private_checkpoint.copy()["state"]["rng"])

    def test_07_full_actor_tool_catalog_not_restricted(self):
        views = make_views(self.root)
        catalog = views.actor.copy()["tools"]
        self.assertEqual(len(catalog), len(self.catalog))
        self.assertGreater(len(catalog), len(self.names))
        self.assertEqual(views.reviewer.copy()["tools"], catalog)
        self.assertEqual(views.actor.copy()["public_study_constraint"]["allowed_intervention_tool_names"], sorted(self.names))

    def test_08_baseline_next_result_matches_frozen_original_live(self):
        b = make_arm(self.root, ArmKind.B, None, type(self).execute)
        original_live = json.loads((PILOT / "results/task_0_live_continuation.json").read_text())
        self.assertEqual(backend.normalize(b.receipt.raw_tool_response.copy()), original_live["next_output"])

    def test_09_noop_B_A_byteidentical_input_and_state(self):
        b = make_arm(self.root, ArmKind.B, None, type(self).execute)
        a = make_arm(self.root, ArmKind.A, self.same, type(self).execute)
        self.assertEqual(b.input_views.actor.text, a.input_views.actor.text)
        self.assertEqual(b.receipt.public.text, a.receipt.public.text)
        self.assertEqual(b.receipt.environment_after_sha256, a.receipt.environment_after_sha256)
        self.assertEqual(b.exact_preintervention_checkpoint_sha256, a.exact_preintervention_checkpoint_sha256)

    def test_10_A_P_same_action_only_declared_packet_difference(self):
        a = make_arm(self.root, ArmKind.A, self.changed, type(self).execute)
        p = make_arm(self.root, ArmKind.P, self.changed, type(self).execute, "SCRIPTED critique")
        self.assertEqual(a.executed_action, p.executed_action)
        self.assertEqual(a.execution_id, p.execution_id)
        self.assertEqual(a.receipt.public, p.receipt.public)
        ai, pi = a.input_views.actor.copy(), p.input_views.actor.copy()
        self.assertNotEqual(ai.pop("additional_packet"), pi.pop("additional_packet"))
        self.assertEqual(ai, pi)
        self.assertEqual(a.input_views.user, p.input_views.user)
        self.assertEqual(a.input_views.reviewer, p.input_views.reviewer)

    def test_11_P_unchanged_action_critique_is_not_noop(self):
        b = make_arm(self.root, ArmKind.B, None, type(self).execute)
        p = make_arm(self.root, ArmKind.P, self.same, type(self).execute, "SCRIPTED unchanged-action critique")
        self.assertEqual(b.executed_action, p.executed_action)
        self.assertNotEqual(b.input_views.actor, p.input_views.actor)

    def test_12_override_never_fakes_original_history_or_result_pairing(self):
        a = make_arm(self.root, ArmKind.A, self.changed, type(self).execute)
        public = a.receipt.public.copy()
        self.assertEqual(public["original_proposal"]["action"], original_action(self.root))
        self.assertEqual(public["original_proposal"]["authored_by"], "actor")
        self.assertEqual(public["original_disposition"], "suppressed_without_tool_result")
        self.assertEqual(public["recommended_by"], "reviewer_fixture")
        self.assertEqual(public["actual_tool_result"][0]["tool_call_id"], a.execution_id)
        self.assertNotEqual(public["actual_tool_result"][0]["tool_call_id"], public["original_proposal"]["call_id"])
        messages = a.input_views.actor.copy()["source_effective_actor_messages"]
        self.assertEqual(messages, self.root.actor_projection.copy())
        self.assertEqual(messages[-1]["tool_calls"][0]["id"], "pending-shared-proposal")
        self.assertEqual(messages[-1]["tool_calls"][0]["function"]["name"], "get_customer_by_phone")
        self.assertIn("timestamp", a.receipt.raw_tool_response.copy())
        self.assertNotIn("timestamp", public["actual_tool_result"][0])

    def test_13_private_canary_and_structural_field_exclusion(self):
        canaries = ("PRIVATE_GOAL_CANARY_58be44", "PRIVATE_SOURCE_CANARY_0308ad")
        private = self.root.private_checkpoint.copy()
        private["private_oracle"] = {"values": canaries[0], "source_ids": [canaries[1]]}
        root = dataclasses.replace(self.root, private_checkpoint=FrozenJSON.of(private))
        views = make_views(root, private_canaries=canaries)
        for view in (views.actor, views.reviewer, views.user):
            check_privacy(view, canaries)
            self.assertTrue(all(canary not in view.text for canary in canaries))
        with self.assertRaises(ValueError): make_views(root, packet={"content": canaries[0]}, private_canaries=canaries)
        with self.assertRaises(ValueError): check_privacy({"x": {"evaluation_criteria": {}}})
        with self.assertRaises(ValueError): check_privacy({"source_ids": []})

    def test_14_legitimate_public_goal_words_are_allowed(self):
        check_privacy({"content": "My goal is excellent speed and working mobile data. I ran a speed test."})
        self.assertIn("instructions", self.root.user_projection.text.lower())
        make_views(self.root)

    def test_15_S_parse_invalid_falls_back_once_honestly(self):
        invalid = classify_q(self.root, "{not JSON", self.catalog, self.names)
        s = make_arm(self.root, ArmKind.S, invalid, type(self).execute)
        self.assertEqual(s.executed_action.copy(), original_action(self.root))
        self.assertEqual(s.receipt.public.copy()["decision"], "fallback_original")
        self.assertIn("unparseable", s.receipt.public.copy()["neutral_factual_receipt"])
        self.assertEqual(s.proposal.draw_index, 1)
        arms, ledger = self.run_arms(s=invalid)
        self.assertEqual(len(arms), 4)
        self.assertEqual([row.component for row in ledger.rows].count("self_reconsider"), 1)
        self.assertEqual(ledger.report()["total_q_draws"], 1)

    def test_16_S_public_schema_invalid_fallback(self):
        invalid = self.proposal({"name": "get_details_by_id", "arguments": {}})
        self.assertIs(invalid.classification, Classification.INVALID)
        s = make_arm(self.root, ArmKind.S, invalid, type(self).execute)
        self.assertEqual(s.receipt.public.copy()["decision"], "fallback_original")
        typed = self.proposal({"name": "get_details_by_id", "arguments": {"id": 14}})
        self.assertIs(typed.classification, Classification.INVALID)
        extra = self.proposal({"name": "get_details_by_id", "arguments": {"id": "L1002", "secret": True}})
        self.assertIs(extra.classification, Classification.INVALID)

    def test_17_valid_format_official_tool_error_remains_outcome(self):
        rejected = self.proposal({"name": "get_details_by_id", "arguments": {"id": "MISSING_FIXTURE_RECORD"}})
        self.assertIs(rejected.classification, Classification.VALID_CHANGED)
        s = make_arm(self.root, ArmKind.S, rejected, type(self).execute)
        self.assertTrue(s.receipt.public.copy()["tool_error"])
        self.assertEqual(s.executed_action, rejected.action)
        self.assertEqual(s.receipt.public.copy()["decision"], "external_override_executed")
        self.assertIn("no_inherited_fidelity_claim", s.fidelity)

    def test_18_Q_invalid_logged_excluded_no_resampling(self):
        invalid = classify_q(self.root, "broken fixture", self.catalog, self.names)
        called = []
        ledger = Ledger(WHOLE_BLOCK)
        arms = run_block(self.root, invalid, self.same, lambda *args: called.append(args), ledger, "", shadow=lambda a: called.append(a))
        self.assertEqual(arms, ())
        self.assertEqual(called, [])
        self.assertEqual(ledger.report()["proposal_counts_before_conditioning"]["invalid"], 1)
        self.assertEqual(ledger.report()["started_arms"], [])
        self.assertEqual(ledger.report()["spent"], sum(x.test_units for x in PREPARATION[:3]))
        with self.assertRaises(ValueError): ledger.record_proposal(self.changed)

    def test_19_Q_out_of_scope_public_constraint_excluded(self):
        outside_name = next(name for name in self.catalog if name not in self.names)
        outside = self.proposal({"name": outside_name, "arguments": {}})
        self.assertIs(outside.classification, Classification.OUT_OF_SCOPE)
        called = []
        ledger = Ledger(WHOLE_BLOCK)
        arms = run_block(self.root, outside, self.same, lambda *a: called.append(a), ledger, "", shadow=lambda a: called.append(a))
        self.assertEqual(arms, ())
        self.assertEqual(called, [])
        self.assertEqual(ledger.report()["proposal_counts_before_conditioning"]["out_of_scope"], 1)
        multi = classify_q(self.root, "[]", self.catalog, self.names)
        self.assertIs(multi.classification, Classification.OUT_OF_SCOPE)
        with self.assertRaises(ValueError): make_arm(self.root, ArmKind.S, outside, type(self).execute)

    def test_20_unchanged_Q_recorded_before_conditioning(self):
        arms, ledger = self.run_arms(q=self.same)
        self.assertEqual(len(arms), 4)
        self.assertEqual(ledger.proposal_counts["unchanged"], 1)
        self.assertEqual(ledger.timeline[0], "raw_q_recorded_before_outcomes")
        self.assertLess(ledger.timeline.index("whole_four_arm_block_reserved"), ledger.timeline.index("start_B"))
        self.assertLess(ledger.timeline.index("raw_q_recorded_before_outcomes"), ledger.timeline.index("shadow_after_q_record_and_full_reservation"))

    def test_21_shadow_fresh_isolation_and_private_analysis_only(self):
        before = self.root.private_checkpoint.text
        o, _ = restore_checkpoint(self.root.private_checkpoint.copy())
        untouched = canonical(backend.orch_state(o, False))
        analysis = shadow_analysis(self.root, self.changed.action.copy())
        self.assertTrue(analysis["private_only_never_feedback_or_gate"])
        self.assertEqual(self.root.private_checkpoint.text, before)
        self.assertEqual(canonical(backend.orch_state(o, False)), untouched)
        a = make_arm(self.root, ArmKind.A, self.changed, type(self).execute)
        self.assertNotIn("analysis_stratum", a.input_views.actor.text)
        self.assertNotIn("analysis_stratum", a.input_views.reviewer.text)
        self.assertNotIn("analysis_stratum", a.input_views.user.text)

    def test_22_budget_insufficient_starts_zero_arms_or_shadow(self):
        ledger = Ledger(WHOLE_BLOCK - 1)
        called = []
        with self.assertRaises(BudgetError):
            run_block(self.root, self.changed, self.same, lambda *a: called.append(a), ledger, "", shadow=lambda a: called.append(a))
        self.assertEqual(called, [])
        self.assertEqual(ledger.started, set())
        self.assertEqual(ledger.reserved, 0)
        self.assertEqual(ledger.available, WHOLE_BLOCK - 1 - sum(x.test_units for x in PREPARATION[:4]))
        self.assertEqual(ledger.report()["spent"], sum(x.test_units for x in PREPARATION[:4]))
        self.assertEqual(ledger.proposal_counts["valid_changed"], 1)

    def test_23_budget_fees_retry_counts_and_full_block(self):
        arms, ledger = self.run_arms()
        self.assertEqual(len(arms), 4)
        self.assertEqual(ledger.reserved, WHOLE_BLOCK)
        self.assertEqual(ledger.report()["spent"], WHOLE_BLOCK - 1)
        for component in ("root_preparation", "proposal_preparation", "reviewer", "self_reconsider", "shadow", "actor", "user", "tool_execution"):
            self.assertIn(component, [row.component for row in ledger.rows])
        self.assertEqual(sum(row.logical_calls for row in ledger.rows if row.component == "actor"), 4)
        ledger.charge(Usage("retries", "S", 1, 1, retry=True))
        self.assertEqual(ledger.report()["retry_count"], 1)
        self.assertEqual(ledger.report()["spent"], WHOLE_BLOCK)
        with self.assertRaises(BudgetError): ledger.charge(Usage("retries", "S", 1, 1, retry=True))
        self.assertEqual(ledger.report()["retry_count"], 1)
        self.assertTrue(all(row.actual_api_calls == 0 and row.fixture_usage for row in ledger.rows))
        with self.assertRaises(ValueError): Usage("actor", "B", 1, 1, actual_api_calls=1)

    def test_24_start_without_reservation_and_duplicate_start_rejected(self):
        ledger = Ledger(WHOLE_BLOCK)
        with self.assertRaises(BudgetError): ledger.start(ArmKind.B)
        ledger.reserve_four_arm_block()
        ledger.start(ArmKind.B)
        with self.assertRaises(BudgetError): ledger.start(ArmKind.B)
        with self.assertRaises(BudgetError): ledger.reserve_four_arm_block()

    def test_25_guard_negative_probes(self):
        probes = guard.negative_tests()
        self.assertEqual({p["test"] for p in probes}, {"model", "network", "dotenv"})
        self.assertTrue(all(p["blocked"] for p in probes))
        self.assertEqual(guard.EVENTS, [])

    def test_26_live_fails_before_client_or_environment_key_read(self):
        calls = []
        with patch("os.getenv", side_effect=AssertionError("Credential read attempted")):
            with self.assertRaises(MissingApproval): require_mode("live")
            with self.assertRaises(ProviderConfigError):
                provider_request(config={"approved": True}, client_factory=lambda: calls.append(True))
        self.assertEqual(calls, [])
        require_mode(MODE)

    def test_27_fixture_stage_flags_and_no_causal_terminal_results(self):
        a = make_arm(self.root, ArmKind.A, self.changed, type(self).execute)
        self.assertEqual(a.mode, MODE)
        self.assertTrue(a.fixture)
        self.assertEqual(a.actual_api_calls, 0)
        self.assertIsNone(a.terminal_result)
        self.assertIsNone(a.causal_harm)
        self.assertIn("BLOCKED", a.input_views.provider_status)
        self.assertIn("not generated", a.fixture_actor_response)
        self.assertIn("not generated", a.fixture_user_response)

    def test_28_actual_response_id_mismatch_fails_closed(self):
        def bad(action, call_id):
            result = type(self).execute(action, call_id)
            result["raw_tool_response"]["id"] = "different_call"
            return result
        with self.assertRaises(ValueError): make_arm(self.root, ArmKind.A, self.changed, bad)

    def test_29_nonfinite_exponent_is_countable_invalid_proposal(self):
        q = classify_q(self.root, '{"name":"get_bills_for_customer","arguments":{"customer_id":"C1001","limit":1e999}}', self.catalog, self.names)
        self.assertIs(q.classification, Classification.INVALID)
        ledger = Ledger(WHOLE_BLOCK)
        ledger.record_proposal(q)
        self.assertEqual(ledger.proposal_counts["invalid"], 1)

    def test_30_user_side_and_multicall_outside_public_scope(self):
        user_call = self.proposal({"name": "run_speed_test", "arguments": {}})
        self.assertIs(user_call.classification, Classification.OUT_OF_SCOPE)
        calls = classify_q(self.root, '{"tool_calls":[]}', self.catalog, self.names)
        self.assertIs(calls.classification, Classification.OUT_OF_SCOPE)

    def test_31_live_block_rejected_before_shadow_reserve_or_charge(self):
        root = dataclasses.replace(self.root, mode="live")
        ledger = Ledger(WHOLE_BLOCK)
        called = []
        with self.assertRaises(MissingApproval):
            run_block(root, self.changed, self.same, lambda *a: called.append(a), ledger, "", shadow=lambda a: called.append(a))
        self.assertEqual(called, [])
        self.assertEqual(ledger.rows, [])
        self.assertEqual(ledger.reserved, 0)

    def test_32_self_outside_scope_charged_and_not_fallback(self):
        outside = self.proposal({"name": "run_speed_test", "arguments": {}})
        ledger = Ledger(WHOLE_BLOCK)
        called = []
        arms = run_block(self.root, self.changed, outside, lambda *a: called.append(a), ledger, "", shadow=lambda a: called.append(a))
        self.assertEqual(arms, ())
        self.assertEqual(called, [])
        self.assertEqual(ledger.report()["spent"], sum(x.test_units for x in PREPARATION[:4]))

    def test_33_declared_provenance_hashes_cannot_be_replaced(self):
        with self.assertRaises(ValueError): dataclasses.replace(self.root, actual_api_calls=1)
        with self.assertRaises(ValueError): dataclasses.replace(self.root, fixture=False)
        with self.assertRaises(ValueError): dataclasses.replace(self.root, original_proposal_sha256="wrong")
        with self.assertRaises(ValueError): dataclasses.replace(self.changed, raw_q_sha256="wrong")
        with self.assertRaises(ValueError): dataclasses.replace(self.changed, draw_index=2)

    def test_34_infrastructure_failure_is_incomplete_not_valid_partial_block(self):
        calls = []
        def broken(action, call_id):
            calls.append(call_id)
            if len(calls) == 2:
                raise RuntimeError("fixture infrastructure failure")
            return type(self).execute(action, call_id)
        ledger = Ledger(WHOLE_BLOCK)
        with self.assertRaises(RuntimeError):
            run_block(self.root, self.changed, self.same, broken, ledger, "", shadow=lambda a: None)
        self.assertEqual(ledger.report()["finished_arms"], ["B"])
        self.assertEqual(ledger.report()["started_arms"], ["B", "S"])
        self.assertEqual(ledger.report()["block_status"], "infrastructure_failed_incomplete_block")
        self.assertEqual(ledger.retry_count, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(ledger.report()["branch_costs"]["S"], 8)

    def test_35_fixture_arms_cannot_be_promoted_to_research_outcomes(self):
        a = make_arm(self.root, ArmKind.A, self.changed, type(self).execute)
        with self.assertRaises(ValueError): dataclasses.replace(a, fixture=False)
        with self.assertRaises(ValueError): dataclasses.replace(a, mode="live")
        with self.assertRaises(ValueError): dataclasses.replace(a, terminal_result=1.0)
        with self.assertRaises(ValueError): dataclasses.replace(a, causal_harm=False)
        with self.assertRaises(ValueError): dataclasses.replace(a.receipt, actual_api_calls=1)

    def test_36_raw_proposal_and_executable_action_must_agree(self):
        with self.assertRaises(ValueError): dataclasses.replace(self.same, action=self.changed.action)
        lying = dataclasses.replace(self.same, classification=Classification.VALID_CHANGED)
        called = []
        with self.assertRaises(ValueError):
            make_arm(self.root, ArmKind.A, lying, lambda *a: called.append(a))
        ledger = Ledger(WHOLE_BLOCK)
        with self.assertRaises(ValueError):
            run_block(self.root, lying, self.same, lambda *a: called.append(a), ledger, "", shadow=lambda a: called.append(a))
        self.assertEqual(called, [])
        self.assertEqual(ledger.proposals, [])


if __name__ == "__main__":
    unittest.main()
