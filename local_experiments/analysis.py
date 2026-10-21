"""Task-macro paired analysis with nested replication and missing-endpoint bounds."""
from collections import defaultdict
import json
from pathlib import Path
import random
import statistics
from .storage import RunFailure,write_json,digest

SCALARS={'task_count','row_count','missing_endpoints','physical_attempts','reported_input_tokens','reported_output_tokens','calls_missing_usage','cost','loss_reduction','completion_difference'}
EPISODE_SCALARS={'task_count','episode_count','scored_episodes','missing_endpoints','physical_attempts','reported_input_tokens','reported_output_tokens','calls_missing_usage','cost','J_P','J_C','dJ_C_minus_P','trigger_rate'}

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

# --- End-to-end episode analysis (doc §11.1 / §12.1): a separate analyzer for the J(P)/J(C)/ΔJ
# estimand. Each policy runs its own natural trajectory, so episodes are NOT paired by a shared
# protected set; J(arm) is the task-macro completion rate over ALL episodes of that arm (no-trigger
# episodes stay in the denominator). ΔJ=J(C)-J(P) is paired by task and bootstrapped over task
# clusters (disjoint fault components), matching the root analyzer's independence caution.
def episode_per_task(rows,arm,field='completion'):
 out={}
 for t in sorted({r['task_id'] for r in rows}):
  v=[r[field] for r in rows if r['task_id']==t and r['arm']==arm and r.get(field) is not None]
  if v: out[t]=mean(v)
 return out

def episode_arm_J(rows,arm,field='completion'):
 per=episode_per_task(rows,arm,field)
 return mean(list(per.values())) if per else None

def episode_paired_delta(rows,armA,armB,field='completion'):
 a=episode_per_task(rows,armA,field);b=episode_per_task(rows,armB,field)
 return {t:b[t]-a[t] for t in sorted(set(a)&set(b))}

def episode_task_interval(per_task,replicates,seed,level):
 vals=list(per_task.values())
 if len(vals)<2: return None
 rng=random.Random(seed)
 samples=sorted(mean(rng.choices(vals,k=len(vals))) for _ in range(replicates))
 alpha=(1-level)/2
 return [samples[int(alpha*(replicates-1))],samples[int((1-alpha)*(replicates-1))]]

def analyze_episode(input_dir,output_dir):
 source=Path(input_dir);target=Path(output_dir)
 if target.exists(): raise RunFailure('Output directory already exists')
 status=json.loads((source/'status.json').read_text())
 if status.get('status') not in ('completed','completed_with_missing'): raise RunFailure('Run is not settled; analysis would omit assigned endpoints')
 manifest=json.loads((source/'run_manifest.json').read_text());rows=read_lines(source/'derived/episode_outcomes.jsonl');events=read_lines(source/'journal/events.jsonl')
 kind=manifest['evidence_kind'];protocol=manifest['protocol_hash']
 if not events or events[-1]['kind']!='episode_run_settled': raise RunFailure('Run ledger is not settled')
 if kind not in ('scripted_fixture','exploratory_live','confirmatory_live'): raise RunFailure('unsupported_evidence_kind')
 if any(r['evidence_kind']!=kind for r in rows) or any(e['protocol_hash']!=protocol or e['evidence_kind']!=kind for e in events): raise RunFailure('mixed_evidence_or_protocol')
 ids=[r['episode_id'] for r in rows]
 if len(ids)!=len(set(ids)): raise RunFailure('duplicate_outcome')
 config=manifest['config']['analysis'];arms=manifest['config']['arms']
 live=kind in ('exploratory_live','confirmatory_live');both={'P','C'}<=set(arms)
 attempts=[e for e in events if e['kind']=='request_dispatched'];responses=[e for e in events if e['kind']=='response_saved']
 input_tokens=[];output_tokens=[]
 for e in responses:
  u=e.get('usage')
  if isinstance(u,dict):
   for key,dest in (('prompt_tokens',input_tokens),('completion_tokens',output_tokens)):
    if type(u.get(key)) is int and u[key]>=0: dest.append(u[key])
 scored=[r for r in rows if r.get('completion') is not None];missing=len(rows)-len(scored)
 byarm={}
 for arm in arms:
  sub=[r for r in rows if r['arm']==arm];ss=[r for r in sub if r.get('completion') is not None]
  per=episode_per_task(rows,arm)
  byarm[arm]={'episodes':len(sub),'scored':len(ss),'J':episode_arm_J(rows,arm),
   'J_interval':episode_task_interval(per,config['bootstrap_replicates'],config['bootstrap_seed'],config['confidence_level']) if live else None,
   'triggered':sum(1 for r in sub if r.get('triggered')),
   'trigger_rate':(sum(1 for r in sub if r.get('triggered'))/len(sub)) if sub else None,
   'natural_terminations':sum(1 for r in ss if r.get('termination') in ('user_stop','agent_stop')),
   'ever_achieved_then_lost':sum(len(r.get('ever_achieved_then_lost_indices') or []) for r in ss)}
 delta=episode_paired_delta(rows,'P','C') if both else {}
 dJ=mean(list(delta.values())) if delta else None
 dJ_interval=episode_task_interval(delta,config['bootstrap_replicates'],config['bootstrap_seed'],config['confidence_level']) if (live and delta) else None
 bounds={}
 if live and both:
  def impute(arm,val):
   sub=[r for r in rows if r['arm']==arm];ss=[r for r in sub if r.get('completion') is not None];per={}
   for t in sorted({r['task_id'] for r in sub}):
    v=[r['completion'] for r in ss if r['task_id']==t];n=len([r for r in sub if r['task_id']==t])
    per[t]=(sum(v)+val*(n-len(v)))/n if n else None
   return mean([x for x in per.values() if x is not None])
  JC_best,JC_worst=impute('C',1),impute('C',0);JP_best,JP_worst=impute('P',1),impute('P',0)
  bounds['dJ_C_minus_P']=[(JC_worst-JP_best) if None not in (JC_worst,JP_best) else None,
                          (JC_best-JP_worst) if None not in (JC_best,JP_worst) else None]
 report={'schema_version':1,'analysis_kind':'end_to_end_episode','evidence_kind':kind,'protocol_hash':protocol,
 'model_outcomes':('confirmatory' if kind=='confirmatory_live' else 'exploratory') if live else 'not_run','formal_experiments':int(kind=='confirmatory_live'),
 'task_count':len({r['task_id'] for r in rows}),'family_count':len({r['family_id'] for r in rows}),
 'episode_count':len(rows),'scored_episodes':len(scored),'missing_endpoints':missing,
 'arms':byarm,'J_P':byarm.get('P',{}).get('J'),'J_C':byarm.get('C',{}).get('J'),'dJ_C_minus_P':dJ,'dJ_interval':dJ_interval,
 'trigger_rate':(sum(1 for r in rows if r.get('triggered'))/len(rows)) if rows else None,
 'missingness_bounds':bounds,
 'physical_attempts':len(attempts),'reported_input_tokens':sum(input_tokens) if input_tokens else None,
 'reported_output_tokens':sum(output_tokens) if output_tokens else None,'calls_missing_usage':len(attempts)-len(input_tokens),
 'cost':None,'cost_status':'unknown','logical_cost_status':'request_ancestry_with_retries_in_derived_costs_json',
 'draw_classifications':{k:sum(e['kind']=='draw_captured' and e.get('classification')==k for e in events) for k in ('invalid','out_of_scope','unchanged','valid_changed')},
 'estimand':'end-to-end episode completion J(arm)=task-macro mean over ALL episodes of that arm (no-trigger included); ΔJ=J(C)-J(P) paired by task; each policy has its own natural trajectory and its own ever-achieved goal set, so this is NOT the root experiment same-protected-set causal contrast',
 'interval_caution':'task-cluster bootstrap over disjoint fault components; fewer than two scored task clusters yields no interval',
 'point_estimate_missingness':'available scored episodes; consult imputation-based worst/best bounds',
 'claim_status':'no_confirmatory_claim'}
 if kind=='confirmatory_live':
  from .freeze import verify_freeze,check_dataset
  verify_freeze(manifest['config']);selected=check_dataset(manifest['config'])
  represented={r['task_id'] for r in rows}
  complete_units=len(represented)==len(selected) and all(t['task_id'] in represented for t in selected)
  report['claim_status']='criteria_met' if complete_units and missing==0 and dJ_interval and dJ_interval[0]>config['delta'] else 'not_established'
  report['confirmation_scope']='fixed benchmark task set; episode-start policies; conditional on the fixed task list, not unseen-family generalization; offline freeze is not external preregistration'
 target.mkdir(parents=True);target.chmod(0o700)
 write_json(target/'summary.json',report)
 write_json(target/'analysis_manifest.json',{'schema_version':1,'protocol_hash':protocol,'evidence_kind':kind,'summary_sha256':digest(report),'analysis_config':config})
 return report

def analyze(input_dir,output_dir):
 source=Path(input_dir)
 stage=None
 try: stage=json.loads((source/'status.json').read_text()).get('stage')
 except (OSError,ValueError): pass
 if stage is None:
  try: stage=json.loads((source/'run_manifest.json').read_text()).get('config',{}).get('stage')
  except (OSError,ValueError): pass
 if stage=='end-to-end': return analyze_episode(input_dir,output_dir)
 target=Path(output_dir)
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
 episode=r.get('analysis_kind')=='end_to_end_episode'
 allowlist=EPISODE_SCALARS if episode else SCALARS
 safe={'schema_version':1,'evidence_kind':r['evidence_kind'],'formal_experiments':int(r['evidence_kind']=='confirmatory_live')}
 if episode: safe['analysis_kind']='end_to_end_episode'
 for key in allowlist:
  value=r.get(key)
  if value is not None and (type(value) not in (int,float) or not -1e15<value<1e15): raise RunFailure('invalid_export_scalar')
  safe[key]=value
 safe['cost_status']='unknown';safe['model_outcomes']='not_run' if safe['evidence_kind']=='scripted_fixture' else ('confirmatory' if safe['evidence_kind']=='confirmatory_live' else 'exploratory')
 if safe['evidence_kind']=='scripted_fixture':
  if episode: safe['J_P']=safe['J_C']=safe['dJ_C_minus_P']=None
  else: safe['loss_reduction']=safe['completion_difference']=None
 target.mkdir(parents=True);target.chmod(0o700)
 write_json(target/'summary.json',safe)
 write_json(target/'disclosure.json',{'schema_version':1,'files':['summary.json'],'summary_sha256':digest(safe),'raw_text_included':False,'upload_performed':False,'limitations':'Aggregate excerpt; see private analysis for intervals, bounds and denominators.'})
 return safe
