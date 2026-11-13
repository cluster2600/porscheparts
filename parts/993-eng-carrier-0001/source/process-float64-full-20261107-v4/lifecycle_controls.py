"""Actual outer-stage interruption control for the separate full-run guard."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time
import common


def run(args, output):
    root=Path(output)/'interrupted-stage';root.mkdir()
    runroot=root/'guard';runroot.mkdir()
    marker=root/'numerical-ready.json';grandchild_marker=root/'grandchild-ready.json'
    grandchild_code="import os,signal,time,pathlib;signal.signal(signal.SIGTERM,signal.SIG_IGN);pathlib.Path(%r).write_text(str(os.getpid()));time.sleep(60)"%str(grandchild_marker)
    numerical_code=("import json,os,pathlib,signal,subprocess,sys,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);"
                    "p=subprocess.Popen([sys.executable,'-I','-B','-S','-c',%r]);"
                    "pathlib.Path(%r).write_text(json.dumps({'pid':os.getpid(),'pgid':os.getpgrp(),'grandchild':p.pid}));time.sleep(60)")%(grandchild_code,str(marker))
    guard_path=Path(__file__).with_name('guard.py')
    pins={str(p):common.sha(p)for p in [Path(__file__),guard_path,Path(common.__file__),common.LAYER/'owned_process_group.py']}
    code="""import sys
sys.path.insert(0,%r)
import guard,common
pins=%r
def verify():
 for path,h in pins.items():
  if common.sha(path)!=h:raise ValueError('Interruption fixture source changed')
report=guard.supervise(%r,%r,verify,%r,%r)
raise SystemExit(0 if report['reason']=='complete' else 1)
"""%(str(Path(__file__).parent),pins,[sys.executable,'-I','-B','-S','-c',numerical_code],str(runroot),str(root),'synthetic-interruption-control')
    sentinel=subprocess.Popen([sys.executable,'-I','-B','-S','-c','import time;time.sleep(60)'],start_new_session=True)
    guard_process=None;numerical=None;started=time.monotonic()
    try:
        with(root/'outer.stdout').open('x')as stdout,(root/'outer.stderr').open('x')as stderr:
            guard_process=subprocess.Popen([sys.executable,'-I','-B','-S','-c',code],stdout=stdout,stderr=stderr,start_new_session=True)
            deadline=time.monotonic()+20
            while not(marker.exists()and grandchild_marker.exists()):
                if guard_process.poll()is not None or time.monotonic()>deadline:raise RuntimeError('Interrupted-stage fixture did not initialize')
                time.sleep(.05)
            numerical=json.loads(marker.read_text());assert int(grandchild_marker.read_text())==numerical['grandchild']
            assert numerical['pid']==numerical['pgid'] and numerical['pgid']!=guard_process.pid
            # This is the same outer process-group signal used by the unchanged v3 runner.
            os.killpg(guard_process.pid,signal.SIGTERM)
            returncode=guard_process.wait(timeout=20)
        terminal=json.loads((runroot/'terminal.json').read_text())
        assert returncode==1 and terminal['reason']=='supervisor_interrupted'
        closure=terminal['owned_group_cleanup']
        assert closure['group_absent']and closure['direct_child_reaped']and closure['only_exact_owned_group_signaled']
        assert terminal['prepared_sources_unchanged']and sentinel.poll()is None
        actual=subprocess.run(['/bin/ps','-g',str(numerical['pgid']),'-o','pid=,pgid='],capture_output=True,text=True,timeout=5)
        assert actual.returncode==1 and not actual.stdout.strip() and not actual.stderr.strip()
        result=dict(status='actual_outer_sigterm_cleanup_control_passed',outer_stage_returncode=returncode,
                    separate_worker_session=True,term_resistant_worker_and_descendant=True,
                    unrelated_sentinel_untouched=True,exact_owned_group_absent=True,
                    terminal_sha256=common.sha(runroot/'terminal.json'),source_sha256=pins,
                    source_manifest_sha256=args.source_manifest_sha256,elapsed_seconds=time.monotonic()-started)
        common.write(Path(output)/'lifecycle-controls.json',result)
        return result
    finally:
        if guard_process is not None and guard_process.poll()is None:
            os.killpg(guard_process.pid,signal.SIGKILL);guard_process.wait(timeout=5)
        if numerical is not None:
            state=subprocess.run(['/bin/ps','-g',str(numerical['pgid']),'-o','pid=,pgid=,command='],capture_output=True,text=True,timeout=5)
            if state.stdout.strip():
                members=[row.split(None,2)for row in state.stdout.splitlines()]
                if not all(int(row[0])in(numerical['pid'],numerical['grandchild'])and int(row[1])==numerical['pgid']for row in members):
                    raise RuntimeError('Fixture fallback ownership differs; no unrelated group signaled')
                os.killpg(numerical['pgid'],signal.SIGKILL)
        if sentinel.poll()is None:sentinel.terminate()
        sentinel.wait(timeout=5)
