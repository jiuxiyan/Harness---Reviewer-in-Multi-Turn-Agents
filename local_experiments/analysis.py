"""Task-macro paired analysis with nested replication and missing-endpoint bounds."""
from collections import defaultdict
import json
from pathlib import Path
import random
import statistics
from .storage import RunFailure,write_json,digest

SCALARS={'task_count','row_count','missing_endpoints','physical_attempts','reported_input_tokens','reported_output_tokens','calls_missing_usage','cost','loss_reduction','completion_difference'}

def mean(values): return statistics.mean(values) if values else None

def read_lines(path):
 return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()] if Path(path).exists() else []

def nested(rows,field,missing=None):
 groups=defaultdict(list)
 for r in rows:
  v=r[field]
  if v not in (0,1,None) or type(v) not in (int,type(None)): raise RunFailure('invalid_endpoint')
  if v is None: v=missing
  if v is not None: groups[(r['root_id'],r['common_prefix_repeat_id'])].append(v)
 roots=defaultdict(list)
 for (root,k),values in groups.items(): roots[root].append(mean(values))
 return mean([mean(values) for values in roots.values()])

def contrast(rows,field,missing_p=None,missing_c=None):
 tasks=sorted({r['task_id'] for r in rows});values=[]
 for task in tasks:
  p=nested([r for r in rows if r['task_id']==task and r['arm_id']=='P'],field,missing_p)
  c=nested([r for r in rows if r['task_id']==task and r['arm_id']=='C'],field,missing_c)
  if p is not None and c is not None: values.append(p-c if field=='loss' else c-p)
 return values

def interval(values,replicates,seed,level):
 if len(values)<2: return None
 rng=random.Random(seed)
 samples=sorted(mean(rng.choices(values,k=len(values))) for _ in range(replicates))
 alpha=(1-level)/2
 return [samples[int(alpha*(replicates-1))],samples[int((1-alpha)*(replicates-1))]]

def analyze(input_dir,output_dir):
 source=Path(input_dir);target=Path(output_dir)
 if target.exists(): raise RunFailure('Output directory already exists')
 status=json.loads((source/'status.json').read_text())
 if status.get('status') not in ('completed','completed_with_missing'): raise RunFailure('Run is not settled; analysis would omit assigned endpoints')
 manifest=json.loads((source/'run_manifest.json').read_text());rows=read_lines(source/'derived/root_outcomes.jsonl');events=read_lines(source/'journal/events.jsonl')
 kind=manifest['evidence_kind'];protocol=manifest['protocol_hash']
 if not events or events[-1]['kind']!='run_settled' or events[-1]['assigned_rows']!=len(rows): raise RunFailure('Run ledger is not settled')
 if kind not in ('scripted_fixture','exploratory_live','confirmatory_live'): raise RunFailure('unsupported_evidence_kind')
 if any(r['evidence_kind']!=kind for r in rows) or any(e['protocol_hash']!=protocol or e['evidence_kind']!=kind for e in events): raise RunFailure('mixed_evidence_or_protocol')
 identities=[(r['root_id'],r['arm_id'],r['common_prefix_repeat_id'],r['suffix_repeat_id']) for r in rows]
 if len(identities)!=len(set(identities)): raise RunFailure('duplicate_outcome')
 config=manifest['config']['analysis'];both={'P','C'}<=set(manifest['config']['arms'])
 live=kind in ('exploratory_live','confirmatory_live');loss=contrast(rows,'loss') if both else [];completion=contrast(rows,'completion') if both else []
 attempts=[e for e in events if e['kind']=='request_dispatched'];responses=[e for e in events if e['kind']=='response_saved']
 input_tokens=[];output_tokens=[]
 for e in responses:
  u=e.get('usage')
  if isinstance(u,dict):
   for key,dest in (('prompt_tokens',input_tokens),('completion_tokens',output_tokens)):
    if type(u.get(key)) is int and u[key]>=0: dest.append(u[key])
 missing=sum(r['loss'] is None for r in rows)
 bounds={}
 if live and both:
  bounds['loss_reduction']=[mean(contrast(rows,'loss',0,1)),mean(contrast(rows,'loss',1,0))]
  bounds['completion_difference']=[mean(contrast(rows,'completion',1,0)),mean(contrast(rows,'completion',0,1))]
 family_groups=defaultdict(list)
 for r in rows: family_groups[r['family_id']].append(r)
 sensitivity=[mean(contrast(v,'loss')) for v in family_groups.values()] if both else []
 report={'schema_version':1,'evidence_kind':kind,'protocol_hash':protocol,
 'model_outcomes':('confirmatory' if kind=='confirmatory_live' else 'exploratory') if live else 'not_run','formal_experiments':int(kind=='confirmatory_live'),
 'task_count':len({r['task_id'] for r in rows}),'family_count':len(family_groups),'row_count':len(rows),'missing_endpoints':missing,
 'loss_reduction':mean(loss) if live else None,'completion_difference':mean(completion) if live else None,
 'loss_interval':interval(loss,config['bootstrap_replicates'],config['bootstrap_seed'],config['confidence_level']) if live else None,
 'completion_interval':interval(completion,config['bootstrap_replicates'],config['bootstrap_seed'],config['confidence_level']) if live else None,
 'missingness_bounds':bounds,'family_macro_loss_reduction':mean([v for v in sensitivity if v is not None]) if live else None,
 'physical_attempts':len(attempts),'reported_input_tokens':sum(input_tokens) if input_tokens else None,
 'reported_output_tokens':sum(output_tokens) if output_tokens else None,'calls_missing_usage':len(attempts)-len(input_tokens),
 'cost':None,'cost_status':'unknown','logical_cost_status':'request_ancestry_with_retries_in_derived_costs_json',
 'interval_caution':'task-cluster bootstrap; confirmation restricts units to disjoint normalized fault components; fewer than two units yields no interval; family sensitivity is a point estimate only',
 'estimand':'equal common-segment means within roots; equal roots within tasks; equal tasks',
 'point_estimate_missingness':'available endpoints within task; consult assignment-based worst/best bounds',
 'structural_zero_rows':sum(bool(r.get('structural_zero')) for r in rows),'draw_classifications':{k:sum(e['kind']=='draw_captured' and e.get('classification')==k for e in events) for k in ('invalid','out_of_scope','unchanged','valid_changed')},
 'claim_status':'no_confirmatory_claim'}
 if kind=='confirmatory_live':
  from .freeze import verify_freeze,check_dataset
  verify_freeze(manifest['config']);selected=check_dataset(manifest['config'])
  represented={r['task_id'] for r in rows}
  coverage=json.loads((source/'derived/coverage.json').read_text())
  report['reference_coverage']=coverage
  complete_units=coverage['reference_failures']==0 and len(represented)==len(selected) and all(r['task_id'] in represented for r in selected)
  lo=report['loss_interval'];co=report['completion_interval']
  report['claim_status']='criteria_met' if complete_units and missing==0 and lo and co and lo[0]>config['delta'] and co[0]>=-config['epsilon'] else 'not_established'
  report['confirmation_scope']='fixed task goals; root-conditioned; independently declared disjoint fault components; no dynamic goal revocation; offline freeze is not external preregistration'
 target.mkdir(parents=True);target.chmod(0o700)
 write_json(target/'summary.json',report)
 write_json(target/'analysis_manifest.json',{'schema_version':1,'protocol_hash':protocol,'evidence_kind':kind,'summary_sha256':digest(report),'analysis_config':config})
 return report

def export(input_dir,output_dir):
 source=Path(input_dir);target=Path(output_dir)
 if target.exists(): raise RunFailure('Output directory already exists')
 r=json.loads((source/'summary.json').read_text());m=json.loads((source/'analysis_manifest.json').read_text())
 if digest(r)!=m['summary_sha256'] or r['protocol_hash']!=m['protocol_hash']: raise RunFailure('analysis_integrity_mismatch')
 if r['evidence_kind'] not in ('scripted_fixture','exploratory_live','confirmatory_live'): raise RunFailure('invalid_evidence_kind')
 # Rebuild from a typed numeric allowlist; never copy arbitrary files/text.
 safe={'schema_version':1,'evidence_kind':r['evidence_kind'],'formal_experiments':int(r['evidence_kind']=='confirmatory_live')}
 for key in SCALARS:
  value=r[key]
  if value is not None and (type(value) not in (int,float) or not -1e15<value<1e15): raise RunFailure('invalid_export_scalar')
  safe[key]=value
 safe['cost_status']='unknown';safe['model_outcomes']='not_run' if safe['evidence_kind']=='scripted_fixture' else ('confirmatory' if safe['evidence_kind']=='confirmatory_live' else 'exploratory')
 if safe['evidence_kind']=='scripted_fixture':
  safe['loss_reduction']=safe['completion_difference']=None
 target.mkdir(parents=True);target.chmod(0o700)
 write_json(target/'summary.json',safe)
 write_json(target/'disclosure.json',{'schema_version':1,'files':['summary.json'],'summary_sha256':digest(safe),'raw_text_included':False,'upload_performed':False,'limitations':'Aggregate excerpt; see private analysis for intervals, bounds and denominators.'})
 return safe
