"""HELD/UNRUN analytic printed-monitor grammar cases; no native log/data read."""
import hashlib
import json
from pathlib import Path
import sys
import traceback
import types

ROOT=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
PARSER={'path': 'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-saved-measurement-parser-prep-003/parse_saved_measurement.py', 'sha256': '3c5bfbc739bb796b6ea63f4373a8984f1702ec3cfdf4883f9903df9bf483e0f4', 'bytes': 13219}
CASES=('startup_without_dt','legacy_startup_with_dt','no_startup',
       'solve1_without_dt','duplicate_startup','nonzero_startup_without_dt',
       'monitor_on_startup','malformed_monitor','missing_monitor_event')


def check(ok,message):
    if not ok:raise AssertionError(message)


def read_verified():
    path=ROOT/PARSER['path']
    check(path.is_file() and not path.is_symlink() and path.resolve(strict=True)==path,
          'Exact canonical regular parser source required')
    with path.open('rb') as handle:raw=handle.read(PARSER['bytes']+1)
    check(len(raw)==PARSER['bytes'] and hashlib.sha256(raw).hexdigest()==PARSER['sha256'],
          'Exact complete parser bytes required before future compilation')
    return path,raw


def load_verified():
    path,raw=read_verified()
    module=types.ModuleType('_parser003_monitor_synthetic')
    module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    check(module.parse_monitor_trace.__globals__ is module.__dict__,
          'Actual whole-source function must retain fresh own globals')
    check(read_verified()[1]==raw,'Parser source changed during future loading')
    return module


def solve_lines():
    rows=[]
    for step in range(1,183):
        rows.extend(['Time Step '+str(step)+', time = '+str(step)+', dt = 0.25',
                     '0 SNES Function norm 1','1 SNES Function norm 0.5'])
    return rows


def positive(name,parser):
    prefix=[] if name=='no_startup' else [
        'Time Step 0, time = 0' if name=='startup_without_dt' else
        'Time Step 0, time = 0, dt = 0.25']
    text='\n'.join(prefix+solve_lines())+'\n'
    result=parser.parse_monitor_trace(text)
    check(result['solves']==182 and result['objects_per_stream']==364,
          'Complete182 solves and364 events required')
    check(result['printed_tokens_are_not_binary64_solver_time_words'] is True,
          'Printed token caveat must remain')
    check([b['step'] for b in result['blocks']]==([0] if prefix else [])+list(range(1,183)),
          'Complete ordered blocks required')
    if prefix:
        expected_dt=None if name=='startup_without_dt' else '0.25'
        check(result['blocks'][0]==dict(step=0,time_token='0',dt_token=expected_dt,line=1,monitors=[]),
              'Startup has exact printed zero and observed missing/legacy dt, no monitor')
    expected=[]
    for ordinal in range(364):
        step=ordinal//2+1;iteration=ordinal%2
        expected.append(dict(object_ordinal=ordinal,step=step,monitor_iteration=iteration,
            printed_time_token=str(step),printed_dt_token='0.25',
            monitor_line=len(prefix)+3*(step-1)+2+iteration))
    check(result['events']==expected,'All364 independent event/token/line associations required')
    check(all(len(b['monitors'])==2 for b in result['blocks'] if b['step']!=0),
          'Startup must not consume or create a solve event')
    return dict(solves=182,events=364,startup_blocks=len(prefix),
                startup_dt_token=None if not prefix else result['blocks'][0]['dt_token'])


def negative(name,parser):
    rows=['Time Step 0, time = 0']+solve_lines()
    grammar='Unsupported monitor/time grammar; preserve, do not guess'
    if name=='solve1_without_dt':
        rows[1]='Time Step 1, time = 1';message=grammar
    elif name=='duplicate_startup':
        rows.insert(1,'Time Step 0, time = 0');message='Initial step is not an invented solve'
    elif name=='nonzero_startup_without_dt':
        rows[0]='Time Step 0, time = 1';message=grammar
    elif name=='monitor_on_startup':
        rows.insert(1,'0 SNES Function norm 1');message='Initial step is not an invented solve'
    elif name=='malformed_monitor':
        rows[2]='0 SNES Function norm';message=grammar
    elif name=='missing_monitor_event':
        del rows[3];message='Exactly182 solves with one monitor0/1 pair each required'
    else:raise AssertionError('Unknown fixed negative case')
    try:parser.parse_monitor_trace('\n'.join(rows)+'\n')
    except ValueError as error:
        check(str(error)==message,'Actual specific grammar/refusal branch required')
        return dict(exception_type='ValueError',message=str(error))
    raise AssertionError('Faulted trace accepted: '+name)


def main():
    check(sys.version_info[:3]==(3,12,11),'Future separately selected Python3.12.11 required')
    check(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
          'Future -B-I-S required')
    parser=load_verified();results=[]
    for index,name in enumerate(CASES):
        try:
            detail=positive(name,parser) if index<3 else negative(name,parser)
            results.append(dict(case=name,status='PASS',detail=detail))
        except Exception as error:
            results.append(dict(case=name,status='FAIL',exception_type=type(error).__name__,
                message=str(error),traceback=traceback.format_exc()))
    read_verified();passed=all(v['status']=='PASS' for v in results)
    report=dict(schema='962-parser003-startup-monitor-nine-case-synthetic/v1',
        status='ALL_NINE_ANALYTIC_CASES_PASSED' if passed else 'SYNTHETIC_CASE_FAILURES',
        parser=PARSER,case_count=len(results),cases=results,whole_verified_fresh_source=True,
        cached_pyc_used=False,native_log_or_scientific_body_read=False,
        actual_dt_scaling_words_verified=False,field_or_physics_or_manufacturing_qualified=False)
    print(json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
    return 0 if passed else 2


if __name__=='__main__':raise SystemExit(main())
