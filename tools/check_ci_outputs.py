"""Assert dry-run CLI acceptance; print only aggregate platform/result evidence."""
import json
from pathlib import Path

def read(path):return json.loads(Path(path).read_text())
statuses={name:read('results/'+name+'/status.json') for name in ('ci-wire','ci-write','ci-pilot','ci-resumed')}
for status in statuses.values():
 assert status['status']=='completed',status
 assert status['evidence_kind']=='scripted_fixture' and status['real_model_calls']==0,status
assert statuses['ci-pilot']['coverage']['roots']==4 and statuses['ci-pilot']['outcomes']==68
assert statuses['ci-wire']['physical_attempts']==statuses['ci-resumed']['physical_attempts']
for name in ('ci-analysis','ci-pilot-analysis','ci-resumed-analysis'):
 r=read('results/'+name+'/summary.json')
 assert r['evidence_kind']=='scripted_fixture' and r['model_outcomes']=='not_run' and r['formal_experiments']==0
 assert r['loss_reduction'] is None and r['completion_difference'] is None and r['missing_endpoints']==0
export=read('exports/ci-wire/summary.json')
assert export['evidence_kind']=='scripted_fixture' and export['formal_experiments']==0
report={'kind':'offline_acceptance','platform':read('results/platform.json'),
        'real_model_calls':0,'pilot_roots':4,'pilot_endpoints':68,
        'recovery_preserved_physical_attempts':True,'model_outcomes':'not_run',
        'scope':'unit suite includes interrupted-reviewer recovery; CLI READ/WRITE/pilot/analysis/export and durable-response resume passed'}
Path('results/platform-acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,sort_keys=True))
