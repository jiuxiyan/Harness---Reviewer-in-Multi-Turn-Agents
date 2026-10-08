"""Independent stdlib verification of final recorded files and immutable source pin."""
import hashlib,importlib.metadata,json,pathlib,sys,tomllib
R=pathlib.Path(__file__).resolve().parent
provenance=json.loads((R/'download_provenance.json').read_text())
guidelines=json.loads((R/'guidelines_provenance.json').read_text())
rows={x['path']:x for x in provenance+guidelines}
tree={x['path']:x for x in json.loads((R/'tree_response.json').read_text())['tree'] if x['type']=='blob'}
manifest=[]
for p,row in sorted(rows.items()):
 b=(R/'upstream'/p).read_bytes()
 h=hashlib.sha256(b).hexdigest();git=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 assert h==row['sha256'] and git==row['git_blob_sha1']==tree[p]['sha']
 manifest.append({'path':p,'bytes':len(b),'sha256':h,'git_blob_sha1':git})
assert all(p in rows for p in tree if p.startswith('src/tau2/'))
(R/'source_manifest_final.json').write_text(json.dumps(manifest,indent=2)+'\n')
lock=tomllib.loads((R/'upstream/uv.lock').read_text());locked={x['name']:x['version'] for x in lock['package']}
site=R/'.venv/lib/python3.12/site-packages'
inventory=[]
for d in importlib.metadata.distributions(path=[str(site)]):
 name=d.metadata['Name'].lower().replace('_','-');assert name in locked,(name,'missing from lock');assert d.version==locked[name],(name,d.version,locked[name]);inventory.append({'name':name,'version':d.version})
(R/'installation_inventory.json').write_text(json.dumps(sorted(inventory,key=lambda x:x['name']),indent=2)+'\n')
assert len(inventory)==75
summary=json.loads((R/'results/suite_summary.json').read_text());assert summary['status']=='PASS'
for i in range(7):
 c=json.loads((R/f'results/task_{i}_checkpoint.json').read_text());a=json.loads((R/f'results/task_{i}_restore_a.json').read_text());b=json.loads((R/f'results/task_{i}_restore_b.json').read_text());live=json.loads((R/f'results/task_{i}_live_continuation.json').read_text())
 assert c['initial_vector']==[False,False] and c['prefix_vector']==[True,False]
 for x in [a,b]:
  assert x['raw_checkpoint_equal_including_timestamps'] and x['effective_model_history_equal'] and x['strict_replay_passed']
  assert x['terminal_vector']==[True,True] and x['official_reward']==1
  assert x['step_budget_enforced']=='max_steps' and x['error_budget_enforced']=='too_many_errors'
  assert x['premature_termination_reward']==0 and not x['unexpected_attempts']
  for key in ['next_output','next_state_sha256','terminal_state_sha256','official_reward','final_steps']:assert x[key]==live[key]
 raw=json.dumps(c['raw_checkpoint'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode();assert hashlib.sha256(raw).hexdigest()==c['raw_checkpoint_sha256']
negative=json.loads((R/'results/negative_controls.json').read_text());assert negative['status']=='PASS' and all(x['rejected'] for x in negative['negative_controls'])
read_a=json.loads((R/'results/read_tool_validation_a.json').read_text())
read_b=json.loads((R/'results/read_tool_validation_b.json').read_text())
assert read_a['status']==read_b['status']=='PASS'
assert read_a['probes']==read_b['probes'] and len(read_a['probes'])==42
assert not read_a['unexpected_attempts'] and not read_b['unexpected_attempts']
for row in read_a['probes']:
 assert row['state_unchanged'] and row['environment_before_sha256']==row['environment_after_sha256']
 checkpoint=json.loads((R/('results/task_'+str(row['task_index'])+'_checkpoint.json')).read_text())
 expected=json.dumps(checkpoint['raw_checkpoint']['environment'],sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
 assert hashlib.sha256(expected).hexdigest()==row['environment_before_sha256']
 assert row['output']['error'] is False
result={'status':'PASS','verified_official_files':len(manifest),'verified_source_bytes':sum(x['bytes'] for x in manifest),'all_tau2_source_present':True,'installed_packages_match_lock':len(inventory),'scripted_live_witnesses':7,'fresh_process_restores':14,'all_raw_checkpoints_match':True,'all_live_restored_continuations_match':True,'official_finalization_and_rewards_pass':True,'additional_read_tool_pairs':42,'additional_read_tool_repetitions':2,'additional_read_tool_outputs_equal_and_state_unchanged':True,'model_calls':0,'source_modified':False,'scope':'Final recorded suite only; development included additional scripted repeats. No natural or model-generated episodes.'}
(R/'final_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
