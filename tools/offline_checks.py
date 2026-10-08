"""Rebuild public development fixtures and test all four guarded source layers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/'code_inputs/reviewer_pilot'

def run(*args):
 command=[sys.executable,*map(str,args)]
 p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
 stem=str(time.time_ns())
 logs=ROOT/'results/offline-checks';logs.mkdir(parents=True,exist_ok=True)
 (logs/(stem+'.log')).write_text(p.stdout+p.stderr)
 print('exit',p.returncode, ' '.join(str(a) for a in args),flush=True)
 if p.returncode: raise SystemExit('Offline check failed; see ignored results/offline-checks logs')

def main():
 for layer in ('reviewer_pilot','reviewer_interventions','controller_receipt_adapter','advice_lifetime_controls'):
  (ROOT/'code_inputs'/layer/'results').mkdir(exist_ok=True)
 run(PILOT/'launch_offline.py','import')
 run(PILOT/'run_suite.py')
 run(PILOT/'launch_offline.py','negative')
 run(PILOT/'launch_offline.py','reads','a')
 run(PILOT/'launch_offline.py','reads','b')
 rows=json.loads((PILOT/'results/read_tool_validation_a.json').read_text())['probes']
 summary={'read_tool_names':sorted({r['tool'] for r in rows}),'concrete_argument_sets':{r['tool']:r['arguments'] for r in rows},'evidence_kind':'scripted_fixture','generated_from_current_run':True}
 (PILOT/'results/read_tool_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 for layer in ('reviewer_interventions','controller_receipt_adapter','advice_lifetime_controls'):
  run(ROOT/'code_inputs'/layer/'launch.py')
 receipt={'evidence_kind':'scripted_fixture','formal_model_calls':0,'backend_tasks':7,'fresh_process_restores':14,'layers':{}}
 for layer in ('reviewer_interventions','controller_receipt_adapter','advice_lifetime_controls'):
  d=ROOT/'code_inputs'/layer/'results'
  # Test report names differ across source layers; include only scalar counts.
  for p in d.glob('*.json'):
   value=json.loads(p.read_text())
   if isinstance(value,dict) and 'tests_run' in value:
    receipt['layers'][layer]={k:value.get(k) for k in ('tests_run','failures','errors','successful')}
 print(json.dumps(receipt,indent=2))
 (ROOT/'results/offline-checks/receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__': main()
