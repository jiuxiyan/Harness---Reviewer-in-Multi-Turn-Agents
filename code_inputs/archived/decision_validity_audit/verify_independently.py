"""Independent stdlib verification; no network, source imports, or raw-data output."""
from argparse import ArgumentParser
import csv, hashlib, json, math, random
from collections import defaultdict, Counter
from fractions import Fraction as F
from pathlib import Path
parser=ArgumentParser(description=__doc__)
parser.add_argument('--input-dir',type=Path,required=True,help='Directory holding the two separately acquired raw source inputs.')
parser.add_argument('--audit-dir',type=Path,default=Path(__file__).resolve().parent,help='Directory holding protocol and derived audit outputs.')
args=parser.parse_args()
D=args.audit_dir
R=json.loads((D/'results.json').read_text())
plan=json.loads((D/'protocol.json').read_text())
assert hashlib.sha256((D/'protocol.json').read_bytes()).hexdigest()==R['protocol_sha256']
assert hashlib.sha256((D/'audit_decisions.py').read_bytes()).hexdigest()==R['script_sha256']
raw=args.input_dir
for fn,hash_ in R['input_integrity']['input_sha256'].items():
 assert hashlib.sha256((raw/fn).read_bytes()).hexdigest()==hash_
mapping=json.loads((raw/'single_setup_repository_map.json').read_text())
selected={}
tasks=defaultdict(dict)
for line in (raw/'single_setup_vectors.md5').read_text().splitlines():
 _,path=line.split(None,1)
 parts=path.split('/')
 if parts[1]!='pooled': continue
 cohort=int(parts[2].split('_')[0]); run=int(parts[3].split('_')[1])
 label=parts[4].split('_')[0]
 traj='chatcmpl-'+parts[4].split('chatcmpl-')[1].rsplit('_',1)[0]
 meta=mapping[traj]
 assert bool(meta['outcome'])==(label=='SUCCESS')
 key=(cohort,meta['instance_id'])
 assert run not in tasks[key]
 tasks[key][run]=int(label=='SUCCESS')
assert len(tasks)==3188 and len(set(i for g,i in tasks))==3188
keys=sorted(tasks)
index={key:i for i,key in enumerate(keys)}
# Independently reconstruct both fixed selectors from only attempts 1 and 2.
for g in range(5,11):
 ids=[i for c,i in keys if c==g]
 n=len(ids); k=max(1,round(F(n,10)))
 h=lambda i:hashlib.sha256(('regression-noop-audit-v1:'+i).encode()).digest()
 hash_uniform=sorted(ids,key=h)[:k]
 strata=defaultdict(list)
 for i in ids: strata[''.join(str(tasks[g,i][r]) for r in (1,2))].append(i)
 quotas={s:F(k*len(v),n) for s,v in strata.items()}
 counts={s:q.numerator//q.denominator for s,q in quotas.items()}
 ranking=sorted(strata,key=lambda s:(-(quotas[s]-counts[s]),s))
 for s in ranking[:k-sum(counts.values())]: counts[s]+=1
 subset=[i for s in sorted(strata) for i in sorted(strata[s],key=h)[:counts[s]]]
 selected[str(g)]={'allocation':counts,'hash_uniform':hash_uniform,'history_stratified':subset,'history_stratified_by_stratum':{s:sorted(strata[s],key=h)[:counts[s]] for s in sorted(strata)},'k':k,'n':n,'stratum_sizes':{s:len(strata[s]) for s in sorted(strata)}}
assert hashlib.sha256((json.dumps({int(g):v for g,v in selected.items()},sort_keys=True,indent=2)+'\n').encode()).hexdigest()==plan['prior_frozen_selections_sha256']
# Independent definitions, exact probability masses and rejection boundary.
Tests=[]; family=[]; mass={}; pvalues={}; alpha=F(1,20)
for g in range(5,11):
 for view in ['full','hash_uniform','history_stratified']:
  ids=[i for c,i in keys if c==g] if view=='full' else selected[str(g)][view]
  f=[]
  for s in ['global',0,1,2,3]:
   members=[index[g,i] for i in ids if s=='global' or int.from_bytes(hashlib.sha256(('harness-decision-validity-v1-slices:'+i).encode()).digest(),'big')%4==s]
   n=len(members); m=sum(tasks[keys[i]][3]!=tasks[keys[i]][4] for i in members)
   tid=f'g{g}.{view}.'+(s if s=='global' else f'slice{s}')
   t=R['tests'][len(Tests)]
   assert (tid,n,m)==(t['id'],t['n'],t['discordances'])
   if m not in mass:
    mass[m]=[F(math.comb(m,l),2**m) for l in range(m+1)]
    pvalues[m]=[sum(mass[m][l:],F(0)) for l in range(m+1)]
   def flags(l): return (n>0 and l>m-l,n>0 and F(2*l-m,n)>=F(1,20),n>0 and pvalues[m][l]<=alpha)
   for j,rule in enumerate(['positive_drop','five_pp_drop','unadjusted_exact']):
    exact=sum((mass[m][l] for l in range(m+1) if flags(l)[j]),F(0))
    rec=t['analytical_marginal_probabilities'][rule]
    assert exact==F(rec['numerator'],rec['denominator'])
    assert t['minimum_losses_to_declare'][rule]==next((l for l in range(m+1) if flags(l)[j]),None)
   f.append(len(Tests)); Tests.append((members,n,m,tid))
  family.append(f)
# Holm rejection is computed via its stopping rule rather than adjusted-p implementation.
def holm(ps):
 rejected=set()
 for j,i in enumerate(sorted(range(len(ps)),key=lambda i:ps[i])):
  if ps[i] > alpha/(len(ps)-j): break
  rejected.add(i)
 return rejected
rng=random.Random(20261007); counts=[Counter() for _ in Tests]; family_counts=[Counter() for _ in family]; audits=Counter()
family_csv=list(csv.DictReader((D/'family_replicates.csv').open()))
audit_csv=list(csv.DictReader((D/'audit_replicates.csv').open()))
assert len(family_csv)==18000 and len(audit_csv)==1000
for rep in range(1000):
 oldnew=[]
 for key in keys:
  old,new=tasks[key][3],tasks[key][4]
  if rng.getrandbits(1): old,new=new,old
  oldnew.append((old,new))
 ps=[]; decisions=[]
 for ti,(members,n,m,tid) in enumerate(Tests):
  losses=sum(oldnew[i]==(1,0) for i in members)
  gains=sum(oldnew[i]==(0,1) for i in members)
  assert losses+gains==m
  drop=F(losses-gains,n) if n else None
  p=pvalues[m][losses]
  flags=(drop is not None and drop>0,drop is not None and drop>=F(1,20),p<=alpha)
  ps.append(p); decisions.append(flags)
  for j,rule in enumerate(['positive_drop','five_pp_drop','unadjusted_exact']): counts[ti][rule]+=flags[j]
 audit_rejections=holm(ps)
 for i in audit_rejections: counts[i]['audit_holm']+=1
 ar=audit_csv[rep]; assert int(ar['replicate'])==rep+1
 assert int(ar['audit_holm_rejections'])==len(audit_rejections)
 audits['audit_holm']+=bool(audit_rejections)
 for j,rule in enumerate(['positive_drop','five_pp_drop','unadjusted_exact']):
  ndec=sum(flags[j] for flags in decisions)
  assert int(ar[rule+'_declarations'])==ndec
  audits[rule]+=bool(ndec)
 for fi,inds in enumerate(family):
  fr=family_csv[rep*18+fi]; assert int(fr['replicate'])==rep+1
  assert fr['family']==Tests[inds[0]][3].rsplit('.',1)[0]
  rejected={inds[i] for i in holm([ps[k] for k in inds])}
  assert int(fr['within_family_holm_rejections'])==len(rejected)
  assert int(fr['audit_holm_rejections'])==len(audit_rejections.intersection(inds))
  family_counts[fi]['within_family_holm']+=bool(rejected)
  for i in rejected: counts[i]['within_family_holm']+=1
  for j,rule in enumerate(['positive_drop','five_pp_drop','unadjusted_exact']):
   ndec=sum(decisions[i][j] for i in inds)
   assert int(fr[rule+'_declarations'])==ndec
   family_counts[fi][rule]+=bool(ndec)
for i,t in enumerate(R['tests']):
 for rule,rec in t['simulation'].items(): assert counts[i][rule]==rec['count'] and rec['replicates']==1000
for i,f in enumerate(R['families']):
 for rule,rec in f['simulation'].items(): assert family_counts[i][rule]==rec['count'] and rec['replicates']==1000
for rule,rec in R['audit_wide']['simulation'].items(): assert audits[rule]==rec['count'] and rec['replicates']==1000
# Validate all Wilson intervals independently via the quadratic roots.
allfreq=[rec for t in R['tests'] for rec in t['simulation'].values()]+[rec for f in R['families'] for rec in f['simulation'].values()]+list(R['audit_wide']['simulation'].values())
z2=1.959963984540054**2
for rec in allfreq:
 n=rec['replicates']; x=rec['count']; a=n+z2; b=-(2*x+z2); c=x*x/n
 disc=math.sqrt(b*b-4*a*c)
 roots=[max(0.,(-b-disc)/(2*a)),min(1.,(-b+disc)/(2*a))]
 assert max(abs(v-w) for v,w in zip(roots,rec['conditional_mc_wilson95']))<1e-12
print(json.dumps({'independent_checks':'PASS','source_imported':False,'tasks':len(keys),'discordant_tasks':sum(tasks[k][3]!=tasks[k][4] for k in keys),'tests':len(Tests),'families':len(family),'test_mc_metrics_verified':len(Tests)*5,'family_replicate_rows_verified':len(family_csv),'audit_replicate_rows_verified':len(audit_csv),'analytical_marginals_verified':len(Tests)*3,'wilson_intervals_verified':len(allfreq),'audit_counts':dict(audits),'empty_tests':sum(n==0 for _,n,_,_ in Tests),'no_discordance_tests_including_empty':sum(m==0 for _,_,m,_ in Tests)},indent=2))
