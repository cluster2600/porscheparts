"""HELD/UNRUN: five fixed persistent-Z3 toy sessions; no real-head input.

There is no CLI or invocation on import. Separate pure-guard passes, source/control
review, runtime freshness and root admission are prerequisites to any call.
Z3 inherits the caller's external-owner group: never a detached/new session.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import traceback


PROTOCOL = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/head-star-current24-coupled-qfnra-prep-001/qfnra_protocol.py')
PROTOCOL_SHA256 = '9b5885a35bfbc681c0354e937b9f57621b3d8137adc25b4e2ba455e86ce59785'
ARGV = ['/opt/homebrew/bin/z3','-in','-smt2']
TOY_IDS = ('rational','algebraic','maxfinite','negative_half_minsubnormal','unsat')
ENV = dict(PATH='/usr/bin:/bin',LANG='C',LC_ALL='C',PYTHONDONTWRITEBYTECODE='1',
           OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
           VECLIB_MAXIMUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
PROLOGUE = ('(set-option :print-success false)\n'
            '(set-option :produce-models true)\n'
            '(set-option :pp.decimal false)\n'
            '(set-logic QF_NRA)\n')
CHECK = ('(check-sat-using (using-params qfnra-nlsat '
         ':randomize false :shuffle_vars false :reorder false :seed 0 :zero_accuracy 0))\n')
CAP = 32*1024**2
GLOBAL_SECONDS = 60
QUERY_SECONDS = 5
TERM_SECONDS = 8
KILL_SECONDS = 8


class ToyRefusal(ValueError):
    pass


def need(value,message):
    if not value:
        raise ToyRefusal(message)


def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def load_protocol():
    raw=PROTOCOL.read_bytes()
    need(len(raw)==12459 and hashlib.sha256(raw).hexdigest()==PROTOCOL_SHA256,'Frozen pure protocol changed')
    spec=importlib.util.spec_from_file_location('held_toy_qfnra_protocol',PROTOCOL)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixed_toys():
    """Source constants/formulas only; this function is not called in preparation."""
    max_integer=str((2**53-1)*2**971)
    half_subnormal_denominator=str(2**1075)
    return [dict(ID='rational',component=1,formulas=['(= {x} (/ 3 2))'],status='sat',word=0x3ff8000000000000),
        dict(ID='algebraic',component=2,formulas=['(= (* {x} {x}) 2)','(> {x} 0)'],status='sat',word=0x3ff6a09e667f3bcd),
        dict(ID='maxfinite',component=3,formulas=['(= {x} '+max_integer+')'],status='sat',word=0x7fefffffffffffff),
        dict(ID='negative_half_minsubnormal',component=4,
             formulas=['(= {x} (- (/ 1 '+half_subnormal_denominator+')))'],status='sat',word=0x8000000000000000),
        dict(ID='unsat',component=5,formulas=['(= (+ (* {x} {x}) 1) 0)'],status='unsat',word=None)]


class Frame:
    """Strict line-delimited echo frame. Full raw streams are captured separately."""
    def __init__(self,tag):
        need(type(tag) is str and tag and all(c.isascii() and (c.isalnum() or c=='_') for c in tag),'Unsafe fixed frame tag')
        self.begin=(tag+'_BEGIN').encode('ascii')
        self.end=(tag+'_END').encode('ascii')
        self.buffer=bytearray()
        self.rows=[]
        self.state='before'
        self.echo_form=None
    def feed(self,data):
        need(type(data) is bytes,'Frame bytes required')
        self.buffer.extend(data)
        need(len(self.buffer)+sum(len(r) for r in self.rows)<=CAP,'Frame exceeds32MiB')
        while b'\n' in self.buffer:
            line,_,tail=self.buffer.partition(b'\n')
            self.buffer=bytearray(tail)
            text=bytes(line).removesuffix(b'\r')
            if self.state=='before':
                if not text.strip():
                    continue
                need(text in (self.begin,b'"'+self.begin+b'"'),'Unexpected text before frame')
                self.echo_form='quoted' if text.startswith(b'"') else 'raw'
                self.state='inside'
            elif self.state=='inside':
                end=self.end if self.echo_form=='raw' else b'"'+self.end+b'"'
                if text==end:
                    self.state='done'
                else:
                    need(text not in (self.begin,b'"'+self.begin+b'"',self.end,b'"'+self.end+b'"'),'Duplicate or inconsistent echo marker')
                    self.rows.append(bytes(line)+b'\n')
            else:
                need(not text.strip(),'Unexpected text after frame')
        if self.state=='done':
            need(not self.buffer.strip(),'Unexpected trailing bytes after frame')
        return self.state=='done'
    def response(self):
        need(self.state=='done','Incomplete frame/EOF')
        return b''.join(self.rows).decode('utf-8')


class Capture:
    def __init__(self,directory):
        need(Path(directory).is_absolute(),'Fresh absolute output directory required')
        self.root=Path(directory)
        self.root.mkdir()  # exclusive: no prior output or overwrite
        self.total=0
        self.over=False
    def write(self,handle,data,enforce=True):
        need(type(data) is bytes,'Capture bytes required')
        handle.write(data)
        handle.flush()
        self.total+=len(data)
        self.over=self.total>CAP
        if enforce:
            need(not self.over,'Inclusive helper output stop exceeded32MiB')
    def record(self,handle,value,enforce=True):
        self.write(handle,encoded(value)+b'\n',enforce)


class Session:
    def __init__(self,toy,capture,deadline,protocol):
        self.toy=toy
        self.capture=capture
        self.deadline=deadline
        self.ordinal=0
        self.check_count=0
        self.phase='new'
        self.proc=None
        self.selector=selectors.DefaultSelector()
        self.pending=bytearray()
        self.frame=None
        self.eof=set()
        self.session_id='toy_'+toy['ID']
        self.cleanup=[]
        self.protocol=protocol
        self.stdout_bytes=0
        self.stderr_bytes=0
        self.out=(capture.root/(self.session_id+'.stdout')).open('xb')
        self.err=(capture.root/(self.session_id+'.stderr')).open('xb')
        self.transcript=(capture.root/(self.session_id+'.jsonl')).open('xb')
    def start(self,expected_group):
        # The caller already retains this Session before any child can exist.
        need(type(expected_group) is int and expected_group>0 and os.getpgrp()==expected_group,
             'External owned process-group association required')
        # No setsid, setpgid, start_new_session or preexec_fn handoff exists.
        self.proc=subprocess.Popen(ARGV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   env=ENV,cwd=self.capture.root,close_fds=True,start_new_session=False)
        for stream,name in ((self.proc.stdout,'stdout'),(self.proc.stderr,'stderr')):
            os.set_blocking(stream.fileno(),False)
            self.selector.register(stream,selectors.EVENT_READ,name)
        os.set_blocking(self.proc.stdin.fileno(),False)
        self.capture.record(self.transcript,dict(event='launch',session=self.session_id,pid=self.proc.pid,
            inherited_group=expected_group,argv=ARGV,environment=ENV,check_count=0,detached=False))
    def pump(self,until,cleanup=False):
        left=until-time.monotonic()
        need(left>0,'Query/global/cleanup deadline expired')
        for key,events in self.selector.select(min(left,0.05)):
            if key.data=='stdin':
                count=os.write(key.fileobj.fileno(),self.pending)
                del self.pending[:count]
                if not self.pending:
                    self.selector.unregister(key.fileobj)
                continue
            try:
                data=os.read(key.fileobj.fileno(),65536)
            except BlockingIOError:
                continue
            if not data:
                self.eof.add(key.data)
                self.selector.unregister(key.fileobj)
                continue
            if key.data=='stdout':
                self.stdout_bytes+=len(data)
            else:
                self.stderr_bytes+=len(data)
            self.capture.write(self.out if key.data=='stdout' else self.err,data,enforce=not cleanup)
            if key.data=='stdout' and not cleanup:
                need(self.frame is not None,'Unframed stdout')
                self.frame.feed(data)
    def exchange(self,kind,command):
        need(self.proc is not None and self.proc.poll() is None,'Session exited; no replacement/retry')
        if kind=='bootstrap':
            need(self.phase=='new' and self.check_count==0,'Exactly one initial check required')
            need(command.startswith(PROLOGUE) and command.endswith(CHECK) and command.count('(check-')==1,
                 'Exactly the pinned initial check literal required')
            self.check_count=1
        else:
            need(self.phase=='sat' and kind in ('model','projection','predicate','oracle'),
                 'Only read-only queries in retained SAT session')
            need(command.startswith(('(get-model)','(get-value (')) and '\n' not in command and '\r' not in command,
                 'Post-SAT assertions/options/checks are prohibited')
            tree=self.protocol.parse_sexpr(command)
            need(type(tree) is list and ((tree==['get-model']) or
                 (len(tree)==2 and tree[0]=='get-value' and type(tree[1]) is list and bool(tree[1]))),
                 'Exactly one read-only command required')
        self.ordinal+=1
        tag='TOY_%s_Q%04d'%(self.toy['ID'],self.ordinal)
        self.frame=Frame(tag)
        wire=('(echo "'+tag+'_BEGIN")\n'+command.rstrip()+'\n(echo "'+tag+'_END")\n').encode('ascii')
        until=min(self.deadline,time.monotonic()+QUERY_SECONDS)
        self.capture.record(self.transcript,dict(event='request',session=self.session_id,pid=self.proc.pid,
            ordinal=self.ordinal,kind=kind,phase=self.phase,check_count=self.check_count,wire=wire.decode('ascii')))
        self.pending=bytearray(wire)
        self.selector.register(self.proc.stdin,selectors.EVENT_WRITE,'stdin')
        while self.pending or self.frame.state!='done':
            need(not ('stdout' in self.eof),'EOF before full framed response')
            self.pump(until)
        response=self.frame.response()
        self.capture.record(self.transcript,dict(event='response',session=self.session_id,pid=self.proc.pid,
            ordinal=self.ordinal,kind=kind,phase=self.phase,check_count=self.check_count,
            echo_form=self.frame.echo_form,complete_response=response))
        need(time.monotonic()<until,'Query full-return deadline expired after response/transcript capture')
        return response
    def close(self,normal):
        """Drain/reap exact direct child. External owner retains group/RSS/byte authority."""
        if self.proc is None:
            return
        try:
            if normal:
                need(self.proc.poll() is None,'Solver exited before deliberate session EOF')
                self.proc.stdin.close()  # EOF closes solver without another command/check.
                until=min(self.deadline,time.monotonic()+QUERY_SECONDS)
                while self.proc.poll() is None or self.eof!={'stdout','stderr'}:
                    self.pump(until)
                self.proc.wait(timeout=max(0.001,until-time.monotonic()))
                need(self.proc.returncode==0,'Solver normal exit must be0')
                need(time.monotonic()<until,'Normal drain full-return deadline expired')
                return
        except BaseException as exc:
            self.cleanup.append(dict(stage='normal_drain',error=repr(exc),traceback=traceback.format_exc()))
            normal=False
        try:
            if not self.proc.stdin.closed:
                try:
                    self.selector.unregister(self.proc.stdin)
                except KeyError:
                    pass  # No pending write was registered.
                self.pending.clear()
                self.proc.stdin.close()  # Cleanup must never send a pending command.
        except BaseException as exc:
            self.cleanup.append(dict(stage='stop_input',error=repr(exc),traceback=traceback.format_exc()))
        for name,grace in (('terminate',TERM_SECONDS),('kill',KILL_SECONDS)):
            try:
                if self.proc.poll() is None:
                    getattr(self.proc,name)()
                until=time.monotonic()+grace
                while self.proc.poll() is None or self.eof!={'stdout','stderr'}:
                    self.pump(until,cleanup=True)
                self.proc.wait(timeout=max(0.001,until-time.monotonic()))
                need(time.monotonic()<until,'Cleanup %s full-return deadline expired'%name)
                break
            except BaseException as exc:
                self.cleanup.append(dict(stage=name,error=repr(exc),traceback=traceback.format_exc()))
        need(not normal,'Unreachable normal cleanup state')
    def finish(self):
        self.selector.close()
        for stream in (() if self.proc is None else (self.proc.stdin,self.proc.stdout,self.proc.stderr)):
            stream.close()
        for stream in (self.out,self.err,self.transcript):
            stream.close()


def one_model(protocol,text,name,expected_aliases):
    need(type(name) is str and type(expected_aliases) is list
         and all(type(alias) is str for alias in expected_aliases)
         and len(set(expected_aliases))==len(expected_aliases) and name not in expected_aliases,
         'Exact unique declared toy names required')
    tree=protocol.parse_sexpr(text)
    if type(tree) is list and tree and tree[0]=='model':
        tree=tree[1:]
    expected={name:'Real',**{alias:'Bool' for alias in expected_aliases}}
    need(type(tree) is list and len(tree)==len(expected),
         'Exactly the target Real and declared Bool aliases required in full model')
    definitions={}
    for row in tree:
        need(type(row) is list and len(row)==5 and row[0]=='define-fun'
             and type(row[1]) is str and row[2]==[],
             'Complete zero-argument toy model definition required')
        key=row[1]
        need(key in expected and key not in definitions and row[3]==expected[key],
             'Exact unique toy model name and sort required')
        definitions[key]=row[4]
    need(set(definitions)==set(expected),'Complete exact toy model definition set required')
    return protocol.model_value(definitions[name])


def run_fixed_toys(output_directory,expected_owner_group):
    """FUTURE ADMITTED call only. No actual/controller/admission is authored here."""
    started=time.monotonic()
    deadline=started+GLOBAL_SECONDS
    need(sys.dont_write_bytecode and sys.flags.isolated==1 and sys.flags.no_site==1,
         'Separately selected isolated/no-site/no-bytecode Python invocation required')
    capture=Capture(output_directory)
    results=[]
    failure=None
    protocol=None
    try:
        protocol=load_protocol()
        toys=fixed_toys()
        for toy in toys:
            need(time.monotonic()<deadline,'Global60s exhausted; remaining toys unattempted')
            session=None
            result=dict(ID=toy['ID'],status='INCOMPLETE',expected=toy['status'],expected_word=toy['word'])
            results.append(result)
            try:
                session=Session(toy,capture,deadline,protocol)
                session.start(expected_owner_group)
                name=protocol.symbol(toy['component'],1,0)
                coordinate=dict(component_ID=toy['component'],node_tag=1,axis=0,symbol=name)
                formulas=[f.format(x=name) for f in toy['formulas']]
                aliases=['toy_%s_assert_%d'%(toy['ID'],i) for i in range(len(formulas))]
                bootstrap=PROLOGUE+'(declare-fun '+name+' () Real)\n'
                for alias,formula in zip(aliases,formulas):
                    bootstrap+='(define-fun '+alias+' () Bool '+formula+')\n(assert '+alias+')\n'
                bootstrap+=CHECK
                result['formula_aliases']=[dict(alias=a,formula=f) for a,f in zip(aliases,formulas)]
                status=protocol.parse_status(session.exchange('bootstrap',bootstrap))
                result['observed_status']=status
                need(status==toy['status'],'Unexpected/UNKNOWN status; no retry or later session')
                if status=='sat':
                    session.phase='sat'
                    initial_model=session.exchange('model','(get-model)')
                    initial_projection=session.exchange('projection','(get-value ('+name+'))')
                    projection=protocol.parse_projection(initial_projection,[name],'sat')
                    model=one_model(protocol,initial_model,name,aliases)
                    need(model==projection[0]['value'],'Full model and initial projection disagree')
                    model_id=protocol.snapshot_id(projection)
                    initial_predicates=[]
                    for alias in aliases:
                        answer=session.exchange('predicate','(get-value ('+alias+'))')
                        initial_predicates.append(protocol.parse_boolean(answer,alias,'sat'))
                    need(all(initial_predicates),'An original asserted toy formula evaluates false')
                    def oracle(request):
                        need(request['model_id']==model_id and request['command']=='(get-value ('+request['term']+'))',
                             'Retained model/request association changed')
                        answer=session.exchange('oracle',request['command'])
                        return protocol.parse_boolean(answer,request['term'],'sat')
                    mapped=protocol.nearest_binary64(coordinate,1,model_id,oracle)
                    need(mapped['word_u64']==toy['word'],'Unexpected toy word; no alternative candidate')
                    final_model=session.exchange('model','(get-model)')
                    final_projection=session.exchange('projection','(get-value ('+name+'))')
                    final=protocol.parse_projection(final_projection,[name],'sat')
                    need(one_model(protocol,final_model,name,aliases)==model==final[0]['value'],
                         'Retained model/projection changed during read-only queries')
                    final_predicates=[]
                    for alias in aliases:
                        answer=session.exchange('predicate','(get-value ('+alias+'))')
                        final_predicates.append(protocol.parse_boolean(answer,alias,'sat'))
                    need(all(final_predicates),'Final original toy assertion evaluates false')
                    result.update(initial_full_model=initial_model,initial_projection=initial_projection,
                        final_full_model=final_model,final_projection=final_projection,model_id=model_id,
                        original_predicates_initial=initial_predicates,original_predicates_final=final_predicates,
                        mapping=mapped,hash_alone_is_model_continuity_proof=False)
                else:
                    session.phase='unsat'
                    result['UNSAT_scope']='Solver-attributed toy result; no checked refutation or head inference'
                session.close(normal=True)
                need(not session.cleanup and session.proc.returncode==0 and session.check_count==1,
                     'Normal0/reaped one-check solver completion required')
                need(session.stderr_bytes==0,'Unexpected stderr; complete raw diagnostic retained')
                need(time.monotonic()<deadline and not capture.over,'Full normal toy deadline/budget gate')
                result.update(status='COMPLETE_TOY_ONLY',solver_returncode=session.proc.returncode,
                    check_count=session.check_count,session_id=session.session_id,pid=session.proc.pid)
            except BaseException as exc:
                result.update(error=repr(exc),traceback=traceback.format_exc())
                if hasattr(exc,'events'):
                    result['partial_mapping_events']=exc.events
                failure=result['error']
                if session is not None:
                    result['session_id']=session.session_id
                    result['pid']=session.proc.pid if session.proc is not None else None
                    session.close(normal=False)
                break
            finally:
                if session is not None:
                    result['cleanup']=session.cleanup
                    result['solver_returncode']=session.proc.poll() if session.proc is not None else None
                    result['stdout_bytes']=session.stdout_bytes
                    result['stderr_bytes']=session.stderr_bytes
                    result['direct_child_reaped']=session.proc is not None and session.proc.returncode is not None
                    session.finish()
    except BaseException as exc:
        failure=repr(exc)
        results.append(dict(status='INCOMPLETE_PREPARATION_OR_CAPTURE',error=repr(exc),traceback=traceback.format_exc()))
    complete=(failure is None and len(results)==5 and all(r.get('status')=='COMPLETE_TOY_ONLY' for r in results))
    report=dict(schema='962-current24-five-persistent-Z3-toy-check/v1',complete=complete,results=results,
        unattempted_session_count=5-sum('ID' in r for r in results),failure=failure,
        unattempted_session_IDs=[name for name in TOY_IDS if name not in {r.get('ID') for r in results}],
        elapsed_before_report_seconds=time.monotonic()-started,captured_bytes_before_report=capture.total,
        same_processgroup_required=True,no_retries=True,real_head_input_or_model_used=False,
        installed_source_or_ABI_equivalence=False,head_word_or_quality_accepted=False,
        native_retry_or_geometry_application_authorized=False,physical_or_manufacturing_accepted=False)
    with (capture.root/'report.json').open('xb') as handle:
        capture.record(handle,report,enforce=False)
    need(time.monotonic()<deadline and capture.total<=CAP,'Post-report global60s/inclusive32MiB gate')
    need(complete,'Incomplete toy gate; complete saved report retained, no retry')
    return report
