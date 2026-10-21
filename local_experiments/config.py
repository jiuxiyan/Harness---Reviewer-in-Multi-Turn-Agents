"""Strict public configuration; validation never reads credentials or imports tau2."""
from copy import deepcopy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = '4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699'
STAGES = ('wire-smoke', 'natural-pilot', 'reference-only', 'confirmatory-roots', 'end-to-end')
ARMS = ('B_bare', 'B', 'S', 'A', 'P0', 'P', 'R', 'C')
# Enumerated, not open-ended: each supported WRITE carries its own restore/official-evaluation proofs.
WRITE_SCOPES = ([], ['enable_roaming', 'disable_roaming'],
                ['enable_roaming', 'disable_roaming', 'refuel_data'])
# Versioned user-simulator communication protocol (continuation doc §5). Both versions add the
# single-channel prompt convention; only the adapter version also reroutes a residual mixed
# text+single-tool-call reply instead of letting the native check terminate the episode.
USER_COMM_VERSIONS = ('user_single_channel_prompt_v1', 'user_single_channel_adapter_v1')
# Research identities (continuation doc §8.2). v3 is the strict-heldout protocol kept for the
# historical confirmatory route; v4 adds the prospective_fixed_benchmark identity, which fixes a
# known benchmark task list and collects NEW independent starts, conditioning inference on that
# fixed task set without claiming generalization to unseen fault families. The protocol_id alone
# discriminates the identity, so no new top-level field is introduced and existing v3 configs
# (and their sealed freezes) keep validating unchanged.
PROTOCOL_IDS = ('advice-lifetimes-local-v3', 'advice-lifetimes-local-v4')
POPULATIONS = ('exposed_development_only', 'heldout_confirmatory', 'prospective_fixed_benchmark')
# Episode-start (end-to-end, doc §11.1) policies: main arms P and C, plus B and R as practical
# baselines. The eight-arm root contrast lives in the confirmatory-roots stage instead.
END_TO_END_ARMS = ('B', 'R', 'P', 'C')
DEFAULT = {
 'schema_version': 2, 'protocol_id': 'advice-lifetimes-local-v3',
 'stage': 'wire-smoke', 'evidence_kind': 'not_run', 'study_label': 'exploratory',
 'source': {'benchmark_commit': PIN},
 'dataset': {'manifest': 'docs/planning/manifests/tasks_readiness.json',
             'population': 'exposed_development_only', 'task_indices': [0], 'exposure_manifests': [], 'operator_attests_unseen': False},
 'models': {'api_protocol': 'openai-compatible-chat-completions',
            'api_base_url_env': 'MODEL_API_BASE_URL', 'api_key_env': 'MODEL_API_KEY',
            'actor_model_env': 'ACTOR_MODEL', 'reviewer_model_env': 'REVIEWER_MODEL',
            'user_model_env': 'USER_MODEL', 'temperature': 0.0,
            'provider_seed_supported': False, 'max_completion_tokens': 1024, 'actor_model': None, 'reviewer_model': None, 'user_model': None, 'require_reported_model': False,
            'user_comm_protocol': 'user_single_channel_adapter_v1'},
 'arms': ['P', 'R', 'C'],
 'endpoint_policy': 'fixed_task_goals_native_model_errors_v1',
 'independence_policy': 'one_task_per_disjoint_fault_component_v1',
 'review': {'max_slots': 1, 'draws_per_root': 1,
            'public_trigger_version': 'public_single_call_after_depth_v3',
            'min_completed_assistant_tools': 2, 'min_user_text_events': 1,
            'fallback': 'original_action_no_packet', 'projection_version': 'local-receipt-v2', 'allowed_writes': ['enable_roaming','disable_roaming'], 'fixture_scenario': 'read'},
 'sampling': {'max_roots_per_trajectory': 1, 'starts_per_task': 1, 'common_prefix_repeats': 1, 'suffix_repeats': 1,
              'independent_control_continuations': 1, 'allocation_seed': 20261008},
 'limits': {'max_physical_requests': 100, 'max_native_steps': 60, 'max_native_errors': 10,
            'max_retries_per_request': 2, 'retry_backoff_seconds': 0.25, 'concurrency': 1,
            'request_timeout_seconds': 60.0, 'run_timeout_seconds': 1800.0,
            'max_output_bytes': 50000000, 'max_response_bytes': 2000000,
            'monetary_cap': None},
 'pricing': {'status': 'unknown'},
 'analysis': {'primary_contrast': ['P','C'], 'confidence_level': 0.95,
              'bootstrap_replicates': 1000, 'bootstrap_seed': 20261008,
              'delta': None, 'epsilon': None, 'confirmatory_sample_size': None},
 'gates': {'frozen_protocol_receipt': None, 'natural_coverage_receipt': None,
           'mutation_restore_receipt': None},
 'output': {'raw_private': True, 'overwrite': False, 'export_allowlist_only': True},
}
class ConfigError(ValueError): pass
class UnsupportedCapability(ConfigError): pass

def canonical(obj):
 return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def unique(pairs):
 out = {}
 for key,value in pairs:
  if key in out: raise ConfigError('Duplicate JSON key')
  out[key] = value
 return out

def integer(x, low=1, high=1000000):
 return type(x) is int and low <= x <= high

def number(x, low=0, high=2**31-1):
 return type(x) in (int,float) and low <= x <= high and math.isfinite(x)

def shape(value, spec, errors, prefix='config'):
 if not isinstance(value,dict): errors.append(prefix+': expected object'); return
 if set(value)-set(spec): errors.append(prefix+': unsupported fields')
 for key,default in spec.items():
  if key not in value: errors.append(prefix+'.'+key+': required'); continue
  if isinstance(default,dict): shape(value[key],default,errors,prefix+'.'+key)

def validate(value, require_freeze=True):
 errors=[]; shape(value,DEFAULT,errors)
 if errors: raise ConfigError('; '.join(errors))
 c=deepcopy(value)
 for name in ('schema_version','evidence_kind','source','output','pricing','endpoint_policy','independence_policy'):
  if c[name] != DEFAULT[name]: errors.append(name+': unsupported value (see supplied configuration)')
 if c['protocol_id'] not in PROTOCOL_IDS: errors.append('protocol_id: unsupported research identity')
 v4 = c['protocol_id'] == 'advice-lifetimes-local-v4'
 if type(c['schema_version']) is not int: errors.append('schema_version: expected integer')
 if c['stage'] not in STAGES: errors.append('stage: unsupported')
 arms=c['arms']
 if not isinstance(arms,list) or not arms or any(not isinstance(a,str) or a not in ARMS for a in arms): errors.append('arms: invalid')
 elif len(set(arms))!=len(arms): errors.append('arms: duplicates')
 if c['study_label'] not in ('exploratory','confirmatory'): errors.append('study_label: unsupported')
 if c['dataset']['population'] not in POPULATIONS: errors.append('dataset.population: unsupported')
 if not isinstance(c['dataset']['manifest'],str) or not c['dataset']['manifest'].endswith('.json'): errors.append('dataset.manifest: expected JSON path')
 if not isinstance(c['dataset']['exposure_manifests'],list) or any(not isinstance(x,str) or not x.endswith('.json') for x in c['dataset']['exposure_manifests']): errors.append('dataset.exposure_manifests: invalid')
 if type(c['dataset']['operator_attests_unseen']) is not bool: errors.append('dataset.operator_attests_unseen: expected boolean')
 indices=c['dataset']['task_indices']
 if not isinstance(indices,list) or not indices or any(not integer(i,0,100000) for i in indices): errors.append('dataset.task_indices: expected nonnegative indices')
 elif len(set(indices))!=len(indices): errors.append('dataset.task_indices: duplicates')
 for k,v in c['review'].items():
  if k=='fixture_scenario':
   if v not in ('read','roaming'): errors.append('review.fixture_scenario: unsupported')
  elif k=='allowed_writes':
   if v not in WRITE_SCOPES: errors.append('review.allowed_writes: unsupported WRITE scope')
  elif k in ('min_completed_assistant_tools','min_user_text_events'):
   if not integer(v,1,1000): errors.append('review.'+k+': invalid public trigger depth')
  elif v!=DEFAULT['review'][k]: errors.append('review.'+k+': unsupported')
 for k,v in c['sampling'].items():
  if not integer(v,0 if k=='allocation_seed' else 1,2**31-1 if k=='allocation_seed' else 1000): errors.append('sampling.'+k+': invalid integer')
 for k,v in c['limits'].items():
  if k=='monetary_cap':
   if v is not None: errors.append('limits.monetary_cap: unsupported with unknown price; use request/step limits')
  elif k in ('request_timeout_seconds','run_timeout_seconds','retry_backoff_seconds'):
   if not number(v,0 if k=='retry_backoff_seconds' else 0.001): errors.append('limits.'+k+': invalid duration')
  elif not integer(v,0 if k=='max_retries_per_request' else 1,2**31-1): errors.append('limits.'+k+': invalid integer')
 if c['limits']['concurrency']!=1: errors.append('limits.concurrency: only sequential execution supported')
 m=c['models']
 for k in ('api_protocol','api_base_url_env','api_key_env','actor_model_env','reviewer_model_env','user_model_env'):
  if m[k]!=DEFAULT['models'][k]: errors.append('models.'+k+': use documented transport/environment names')
 if not number(m['temperature'],0,2) or type(m['provider_seed_supported']) is not bool or not integer(m['max_completion_tokens']): errors.append('models: invalid sampling parameters')
 a=c['analysis']
 if a['primary_contrast']!=['P','C']: errors.append('analysis.primary_contrast: must be P,C')
 if not number(a['confidence_level'],0.5,0.999) or not integer(a['bootstrap_replicates'],100,100000) or not integer(a['bootstrap_seed'],0,2**31-1): errors.append('analysis: invalid resampling configuration')
 for k in ('delta','epsilon'):
  if a[k] is not None and not number(a[k],0,1): errors.append('analysis.'+k+': invalid margin')
 if a['confirmatory_sample_size'] is not None and not integer(a['confirmatory_sample_size']): errors.append('analysis.confirmatory_sample_size: invalid')
 for k,v in c['gates'].items():
  if v is not None and (not isinstance(v,str) or not v.endswith('.json')): errors.append('gates.'+k+': expected JSON receipt path')
 for key in ('natural_coverage_receipt','mutation_restore_receipt'):
  if c['gates'][key] is not None: errors.append('gates.'+key+': reserved; empirical readiness is not checked by this field')
 for role in ('actor','reviewer','user'):
  value=m[role+'_model']
  if value is not None and (not isinstance(value,str) or not value.strip()): errors.append('models: invalid explicit model identifier')
 if type(m['require_reported_model']) is not bool: errors.append('models.require_reported_model: expected boolean')
 if m['user_comm_protocol'] not in USER_COMM_VERSIONS: errors.append('models.user_comm_protocol: unsupported communication protocol version')
 if c['stage']=='confirmatory-roots':
  for k in ('delta','epsilon','confirmatory_sample_size'):
   if a[k] is None: errors.append('analysis.'+k+': required before confirmation')
  if c['study_label']!='confirmatory': errors.append('study_label: must be confirmatory')
  if not m['require_reported_model'] or any(not m[r+'_model'] for r in ('actor','reviewer','user')): errors.append('models: freeze explicit models and require reported-model identity')
  if require_freeze and not c['gates']['frozen_protocol_receipt']: errors.append('gates.frozen_protocol_receipt: required; use freeze before data collection')
  if v4:
   # prospective_fixed_benchmark identity (doc §8.2): a known, fixed benchmark task list with NEW
   # independent starts. Inference is conditional on this fixed task set; it does NOT claim unseen
   # generalization, so operator_attests_unseen must stay false and the exposure ledger is bound.
   if c['dataset']['population']!='prospective_fixed_benchmark': errors.append('v4 confirmatory-roots: population must be prospective_fixed_benchmark')
   if c['dataset']['operator_attests_unseen']: errors.append('v4 prospective_fixed_benchmark: must not claim unseen; operator_attests_unseen must be false')
   if not c['dataset']['exposure_manifests']: errors.append('v4 confirmatory-roots: exposure ledger binding required (dataset.exposure_manifests)')
  else:
   # v3 strict-heldout identity (unchanged): tasks must be unseen and disjoint from every exposure.
   if c['dataset']['population']!='heldout_confirmatory': errors.append('confirmatory-roots: exposed development tasks are ineligible')
   if not c['dataset']['operator_attests_unseen']: errors.append('dataset.operator_attests_unseen: required')
 elif c['stage']=='end-to-end':
  # Episode-start estimand J(P)/J(C)/ΔJ (doc §11.1). Each policy runs its own natural trajectory
  # from the official initial state; the public rule triggers at most one review per episode and
  # no-trigger episodes still enter the denominator. Implemented under the v4 fixed-benchmark identity.
  if not v4: errors.append('end-to-end: requires advice-lifetimes-local-v4 prospective_fixed_benchmark identity')
  if any(x not in END_TO_END_ARMS for x in arms): errors.append('end-to-end: arms limited to B,R,P,C episode-start policies')
  if c['dataset']['population'] not in ('prospective_fixed_benchmark','exposed_development_only'): errors.append('end-to-end: population must be prospective_fixed_benchmark or exposed_development_only')
  if c['study_label']=='confirmatory':
   for k in ('delta','epsilon','confirmatory_sample_size'):
    if a[k] is None: errors.append('analysis.'+k+': required before confirmation')
   if not m['require_reported_model'] or any(not m[r+'_model'] for r in ('actor','reviewer','user')): errors.append('models: freeze explicit models and require reported-model identity')
   if require_freeze and not c['gates']['frozen_protocol_receipt']: errors.append('gates.frozen_protocol_receipt: required; use freeze before data collection')
   if c['dataset']['population']!='prospective_fixed_benchmark': errors.append('end-to-end confirmatory: population must be prospective_fixed_benchmark')
   if c['dataset']['operator_attests_unseen']: errors.append('v4 prospective_fixed_benchmark: must not claim unseen; operator_attests_unseen must be false')
   if not c['dataset']['exposure_manifests']: errors.append('end-to-end confirmatory: exposure ledger binding required (dataset.exposure_manifests)')
 elif c['study_label']!='exploratory': errors.append('study_label: development stages must be exploratory')
 if errors: raise ConfigError('; '.join(errors))
 from .freeze import check_dataset,verify_freeze
 check_dataset(c)
 if c['study_label']=='confirmatory' and require_freeze: verify_freeze(c)
 return c

def load(path,require_freeze=True):
 try:
  with Path(path).open('rb') as f: raw=f.read(65537)
  if len(raw)>65536: raise ConfigError('Configuration exceeds 64 KiB')
  value=json.loads(raw,object_pairs_hook=unique)
 except ConfigError: raise
 except (OSError,ValueError,UnicodeError,RecursionError): raise ConfigError('Cannot read valid JSON configuration') from None
 return validate(value,require_freeze=require_freeze)
