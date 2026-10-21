"""Work-only exact Fraction area comparison; no geometry/generator imports."""
import ast
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import signal
import statistics
import sys
import time
import traceback

import gmpy2 as g

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
SOURCE = ROOT / 'parts/993-eng-carrier-0001/source/process-skins-20261016/incremental_combinatorial_interfaces.py'
SOURCE_SHA = '69b32aee03445071f9d6d1705d1e153baf16d82f85a9ea7f25cb6532dfb99ad8'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (BASE/name).write_text(json.dumps(value, separators=(',', ':'), allow_nan=False)+'\n')
assert sha(SOURCE) == SOURCE_SHA
node = next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'exact_area')
namespace = dict(Q=Q, math=math)
exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
reference = namespace['exact_area']

def gmp_integer_lcm(points):
    """Same integer shoelace, GMP LCM/scaling/sum, exact Fraction boundary."""
    if not points: return Q(0)
    sx = g.lcm(*(p[0].denominator for p in points))
    sy = g.lcm(*(p[1].denominator for p in points))
    integers = [(p[0].numerator*(sx//p[0].denominator), p[1].numerator*(sy//p[1].denominator)) for p in points]
    numerator = sum((a[0]*b[1]-a[1]*b[0] for a,b in zip(integers, integers[1:]+integers[:1])), g.mpz(0))
    reduced = g.mpq(numerator, 2*sx*sy)
    return Q(int(reduced.numerator), int(reduced.denominator))

def gmp_rational_shoelace(points):
    """Independent exact rational GMP path, including input/output conversion."""
    if not points: return Q(0)
    rationals = [(g.mpq(x.numerator,x.denominator),g.mpq(y.numerator,y.denominator)) for x,y in points]
    area = sum((a[0]*b[1]-a[1]*b[0] for a,b in zip(rationals,rationals[1:]+rationals[:1])),g.mpq(0))/2
    return Q(int(area.numerator),int(area.denominator))

def independent(points):
    return sum((a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])),Q(0))/2

def result_value(q): return dict(numerator=str(q.numerator), denominator=str(q.denominator))
def measure(function, points, loops):
    wall,cpu=time.perf_counter(),time.process_time()
    value=None
    for _ in range(loops): value=function(points)
    return dict(wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,loops=loops),value

def expire(*_): raise TimeoutError('180-second standalone exact area benchmark budget')
signal.signal(signal.SIGALRM,expire)
signal.alarm(180)
resource.setrlimit(resource.RLIMIT_CPU,(120,121))
assert os.getpriority(os.PRIO_PROCESS,0)==10
wall_start,cpu_start=time.perf_counter(),time.process_time()
plan=json.loads((BASE/'plan.json').read_text())
assert sha(Path(__file__))==plan['benchmark_sha256']
assert all(sha(ROOT/p)==s for p,s in plan['inputs_sha256'].items())
runtime_files={str(p.relative_to(BASE)):sha(p) for p in (BASE/'env/lib/python3.11/site-packages').rglob('*') if p.is_file() and p.suffix!='.pyc'}
report=dict(schema='exact-gmp-area-experiment-1',adopted=False,region_generator_executed=False,plan_sha256=sha(BASE/'plan.json'),
    benchmark_sha256=sha(Path(__file__)),base69_sha256=sha(SOURCE),runtime_files_sha256=runtime_files,
    runtime=dict(python=sys.version,executable=sys.executable,gmpy2=g.version(),GMP=g.mp_version(),MPFR=g.mpfr_version(),MPC=g.mpc_version(),
                 nice=os.getpriority(os.PRIO_PROCESS,0),threads='one sequential Python process; no thread pool',omp_threads=os.environ.get('OMP_NUM_THREADS'),openblas_threads=os.environ.get('OPENBLAS_NUM_THREADS')),
    status='incomplete_no_adoption')
exitcode=1
try:
    cases={}
    for name in ('real-domain-ring','intercepted-ring'):
        capture=json.loads((BASE/(name+'.json')).read_text())
        cases[name]=[tuple(Q(int(n),int(d)) for n,d in p) for p in capture['points']]
    real_cases=set(cases)
    cases.update(empty=[],one_point=[(Q(1,3),Q(-7,9))],two_points=[(Q(2),Q(3)),(Q(7),Q(11))],
        dyadic_square=[(Q(0),Q(0)),(Q(1,8),Q(0)),(Q(1,8),Q(3,32)),(Q(0),Q(3,32))],
        negative_orientation=[(Q(0),Q(0)),(Q(0),Q(2)),(Q(3),Q(2)),(Q(3),Q(0))],
        non_dyadic=[(Q(1,3),Q(1,7)),(Q(4,9),Q(2,11)),(Q(-5,13),Q(1,17))],
        collinear=[(Q(1,3),Q(1,3)),(Q(2,3),Q(2,3)),(Q(4,3),Q(4,3))],
        repeated_closing_point=[(Q(0),Q(0)),(Q(1),Q(0)),(Q(0),Q(1)),(Q(0),Q(0))])
    rng=random.Random(704203)
    for i in range(100):
        cases['random-non-dyadic-'+str(i)]=[(Q(rng.randrange(-2**90,2**90),rng.randrange(1,1000)),Q(rng.randrange(-2**90,2**90),rng.randrange(1,1000))) for _ in range(rng.randrange(0,30))]
    functions=dict(base69_fraction=reference,gmp_integer_lcm=gmp_integer_lcm,gmp_rational_shoelace=gmp_rational_shoelace)
    checks=[]
    for name,points in cases.items():
        expected=reference(points)
        if name not in real_cases: assert expected==independent(points)
        values={method:fn(points) for method,fn in functions.items()}
        assert all(type(v) is Q and v==expected for v in values.values()),name
        checks.append(dict(name=name,point_count=len(points),exact_fraction_identical=True,reference=result_value(expected)))
    assert reference(cases['negative_orientation'])<0 and reference(cases['collinear'])==0
    measurements=[]
    for case in sorted(real_cases):
        points=cases[case]
        pilot,_=measure(reference,points,1)
        loops=max(1,min(200,int(.15/max(pilot['cpu_seconds'],1e-5))))
        raw=[]
        expected=reference(points)
        names=list(functions)
        for sample in range(7):
            # Rotate order to avoid always charging the same method with a phase.
            for name in names[sample%3:]+names[:sample%3]:
                timing,value=measure(functions[name],points,loops)
                assert value==expected and type(value) is Q
                raw.append(dict(method=name,sample=sample,**timing))
        summaries={name:dict(median_cpu_seconds_per_call=statistics.median(r['cpu_seconds']/r['loops'] for r in raw if r['method']==name),
                             median_wall_seconds_per_call=statistics.median(r['wall_seconds']/r['loops'] for r in raw if r['method']==name)) for name in names}
        for name in names:
            summaries[name]['cpu_speedup_vs_base69']=summaries['base69_fraction']['median_cpu_seconds_per_call']/summaries[name]['median_cpu_seconds_per_call']
        measurements.append(dict(name=case,point_count=len(points),fraction_result=result_value(expected),samples=raw,summary=summaries,
            scope='Only area function, Fraction inputs and returned Fraction; conversion overhead included; no constructor replay'))
        print(json.dumps(dict(case=case,summary=summaries)),flush=True)
    report.update(status='passed_exact_function_equivalence_no_adoption',checks=checks,measurements=measurements,
        limits='Two real area inputs only, one intercepted at the actual base69 call in private constructor814. No complete chart or regional timing, no production hook or dependency adoption. Interleaved microbenchmark shares a busy host; CPU ratios are function-local.')
    exitcode=0
except BaseException as exc:
    report.update(status='refused_or_failed_no_adoption',error=repr(exc),traceback=traceback.format_exc())
finally:
    signal.alarm(0)
    after={str(p.relative_to(BASE)):sha(p) for p in (BASE/'env/lib/python3.11/site-packages').rglob('*') if p.is_file() and p.suffix!='.pyc'}
    report.update(total_wall_seconds=time.perf_counter()-wall_start,total_cpu_seconds=time.process_time()-cpu_start,
        maximum_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        inputs_unchanged=all(sha(ROOT/p)==s for p,s in plan['inputs_sha256'].items()),
        runtime_files_unchanged=runtime_files==after,base69_unchanged=sha(SOURCE)==SOURCE_SHA)
    if not report['inputs_unchanged'] or not report['runtime_files_unchanged'] or not report['base69_unchanged']:
        report['status']='refused_integrity_changed';exitcode=1
    write('assessment.json',report)
    print(json.dumps({k:report[k] for k in ['status','total_wall_seconds','total_cpu_seconds','maximum_rss_bytes','inputs_unchanged','runtime_files_unchanged']}),flush=True)
raise SystemExit(exitcode)
