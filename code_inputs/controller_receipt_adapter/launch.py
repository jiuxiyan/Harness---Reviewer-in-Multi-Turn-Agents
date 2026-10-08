"""Sanitized launcher: imports upstream only in the existing guarded private venv."""
import hashlib
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
PILOT = HERE.parent / 'reviewer_pilot'
INTERVENTIONS = HERE.parent / 'reviewer_interventions'
RESULTS = HERE / 'results'
RESULTS.mkdir(exist_ok=True)
RUN_ID = str(time.time_ns())
(RESULTS / 'run_status.json').write_text(json.dumps({'run_id': RUN_ID, 'status': 'RUNNING'}) + '\n')
for name in ('tests.json', 'demonstration.json', 'process_restart.json'):
    (RESULTS / name).write_text(json.dumps({'run_id': RUN_ID, 'status': 'NOT_COMPLETED_CURRENT_RUN'}) + '\n')
PRIVATE = HERE / '.runtime'
for name in ('home', 'xdg', 'cache', 'hf'):
    (PRIVATE / name).mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot(root):
    return {str(p.relative_to(root)): sha(p) for p in root.rglob('*') if p.is_file()
            and not any(x.startswith('.') or x.startswith('private_') or x == '__pycache__'
                        for x in p.relative_to(root).parts)}

commit = '4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699'
assert json.loads((PILOT / 'commit_response.json').read_text())['sha'] == commit
manifest = json.loads((PILOT / 'source_manifest_final.json').read_text())
for row in manifest:
    if sha(PILOT / 'upstream' / row['path']) != row['sha256']:
        raise SystemExit('Frozen official source mismatch: ' + row['path'])
dependency_manifest_counts = {}
for root in (PILOT, INTERVENTIONS):
    rows = json.loads((root / 'PUBLIC_PACKAGE_MANIFEST.json').read_text())
    dependency_manifest_counts[root.name] = len(rows)
    for row in rows:
        if sha(root / row['path']) != row['sha256']:
            raise SystemExit('Frozen bundle mismatch: ' + root.name + '/' + row['path'])
before = {r.name: snapshot(r) for r in (PILOT, INTERVENTIONS)}
source_before = {p.name: sha(p) for p in HERE.glob('*.py')}
env = {
    'PATH': str(PILOT / '.venv/bin') + ':/usr/bin:/bin',
    'HOME': str(PRIVATE / 'home'), 'XDG_CONFIG_HOME': str(PRIVATE / 'xdg'),
    'XDG_CACHE_HOME': str(PRIVATE / 'cache'), 'HF_HOME': str(PRIVATE / 'hf'),
    'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
    'TAU2_DATA_DIR': str(PILOT / 'upstream/data'), 'PYTHON_DOTENV_DISABLED': '1',
    'LITELLM_MODE': 'PRODUCTION', 'LITELLM_LOCAL_MODEL_COST_MAP': 'true',
    'LITELLM_DISABLE_LAZY_LOADING': 'false', 'HF_HUB_OFFLINE': '1',
    'HF_HUB_DISABLE_TELEMETRY': '1', 'TOKENIZERS_PARALLELISM': 'false',
    'PYTHONHASHSEED': '0',
}
p = subprocess.run([str(PILOT / '.venv/bin/python'), '-I', '-B', str(HERE / 'worker.py'), *sys.argv[1:]],
                   cwd=HERE, env=env, capture_output=True, text=True)
if p.returncode == 0:
    restart = subprocess.run([str(PILOT / '.venv/bin/python'), '-I', '-B', str(HERE / 'worker.py'), '--restore-probe'],
                             cwd=HERE, env=env, capture_output=True, text=True)
    p.stdout += '\nFresh-process restore probe:\n' + restart.stdout
    p.stderr += restart.stderr
    p.returncode = restart.returncode
after = {r.name: snapshot(r) for r in (PILOT, INTERVENTIONS)}
source_after = {p.name: sha(p) for p in HERE.glob('*.py')}
report = {'run_id': RUN_ID, 'subprocess_returncode': p.returncode, 'adapter_source_sha256': source_before,
          'adapter_source_unchanged_during_run': source_before == source_after, 'source_commit': commit, 'official_manifest_entries': len(manifest), 'frozen_bundle_manifest_entries': dependency_manifest_counts,
          'files_checked': {k: len(v) for k, v in before.items()},
          'all_frozen_files_unchanged': before == after,
          'before_sha256': hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
          'after_sha256': hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest(),
          'scope': 'All non-runtime dependency files; no bytecode writes; manifests checked before imports'}
(RESULTS / 'integrity.json').write_text(json.dumps(report, indent=2) + '\n')
(RESULTS / 'stdout.txt').write_text(p.stdout)
(RESULTS / 'stderr.txt').write_text(p.stderr)
(RESULTS / 'run_status.json').write_text(json.dumps({'run_id': RUN_ID,
    'status': 'PASS' if p.returncode == 0 and before == after and source_before == source_after else 'FAIL',
    'subprocess_returncode': p.returncode, 'adapter_source_unchanged': source_before == source_after}, indent=2) + '\n')
print(p.stdout, end='')
print(p.stderr, file=sys.stderr, end='')
if before != after or source_before != source_after:
    raise SystemExit('Dependency or adapter source changed during run')
sys.exit(p.returncode)
