"""Metadata-only gate tests: no heldout task is simulated or evaluated here."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from local_experiments.config import DEFAULT,ROOT,PIN,ConfigError,validate
from local_experiments.freeze import sha,seal,near_family,fault_set

class FreezeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.tasks=json.loads((ROOT/'code_inputs/reviewer_pilot/upstream/data/tau2/domains/telecom/tasks.json').read_text())
  self.c=copy.deepcopy(DEFAULT);self.c.update(stage='confirmatory-roots',study_label='confirmatory')
  self.c['dataset'].update(manifest=str(self.root/'tasks.json'),population='heldout_confirmatory',operator_attests_unseen=True)
  self.c['models'].update(actor_model='frozen-actor',reviewer_model='frozen-reviewer',user_model='frozen-user',require_reported_model=True)
  self.c['analysis'].update(delta=.05,epsilon=.05,confirmatory_sample_size=1)
 def manifest(self,ids):
  rows=[]
  for name in ids:
   t=next(t for t in self.tasks if t['id']==name)
   rows.append({'task_id':name,'task_sha256':sha(t),'family_id':name.split(']',1)[-1].split('[PERSONA:',1)[0],'research_partition':'heldout_confirmatory'})
  Path(self.c['dataset']['manifest']).write_text(json.dumps({'source_commit':PIN,'tasks':rows}))
  self.c['dataset']['task_indices']=list(range(len(rows)));self.c['analysis']['confirmatory_sample_size']=len(rows)
 def test_frozen_manifest_verifies_then_rejects_design_change(self):
  self.manifest(['[mobile_data_issue]bad_vpn[PERSONA:None]'])
  path=self.root/'freeze.json';result=seal(self.c,path)
  self.assertEqual(result['model_calls'],0)
  self.c['gates']['frozen_protocol_receipt']=str(path);validate(self.c)
  self.c['sampling']['suffix_repeats']+=1
  with self.assertRaisesRegex(ConfigError,'binding mismatch'):validate(self.c)
 def test_exposed_task_and_family_excluded(self):
  known=json.loads((ROOT/'docs/planning/manifests/tasks_readiness.json').read_text())['tasks'][0]['task_id']
  self.manifest([known])
  with self.assertRaisesRegex(ConfigError,'already exposed'):validate(self.c,require_freeze=False)
 def test_shared_component_units_rejected(self):
  self.manifest(['[mobile_data_issue]bad_vpn[PERSONA:None]','[mobile_data_issue]airplane_mode_on|bad_vpn[PERSONA:None]'])
  with self.assertRaisesRegex(ConfigError,'share a fault component'):validate(self.c,require_freeze=False)
 def test_polarity_variants_are_near_family(self):
  self.assertTrue(near_family(fault_set('[x]user_abroad_roaming_enabled_off[PERSONA:None]'),fault_set('[x]user_abroad_roaming_disabled_on[PERSONA:Easy]')))
 def test_unseen_attestation_cannot_be_inferred(self):
  self.manifest(['[mobile_data_issue]bad_vpn[PERSONA:None]']);self.c['dataset']['operator_attests_unseen']=False
  with self.assertRaisesRegex(ConfigError,'attests_unseen'):validate(self.c,require_freeze=False)
