#!/usr/bin/env python3
"""Run the existing worker with explicit process-group memory and time bounds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as s:
        for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def group_rss(text,pgid):
    return sum(int(row[1]) for line in text.splitlines() if len(row:=line.split())==2 and int(row[0])==pgid)


def run(prepared,output,max_gib,seconds):
    prepared,output=Path(prepared).resolve(),Path(output).resolve()
    if not 1<=max_gib<=48 or not 30<=seconds<=3600 or output.exists():raise ValueError('Bounded fresh solver execution required')
    proof=json.loads((prepared/'receipt.json').read_text())
    if (proof['schema']!='935-conforming-fea-preparation-v1' or proof['numeric_geometry_admitted_for_solver'] is not True
            or proof['manufacturing_authorized'] is not False or sha(prepared/'rotor.inp')!=proof['deck_sha256']):
        raise ValueError('Audited prepared solver geometry required')
    worker=Path(__file__).with_name('run_candidate_fea.sh');exe=shutil.which('ccx')
    if exe is None:raise ValueError('Qualified ccx must be on PATH')
    journal=output.with_name(output.name+'.execution.json')
    if journal.exists() or not output.parent.is_dir():raise ValueError('Fresh execution journal required')
    for parent in output.parents:
        if (parent/'.git').exists() and output.relative_to(parent).parts[0]!='work':raise ValueError('Private work/ output required')
    started=time.monotonic();stop=None;peak=0
    record=dict(schema='935-bounded-native-solve-v1',pid=None,process_group=None,
                binary_sha256=sha(exe),worker_sha256=sha(worker),source_sha256=sha(__file__),
                platform=platform.system(),architecture=platform.machine(),max_rss_GiB=max_gib,timeout_s=seconds,
                deck_sha256=proof['deck_sha256'],solver_finished=False,physical_validation=False,manufacturing_authorized=False)
    with journal.open('x') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    process=subprocess.Popen(['bash',str(worker),str(prepared/'rotor.inp'),proof['deck_sha256'],str(output)],start_new_session=True)
    try:
        record.update(pid=process.pid,process_group=process.pid);journal.write_text(json.dumps(record,indent=2)+'\n')
        while process.poll() is None:
            try:rss=group_rss(subprocess.check_output(['ps','-axo','pgid=,rss='],text=True),process.pid)
            except (subprocess.SubprocessError,ValueError):stop='monitoring_failed';rss=0
            peak=max(peak,rss)
            if rss>max_gib*1024**2:stop='memory_limit'
            if time.monotonic()-started>seconds:stop='wall_time_limit'
            if stop:break
            time.sleep(2)
    finally:
        if process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
    rc=process.wait()
    record.update(exit=rc,stop_reason=stop,peak_group_rss_KiB=peak,elapsed_s=time.monotonic()-started,
                  solver_finished=rc==0 and stop is None)
    journal.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
    return record['solver_finished']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prepared',type=Path);p.add_argument('new_output',type=Path)
    p.add_argument('--max-rss-gib',type=int,required=True);p.add_argument('--seconds',type=int,required=True)
    a=p.parse_args();raise SystemExit(0 if run(a.prepared,a.new_output,a.max_rss_gib,a.seconds) else 2)
