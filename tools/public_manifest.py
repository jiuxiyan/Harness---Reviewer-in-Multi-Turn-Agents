"""Build/check the reviewed public tree and verify the exact official allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'PUBLIC_MANIFEST.json'}
RECEIPT='docs/validation/current_release.json'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def files():
 p=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT,check=True,capture_output=True)
 return sorted({s.decode() for s in p.stdout.split(b'\0') if s and s.decode() not in EXCLUDED and (ROOT/s.decode()).is_file()})

def inventory():
 rows=[]
 for name in files():
  p=ROOT/name
  if p.is_symlink():raise SystemExit('Public symlink is not allowed')
  rows.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
 return rows

def source_digest(rows):
 return hashlib.sha256(json.dumps([r for r in rows if r['path']!=RECEIPT],sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
 pilot=ROOT/'code_inputs/reviewer_pilot'
 official=json.loads((pilot/'source_manifest_final.json').read_text())
 for row in official:
  p=pilot/'upstream'/row['path']
  if p.is_symlink() or not p.is_file() or sha(p)!=row['sha256']:raise SystemExit('Official source mismatch: '+row['path'])
 rows=inventory();value={'schema_version':'public-release-v1','not_preregistration':True,'source_tree_sha256':source_digest(rows),'files':rows}
 path=ROOT/'PUBLIC_MANIFEST.json'
 if args.check:
  if json.loads(path.read_text())!=value:raise SystemExit('Public manifest mismatch; regenerate only after reviewing intended changes')
 else:path.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'public_files':len(rows),'official_files':len(official),'source_tree_sha256':value['source_tree_sha256'],'status':'verified' if args.check else 'generated'}))

if __name__=='__main__':main()
