"""Guard installed before any upstream import; no frozen dependency writers called."""
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PILOT = HERE.parent / 'reviewer_pilot'
sys.path.insert(0, str(PILOT))
import no_api_guard as guard
sys.path.insert(0, str(PILOT / 'upstream/src'))
import tau2
guard.finish_upstream_guards()
from loguru import logger
logger.remove()
sys.path.insert(0, str(HERE.parent / 'reviewer_interventions'))
sys.path.insert(0, str(HERE))
import backend_checks as backend
backend.block_uuid()

if __name__ == '__main__':
    if sys.argv[1:] == ['--restore-probe']:
        from adapter import restore
        from interventions import FrozenJSON, digest
        saved = FrozenJSON((HERE / '.runtime/restart_checkpoint.json').read_text())
        expected = json.loads((HERE / '.runtime/restart_expected.json').read_text())
        o, _ = restore(saved)
        checks = {
            'exact_effective_request': digest(o.agent.request_for(o.message,o.agent_state).payload) == expected['request_sha256'],
            'exact_official_state': digest(backend.orch_state(o,False)) == expected['official_state_sha256'],
            'exact_usage_ledger': digest(o.agent.ledger.report()) == expected['ledger_sha256'],
        }
        target=o.message.id
        o.step(); o._check_termination()
        checks['actual_result_appended_once'] = sum(getattr(m,'id',None)==target for m in o.agent_state.messages)==1
        checks['registry_survives_continuation'] = len(o.agent.ledger.requests)==1
        checks['no_unexpected_guard_events'] = not guard.EVENTS
        report = {'status':'PASS' if all(checks.values()) else 'FAIL', 'fresh_process':True,
                  'mode':'scripted_fixture','actual_model_calls':0,'checks':checks}
        (HERE/'results/process_restart.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        raise SystemExit(0 if all(checks.values()) else 1)
    if sys.argv[1:]:
        raise SystemExit('Unknown worker mode')
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_*.py')
    expected = suite.countTestCases()
    if expected != 37:
        raise SystemExit('Missing test inventory')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'mode': 'scripted_fixture', 'actual_model_calls': 0, 'actual_network_calls': 0,
              'tests_run': result.testsRun, 'expected_tests': expected,
              'failures': len(result.failures), 'errors': len(result.errors),
              'successful': result.wasSuccessful() and not guard.EVENTS,
              'unexpected_guard_events': guard.EVENTS,
              'provider_format_verified': False, 'causal_effect_measured': False}
    if result.wasSuccessful() and not guard.EVENTS:
        from test_adapter import write_demo
        write_demo(HERE / 'results')
        if guard.EVENTS:
            report['successful'] = False
    (HERE / 'results/tests.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['successful'] else 1)
