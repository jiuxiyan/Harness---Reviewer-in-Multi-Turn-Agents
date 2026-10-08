import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from local_experiments.config import ConfigError,DEFAULT,load,validate
from local_experiments.launcher import launch

class ConfigTests(unittest.TestCase):
 def test_defaults_and_roundtrip(self): self.assertEqual(validate(DEFAULT),DEFAULT)
 def test_no_live_or_credentials(self):
  for key in ('mode','api_key','provider'):
   with self.assertRaises(ConfigError): validate({**DEFAULT,key:'private-sentinel'})
 def test_all_missing_fields_reported(self):
  with self.assertRaises(ConfigError) as caught: validate({})
  for key in DEFAULT: self.assertIn(key,str(caught.exception))
 def test_limits(self):
  for key,value in [('max_physical_requests',True),('max_native_steps',0),('max_retries_per_request',-1),('request_timeout_seconds',float('nan')),('request_timeout_seconds',10**1000),('monetary_cap',1)]:
   c=copy.deepcopy(DEFAULT);c['limits'][key]=value
   with self.subTest(key=key),self.assertRaises(ConfigError): validate(c)
 def test_confirmatory_and_unsupported_arms(self):
  c=copy.deepcopy(DEFAULT);c['stage']='confirmatory-roots'
  with self.assertRaises(ConfigError) as caught: validate(c)
  self.assertIn('delta',str(caught.exception));self.assertIn('epsilon',str(caught.exception));self.assertIn('ineligible',str(caught.exception))
  c=copy.deepcopy(DEFAULT);c['arms']=['S']
  self.assertEqual(validate(c)['arms'],['S'])
 def test_malformed_and_duplicate_files(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input.json'
   for raw in ('{"schema_version":1,"schema_version":1}','['*2000,' '*65537,'9'*5000,'{"private-sentinel":'):
    p.write_text(raw)
    with self.assertRaises(ConfigError) as e: load(p)
    self.assertNotIn('private-sentinel',str(e.exception))
 def test_dry_launcher_never_reads_environment(self):
  with tempfile.TemporaryDirectory() as d,patch('local_experiments.launcher.subprocess.run') as run:
   with patch('os.environ',{}),patch('os.getenv',side_effect=AssertionError('No env access')):
    launch('configs/wire-smoke.json','dry-run',Path(d)/'run')
   env=run.call_args.kwargs['env']
   self.assertFalse(any('KEY' in k for k in env));self.assertEqual(env['PYTHON_DOTENV_DISABLED'],'1')
 def test_dry_mode_cannot_initialize_live_client(self):
  from local_experiments.__main__ import main
  with patch('local_experiments.launcher.launch',return_value=0) as launch_mock:
   self.assertEqual(main(['run','--config','configs/wire-smoke.json','--output-dir','results/noop']),0)
   self.assertEqual(launch_mock.call_args.args[1],'dry-run')
 def test_configuration_does_not_mutate(self):
  before=copy.deepcopy(DEFAULT);validate(DEFAULT);self.assertEqual(before,DEFAULT)
