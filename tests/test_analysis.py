import copy
import json
from pathlib import Path
import tempfile
import unittest
from local_experiments.analysis import contrast,interval,nested,export
from local_experiments.storage import digest,write_json,RunFailure

class AnalysisTests(unittest.TestCase):
 def test_equal_tasks_not_rows(self):
  rows=[]
  for task,n,p,c in [('a',1,1,0),('b',10,0,1)]:
   for arm,v in [('P',p),('C',c)]:
    for r in range(n):rows.append({'task_id':task,'root_id':task,'common_prefix_repeat_id':0,'arm_id':arm,'suffix_repeat_id':r,'loss':v})
  self.assertEqual(contrast(rows,'loss'),[1,-1])
 def test_equal_common_segments_not_suffix_rows(self):
  rows=[{'root_id':'r','common_prefix_repeat_id':0,'loss':0}]+[{'root_id':'r','common_prefix_repeat_id':1,'loss':1} for _ in range(10)]
  self.assertEqual(nested(rows,'loss'),0.5)
 def test_missing_bounds(self):
  rows=[{'task_id':'t','root_id':'r','common_prefix_repeat_id':0,'arm_id':a,'loss':None} for a in ('P','C')]
  self.assertEqual(contrast(rows,'loss',0,1),[-1]);self.assertEqual(contrast(rows,'loss',1,0),[1])
 def test_reproducible_cluster_intervals(self):
  self.assertEqual(interval([0,1,-1],1000,1,.95),interval([0,1,-1],1000,1,.95));self.assertIsNone(interval([1],1000,1,.95))
 def test_export_rejects_injected_scalar(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);source=p/'source';source.mkdir()
   from local_experiments.analysis import SCALARS
   report={k:None for k in SCALARS};report.update(evidence_kind='scripted_fixture',protocol_hash='a',task_count='private-sentinel')
   write_json(source/'summary.json',report);write_json(source/'analysis_manifest.json',{'summary_sha256':digest(report),'protocol_hash':'a'})
   with self.assertRaises(RunFailure):export(source,p/'export')
   self.assertFalse((p/'export').exists())

 def test_unsettled_runs_are_not_analyzable(self):
  from local_experiments.analysis import analyze
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'run';source.mkdir()
   write_json(source/'status.json',{'status':'implementation_error'})
   with self.assertRaisesRegex(RunFailure,'not settled'):analyze(source,Path(d)/'analysis')
