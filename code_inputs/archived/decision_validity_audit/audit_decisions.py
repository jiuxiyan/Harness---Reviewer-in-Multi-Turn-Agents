"""Independent offline stdlib audit of fixed-pair, fair-sign pseudo-version declarations.
No networking, model calls, raw-input redistribution, or upstream code execution.
"""
from argparse import ArgumentParser
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import csv
import hashlib
import json
import math
import platform
import random
import re

ROOT = Path(__file__).resolve().parent
EXPECTED_PROTOCOL = '13e35e1beba74b2860adaf56dd9a26f0d493ac83ebe7f4f9b615c9ca72ea0eb4'
INPUTS = {
    'single_setup_vectors.md5': 'd4c03560181ed4f024bcf607150808eb7ff7a8dd687d332c3fe0ef67ace755d4',
    'single_setup_repository_map.json': '65b5aaf7b258dff691b3e012cb98a78e8cec5a79be38db1798571bc027fa91f8',
}
ALPHA = Fraction(1, 20)
RULES = ('positive_drop', 'five_pp_drop', 'unadjusted_exact')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fraction_record(x):
    return {'numerator': x.numerator, 'denominator': x.denominator, 'decimal': float(x)}


def binomial_tails(m):
    # tail[L] = Pr(Bin(m, 1/2) >= L), including tail[0]=1 and tail[m+1]=0.
    tails = [Fraction(0)] * (m + 2)
    total = 0
    for k in range(m, -1, -1):
        total += math.comb(m, k)
        tails[k] = Fraction(total, 2 ** m)
    assert tails[0] == 1 and tails[-1] == 0
    return tails


def holm_adjust(ps):
    count = len(ps)
    adjusted = [Fraction(1)] * count
    running_max = Fraction(0)
    for rank, i in enumerate(sorted(range(count), key=lambda i: (ps[i], i))):
        running_max = max(running_max, min(Fraction(1), (count - rank) * ps[i]))
        adjusted[i] = running_max
    return adjusted


def declarations(n, m, losses, tail):
    if n == 0:
        return (False, False, False)
    signed_count = 2 * losses - m
    return (signed_count > 0, 20 * signed_count >= n, tail[losses] <= ALPHA)


def wilson(count, total):
    z = 1.959963984540054
    p = count / total
    den = 1 + z*z/total
    center = (p + z*z/(2*total)) / den
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / den
    return [max(0., center-half), min(1., center+half)]


def frequency(count, total):
    return {'count': count, 'replicates': total, 'frequency': count / total,
            'conditional_mc_wilson95': wilson(count, total)}


def checker_tests():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append({'name': name, 'passed': True})
    check('m0_p_equals_one', binomial_tails(0)[0] == 1)
    check('m5_all_losses_p_equals_1_over_32', binomial_tails(5)[5] == Fraction(1,32))
    check('m4_cannot_reject_at_005', all(p > ALPHA for p in binomial_tails(4)[:-1]))
    check('m20_all_losses_p_equals_1_over_1048576', binomial_tails(20)[20] == Fraction(1,1048576))
    check('empty_set_no_declaration', declarations(0,0,0,binomial_tails(0)) == (False,False,False))
    check('identical_pair_negative_control', declarations(80,0,0,binomial_tails(0)) == (False,False,False))
    check('zero_change_is_not_positive', declarations(20,2,1,binomial_tails(2)) == (False,False,False))
    check('inclusive_five_pp_boundary', declarations(20,1,1,binomial_tails(1)) == (True,True,False))
    check('below_five_pp_boundary', declarations(21,1,1,binomial_tails(1)) == (True,False,False))
    check('holm_retains_empty_hypotheses', holm_adjust([Fraction(1,100),Fraction(1),Fraction(1),Fraction(1),Fraction(1)])[0] == ALPHA)
    check('holm_fixed_90_boundary', holm_adjust([Fraction(1,1800)]+[Fraction(1)]*89)[0] == ALPHA)
    check('holm_fixed_90_just_above_boundary', holm_adjust([Fraction(1,1799)]+[Fraction(1)]*89)[0] > ALPHA)
    check('holm_monotonic_step_down', holm_adjust([Fraction(1,100),Fraction(3,100),Fraction(4,100)]) == [Fraction(3,100),Fraction(6,100),Fraction(6,100)])
    check('holm_empty_list', holm_adjust([]) == [])
    # Deterministic checker: 80 losses, 4 slices of 20 losses, repeated into 18 families.
    # This is manufactured code validation, never evidence of real-edit sensitivity.
    fixture = [binomial_tails(80)[80]] + [binomial_tails(20)[20]] * 4
    check('positive_fixture_family_holm_all_five', all(p <= ALPHA for p in holm_adjust(fixture)))
    check('positive_fixture_audit_holm_all_90', all(p <= ALPHA for p in holm_adjust(fixture*18)))
    check('negative_fixture_audit_holm_none', all(p == 1 for p in holm_adjust([Fraction(1)]*90)))
    return {'purpose': 'Checker fixtures only; not observed data or empirical effectiveness evidence.',
            'tests': checks, 'passed': len(checks), 'failed': 0}


def load_inputs(input_dir):
    for filename, expected in INPUTS.items():
        actual = sha(input_dir / filename)
        assert actual == expected, (filename, actual)
    mapping = json.loads((input_dir / 'single_setup_repository_map.json').read_text())
    rx = re.compile(r'vectors/(pooled|timeseries)/(\d+)_runs/run_(\d+)/(SUCCESS|FAIL)_(.*?)_(chatcmpl-[^_]+)_(pooled|ts)\.npy$')
    mat = defaultdict(lambda: defaultdict(dict))
    rep_count = defaultdict(set)
    seen_paths = set()
    for line in (input_dir / 'single_setup_vectors.md5').read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        assert path not in seen_paths
        seen_paths.add(path)
        match = rx.fullmatch(path)
        assert match, path
        mode, g, run, label, _, tid, suffix = match.groups()
        g, run = int(g), int(run)
        info = mapping[tid]
        assert (label == 'SUCCESS') == info['outcome']
        assert (suffix == 'pooled') == (mode == 'pooled')
        assert mode not in rep_count[tid]
        rep_count[tid].add(mode)
        if mode == 'pooled':
            iid = info['instance_id']
            assert run not in mat[g][iid]
            mat[g][iid][run] = int(label == 'SUCCESS')
    assert set(mapping) == set(rep_count)
    assert all(v == {'pooled','timeseries'} for v in rep_count.values())
    assert len({iid for tasks in mat.values() for iid in tasks}) == sum(map(len,mat.values()))
    for g,tasks in mat.items():
        assert all(set(v) == set(range(1,g+1)) for v in tasks.values())
    return mat, {'manifest_entries':len(seen_paths),'trajectories':len(mapping),
                 'tasks':sum(map(len,mat.values())), 'input_sha256': INPUTS}


def reconstruct_selections(mat, plan):
    def h(iid):
        return hashlib.sha256((plan['selector_hash_salt']+':'+iid).encode()).hexdigest()
    selections = {}
    for g,tasks in sorted(mat.items()):
        n=len(tasks)
        k=max(1,round(Fraction(n,10)))
        strata=defaultdict(list)
        for iid in sorted(tasks):
            pattern=''.join(str(tasks[iid][r]) for r in plan['history_attempt_indices'])
            strata[pattern].append(iid)
        alloc={s:k*len(ids)//n for s,ids in strata.items()}
        remainders={s:k*len(ids)%n for s,ids in strata.items()}
        for s in sorted(strata,key=lambda s:(-remainders[s],s))[:k-sum(alloc.values())]:
            alloc[s]+=1
        chosen={s:sorted(ids,key=h)[:alloc[s]] for s,ids in sorted(strata.items())}
        selections[g]={'n':n,'k':k,'stratum_sizes':{s:len(v) for s,v in sorted(strata.items())},
                       'allocation':alloc,'hash_uniform':sorted(tasks,key=h)[:k],
                       'history_stratified':[iid for selected in chosen.values() for iid in selected],
                       'history_stratified_by_stratum':chosen}
    encoded=(json.dumps(selections,sort_keys=True,indent=2)+'\n').encode()
    digest=hashlib.sha256(encoded).hexdigest()
    assert digest == plan['prior_frozen_selections_sha256'], digest
    return selections,digest


def build_tests(mat, selections, plan):
    all_tasks=[(g,iid) for g in sorted(mat) for iid in sorted(mat[g])]
    task_index={key:i for i,key in enumerate(all_tasks)}
    a,b=plan['evaluation_attempt_indices']
    fixed_delta=[mat[g][iid][a]-mat[g][iid][b] for g,iid in all_tasks]
    def slice_id(iid):
        return int(hashlib.sha256((plan['slice_hash_salt']+':'+iid).encode()).hexdigest(),16)%4
    tests=[]
    families=[]
    for g in sorted(mat):
        for view in plan['views']:
            ids=sorted(mat[g]) if view=='full' else selections[g][view]
            family=[]
            for s in [None,0,1,2,3]:
                members=[task_index[g,iid] for iid in ids if s is None or slice_id(iid)==s]
                m=sum(fixed_delta[i]!=0 for i in members)
                n=len(members)
                tails=binomial_tails(m)
                min_loss={rule:next((k for k in range(m+1) if declarations(n,m,k,tails)[j]),None)
                          for j,rule in enumerate(RULES)}
                analytic={rule:Fraction(0) if k is None else tails[k] for rule,k in min_loss.items()}
                family.append(len(tests))
                tests.append({'id':f'g{g}.{view}.'+('global' if s is None else f'slice{s}'),
                    'cohort':g,'view':view,'slice':'global' if s is None else f'slice{s}',
                    'n':n,'discordances':m,'members':members,'tails':tails,
                    'minimum_losses_to_declare':min_loss,'analytical':analytic,
                    'counts':{rule:0 for rule in RULES},'family_holm_count':0,'audit_holm_count':0})
            families.append({'id':f'g{g}.{view}','test_indices':family,'counts':{rule:0 for rule in RULES},
                             'holm_count':0})
    assert len(tests)==90 and len(families)==18
    assert all(len(f['test_indices'])==5 for f in families)
    return tests,families,fixed_delta


def main():
    parser=ArgumentParser()
    parser.add_argument('--input-dir',type=Path,default=ROOT.parent/'regression_data_audit')
    parser.add_argument('--output-dir',type=Path,default=ROOT)
    args=parser.parse_args()
    out=args.output_dir
    out.mkdir(parents=True,exist_ok=True)
    assert sha(ROOT/'protocol.json')==EXPECTED_PROTOCOL, 'Frozen protocol mismatch'
    plan=json.loads((ROOT/'protocol.json').read_text())
    checks=checker_tests()
    mat,integrity=load_inputs(args.input_dir)
    assert sorted(mat)==plan['cohorts']
    selections,selection_digest=reconstruct_selections(mat,plan)
    tests,families,fixed_delta=build_tests(mat,selections,plan)
    rng=random.Random(plan['orientation_seed'])
    R=plan['replicates']
    family_replicates=[]
    audit_replicates=[]
    audit_counts={rule:0 for rule in RULES}
    audit_holm_count=0
    for rep in range(R):
        delta=[(-d if rng.getrandbits(1) else d) for d in fixed_delta]
        ps=[]
        dec=[]
        for t in tests:
            signed_count=sum(delta[i] for i in t['members'])
            losses=(signed_count+t['discordances'])//2
            p=t['tails'][losses]
            flags=declarations(t['n'],t['discordances'],losses,t['tails'])
            ps.append(p)
            dec.append(flags)
            for j,rule in enumerate(RULES):
                t['counts'][rule]+=flags[j]
        audit_adjusted=holm_adjust(ps)
        audit_reject=[p<=ALPHA for p in audit_adjusted]
        for i,t in enumerate(tests):
            t['audit_holm_count']+=audit_reject[i]
        for family in families:
            idx=family['test_indices']
            adjusted=holm_adjust([ps[i] for i in idx])
            rejection=[p<=ALPHA for p in adjusted]
            for j,i in enumerate(idx):
                tests[i]['family_holm_count']+=rejection[j]
            row={'replicate':rep+1,'family':family['id']}
            for j,rule in enumerate(RULES):
                n_declared=sum(dec[i][j] for i in idx)
                family['counts'][rule]+=bool(n_declared)
                row[rule+'_declarations']=n_declared
            family['holm_count']+=any(rejection)
            row['within_family_holm_rejections']=sum(rejection)
            row['audit_holm_rejections']=sum(audit_reject[i] for i in idx)
            family_replicates.append(row)
        row={'replicate':rep+1}
        for j,rule in enumerate(RULES):
            n_declared=sum(flags[j] for flags in dec)
            audit_counts[rule]+=bool(n_declared)
            row[rule+'_declarations']=n_declared
        audit_holm_count+=any(audit_reject)
        row['audit_holm_rejections']=sum(audit_reject)
        audit_replicates.append(row)
    test_results=[]
    csv_rows=[]
    diagnostic_z=[]
    for t in tests:
        rec={k:t[k] for k in ['id','cohort','view','slice','n','discordances','minimum_losses_to_declare']}
        rec['interpretation']='empty set; no evidence' if t['n']==0 else ('no discordances; no evidence' if t['discordances']==0 else 'conditional fair-sign pseudo-version test')
        rec['minimum_attainable_p']=fraction_record(Fraction(1,2**t['discordances']))
        rec['global_nominal_alpha']=fraction_record(ALPHA)
        rec['analytical_marginal_probabilities']={k:fraction_record(v) for k,v in t['analytical'].items()}
        rec['simulation']={rule:frequency(t['counts'][rule],R) for rule in RULES}
        rec['simulation']['within_family_holm']=frequency(t['family_holm_count'],R)
        rec['simulation']['audit_holm']=frequency(t['audit_holm_count'],R)
        test_results.append(rec)
        for rule in RULES:
            exact=float(t['analytical'][rule])
            observed=t['counts'][rule]/R
            se=math.sqrt(exact*(1-exact)/R)
            z=(observed-exact)/se if se else None
            if z is not None:
                diagnostic_z.append(abs(z))
            assert se or observed==exact
            csv_rows.append({'test_id':t['id'],'tasks':t['n'],'discordances':t['discordances'],
                'rule':rule,'minimum_losses_to_declare':t['minimum_losses_to_declare'][rule],
                'analytical_probability':exact,'simulation_count':t['counts'][rule],
                'replicates':R,'simulation_frequency':observed,
                'mc_minus_analytical':observed-exact,'standardized_mc_deviation':z})
    family_results=[]
    for f in families:
        family_results.append({'id':f['id'],'hypotheses':5,
            'simulation':{**{rule:frequency(f['counts'][rule],R) for rule in RULES},
                          'within_family_holm':frequency(f['holm_count'],R)}})
    result={
        'verdict':'Expected conditional fair-sign noise and ordinary exact-test/multiplicity calibration only; ARCHIVE current regression branch absent a genuine real-edit data collection plan.',
        'protocol_sha256':EXPECTED_PROTOCOL,
        'script_sha256':sha(Path(__file__)),
        'python_version':platform.python_version(),
        'input_integrity':integrity,
        'prior_selection_sha256_verified':selection_digest,
        'constructed_randomization':{'replicates':R,'seed':plan['orientation_seed'],
            'fixed_attempt_pair':plan['evaluation_attempt_indices'],'tasks':len(fixed_delta),
            'discordant_tasks':sum(d!=0 for d in fixed_delta),
            'assumption':'Independent fair orientation per fixed task pair; shared signs across overlaps. This is imposed by the simulator, not inferred for the original agent.'},
        'hypothesis_counts':{'cohorts':6,'views_per_cohort':3,'tests_per_family':5,'families':18,'all_tests':90},
        'scope_warnings':['No real software version contrasts or real-model false-positive rate.',
            'The positive-drop, 5 pp sensitivity, and exact zero-effect tests have different decision targets; no methods ranking.',
            'Subset views concern selected-task sets only; no weighted-binomial population-effect claim.',
            'Monte Carlo intervals are conditional simulation uncertainty only, not simultaneous, and overlapping tests are dependent.',
            'Failure to reject, an empty set, or zero discordances never establishes safety or equivalence.',
            'No actual collection plan or matched real-edit traces are supplied by this audit.'],
        'audit_wide':{'hypotheses':90,'simulation':{**{rule:frequency(audit_counts[rule],R) for rule in RULES},
                             'audit_holm':frequency(audit_holm_count,R)}},
        'families':family_results,'tests':test_results,
        'analytical_mc_diagnostics':{'comparisons':len(csv_rows),
            'maximum_absolute_standardized_mc_deviation':max(diagnostic_z),
            'interpretation':'Descriptive Monte Carlo-versus-exact marginal check; many dependent comparisons, no pass/fail cutoff and no tuning.'},
        'checker_tests':checks,
        'model_api_cost':0,
    }
    write_json(out/'results.json',result)
    write_json(out/'checker_tests.json',checks)
    write_csv(out/'marginal_probabilities.csv',csv_rows)
    write_csv(out/'family_replicates.csv',family_replicates)
    write_csv(out/'audit_replicates.csv',audit_replicates)
    print(json.dumps({'verdict':result['verdict'],'tasks':len(fixed_delta),
                     'discordant_tasks':result['constructed_randomization']['discordant_tasks'],
                     'audit_wide':result['audit_wide'],'checker_tests_passed':checks['passed'],
                     'full_view_families':[f for f in family_results if f['id'].endswith('.full')]},indent=2))


if __name__=='__main__':
    main()
