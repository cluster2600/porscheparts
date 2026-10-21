"""HELD source only. One fixed unchanged-T002 call after external admission."""
import time
started=time.monotonic()
import hashlib,importlib.util,json,os,re,sys,traceback
from pathlib import Path

R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
P=E/'head-star-current24-qfnra-five-toy-owner-prep-005'
D=E/'head-star-current24-qfnra-five-toy-root-execution-002'
TOYS=D/'toys'
PY='/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10'
TRANSPORT=E/'head-star-current24-qfnra-toy-transport-prep-003/check_toy_sessions.py'
PROTOCOL=E/'head-star-current24-coupled-qfnra-prep-001/qfnra_protocol.py'
TRANSPORT_SHA='3619b5316cf23398ed479ebf724a1159bb816ce3bafb85ad93c40b67b7df4990'
PROTOCOL_SHA='9b5885a35bfbc681c0354e937b9f57621b3d8137adc25b4e2ba455e86ce59785'
IDS=('rational','algebraic','maxfinite','negative_half_minsubnormal','unsat')
CAP=33554432

def need(value,message):
    if not value:raise ValueError(message)

def rec(p):
    h=hashlib.sha256();size=0
    with p.open('rb') as f:
        while True:
            b=f.read(1048576)
            if not b:break
            h.update(b);size+=len(b)
    return dict(path=str(p.relative_to(R)) if p.is_relative_to(R) else str(p),sha256=h.hexdigest(),bytes=size)

def output_bytes():
    total=0
    for p in D.rglob('*'):
        need(not p.is_symlink(),'Unexpected owned symlink')
        if p.is_file():total+=p.stat().st_size
    return total

def main():
    need(len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'Separate admission digest required')
    A=D/'admission.json';need(rec(A)['sha256']==sys.argv[1],'Changed admission')
    auth=json.loads(A.read_text());actual_path=P/'actual-contract.json'
    need(auth['schema']=='962-five-toy-owner-root-admission/v1' and auth['five_toy_execution_authorized'] is True,'No five-toy authority')
    need(type(auth['invocations']) is int and auth['invocations']==1 and auth['automatic_retry'] is False,'One call only')
    need(auth['actual']==rec(actual_path),'Changed actual')
    actual=json.loads(actual_path.read_text())
    need(actual['schema']=='962-five-toy-owner-held-actual/v1' and actual['status']=='HELD_UNRUN' and actual['execution_authorized'] is False,'Held exact actual required')
    need(all(auth[k] is True for k in ['source_review_complete','fake_guard_acceptance_complete','selected_runtime_and_API_acceptance_complete','exact_child_review_complete']),'Pending reviewed prerequisites')
    need(all(auth[k] is False for k in ['real_head_input_authorized','real_head_model_or_word_authorized','native_execution_authorized','field_parsing_authorized','geometry_write_authorized','physical_acceptance','manufacturing_authorized']),'Toy scope only')
    need(auth['controller']==actual['controller'] and auth['adapter']==actual['adapter']==rec(Path(__file__)) and auth['wrapper']==actual['wrapper'],'Changed source association')
    need(sys.version_info[:3]==(3,10,11) and os.path.realpath(sys.executable)==actual['selected_python']['resolved_path'] and actual['selected_python']['path']==PY,'Selected historical3.10.11 required')
    need(sys.flags.isolated==sys.flags.no_site==sys.flags.dont_write_bytecode==1 and sys.flags.optimize==0 and 'site' not in sys.modules and '_distutils_hack' not in sys.modules,'-B-I-S required')
    group=os.getpgrp();need(os.getpid()==group==os.getsid(0),'Same retained owned leader required')
    need(not TOYS.exists() and not (D/'adapter-report.json').exists(),'Fresh single-call capture required')
    before=dict(transport=rec(TRANSPORT),protocol=rec(PROTOCOL),actual=rec(actual_path),admission=rec(A),adapter=rec(Path(__file__)))
    need(before['transport']==actual['transport'] and before['transport']['sha256']==TRANSPORT_SHA and before['transport']['bytes']==22291,'Frozen transport required')
    need(before['protocol']==actual['protocol'] and before['protocol']['sha256']==PROTOCOL_SHA and before['protocol']['bytes']==12459,'Frozen protocol required')
    report=dict(schema='962-five-toy-fixed-adapter-result/v1',status='INCOMPLETE',transport_calls=0,transport_returned=False,helper_report=None,helper_complete=None,helper_failure=None,unattempted_session_IDs=None,traceback=None,controls_before=before,controls_after=None,owned_group=group,returned_report_agrees_with_saved=None,real_head_input_used=False,physical_acceptance=False)
    try:
        spec=importlib.util.spec_from_file_location('fixed_held_five_toy_transport',TRANSPORT)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        need(module.PROTOCOL==PROTOCOL and module.PROTOCOL_SHA256==PROTOCOL_SHA and module.TOY_IDS==IDS and module.ARGV==['/opt/homebrew/bin/z3','-in','-smt2'],'Unchanged fixed transport required')
        report['transport_calls']=1
        returned=module.run_fixed_toys(TOYS,group)
        report['transport_returned']=True
        saved=json.loads((TOYS/'report.json').read_bytes())
        report['returned_report_agrees_with_saved']=returned==saved
        need(returned==saved and saved['schema']=='962-current24-five-persistent-Z3-toy-check/v1' and saved['complete'] is True and [v['ID'] for v in saved['results']]==list(IDS),'Complete exact five-toy result required')
        need(all(v['status']=='COMPLETE_TOY_ONLY' and v['check_count']==1 and v['solver_returncode']==0 and v['direct_child_reaped'] is True and v['cleanup']==[] for v in saved['results']),'Every original session must close normally once')
        report['status']='COMPLETE_TOY_ADAPTER_ONLY'
    except BaseException:
        report['traceback']=traceback.format_exc()
    finally:
        hp=TOYS/'report.json'
        if hp.is_file() and not hp.is_symlink():
            try:
                report['helper_report']=rec(hp)
                need(report['helper_report']['bytes']<=CAP,'Oversize helper report')
                saved=json.loads(hp.read_bytes())
                report['helper_complete']=saved.get('complete')
                report['helper_failure']=saved.get('failure')
                report['unattempted_session_IDs']=saved.get('unattempted_session_IDs')
            except BaseException:report['helper_read_error']=traceback.format_exc()
        try:
            report['controls_after']=dict(transport=rec(TRANSPORT),protocol=rec(PROTOCOL),actual=rec(actual_path),admission=rec(A),adapter=rec(Path(__file__)))
        except BaseException:report['identity_after_error']=traceback.format_exc()
        report['all_controls_unchanged']=report['controls_after']==before
        report['elapsed_before_receipt']=time.monotonic()-started
        report['forced_stop_scope']='Missing report/traceback/cleanup/unattempted IDs after outer TERM/KILL stay unknown. No signal handler or synthesized helper report.'
        raw=(json.dumps(report,indent=2,allow_nan=False)+'\n').encode()
        need(output_bytes()+len(raw)<=CAP,'Adapter inclusive32MiB refusal; preserve existing evidence')
        with (D/'adapter-report.json').open('xb') as f:f.write(raw);f.flush()
    if report['status']!='COMPLETE_TOY_ADAPTER_ONLY' or not report['all_controls_unchanged'] or report['traceback'] is not None or report.get('helper_read_error') or output_bytes()>CAP or time.monotonic()-started>=60:
        return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
