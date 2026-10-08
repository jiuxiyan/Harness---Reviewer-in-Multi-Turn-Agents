"""Fetch a fixed official allowlist with integrity checks. Never install or execute it."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

COMMIT = '4ce7c0397c1eb65c9bbe59aeacfe1ca44a1cd699'
REPOSITORY = 'https://github.com/sierra-research/tau2-bench'
ROOT = Path(__file__).resolve().parents[1]

def verify(data: bytes, row: dict) -> None:
    if len(data) != row['bytes']:
        raise ValueError('Length mismatch: ' + row['path'])
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('SHA-256 mismatch: ' + row['path'])
    blob = b'blob ' + str(len(data)).encode() + b'\0' + data
    if hashlib.sha1(blob).hexdigest() != row['git_blob_sha1']:
        raise ValueError('Git blob mismatch: ' + row['path'])

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=ROOT/'code_inputs/reviewer_pilot/upstream')
    parser.add_argument('--verify-only', action='store_true', help='Read local files only; perform no download.')
    args = parser.parse_args()
    manifest = json.loads((ROOT/'code_inputs/reviewer_pilot/source_manifest_final.json').read_text())
    destination = args.destination.resolve()
    records = []
    for row in manifest:
        relative = Path(row['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe manifest path')
        target = (destination/relative).resolve()
        if not target.is_relative_to(destination):
            raise ValueError('Unsafe destination path')
        url = f'https://raw.githubusercontent.com/sierra-research/tau2-bench/{COMMIT}/{row["path"]}'
        if target.exists():
            data = target.read_bytes()
            verify(data, row)
        elif args.verify_only:
            raise FileNotFoundError(target)
        else:
            with urlopen(url, timeout=60) as response:
                data = response.read(row['bytes']+1)
            verify(data, row)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        records.append({**row, 'url': url})
    if not args.verify_only:
        (destination.parent/'download_provenance.json').write_text(json.dumps(records, indent=2)+'\n')
    print(json.dumps({'status':'PASS', 'commit':COMMIT, 'files':len(records),
                      'bytes':sum(r['bytes'] for r in records), 'source_executed':False}))

if __name__ == '__main__':
    main()
