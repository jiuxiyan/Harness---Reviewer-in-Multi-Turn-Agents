"""Source/protocol hashes for each new run; no environment or Git subprocess."""
import hashlib
import json
from pathlib import Path
from .config import ROOT
from .storage import RunFailure

def source_hashes():
 paths=list((ROOT/'local_experiments').glob('*.py'))+[ROOT/'docs/protocol/local_runner_v2.md',ROOT/'docs/validation/development_exposures.json',ROOT/'paper/manuscript.txt',ROOT/'docs/protocol/current_protocol.md',ROOT/'docs/planning/manifests/tasks_readiness.json',ROOT/'code_inputs/reviewer_pilot/source_manifest_final.json']
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def verify_upstream():
 pilot=ROOT/'code_inputs/reviewer_pilot'
 for row in json.loads((pilot/'source_manifest_final.json').read_text()):
  p=pilot/'upstream'/row['path']
  if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise RunFailure('upstream_source_mismatch')
