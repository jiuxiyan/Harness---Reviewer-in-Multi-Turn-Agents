"""Offline official-backend checks. All preparation trajectories are scripted."""
import pathlib,sys,json,traceback
R=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(R))
try:
    import no_api_guard as guard
    sys.path.insert(0,str(R/'upstream/src'))
    import tau2
    guard.finish_upstream_guards()
    from loguru import logger
    logger.remove()
    from tau2.domains.telecom.environment import get_environment,get_tasks
    mode=sys.argv[1] if len(sys.argv)>1 else 'import'
    if mode=='reads':
        import backend_checks
        print(json.dumps(backend_checks.read_tool_validation(sys.argv[2]),indent=2));sys.exit(0)
    if mode=='negative':
        import backend_checks
        print(json.dumps(backend_checks.negative_controls(),indent=2));sys.exit(0)
    if mode in {'create','restore'}:
        import backend_checks
        result=backend_checks.create(int(sys.argv[2])) if mode=='create' else backend_checks.restore(int(sys.argv[2]),sys.argv[3])
        print(json.dumps(result,indent=2));sys.exit(0)
    env=get_environment()
    result={'status':'official import/environment construction passed','agent_tools':len(env.get_tools()),'user_tools':len(env.get_user_tools()),'base_tasks':len(get_tasks('base')),'guards':guard.negative_tests(),'unexpected_attempts':guard.EVENTS,'model_calls':0}
    assert not guard.EVENTS
    (R/'results/import_check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
except SystemExit:
    raise
except BaseException as exc:
    result={'status':'blocked_or_failed','error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(),'guard_events':getattr(sys.modules.get('no_api_guard'),'EVENTS',[])}
    (R/'results/import_failure.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));sys.exit(1)
