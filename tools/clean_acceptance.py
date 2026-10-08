"""Exercise documented commands in a new source tree; never enables live mode."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('public_manifest',ROOT/'tools/public_manifest.py')
manifest=importlib.util.module_from_spec(spec);spec.loader.exec_module(manifest)

def main():
 receipts=[]
 frozen_source_hash=manifest.source_digest(manifest.inventory())
 with tempfile.TemporaryDirectory(prefix='harness-clean-') as d:
  dest=Path(d)/'repo';dest.mkdir()
  for name in [*manifest.files(),'PUBLIC_MANIFEST.json']:
   source=ROOT/name
   if source.is_file():
    target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
  subprocess.run(['git','init','-q'],cwd=dest,check=True)
  commands=[
   ['tools/public_manifest.py','--check'],
   ['code_inputs/reviewer_pilot/install_locked.py'],
   ['code_inputs/reviewer_pilot/install_locked.py','gap'],
   ['-m','unittest','discover','-s','tests','-v'],
   ['tools/offline_checks.py'],
   ['-m','local_experiments','validate','--config','configs/wire-smoke.json'],
   ['-m','local_experiments','run','--config','configs/wire-smoke.json','--output-dir','results/wire-smoke'],
   ['-m','local_experiments','analyze','--input-dir','results/wire-smoke','--output-dir','results/wire-smoke-analysis'],
   ['-m','local_experiments','export','--input-dir','results/wire-smoke-analysis','--output-dir','exports/wire-smoke'],
   ['-m','local_experiments','run','--config','configs/natural-pilot.json','--output-dir','results/pilot'],
   ['-m','local_experiments','run','--config','configs/write-smoke.json','--output-dir','results/write-smoke'],
   ['-m','local_experiments','recovery-plan','--input-dir','results/wire-smoke','--output-file','results/recovery-decisions.json'],
   ['-m','local_experiments','resume','--config','configs/wire-smoke.json','--input-dir','results/wire-smoke','--decisions','results/recovery-decisions.json','--output-dir','results/recovered-wire'],
   ['-m','local_experiments','analyze','--input-dir','results/recovered-wire','--output-dir','results/recovered-analysis'],
   ['-m','local_experiments','validate','--config','configs/confirmatory-roots.json'],
   ['-m','local_experiments','validate','--config','configs/end-to-end.json'],
  ]
  logs=ROOT/'results/clean-acceptance'/frozen_source_hash[:12];logs.mkdir(parents=True,exist_ok=True)
  for i,args in enumerate(commands):
   p=subprocess.run([sys.executable,*args],cwd=dest,capture_output=True,text=True)
   (logs/f'{i}.log').write_text(p.stdout+p.stderr)
   expected=2 if any(x in args for x in ('configs/confirmatory-roots.json','configs/end-to-end.json')) else 0
   receipt={'command':'python3 '+' '.join(args),'exit_code':p.returncode,'expected_exit_code':expected}
   receipts.append(receipt);print(json.dumps(receipt),flush=True)
   if p.returncode!=expected: raise SystemExit('Clean acceptance failed; see ignored logs')
  for name in ('wire-smoke','pilot','write-smoke','recovered-wire'):
   status=json.loads((dest/'results'/name/'status.json').read_text());assert status['real_model_calls']==0 and status['status']=='completed'
  original=json.loads((dest/'results/wire-smoke/status.json').read_text());recovered=json.loads((dest/'results/recovered-wire/status.json').read_text())
  assert original['physical_attempts']==recovered['physical_attempts']
  pilot=json.loads((dest/'results/pilot/status.json').read_text());assert pilot['coverage']['roots']==4 and pilot['outcomes']==68
  if manifest.source_digest(manifest.inventory())!=frozen_source_hash: raise SystemExit('Source changed during acceptance; rerun after changes settle')
  receipt={'schema_version':1,'source_tree_sha256':frozen_source_hash,'commands':receipts,'formal_model_calls':0,'status':'passed','scope':'new source directory and fresh pinned virtual environment; all executions offline/mock after dependency setup'}
  (logs/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
  print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
