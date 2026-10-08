"""Read and hash pinned text/data only. Never import or execute upstream code."""
import ast
import collections
import hashlib
import importlib.metadata
import json
import pathlib
import platform
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent
UPSTREAM = ROOT / 'upstream'
SRC = UPSTREAM / 'src'

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def write(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

class ImportTimeNodes(ast.NodeVisitor):
    def __init__(self):
        self.nodes = []
    def visit_Import(self, node):
        self.nodes.append(node)
    def visit_ImportFrom(self, node):
        self.nodes.append(node)
    def visit_FunctionDef(self, node):
        return
    def visit_AsyncFunctionDef(self, node):
        return

def version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None

provenance = json.loads((ROOT / 'download_provenance.json').read_text())
tree_response = json.loads((ROOT / 'tree_response.json').read_text())
tree = {row['path']: row for row in tree_response['tree'] if row['type'] == 'blob'}
commit_response = json.loads((ROOT / 'commit_response.json').read_text())
commit = commit_response['sha']
assert not tree_response['truncated']
assert tree_response['sha'] == commit_response['commit']['tree']['sha']
for row in provenance:
    content = (UPSTREAM / row['path']).read_bytes()
    assert sha256(content) == row['sha256']
    assert len(content) == row['bytes']
    git_blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    assert git_blob == tree[row['path']]['sha'] == row['git_blob_sha1']

source_manifest = [{k: row[k] for k in ['path', 'bytes', 'sha256', 'git_blob_sha1']} for row in sorted(provenance, key=lambda x:x['path'])]
write('source_manifest.json', source_manifest)
project = tomllib.loads((UPSTREAM / 'pyproject.toml').read_text())
lock = tomllib.loads((UPSTREAM / 'uv.lock').read_text())
locked = {p['name']:p for p in lock['package']}

# Semantic leaf closure only: normal Python imports additionally execute the eager
# tau2/__init__.py. No import suppression, stubbing, or upstream execution occurs here.
pending = ['tau2.domains.telecom.environment']
seen = set()
closure = []
external = set()
while pending:
    mod = pending.pop()
    if mod in seen:
        continue
    seen.add(mod)
    rel = mod.replace('.', '/')
    path = SRC / (rel + '.py')
    is_package = False
    if not path.exists():
        path = SRC / rel / '__init__.py'
        is_package = True
    assert path.exists(), mod
    content = path.read_bytes()
    closure.append({'module':mod, 'path':str(path.relative_to(UPSTREAM)), 'sha256':sha256(content)})
    package = mod if is_package else mod.rpartition('.')[0]
    visitor = ImportTimeNodes()
    visitor.visit(ast.parse(content))
    for node in visitor.nodes:
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split('.')[:len(package.split('.')) - node.level + 1]
                modules = ['.'.join(parts + ([node.module] if node.module else []))]
            else:
                modules = [node.module or '']
        else:
            continue
        for name in modules:
            if name == 'tau2' or name.startswith('tau2.'):
                pending.append(name)
            elif name and name.split('.')[0] not in sys.stdlib_module_names:
                external.add(name.split('.')[0])
module_to_dist = {'yaml':'pyyaml','dotenv':'python-dotenv','docstring_parser':'docstring-parser','typing_extensions':'typing-extensions'}
dep_rows = []
for module in sorted(external):
    dist = module_to_dist.get(module,module)
    dep_rows.append({'import':module,'distribution':dist,'installed':version(dist),'locked':locked.get(dist,{}).get('version')})
write('leaf_source_closure.json', {'scope':'Semantic Telecom state/assertion leaf closure. Excludes implicit eager package-root import; not a runnable minimal-install claim.', 'upstream_executed':False,'modules':sorted(closure,key=lambda x:x['path']),'external_direct_dependencies':dep_rows})
missing = [row['distribution'] for row in dep_rows if row['installed'] is None]
assert set(missing) == {'addict','deepdiff','docstring-parser','loguru','toml'}
core = []
for requirement in project['project']['dependencies']:
    dist = requirement.split('>=')[0].split('<')[0].lower()
    core.append({'requirement':requirement,'installed':version(dist),'locked':locked.get(dist,{}).get('version')})
write('runtime_audit.json', {'python':platform.python_version(),'platform':platform.platform(),'required_python':project['project']['requires-python'],'leaf_direct_dependencies':dep_rows,'missing_leaf_direct':missing,'missing_leaf_transitive':[{'name':'orderly-set','installed':version('orderly-set'),'locked':locked['orderly-set']['version'],'required_by':'deepdiff'}],'declared_core_dependencies':core,'installation_attempted':False,'upstream_import_attempted':False,'backend_replay_executed':False,'backend_test_status':'NOT RUN: dependencies absent; no installation authorized for this phase','network_or_provider_access':'Public GitHub read downloads succeeded. Model/provider and future saved-cloud execution routes untested.'})

data_root = UPSTREAM / 'data/tau2/domains/telecom'
tasks = json.loads((data_root/'tasks.json').read_text())
splits = json.loads((data_root/'split_tasks.json').read_text())
by_id = {task['id']:task for task in tasks}
assert len(by_id)==len(tasks)==2285
legacy_small = json.loads((data_root/'tasks_small.json').read_text())
rows = []
base_candidates = []
for name, ids in splits.items():
    assert len(set(ids))==len(ids)
    assert set(ids)<=set(by_id)
    selected=[task for task in tasks if task['id'] in set(ids)]
    pure=[task for task in selected if task['evaluation_criteria']['reward_basis']==['ENV_ASSERTION'] and not task['evaluation_criteria'].get('nl_assertions')]
    multi=[task for task in pure if len(task['evaluation_criteria'].get('env_assertions') or [])>=2]
    nofuel=[task for task in multi if not any(a['name']=='refuel_data' for a in task['evaluation_criteria'].get('actions') or [])]
    no_vpn=[task for task in nofuel if not any(a['func_name']=='break_vpn' for a in task['initial_state'].get('initialization_actions') or [])]
    staged=[]
    for task in no_vpn:
        names={a['func_name'] for a in task['initial_state']['initialization_actions']}
        if task['id'].startswith('[mobile_data_issue]') and names & {'set_network_mode_preference','turn_data_saver_mode_on'} and names & {'turn_airplane_mode_on','turn_data_off','turn_roaming_off','disable_roaming'}:
            staged.append(task)
    if name=='base':
        base_candidates=staged
    rows.append({'split':name,'tasks':len(selected),'reward_basis_counts':dict(collections.Counter('+'.join(t['evaluation_criteria']['reward_basis']) for t in selected)),'nonempty_nl_assertions':sum(bool(t['evaluation_criteria'].get('nl_assertions')) for t in selected),'assertion_count_histogram':dict(collections.Counter(len(t['evaluation_criteria'].get('env_assertions') or []) for t in selected)),'pure_env':len(pure),'pure_env_at_least_two_predicates':len(multi),'excluding_gold_refuel':len(nofuel),'also_excluding_initial_vpn':len(no_vpn),'staged_connectivity_then_speed_static_candidates':len(staged),'staged_candidate_ids':[t['id'] for t in staged]})
write('task_audit.json',{'scope':'Static metadata eligibility, not demonstrated replay or natural-prefix frequency. Exclusions are conservative and path-specific. Multiple predicates need not be independent.','tasks_file_sha256':sha256((data_root/'tasks.json').read_bytes()),'split_file_sha256':sha256((data_root/'split_tasks.json').read_bytes()),'all_tasks_initialization_data_null':all(t['initial_state'].get('initialization_data') is None for t in tasks),'all_tasks_message_history_null':all(t['initial_state'].get('message_history') is None for t in tasks),'legacy_small_equal_to_current_small':{t['id']:t for t in legacy_small}=={tid:by_id[tid] for tid in splits['small']},'splits':rows,'base_candidate_task_hashes':{t['id']:sha256(canonical(t)) for t in base_candidates},'canonical_task_hash_encoding':'UTF-8 json.dumps(sort_keys=True,separators=(comma,colon),ensure_ascii=False)'})
first='[mobile_data_issue]airplane_mode_on|bad_network_preference[PERSONA:Hard]'
assert first in {t['id'] for t in base_candidates}
write('selected_task.json',by_id[first])
write('readiness.json',{'name':'tau3-telecom-1.0.1@'+commit[:12]+'-reviewer-preflight','official_package':'tau2','official_package_version':project['project']['version'],'repository':'https://github.com/sierra-research/tau2-bench','commit':commit,'commit_date':commit_response['commit']['committer']['date'],'git_tree':tree_response['sha'],'license':'MIT, Copyright (c) 2025 Sierra Research','source_manifest_sha256':sha256(canonical(source_manifest)),'selected_split':'base','selected_task_id':first,'state_replay':'NOT RUN','scripted_traces_collected':0,'natural_episodes_collected':0,'model_calls':0,'new_model_credentials':False,'paid_resources':False,'installation_attempted':False,'decision':'STATIC FEASIBILITY ONLY: missing dependencies block exact upstream execution in the present runtime.','upstream_import_policy':'No downloaded source/tests/scripts were executed.','next_allowed_step':'Parent review. No installation, cloud setup, API calls or publication performed.'})
summary={'status':'STATIC AUDIT PASSED; BACKEND NOT RUN','commit':commit,'verified_downloaded_files':len(provenance),'verified_downloaded_bytes':sum(r['bytes'] for r in provenance),'semantic_leaf_modules':len(closure),'missing_leaf_direct':missing,'task_counts':{r['split']:r['tasks'] for r in rows},'staged_static_candidate_counts':{r['split']:r['staged_connectivity_then_speed_static_candidates'] for r in rows},'source_manifest_canonical_sha256':sha256(canonical(source_manifest))}
write('static_audit_results.json',summary)
print(json.dumps(summary,indent=2))
