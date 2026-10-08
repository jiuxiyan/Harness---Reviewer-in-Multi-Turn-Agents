"""Guard-before-import bootstrap. No backend result writers are invoked."""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PILOT = HERE.parent / "reviewer_pilot"
sys.path.insert(0, str(PILOT))
import no_api_guard as guard
sys.path.insert(0, str(PILOT / "upstream/src"))
import tau2
guard.finish_upstream_guards()
from loguru import logger
logger.remove()
sys.path.insert(0, str(HERE))

from interventions import *
from offline_backend import load_root, execute_read, shadow_analysis


def demo():
    root, catalog, names = load_root()
    q = classify_q(root, canonical({"name": "get_details_by_id", "arguments": {"id": "L1002"}}), catalog, names)
    s = classify_q(root, "{FIXTURE invalid JSON", catalog, names)
    ledger = Ledger(WHOLE_BLOCK)
    shadows = []
    arms = run_block(root, q, s, lambda action, call_id: execute_read(root, action, call_id), ledger,
                     "The line-details read can provide line-specific facts for the remaining speed discussion.",
                     shadow=lambda action: shadows.append(shadow_analysis(root, action)))
    check = {
        "mode": MODE, "fixture": True, "actual_api_calls": 0,
        "status": "PASS_INTERNAL_EVENT_DRYRUN_PROVIDER_CONTINUATION_BLOCKED",
        "source_commit": SOURCE_COMMIT, "checkpoint_index": 0,
        "exact_root_raw_sha256": root.raw_checkpoint_sha256,
        "original_proposal_sha256": root.original_proposal_sha256,
        "q": _serial(q), "arm_count": len(arms),
        "arms": [{
            "kind": a.kind.value, "mode": a.mode, "fixture": a.fixture,
            "actual_api_calls": 0, "action": a.executed_action.copy(),
            "execution_id": a.execution_id,
            "receipt": a.receipt.public.copy(),
            "raw_tool_response": a.receipt.raw_tool_response.copy(),
            "preintervention_checkpoint_sha256": a.exact_preintervention_checkpoint_sha256,
            "environment_before_sha256": a.receipt.environment_before_sha256,
            "environment_after_sha256": a.receipt.environment_after_sha256,
            "internal_actor_input_sha256": digest(a.input_views.actor),
            "input_provider_status": a.input_views.provider_status,
            "additional_packet": a.extra_packet.copy(), "fidelity": a.fidelity,
            "terminal_result": None, "causal_harm": None,
        } for a in arms],
        "ledger": ledger.report(),
        "analysis_only": shadows,
        "guards": guard.negative_tests(), "unexpected_guard_attempts": guard.EVENTS,
        "limitations": [
            "No stochastic actor, user or reviewer was generated; all packets and responses are fixtures.",
            "Four isolated READ transitions do not validate replacement orchestration or provider message format.",
            "Original pending customer lookup alone has frozen full-orchestration scripted readiness evidence.",
            "Terminal effectiveness and causal HARM are unmeasured, not zero.",
        ],
    }
    assert not guard.EVENTS
    (HERE / "results/dryrun.json").write_text(json.dumps(check, indent=2) + "\n")
    return {k: check[k] for k in ("status", "arm_count", "mode", "actual_api_calls")}


def _serial(value):
    return json.loads(canonical(value))


def main():
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py")
    expected_count = suite.countTestCases()
    if expected_count != 36:
        raise RuntimeError("Missing required test inventory; refusing an empty/partial suite")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"mode": MODE, "fixture": True, "actual_api_calls": 0,
              "tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "successful": result.wasSuccessful() and result.testsRun == expected_count,
              "expected_tests": expected_count,
              "unexpected_guard_attempts": guard.EVENTS,
              "provider_format_verified": False, "causal_effect_measured": False}
    (HERE / "results/tests.json").write_text(json.dumps(report, indent=2) + "\n")
    if not result.wasSuccessful() or guard.EVENTS:
        return 1
    print(json.dumps(demo(), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
