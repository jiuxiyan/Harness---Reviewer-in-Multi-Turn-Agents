import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from local_experiments.config import ROOT

class IntegrationTests(unittest.TestCase):
 def test_guarded_engine_and_fresh_process_restore(self):
  pilot=ROOT/'code_inputs/reviewer_pilot';python=pilot/'.venv/bin/python'
  if not python.is_file():self.fail('Run documented pinned dependency setup before integration tests')
  with tempfile.TemporaryDirectory() as d:
   env={'PATH':str(python.parent)+':/usr/bin:/bin','HOME':d,'LANG':'C.UTF-8','PYTHON_DOTENV_DISABLED':'1','TAU2_DATA_DIR':str(pilot/'upstream/data'),'LITELLM_MODE':'PRODUCTION','LITELLM_LOCAL_MODEL_COST_MAP':'true','LITELLM_DISABLE_LAZY_LOADING':'false','HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','TOKENIZERS_PARALLELISM':'false','PYTHONDONTWRITEBYTECODE':'1'}
   for args in ([],['save',str(Path(d)/'checkpoint.json')],['restore',str(Path(d)/'checkpoint.json')],['save-write',str(Path(d)/'write.json')],['restore-write',str(Path(d)/'write.json')],['save-init',str(Path(d)/'init.json')],['restore-init',str(Path(d)/'init.json')],['save-history',str(Path(d)/'history.json')],['restore-history',str(Path(d)/'history.json')],['save-vpn',str(Path(d)/'vpn.json')],['restore-vpn',str(Path(d)/'vpn.json')]):
    p=subprocess.run([str(python),'-I','-B',str(ROOT/'tests/engine_checks.py'),*args],env=env,cwd=ROOT,capture_output=True,text=True)
    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
