"""Verify a curated transfer manifest without executing any implementation code."""
import hashlib
import json
from pathlib import Path

import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input-root',required=True,help='Original extracted input archive, not the integrated repository')
root=Path(parser.parse_args().input_root).resolve()
manifest=json.loads((root/'TRANSFER_MANIFEST.json').read_text())
expected=set()
for row in manifest['files']:
    relative=Path(row['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise SystemExit('Unsafe manifest path')
    path=root/relative
    if path.is_symlink() or not path.is_file():
        raise SystemExit('Missing or symlinked file: '+row['path'])
    data=path.read_bytes()
    if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
        raise SystemExit('Integrity mismatch: '+row['path'])
    expected.add(row['path'])
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
extras=actual-expected-{'TRANSFER_MANIFEST.json'}
if extras:
    raise SystemExit('Unlisted files: '+', '.join(sorted(extras)))
print(json.dumps({'status':'PASS','verified_files':len(expected),'model_code_executed':False}))
