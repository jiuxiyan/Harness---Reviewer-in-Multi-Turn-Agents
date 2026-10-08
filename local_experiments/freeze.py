"""Model-free design freeze and declared exposure/fault-family exclusion."""
import copy
import hashlib
import json
import re
from pathlib import Path
from datetime import datetime,timezone
from .config import ROOT,PIN,ConfigError,canonical


def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()

def read_json(name):
 path=Path(name)
 if not path.is_absolute():path=ROOT/path
 if path.suffix!='.json' or path.is_symlink():raise ConfigError('Expected a regular JSON manifest')
 try:
  with path.open('rb') as f: raw=f.read(20000001)
  if len(raw)>20000000:raise ValueError()
  return json.loads(raw)
 except (OSError,ValueError,UnicodeError):raise ConfigError('Cannot read valid manifest') from None

def fault_set(task_id):
 # Freeze a conservative lexical family rule, independent of outcome labels.
 tail=task_id.split(']',1)[-1].split('[PERSONA:',1)[0]
 return frozenset(re.sub(r'_(?:on|off)$','',token.replace('disabled','state').replace('enabled','state')) for token in tail.split('|'))

def near_family(a,b):
 # Any containment or >= half-overlap is excluded, not merely exact task reuse.
 return bool(a and b and (a<=b or b<=a or len(a&b)/len(a|b)>=0.5))

def check_dataset(config):
 d=config['dataset'];manifest=read_json(d['manifest'])
 if not isinstance(manifest,dict) or not isinstance(manifest.get('tasks'),list):raise ConfigError('Task manifest requires tasks list')
 rows=manifest['tasks'];indices=d['task_indices']
 if max(indices)>=len(rows):raise ConfigError('Selected task index is absent')
 selected=[rows[i] for i in indices]
 official_path=ROOT/'code_inputs/reviewer_pilot/upstream/data/tau2/domains/telecom/tasks.json'
 official={t['id']:t for t in json.loads(official_path.read_text())}
 ids=[]
 for row in selected:
  if not isinstance(row,dict) or not all(isinstance(row.get(k),str) for k in ('task_id','task_sha256','family_id')):raise ConfigError('Invalid task manifest row')
  task=official.get(row['task_id'])
  if task is None or sha(task)!=row['task_sha256']:raise ConfigError('Pinned task identity/hash mismatch')
  if row['family_id']!='|'.join(sorted(fault_set(row['task_id']))) and row['family_id']!='|'.join(row['task_id'].split(']',1)[-1].split('[PERSONA:',1)[0].split('|')):raise ConfigError('Fault family must come from the frozen lexical rule')
  if set(task['evaluation_criteria']['reward_basis'])!={'ENV_ASSERTION'}:raise ConfigError('Unsupported evaluator basis for this study scope')
  ids.append(row['task_id'])
 if len(set(ids))!=len(ids):raise ConfigError('Duplicate task identity')
 if config['stage']=='confirmatory-roots':
  if manifest.get('source_commit')!=PIN:raise ConfigError('Confirmation requires pinned source commit')
  known=read_json('docs/planning/manifests/tasks_readiness.json')['tasks']+read_json('docs/validation/development_exposures.json')['tasks']
  for path in d['exposure_manifests']:
   extra=read_json(path)
   if not isinstance(extra,dict) or not isinstance(extra.get('tasks'),list):raise ConfigError('Invalid exposure manifest')
   known.extend(extra['tasks'])
  exposed_ids={r['task_id'] for r in known}
  for row in selected:
   if row['task_id'] in exposed_ids or any(near_family(fault_set(row['task_id']),fault_set(x)) for x in exposed_ids):raise ConfigError('Confirmation task or near-duplicate fault family already exposed')
   if row.get('research_partition')!='heldout_confirmatory':raise ConfigError('Confirmation task is not marked heldout')
  # A stricter sufficient independence restriction: no shared normalized fault token.
  for i,row in enumerate(selected):
   if any(fault_set(row['task_id']) & fault_set(other['task_id']) for other in selected[:i]):raise ConfigError('Confirmation independent units share a fault component; select one task per disjoint component')
  if config['analysis']['confirmatory_sample_size']!=len(selected):raise ConfigError('Frozen sample size must equal selected independent task count')
 return selected

def normalized(config):
 value=copy.deepcopy(config);value['gates']['frozen_protocol_receipt']=None;return value

def binding(config):
 from .provenance import source_hashes
 return {'schema_version':'frozen-root-study-v1','config':normalized(config),'source_hashes':source_hashes(),
         'task_manifest':read_json(config['dataset']['manifest']),
         'additional_exposures':[read_json(p) for p in config['dataset']['exposure_manifests']],
         'known_exposure_sha256':sha([read_json('docs/planning/manifests/tasks_readiness.json'),read_json('docs/validation/development_exposures.json')]),
         'family_exclusion_rule':'normalized on/off and enabled/disabled; containment or Jaccard >= 0.5; confirmation units share no fault token; v2',
         'not_external_preregistration':True}

def seal(config,output):
 from .config import validate
 validate(config,require_freeze=False)
 if config['stage']!='confirmatory-roots':raise ConfigError('Freeze targets confirmatory-roots only')
 body=binding(config)
 record={'payload':body,'sha256':sha(body),'created_utc':datetime.now(timezone.utc).isoformat(),'model_calls':0}
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
 return {'freeze_sha256':record['sha256'],'selected_tasks':len(check_dataset(config)),'model_calls':0}

def verify_freeze(config):
 record=read_json(config['gates']['frozen_protocol_receipt'])
 body=binding(config)
 if record.get('sha256')!=sha(record.get('payload')) or record.get('payload')!=body:raise ConfigError('Frozen protocol/source/task binding mismatch')
