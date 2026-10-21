"""HELD/UNRUN pure four-copy/hash entrypoint; separate root admission required."""
import hashlib,json,sys,time,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
P=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-staging-freshness-prep-001'
H=E/'cp1-oneway-cooling-release-richardson2-observer004-native003-four-input-staging-root-execution-001'
O=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-003'
D=E/'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-003'
CAP=32*1024**2
START=time.monotonic()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def rec(p):
 h=hashlib.sha256();size=0
 with p.open('rb') as f:
  while True:
   b=f.read(1024**2)
   if not b:break
   h.update(b);size+=len(b)
 return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)


def time_check():
    need(time.monotonic()-START<60,'Whole-operation internal60s bound')


def selected(pin):
    name=Path(pin['path'])
    need(not name.is_absolute() and '..' not in name.parts,'Relative fixed control/input required')
    p=R/name
    need(p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,'Canonical regular declared file required')
    time_check();got=rec(p);time_check()
    need(got==pin,'Declared file identity changed: '+str(name))
    return p,got


def admit():
    need(len(sys.argv)==2 and len(sys.argv[1])==64 and all(x in '0123456789abcdef' for x in sys.argv[1]),'Exact separate root authorization digest required')
    A=H/'authorization.json'
    need(H.is_dir() and not H.is_symlink() and set(p.name for p in H.iterdir())=={'authorization.json'},'Fresh helper root with authorization only required')
    need(A.is_file() and not A.is_symlink() and rec(A)['sha256']==sys.argv[1],'Changed root authorization')
    auth=json.loads(A.read_text());plan_path=P/'held-plan.json';plan=json.loads(plan_path.read_text())
    need(auth.get('schema')=='962-native003-finite-helper-root-admission/v1' and auth.get('operation')=='stage' and auth.get('operation_authorized') is True,'No staging authority')
    need(type(auth.get('invocations')) is int and auth['invocations']==1 and auth.get('automatic_retry') is False,'One operation and no retry required')
    need(auth.get('independent_source_review_complete') is True and auth.get('root_source_review_complete') is True,'Pending helper source reviews')
    need(all(auth.get(k) is False for k in ['native_execution_authorized','fixture_execution_authorized','field_parsing_authorized','runtime_metadata_query_authorized','manufacturing_authorized']),'Staging grants no process/scientific authority')
    need(auth['helper']==rec(Path(__file__)) and auth['plan']==rec(plan_path),'Exact helper/plan required')
    need(auth['limits']==plan['operation_limits'] and auth['limits']==dict(whole_seconds=60,TERM_grace_seconds=8,stream_buffer_bytes=1048576,query_seconds=5,total_inclusive_bytes=33554432,thread_environment=1,retries=0),'Fixed helper limits required')
    need(plan['operation_source_authority_only'] is True and plan['native_execution_authorized'] is False,'Exact held plan required')
    before={name:selected(pin)[1] for name,pin in plan['known_native_roles'].items()}
    for name,pin in plan['source_plan_bindings'].items():before[name]=selected(pin)[1]
    for name in ['helper_source_peer','helper_source_bindings','helper_root_review','helper_preparation_index']:
        before[name]=selected(auth[name])[1]
    before.update(helper=rec(Path(__file__)),plan=rec(plan_path),authorization=rec(A))
    return auth,plan,before


def owned_bytes():
    total=0
    for root in [H]+([O] if O.exists() else []):
        need(root.is_dir() and not root.is_symlink(),'Owned directory changed')
        for p in root.iterdir():
            need(p.is_file() and not p.is_symlink(),'Unexpected owned entry')
            total+=p.stat().st_size
    return total


def main():
    auth,plan,before=admit()
    report=dict(schema='962-observer004-native-measurement-four-input-staging/v1',all_four_copies_byte_exact=False,no_execution=True,
        no_execution_scope='No staged-input, native or fixture execution; this interpreter only copies/hashes. No subprocess interface is present.',
        staged_inputs=plan['expected_staged_inputs'],helper=before['helper'],held_plan=before['plan'],authorization=before['authorization'],known_native_roles=plan['known_native_roles'],before=before,source_before={},copy_observations={},source_after={},destination_after={},error=None,staging_only=True)
    try:
        actual=json.loads(selected(plan['known_native_roles']['actual'])[0].read_text())
        original_stage=json.loads(selected(plan['source_plan_bindings']['native_staging_plan'])[0].read_text())
        need(actual['schema']=='962-observer004-native-measurement-actual/v1' and actual['native_execution_authorized'] is False and actual['staged_inputs']==plan['expected_staged_inputs']==original_stage['expected_staged_inputs'] and plan['copies']==original_stage['copies'],'Exact native actual/staging-plan joins required')
        need(not O.exists() and not D.exists(),'Native003 output/root must be absent; no retry')
        need(len(plan['copies'])==4 and set(plan['expected_staged_inputs'])=={Path(x['destination']['path']).name for x in plan['copies']},'Exactly four declared inputs required')
        for item in plan['copies']:
            name=Path(item['destination']['path']).name
            report['source_before'][name]=selected(item['source'])[1]
        O.mkdir()
        for item in plan['copies']:
            source,_=selected(item['source']);name=Path(item['destination']['path']).name;dest=O/name
            need(item['destination']==plan['expected_staged_inputs'][name] and str(dest.relative_to(R))==item['destination']['path'],'Changed fixed staging destination')
            count=0;digest=hashlib.sha256()
            with source.open('rb') as src,dest.open('xb') as out:
                while True:
                    time_check();block=src.read(1048576)
                    if not block:break
                    count+=len(block);need(count<=item['source']['bytes'],'Source grew during copy')
                    out.write(block);digest.update(block)
            report['copy_observations'][name]=dict(bytes=count,sha256=digest.hexdigest(),EOF=True)
            need(count==item['source']['bytes'] and digest.hexdigest()==item['source']['sha256'],'Opaque copy byte identity mismatch')
        for item in plan['copies']:
            name=Path(item['destination']['path']).name
            report['source_after'][name]=selected(item['source'])[1]
            report['destination_after'][name]=selected(item['destination'])[1]
        after={name:selected(pin)[1] for name,pin in plan['known_native_roles'].items()}
        for name,pin in plan['source_plan_bindings'].items():after[name]=selected(pin)[1]
        for name in ['helper_source_peer','helper_source_bindings','helper_root_review','helper_preparation_index']:after[name]=selected(auth[name])[1]
        after.update(helper=rec(Path(__file__)),plan=rec(P/'held-plan.json'),authorization=rec(H/'authorization.json'))
        report['after']=after
        need(before==after and report['source_before']==report['source_after'],'Control/source identities changed')
        need(set(p.name for p in O.iterdir())==set(plan['expected_staged_inputs']) and not D.exists(),'Only four staged inputs; native root remains absent')
        need(sum(x['bytes'] for x in report['destination_after'].values())==1213802,'Exact input byte total required')
        report['all_four_copies_byte_exact']=True
    except BaseException:
        report['error']=traceback.format_exc();report['all_four_copies_byte_exact']=False
    report['elapsed_before_receipt']=time.monotonic()-START
    report['whole_return_external_clock_and_inclusive_postchecks_required']=True
    encoded=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
    need(owned_bytes()+len(encoded)<=CAP,'Complete staging output/receipt exceeds32MiB; no truncation')
    with (H/'staging-receipt.json').open('xb') as f:f.write(encoded)
    if not report['all_four_copies_byte_exact'] or report['error'] is not None or owned_bytes()>CAP or time.monotonic()-START>=60:
        print('Staging closure refused; retain full prefinal receipt and require independent outer0.',file=sys.stderr,flush=True);return 2
    return 0


if __name__=='__main__':raise SystemExit(main())
