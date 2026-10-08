"""Only launched with sanitized environment, existing venv, and pre-import guard."""
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
sys.path.insert(0, str(HERE.parent / 'controller_receipt_adapter'))
sys.path.insert(0, str(HERE))
import backend_checks as backend
backend.block_uuid()

if __name__ == '__main__':
    if sys.argv[1:] == ['--restore-probe']:
        from test_lifetime import restore_probe
        checks = restore_probe(HERE)
        report = {'status':'PASS' if all(checks.values()) else 'FAIL',
                  'fresh_process':True, 'checks':checks,
                  'actual_model_calls':0, 'unexpected_guard_events':guard.EVENTS}
        if guard.EVENTS:
            report['status'] = 'FAIL'
        (HERE/'results/process_restart.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        raise SystemExit(0 if report['status']=='PASS' else 1)
    if sys.argv[1:]:
        raise SystemExit('Unsupported worker mode')
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_lifetime.py')
    expected = suite.countTestCases()
    if expected < 25:
        raise SystemExit('Incomplete test inventory')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'mode':'scripted_fixture', 'tests_run':result.testsRun,
              'failures':len(result.failures),'errors':len(result.errors),
              'successful':result.wasSuccessful() and not guard.EVENTS,
              'unexpected_guard_events':guard.EVENTS, 'actual_model_calls':0,
              'actual_network_calls':0, 'provider_format_verified':False,
              'causal_effect_measured':False}
    if report['successful']:
        from test_lifetime import write_demo
        write_demo(HERE)
        report['successful'] = not guard.EVENTS
    (HERE/'results/tests.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['successful'] else 1)
