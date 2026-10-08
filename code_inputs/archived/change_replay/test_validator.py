"""Engineering invariants; never statistical Agent-performance tests."""
import ast
from copy import deepcopy
import json
import subprocess
import sys
import unittest
from common import ROOT, canonical, component_id, file_hash, verify_freeze
from fixtures import CURSOR_1, LONG_TEXT, SCRIPTS, ToolWorld, UnsupportedPath, call, public_tasks, tapes
from hidden_checker import check
from replay import Harness, local_predicate_probe
from selection_probe import all_rankings, validate_view
from variant_source import BASE, VARIANTS, load_source, structural_diff

TASKS = {task["id"]: task for task in public_tasks()}


def record(task_id, tape_index=0, task=None):
    return Harness(task or TASKS[task_id], load_source(BASE), tapes(task_id)[tape_index]).run()


def replay(task_id, change, old=None, world=None):
    old = old or record(task_id)
    return Harness(TASKS[task_id], load_source(VARIANTS[change]), {"tape_id": old["tape_id"], "responses": []}, reference=old, world=world).run()


class EngineeringTests(unittest.TestCase):
    def test_frozen_payload_hashes(self):
        self.assertEqual(len(verify_freeze()["frozen_payloads"]), 3)

    def test_public_schema_and_two_distinct_wording_tapes(self):
        fields = {"id", "family", "prompt", "capabilities", "horizon_model_requests", "tool_dispatch_budget"}
        self.assertEqual(len(TASKS), 16)
        self.assertEqual({family: sum(task["family"] == family for task in TASKS.values()) for family in "APER"}, dict.fromkeys("APER", 4))
        for task in TASKS.values():
            self.assertEqual(set(task), fields)
            left, right = tapes(task["id"])
            self.assertNotEqual(left["responses"], right["responses"])
            strip = lambda tape: [{key: value for key, value in response.items() if key != "content"} for response in tape["responses"]]
            self.assertEqual(strip(left), strip(right))

    def test_all_32_h0_replays_exact(self):
        for task_id in TASKS:
            for number in (0, 1):
                old = record(task_id, number)
                new = replay(task_id, "C_NO_OP", old)
                self.assertEqual(new["status"], "historical_path_equivalent")
                self.assertEqual(canonical(new["events"]), canonical(old["events"]))
                self.assertEqual(new["responses_consumed"], len(old["request_bindings"]))

    def test_refactor_has_actual_ast_diff_without_boundary_divergence(self):
        self.assertEqual(len(structural_diff(VARIANTS["C_REFACTOR"])), 1)
        self.assertEqual(structural_diff(VARIANTS["C_NO_OP"]), [])
        for task_id in TASKS:
            self.assertEqual(replay(task_id, "C_REFACTOR")["status"], "historical_path_equivalent")

    def test_global_prompt_consumes_no_response(self):
        for task_id in TASKS:
            new = replay(task_id, "C_GLOBAL_PROMPT")
            self.assertEqual(new["status"], "diverged_unknown")
            self.assertEqual(new["detail"]["boundary_index"], 0)
            self.assertEqual(new["responses_consumed"], 0)
            self.assertEqual(new["actual_tool_dispatches"], 0)
            self.assertEqual(new["model_request_boundaries_attempted"], 1)

    def test_no_historical_response_consumed_after_any_first_difference(self):
        for task_id in TASKS:
            for change in VARIANTS:
                new = replay(task_id, change)
                self.assertEqual(new["responses_consumed"], sum(e["kind"] == "model_request" for e in new["events"]))
                self.assertEqual(new["actual_tool_dispatches"], sum(e["kind"] == "tool_dispatch" for e in new["events"]))
                self.assertEqual(len(new["request_bindings"]), new["responses_consumed"])
                if new["status"] == "diverged_unknown":
                    self.assertIsNone(new["answer"])
                    self.assertEqual(new["goal_outcome"], "unknown_after_divergence")
                    self.assertEqual(len(new["events"]), new["detail"]["boundary_index"])
                    self.assertEqual(new["responses_consumed"], new["detail"]["responses_consumed_at_stop"])

    def test_complete_request_generation_option_change_is_guarded(self):
        old = record("A1")
        class ChangedRequest(Harness):
            def request(self):
                request = super().request()
                request["generation"]["temperature"] = 1
                return request
        run = ChangedRequest(TASKS["A1"], load_source(BASE), tapes("A1")[0], reference=old).run()
        self.assertEqual(run["responses_consumed"], 0)
        self.assertEqual(run["detail"]["new_kind"], "model_request")

    def test_complete_request_tool_schema_change_is_guarded(self):
        old = record("A1")
        class ChangedRequest(Harness):
            def request(self):
                request = super().request()
                request["tools"][0]["function"]["description"] += " changed"
                return request
        run = ChangedRequest(TASKS["A1"], load_source(BASE), tapes("A1")[0], reference=old).run()
        self.assertEqual(run["responses_consumed"], 0)

    def test_request_bound_tape_has_separate_guard(self):
        old = record("A1")
        old["request_bindings"][1]["request"]["metadata"]["fixture_protocol"] = "corrupt"
        run = replay("A1", "C_NO_OP", old)
        self.assertEqual(run["status"], "diverged_unknown")
        self.assertEqual(run["detail"]["reason"], "request_binding_mismatch")
        self.assertEqual(run["responses_consumed"], 1)

    def test_dispatch_difference_stops_before_new_tool_execution(self):
        for task_id in ("A1", "A2", "A3"):
            run = replay(task_id, "M_ARGUMENT_NORMALIZATION")
            self.assertEqual(run["detail"]["new_kind"], "tool_dispatch")
            self.assertEqual(run["state"]["invocations"], 0)
            self.assertEqual(run["actual_tool_dispatches"], 0)

    def test_unicode_nested_arrays_and_string_whitespace_are_exact(self):
        self.assertNotEqual(canonical("é"), canonical("e\u0301"))
        self.assertNotEqual(canonical("A"), canonical("a"))
        self.assertNotEqual(canonical(" A "), canonical("A"))
        self.assertNotEqual(canonical({"x": ["a", "b"]}), canonical({"x": ["b", "a"]}))
        self.assertEqual(canonical({"a": 1, "b": 2}), canonical({"b": 2, "a": 1}))

    def test_long_observation_and_cursor_are_not_truncated_in_reference(self):
        old = record("P3")
        observation = next(e["payload"]["observation"] for e in old["events"] if e["kind"] == "tool_observation")
        self.assertEqual(observation["detail"], LONG_TEXT)
        self.assertGreater(len(LONG_TEXT), 3000)
        self.assertEqual(observation["next_cursor"], CURSOR_1)
        new = replay("P3", "M_CURSOR_TRUNCATION", old)
        self.assertEqual(new["detail"]["new_kind"], "tool_observation")
        self.assertEqual(new["responses_consumed"], 1)

    def test_empty_page_continues_in_h0_and_early_stop_is_unknown(self):
        old = record("P4")
        self.assertEqual(old["actual_tool_dispatches"], 2)
        new = replay("P4", "M_PREMATURE_TERMINATION", old)
        self.assertEqual(new["detail"]["new_kind"], "termination")
        self.assertEqual(new["status"], "diverged_unknown")
        self.assertIsNone(new["answer"])

    def test_transient_read_and_permanent_error_classification(self):
        self.assertEqual(record("E1")["actual_tool_dispatches"], 2)
        self.assertEqual(record("E3")["actual_tool_dispatches"], 1)
        changed = replay("E3", "M_RETRY_IDEMPOTENCY")
        self.assertEqual(changed["actual_tool_dispatches"], 1)
        self.assertEqual(changed["detail"]["old_kind"], "model_request")
        self.assertEqual(changed["detail"]["new_kind"], "tool_dispatch")

    def test_side_effects_independent_and_idempotent(self):
        first, second = record("E2"), record("E2")
        self.assertEqual(first["state"]["committed_writes"], 1)
        self.assertEqual(second["state"]["committed_writes"], 1)
        first["state"]["ledger"]["op-E2"] = "changed-snapshot"
        self.assertEqual(second["state"]["ledger"]["op-E2"], "r-1")
        run = replay("E2", "M_RETRY_IDEMPOTENCY", second)
        self.assertEqual(run["state"]["committed_writes"], 1)
        self.assertEqual(run["state"]["invocations"], 1)
        self.assertEqual(second["state"]["committed_writes"], 1)

    def test_checker_positive_and_negative_for_all_tasks(self):
        for task_id in TASKS:
            run = record(task_id)
            self.assertTrue(check(task_id, run["answer"], run["state"], run["events"])["passed"])
            self.assertFalse(check(task_id, {"result": "deliberately-wrong"}, run["state"], run["events"])["passed"])
            self.assertFalse(check(task_id, {}, run["state"], run["events"])["passed"])

    def test_checker_rejects_duplicate_writes_and_extra_dispatch(self):
        write = record("E2")
        for count in (0, 2, True, "1"):
            self.assertFalse(check("E2", write["answer"], {"committed_writes": count}, write["events"])["passed"])
        error = record("E3")
        self.assertFalse(check("E3", error["answer"], error["state"], error["events"] + [{"kind": "tool_dispatch"}])["passed"])
        self.assertFalse(check("P1", {"result": ["a", "c", "b"]}, {}, [])["passed"])
        self.assertFalse(check("P1", {"result": ["a", "b"]}, {}, [])["passed"])

    def test_unsupported_tool_path_is_unknown_not_unaffected(self):
        old = record("A1")
        class UnsupportedWorld(ToolWorld):
            def invoke(self, name, args):
                raise UnsupportedPath("New path lacks authored fixture")
        run = replay("A1", "C_NO_OP", old, UnsupportedWorld("A1"))
        self.assertEqual(run["status"], "unsupported_unknown")
        self.assertEqual(run["responses_consumed"], 1)
        self.assertIsNone(run["answer"])

    def test_absent_old_component_coverage_is_unknown(self):
        probe = local_predicate_probe(record("A1"), load_source(BASE), [{"component_id": component_id("new_unexposed_path")}])
        self.assertEqual(probe["status"], "unknown_unexposed_component")

    def test_tape_exhaustion_is_unknown(self):
        tape = {"tape_id": "A1-short", "responses": [call("get", id="AbC-07")]}
        run = Harness(TASKS["A1"], load_source(BASE), tape).run()
        self.assertEqual(run["status"], "unsupported_unknown")
        self.assertEqual(run["responses_consumed"], 1)

    def test_model_horizon_enforced(self):
        tape = {"tape_id": "A4-loop", "responses": [call("get", id="plain-4")] * 20}
        task = {**TASKS["A4"], "horizon_model_requests": 2}
        run = Harness(task, load_source(BASE), tape).run()
        self.assertEqual(run["status"], "budget_exhausted")
        self.assertEqual(run["model_request_boundaries_attempted"], 2)
        self.assertEqual(run["responses_consumed"], 2)
        self.assertEqual(run["events"][-2]["kind"], "budget")
        self.assertEqual(run["events"][-1]["payload"]["exhausted_budget"], "model_requests")

    def test_tool_budget_enforced_before_extra_dispatch(self):
        task = {**TASKS["E1"], "tool_dispatch_budget": 1}
        run = Harness(task, load_source(BASE), tapes("E1")[0]).run()
        self.assertEqual(run["status"], "budget_exhausted")
        self.assertEqual(run["actual_tool_dispatches"], 1)
        self.assertEqual(run["state"]["invocations"], 1)
        self.assertEqual(run["events"][-1]["payload"]["exhausted_budget"], "tool_dispatches")

    def test_different_budget_boundary_stops_replay(self):
        old = record("E1")
        task = {**TASKS["E1"], "tool_dispatch_budget": 1}
        run = Harness(task, load_source(BASE), tapes("E1")[0], reference=old).run()
        self.assertEqual(run["status"], "diverged_unknown")
        self.assertEqual(run["detail"]["new_kind"], "budget")
        self.assertEqual(run["responses_consumed"], 1)

    def test_cost_is_scripted_counter_not_currency_or_tokens(self):
        for task_id in TASKS:
            run = record(task_id)
            self.assertEqual(run["scripted_synthetic_units"], run["model_request_boundaries_attempted"] + run["actual_tool_dispatches"])
            self.assertNotIn("dollars", run)
            self.assertNotIn("billed_tokens", run)

    def test_direct_predicate_matches_only_structural_presence_and_position(self):
        for task_id in TASKS:
            old = record(task_id)
            for change, source in VARIANTS.items():
                run = replay(task_id, change, old)
                probe = local_predicate_probe(old, load_source(source), structural_diff(source))
                self.assertEqual(run["status"] == "diverged_unknown", probe["status"] == "changed_local_return")
                if run["status"] == "diverged_unknown":
                    self.assertEqual(run["detail"]["boundary_index"], probe["next_boundary_index"])

    def test_selector_no_checker_import_or_fixture_read(self):
        module = ast.parse((ROOT / "selection_probe.py").read_text())
        imports = {name.name.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.Import) for name in node.names} | {node.module.split(".")[0] for node in ast.walk(module) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(imports, {"hashlib", "json", "sys", "fractions"})
        self.assertNotIn("hidden_checker", (ROOT / "selection_probe.py").read_text())

    def test_saved_selector_views_allowlist_and_no_raw_payload(self):
        views = json.loads((ROOT / "results/selector_views.json").read_text())
        for change, view in views.items():
            validate_view(view)
            self.assertNotIn(change, canonical(view))
            for task in view["tasks"]:
                self.assertEqual(task["public_capability_tags"], TASKS[task["task_id"]]["capabilities"])
            for forbidden in ("Alpha", "Bridge", "Nested", "bad_request", "op-E2", "request_bindings", "committed_writes"):
                self.assertNotIn(forbidden, canonical(view))
            bad = deepcopy(view)
            bad["tasks"][0]["hidden_answer"] = "forbidden"
            with self.assertRaises(AssertionError):
                validate_view(bad)

    def test_deterministic_hash_ties_independent_of_input_order(self):
        view = {"structural_diff_ids": [], "tasks": [{"task_id": task_id, "old_exposures": [], "public_capability_tags": [], "historical_scripted_costs": 3, "first_valid_divergence_features": []} for task_id in ("A1", "A4", "P2", "R2")]}
        before = all_rankings(view)
        view["tasks"].reverse()
        self.assertEqual(before, all_rankings(view))
        for ranking in before.values():
            self.assertEqual([item["stable_tie_sha256"] for item in ranking], sorted(item["stable_tie_sha256"] for item in ranking))

    def test_selection_freeze_precedes_checker_import_and_hashes_match(self):
        freeze = json.loads((ROOT / "results/selection_freeze.json").read_text())
        self.assertFalse(freeze["hidden_checker_loaded"])
        self.assertEqual(freeze["frozen_rankings_sha256"], file_hash(ROOT / "results/frozen_rankings.json"))
        self.assertEqual(freeze["selector_views_sha256"], file_hash(ROOT / "results/selector_views.json"))

    def test_all_diverged_goal_outcomes_remain_unknown(self):
        hidden = json.loads((ROOT / "results/hidden_goal_view.json").read_text())
        matrix = json.loads((ROOT / "results/replay_traces.json").read_text())
        for change, runs in matrix.items():
            for run in runs:
                if run["status"] == "diverged_unknown":
                    self.assertIsNone(hidden["h1"][change][run["tape_id"]]["passed"])
                elif run["status"] == "historical_path_equivalent":
                    self.assertTrue(hidden["h1"][change][run["tape_id"]]["passed"])

    def test_global_candidate_degenerates_to_diff_capability(self):
        rankings = json.loads((ROOT / "results/frozen_rankings.json").read_text())
        self.assertEqual(rankings["C_GLOBAL_PROMPT"]["candidate_replay"], rankings["C_GLOBAL_PROMPT"]["diff_plus_capability"])

    def test_end_to_end_outputs_are_byte_deterministic(self):
        paths = sorted((ROOT / "results").glob("*"))
        hashes = {path.name: file_hash(path) for path in paths}
        subprocess.run([sys.executable, str(ROOT / "runner.py")], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
        self.assertEqual(hashes, {path.name: file_hash(path) for path in paths})


if __name__ == "__main__":
    unittest.main(verbosity=2)
