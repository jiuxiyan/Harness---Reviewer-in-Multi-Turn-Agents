import copy
import json
from pathlib import Path
import tempfile
import unittest
from local_experiments.analysis import contrast,interval,nested,export,analyze_episode
from local_experiments.storage import digest,write_json,RunFailure

def _episode_fixture(root,kind,arms,tasks_rows,settled=True):
 """Build a minimal but valid end-to-end run directory for analyze_episode.

 tasks_rows: list of dicts with task_id,family_id,arm,completion,triggered,termination.
 kind: evidence_kind ('scripted_fixture' or 'exploratory_live').
"""
 source=Path(root)/'run';(source/'derived').mkdir(parents=True);(source/'journal').mkdir(parents=True)
 protocol='proto-abc'
 write_json(source/'status.json',{'status':'completed'})
 write_json(source/'run_manifest.json',{'evidence_kind':kind,'protocol_hash':protocol,
  'config':{'arms':arms,'analysis':{'bootstrap_replicates':1000,'bootstrap_seed':1,
   'confidence_level':0.95,'delta':0.0}}})
 rows=[]
 for i,r in enumerate(tasks_rows):
  rows.append({'episode_id':f"{r['task_id']}-{r['arm']}",'task_id':r['task_id'],
   'family_id':r['family_id'],'arm':r['arm'],'completion':r['completion'],
   'triggered':r.get('triggered',True),'termination':r.get('termination','user_stop'),
   'ever_achieved_then_lost_indices':r.get('lost',[]),'evidence_kind':kind})
 (source/'derived/episode_outcomes.jsonl').write_text(
  '\n'.join(json.dumps(x) for x in rows)+'\n')
 events=[{'kind':'request_dispatched','protocol_hash':protocol,'evidence_kind':kind,'usage':None},
  {'kind':'response_saved','protocol_hash':protocol,'evidence_kind':kind,'usage':{'prompt_tokens':10,'completion_tokens':5}}]
 if settled: events.append({'kind':'episode_run_settled','protocol_hash':protocol,'evidence_kind':kind})
 (source/'journal/events.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
 return source

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

 # --- End-to-end episode analyzer (doc §9.4: no-trigger episodes, single review slot,
 # P/C allowed to differ, task-cluster intervals, missingness bounds) ---
 def test_episode_J_is_task_macro_and_no_trigger_stays_in_denominator(self):
  # P completes t0 only, C completes t1 only; the P/t1 no-trigger episode (completion 0)
  # must remain in J(P)'s denominator, so J(P)=mean(1,0)=0.5 not 1.0.
  rows=[{'task_id':'t0','family_id':'f0','arm':'P','completion':1,'triggered':True},
        {'task_id':'t1','family_id':'f1','arm':'P','completion':0,'triggered':False,'termination':None},
        {'task_id':'t0','family_id':'f0','arm':'C','completion':0},
        {'task_id':'t1','family_id':'f1','arm':'C','completion':1}]
  with tempfile.TemporaryDirectory() as d:
   src=_episode_fixture(d,'scripted_fixture',['P','C'],rows)
   rep=analyze_episode(src,Path(d)/'analysis')
   self.assertEqual(rep['analysis_kind'],'end_to_end_episode')
   self.assertEqual(rep['J_P'],0.5);self.assertEqual(rep['J_C'],0.5)
   self.assertEqual(rep['dJ_C_minus_P'],0.0)  # t0:-1, t1:+1 -> mean 0
   self.assertEqual(rep['arms']['P']['triggered'],1)  # only t0 triggered
   self.assertEqual(rep['episode_count'],4);self.assertEqual(rep['scored_episodes'],4)
   # scripted_fixture is not live: no interval, no missingness bounds
   self.assertIsNone(rep['arms']['P']['J_interval']);self.assertIsNone(rep['dJ_interval'])
   self.assertEqual(rep['missingness_bounds'],{})
   self.assertEqual(rep['claim_status'],'no_confirmatory_claim')

 def test_episode_live_interval_and_missingness_bounds(self):
  # >=2 scored task clusters -> task-cluster bootstrap interval is produced (live only),
  # and a missing (None) completion yields finite worst/best ΔJ bounds.
  rows=[{'task_id':'t0','family_id':'f0','arm':'P','completion':1},
        {'task_id':'t1','family_id':'f1','arm':'P','completion':None},
        {'task_id':'t2','family_id':'f2','arm':'P','completion':1},
        {'task_id':'t0','family_id':'f0','arm':'C','completion':0},
        {'task_id':'t1','family_id':'f1','arm':'C','completion':1},
        {'task_id':'t2','family_id':'f2','arm':'C','completion':1}]
  with tempfile.TemporaryDirectory() as d:
   src=_episode_fixture(d,'exploratory_live',['P','C'],rows)
   rep=analyze_episode(src,Path(d)/'analysis')
   self.assertEqual(rep['missing_endpoints'],1);self.assertEqual(rep['scored_episodes'],5)
   self.assertIsNotNone(rep['dJ_interval']);self.assertEqual(len(rep['dJ_interval']),2)
   b=rep['missingness_bounds']['dJ_C_minus_P']
   self.assertIsNotNone(b[0]);self.assertIsNotNone(b[1]);self.assertLessEqual(b[0],b[1])
   self.assertEqual(rep['physical_attempts'],1);self.assertEqual(rep['reported_input_tokens'],10)
   self.assertEqual(rep['calls_missing_usage'],0)

 def test_episode_single_task_cluster_has_no_interval(self):
  rows=[{'task_id':'t0','family_id':'f0','arm':'P','completion':1},
        {'task_id':'t0','family_id':'f0','arm':'C','completion':0}]
  with tempfile.TemporaryDirectory() as d:
   src=_episode_fixture(d,'exploratory_live',['P','C'],rows)
   rep=analyze_episode(src,Path(d)/'analysis')
   self.assertIsNone(rep['dJ_interval'])  # one task cluster -> no bootstrap interval
   self.assertIsNone(rep['arms']['P']['J_interval'])
   self.assertEqual(rep['dJ_C_minus_P'],-1.0)

 def test_episode_rejects_unsettled_ledger_and_duplicate_outcomes(self):
  rows=[{'task_id':'t0','family_id':'f0','arm':'P','completion':1}]
  with tempfile.TemporaryDirectory() as d:
   src=_episode_fixture(d,'scripted_fixture',['P','C'],rows,settled=False)
   with self.assertRaisesRegex(RunFailure,'not settled'):analyze_episode(src,Path(d)/'analysis')
  with tempfile.TemporaryDirectory() as d:
   src=_episode_fixture(d,'scripted_fixture',['P','C'],rows+rows)  # duplicate episode_id
   with self.assertRaisesRegex(RunFailure,'duplicate_outcome'):analyze_episode(src,Path(d)/'analysis')
