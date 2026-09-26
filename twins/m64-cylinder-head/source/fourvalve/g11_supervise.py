#!/usr/bin/env python3
"""Collect an already-started G11 job; no rental, producer stop or destruction.

Run under launchd/caffeinate, not a Codex-owned terminal. The Mac must stay awake
and online. Upload unchanged g11_collect.py at its canonical source path first.
The detached remote launcher must publish producer-exit.json after its job exits:
The marker binds process_group, instance_id, job_id, manifest_sha256,
producer_deadline and exit_code. Only clean exit 0 permits packing: workers use
separate process groups, so launcher-group absence alone is not sufficient.
"""
import argparse
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shlex
import subprocess
import time

import g11_collect as collect

REPO = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location('g11_guard', REPO/'deploy/vast/picogk/deadline_guard.py')
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
ARCHIVE = '/workspace/m64-g11/supervised-collection.tar.xz'
META_LIMIT, RESPONSE_LIMIT = 2_000_000, 65536  # Remaining 8 MB are reserved for SSH transport overhead.
SAFE_JSON = re.compile(r'results/(?:identity\.json|checkpoint-\d{4}\.json|summary-\d{4}\.json|(?:centre_w(?:10|11|12)|outer_d(?:18|24|30)_w(?:18|24|30))-(?:2|1\.5|1)-attempt\d+/result\.json)')

REMOTE = r'''
import base64,hashlib,importlib.util,json,os,pathlib,sys
root=pathlib.Path('/workspace/m64-g11')
context=json.loads(base64.b64decode(sys.argv[3]))
source=root/'twins/m64-cylinder-head/source/fourvalve/g11_collect.py'
if hashlib.sha256(source.read_bytes()).hexdigest()!=sys.argv[2]:raise ValueError('collector fingerprint mismatch')
spec=importlib.util.spec_from_file_location('collect',source);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
def read(path):
 with c.regular(path,root) as f:
  before=os.fstat(f.fileno());data=f.read(1_000_001);after=os.fstat(f.fileno())
  if len(data)>1_000_000 or not data.endswith(b'\n') or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('unstable metadata')
  return data
terminal=None
if (root/'producer-exit.json').exists():
 marker=json.loads(read(root/'producer-exit.json'))
 if set(marker)!=set(context['expected_terminal'])|{'exit_code'} or any(marker.get(k)!=v for k,v in context['expected_terminal'].items()) or type(marker.get('exit_code')) is not int or not 0<=marker['exit_code']<=255:raise ValueError('invalid producer marker')
 try:os.killpg(marker['process_group'],0)
 except ProcessLookupError:terminal=marker
if sys.argv[1]=='snapshot':
 files=[];more=False;known=context['known']
 paths=[root/'results/identity.json']+sorted((root/'results').glob('checkpoint-*.json'))+sorted((root/'results').glob('summary-*.json'))+sorted((root/'results').glob('*/result.json'))
 for path in paths:
  if not path.exists():continue
  try:data=read(path);json.loads(data)
  except ValueError:continue
  name=str(path.relative_to(root));sha=hashlib.sha256(data).hexdigest()
  if known.get(name)==sha:continue
  item={'path':name,'sha256':sha,'data':base64.b64encode(data).decode()}
  if len(json.dumps(item))>60000:raise ValueError('single metadata file too large')
  if len(json.dumps(files+[item]))>60000:more=True;break
  files.append(item)
 payload=json.dumps({'terminal':terminal,'files':files,'more':more})
 print(payload)
elif sys.argv[1]=='pack':
 if terminal is None or terminal['exit_code']!=0:raise ValueError('clean producer completion required')
 receipt=root/'supervised-collection.json'
 if receipt.exists():result=json.loads(read(receipt))
 else:
  result=c.pack(root,root/'supervised-collection.tar.xz',xz_preset=1)
  result['producer']=terminal
  with receipt.open('x') as f:json.dump(result,f);f.write('\n')
 if result.get('producer')!=terminal:raise ValueError('archive belongs to another producer')
 print(json.dumps(result))
else:raise ValueError('unsupported operation')
'''


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def ssh(config, command, timeout, limit, sink=None):
    """Bound bytes and lifetime locally even if the remote violates its contract."""
    process = subprocess.Popen(['ssh', '-F', str(config), 'g11', command], stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    end, count, chunks = time.monotonic()+timeout, 0, []
    try:
        while True:
            seconds = end-time.monotonic()
            if seconds <= 0:
                raise TimeoutError('SSH deadline reached')
            if not select.select([process.stdout], [], [], min(seconds, 1))[0]:
                continue
            data = os.read(process.stdout.fileno(), min(65536, limit-count+1))
            if not data:
                break
            count += len(data)
            if count > limit:
                raise ValueError('SSH output exceeds byte cap')
            sink.write(data) if sink else chunks.append(data)
        if process.wait(timeout=max(.001, end-time.monotonic())):
            raise ValueError('SSH operation failed')
        return b''.join(chunks)
    finally:
        if process.poll() is None:
            process.kill(); process.wait()
        process.stdout.close()


def save(path, data):
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('symlink destination forbidden')
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('immutable local snapshot changed')
        return
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def validate_config(path, instance_id):
    data = guard.read_owned(path, 16384)
    values = {}
    for line in data.decode().splitlines():
        tokens = shlex.split(line, comments=True)
        if not tokens:
            continue
        if len(tokens) != 2 or tokens[0].lower() in values:
            raise ValueError('one literal SSH host stanza required')
        values[tokens[0].lower()] = tokens[1]
    allowed = {'host', 'hostname', 'port', 'user', 'identityfile', 'identitiesonly', 'batchmode', 'connecttimeout',
               'forwardagent', 'loglevel', 'stricthostkeychecking', 'hostkeyalias', 'userknownhostsfile'}
    required = {'host': 'g11', 'user': 'root', 'identitiesonly': 'yes', 'batchmode': 'yes', 'forwardagent': 'no',
                'stricthostkeychecking': 'yes', 'hostkeyalias': f'f41-{instance_id}'}
    if (not values.keys() <= allowed or any(values.get(k) != v for k,v in required.items())
            or not re.fullmatch(r'[A-Za-z0-9.-]+', values.get('hostname', ''))
            or not values.get('port', '').isdigit() or not 1 <= int(values['port']) <= 65535
            or any(not Path(values.get(k, '')).is_absolute() for k in ('identityfile', 'userknownhostsfile'))):
        raise ValueError('unsafe or wrong-instance SSH configuration')
    return data


def _run(args):
    manifest_bytes = guard.read_owned(args.manifest, 65536)
    manifest = json.loads(manifest_bytes); guard.validate_manifest(manifest)
    if manifest['max_output_gb'] != 2:
        raise ValueError('this fixed collection allocation requires exactly 2 GB output budget')
    config_bytes = validate_config(args.ssh_config, args.instance_id)
    if (not time.time() < args.collect_deadline <= manifest['deadline_epoch']-300 or args.reserve_seconds < 60
            or args.producer_deadline > args.collect_deadline-args.reserve_seconds):
        raise ValueError('collection deadline/reserve invalid')
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.output.is_symlink() or args.log.parent.resolve() != args.output.resolve() or args.log.is_symlink():
        raise ValueError('log must be a regular file inside private output')
    identity = {'instance_id': args.instance_id, 'manifest_sha256': fingerprint(manifest_bytes),
                'ssh_config_sha256': fingerprint(config_bytes), 'supervisor_sha256': fingerprint(Path(__file__).read_bytes()),
                'collector_sha256': fingerprint(Path(collect.__file__).read_bytes()),
                'producer_group': args.producer_group, 'producer_deadline': args.producer_deadline,
                'collect_deadline': args.collect_deadline}
    save(args.output/'identity.json', (json.dumps(identity, sort_keys=True)+'\n').encode())
    charged = archive_charged = 0
    for line in guard.read_owned(args.log, 2_000_000).decode().splitlines() if args.log.exists() else []:
        row = json.loads(line); delta, archive_delta = row.get('metadata_charge_delta', 0), row.get('archive_charge_delta', 0)
        if type(delta) is not int or not -RESPONSE_LIMIT <= delta <= RESPONSE_LIMIT or type(archive_delta) is not int or not 0 <= archive_delta <= collect.LIMIT:
            raise ValueError('invalid durable transfer ledger')
        charged += delta; archive_charged += archive_delta
        if not 0 <= charged <= META_LIMIT or not 0 <= archive_charged <= collect.LIMIT:
            raise ValueError('durable transfer allocation exceeded')
    terminal_identity = {'process_group': args.producer_group, 'instance_id': args.instance_id,
                         'job_id': manifest['job_id'], 'manifest_sha256': identity['manifest_sha256'],
                         'producer_deadline': args.producer_deadline}
    known = {}
    for path in (args.output/'snapshots').rglob('*.json'):
        name = str(path.relative_to(args.output/'snapshots'))
        if not SAFE_JSON.fullmatch(name):
            raise ValueError('unexpected saved snapshot path')
        known[name] = fingerprint(guard.read_owned(path, 1_000_000))

    def log(event, **fields):
        fd = os.open(args.log, os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as stream:
            stream.write(json.dumps({'epoch': time.time(), 'event': event, **fields})+'\n'); stream.flush(); os.fsync(stream.fileno())

    def remaining():
        seconds = args.collect_deadline-time.time()
        if seconds <= 0:
            raise TimeoutError('collection deadline reached')
        return seconds

    def owned():
        if guard.read_owned(args.manifest, 65536) != manifest_bytes or validate_config(args.ssh_config, args.instance_id) != config_bytes:
            raise ValueError('pinned control inputs changed')
        if guard.exact_match([guard.wrapper_call('show', str(args.instance_id))], manifest, args.instance_id) is None:
            raise ValueError('owned instance not present')

    def remote(mode, timeout):
        nonlocal charged
        owned()
        if charged+RESPONSE_LIMIT > META_LIMIT:
            raise ValueError('cumulative metadata transfer allocation exhausted')
        log('metadata_reserved', metadata_charge_delta=RESPONSE_LIMIT); charged += RESPONSE_LIMIT
        context = {'known': known, 'expected_terminal': terminal_identity}
        command = 'python3 -c '+shlex.quote(REMOTE)+' '+mode+' '+fingerprint(Path(collect.__file__).read_bytes())+' '+base64.b64encode(json.dumps(context).encode()).decode()
        reply = ssh(args.ssh_config, command, min(timeout, remaining()), RESPONSE_LIMIT)
        refund = len(reply)-RESPONSE_LIMIT
        log('metadata_received', metadata_charge_delta=refund); charged += refund
        return json.loads(reply)

    try:
        while True:
            snapshot = remote('snapshot', 60)
            for item in snapshot['files']:
                if not SAFE_JSON.fullmatch(item['path']):
                    raise ValueError('snapshot path not allowed')
                data = base64.b64decode(item['data'], validate=True)
                if len(data)>1_000_000 or fingerprint(data) != item['sha256']:
                    raise ValueError('snapshot fingerprint mismatch')
                json.loads(data); save(args.output/'snapshots'/item['path'], data)
                known[item['path']] = item['sha256']
            log('snapshots_saved', files=len(snapshot['files']), terminal=snapshot['terminal'])
            if snapshot['more']:
                continue
            if snapshot['terminal'] is not None:
                if snapshot['terminal'] != dict(terminal_identity, exit_code=0):
                    raise ValueError('unclean producer exit: snapshots retained, no automatic packing')
                break
            if remaining() <= args.reserve_seconds:
                raise TimeoutError('producer not finished before collection reserve')
            time.sleep(min(60, remaining()-args.reserve_seconds))
        if remaining() < args.reserve_seconds:
            raise TimeoutError('insufficient collection reserve')
        receipt = remote('pack', remaining()/2)
        if receipt.get('producer') != dict(terminal_identity, exit_code=0) or type(receipt['archive_bytes']) is not int or not 0 < receipt['archive_bytes'] <= collect.LIMIT or not re.fullmatch('[0-9a-f]{64}', receipt['archive_sha256']):
            raise ValueError('invalid archive receipt')
        save(args.output/'archive-receipt.json', (json.dumps(receipt, sort_keys=True)+'\n').encode())
        archive = args.output/'collection.tar.xz'
        if not archive.exists():
            if (args.output/'collection.partial').exists() or archive_charged+receipt['archive_bytes']+1 > collect.LIMIT:
                raise ValueError('prior uncertain transfer or cumulative archive allowance exhausted')
            owned()
            log('archive_reserved', archive_charge_delta=receipt['archive_bytes']+1)
            with (args.output/'collection.partial').open('xb') as stream:
                os.chmod(stream.name, 0o600)
                ssh(args.ssh_config, f'head -c {receipt["archive_bytes"]+1} '+ARCHIVE,
                    remaining()/2, receipt['archive_bytes'], stream)
                stream.flush(); os.fsync(stream.fileno())
            if (args.output/'collection.partial').stat().st_size != receipt['archive_bytes']:
                raise ValueError('download size mismatch')
            collect.verify(args.output/'collection.partial', receipt['archive_sha256'])
            remaining()
            os.rename(args.output/'collection.partial', archive)
        remaining()
        verified = collect.verify(archive, receipt['archive_sha256'])
        remaining()
        save(args.output/'verified.json', (json.dumps({**identity, **verified, 'archive_sha256': receipt['archive_sha256'],
             'producer_exit_code': snapshot['terminal']['exit_code'], 'collection_verified': True}, sort_keys=True)+'\n').encode())
        log('collection_verified'); return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, guard.GuardError) as error:
        log('collection_failed', error_type=type(error).__name__, collection_verified=False)
        return 1


def run(args):
    if args.instance_id <= 0 or args.producer_group <= 1 or not args.output.is_absolute() or any(p.is_symlink() for p in (args.output, *args.output.parents)):
        raise ValueError('positive identities and literal output path required')
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(args.output/'controller.lock', os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW, 0o600), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _run(args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'ssh-config', 'output', 'log'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--instance-id', type=int, required=True)
    parser.add_argument('--producer-pgid', dest='producer_group', type=int, required=True)
    parser.add_argument('--producer-deadline', type=int, required=True)
    parser.add_argument('--collect-deadline', type=int, required=True)
    parser.add_argument('--reserve-seconds', type=int, default=1800)
    raise SystemExit(run(parser.parse_args()))
