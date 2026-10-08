"""Run seven independent scripted backend witnesses, with fresh process per phase."""
import concurrent.futures,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parent
OUT=R/'results'
def phase(args):
    result=subprocess.run([sys.executable,str(R/'launch_offline.py'),*args],capture_output=True,text=True)
    stem='_'.join(args)
    (OUT/(stem+'_stdout.txt')).write_text(result.stdout)
    (OUT/(stem+'_stderr.txt')).write_text(result.stderr)
    if result.returncode:raise RuntimeError(stem+' failed: '+result.stdout[-2500:])
    return stem
# Creation writes each task-specific checkpoint; no workers share mutable environments.
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for item in pool.map(phase,[['create',str(i)] for i in range(7)]):print(item+' passed',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for item in pool.map(phase,[['restore',str(i),rep] for i in range(7) for rep in ['a','b']]):print(item+' passed',flush=True)
rows=[]
for i in range(7):
    a=json.loads((OUT/f'task_{i}_restore_a.json').read_text());b=json.loads((OUT/f'task_{i}_restore_b.json').read_text())
    for key in ['semantic_checkpoint_sha256','next_state_sha256','terminal_state_sha256','next_output','prefix_vector','terminal_vector','official_reward_info','final_steps','remaining_steps']:
        assert a[key]==b[key],(i,key)
    live=json.loads((OUT/f'task_{i}_live_continuation.json').read_text())
    for key in ['next_output','next_state_sha256','terminal_state_sha256','official_reward','final_steps']:
        assert a[key]==b[key]==live[key],('live comparison',i,key)
    assert a['official_finalization_passed'] and a['step_budget_enforced']=='max_steps' and a['error_budget_enforced']=='too_many_errors'
    rows.append({'raw_checkpoint_equal_including_timestamps':a['raw_checkpoint_equal_including_timestamps'],'effective_model_history_equal':a['effective_model_history_equal'],'live_next_and_terminal_equal':True,'official_finalization_passed':True,'step_and_error_budgets_enforced':True,'task_index':i,'task_id':a['task_id'],'reconstructed_twice':True,'checkpoint_equal':True,'next_action_output_and_state_equal':True,'terminal_state_equal':True,'prefix_vector':a['prefix_vector'],'terminal_vector':a['terminal_vector'],'official_reward':a['official_reward'],'steps':a['final_steps'],'checkpoint_sha256':a['semantic_checkpoint_sha256'],'next_state_sha256':a['next_state_sha256'],'terminal_state_sha256':a['terminal_state_sha256']})
summary={'status':'PASS','scope':'7 scripted infrastructure witnesses; 14 fresh-process restores. No model behavior measured.','source_commit':'4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699','tasks':rows,'model_calls':0,'unexpected_model_or_network_attempts':0,'official_source_modified':False,'normalization':'Checkpoint restores raw timestamp/turn_idx exactly. Future fresh timestamps excluded only from semantic comparisons; official prompt conversion strips them and official chronological finalization is tested.','adapter_scope':'single pending assistant tool call after user message; explicit step/error budget and Python/NumPy RNG restoration; scripted participant queues only'}
(OUT/'suite_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
