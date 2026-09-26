# G11 durable collection supervisor

Prepared and tested locally; **not installed, started, or demonstrated on a live
Vast job**. No rental or destruction operation exists in this supervisor.
The numerical sources, GPU job and collector remain unchanged.

## Preconditions

- Use only a newly verified owned instance and the approved PicoGK manifest.
  Its independent billing guard must already be armed through an autonomous
  local service, before rental. Do not weaken its empty-inventory requirement.
- Keep the Mac awake and online. `launchd` survives a Codex interruption;
  `caffeinate` does not guarantee connectivity, power or survival of shutdown.
- Upload the unchanged collector to
  `/workspace/m64-g11/twins/m64-cylinder-head/source/fourvalve/g11_collect.py`.
  The supervisor uses system `python3`, so it can start before the GPU venv exists.
- Use an ownership-checked SSH configuration containing one literal `Host g11`,
  strict known-host checking, `HostKeyAlias f41-INSTANCE_ID`, no forwarding,
  and the existing approved identity file. No credentials enter arguments.
- Require `max_output_gb: 2`. Archive payload is capped below 1.99 GB,
  cumulative metadata payload at 2 MB, with the remaining 8 MB reserved for
  SSH overhead. These are conservative transfer allocations, not measured
  provider billing. Unchanged JSON payloads are not downloaded again.
- Choose `producer_deadline <= collect_deadline - reserve_seconds` and
  `collect_deadline <= manifest.deadline_epoch - 300`. The default collection
  reserve is 1,800 seconds; raise it for slow transfer/compression. No deadline
  or billing guard is renewed automatically.

## Future remote launcher (do not run without the preconditions)

Substitute verified instance ID, uploaded manifest and absolute compute deadline.
Start once in a fresh `/workspace/m64-g11`; existing markers are not overwritten.
The standard `nohup` + `setsid` launcher records its process group before starting
the frozen job and writes a bound terminal marker afterward:

```sh
nohup setsid python3 -u -c '
import hashlib,json,os,pathlib,subprocess,sys
root=pathlib.Path("/workspace/m64-g11")
raw=pathlib.Path(sys.argv[1]).read_bytes(); manifest=json.loads(raw)
context=dict(process_group=os.getpgrp(),instance_id=int(sys.argv[2]),
             job_id=manifest["job_id"],manifest_sha256=hashlib.sha256(raw).hexdigest(),
             producer_deadline=int(sys.argv[3]))
def write(name,value):
 with (root/name).open("x") as f:
  json.dump(value,f);f.write("\n");f.flush();os.fsync(f.fileno())
write("producer-start.json",context)
with (root/"run.log").open("x") as log:
 code=subprocess.run(["bash",str(root/"g11_gpu_job.sh"),sys.argv[3]],
                     cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT).returncode
write("producer-exit.json",dict(context,exit_code=code if code>=0 else 128-code))
' /workspace/m64-g11/owned-manifest.json INSTANCE_ID COMPUTE_DEADLINE \
  </dev/null >/workspace/m64-g11/launcher.log 2>&1 &
```

Retrieve `producer-start.json` and check all fields against the owned manifest;
pass its exact process group to the local supervisor. A clean exit zero and
absence of that group are both required for packing. Nonzero exits, missing
markers, or identity mismatches retain snapshots but **do not** permit automatic
packing: the numerical workers use detached groups, so launcher-group absence
alone would not prove quiescence following SIGKILL/OOM.

## Future local service (commands prepared, not executed)

Use absolute paths and a new private output directory. Submit the guard under
its own unique launchd label before rental; verify its readiness receipt before
the approved rental action. The supervisor is a separate service and never
replaces that guard. After obtaining the producer start receipt:

```sh
launchctl submit -l com.cluster2600.m64-g11-supervisor-JOB \
  -o /ABS/PRIVATE/launchd.stdout -e /ABS/PRIVATE/launchd.stderr -- \
  /usr/bin/caffeinate -ims /ABS/PYTHON \
  /ABS/REPO/twins/m64-cylinder-head/source/fourvalve/g11_supervise.py \
  --manifest /ABS/PRIVATE/owned-manifest.json --ssh-config /ABS/PRIVATE/ssh.conf \
  --instance-id INSTANCE_ID --producer-pgid RECORDED_PGID \
  --producer-deadline COMPUTE_DEADLINE --collect-deadline COLLECTION_DEADLINE \
  --output /ABS/PRIVATE/supervisor --log /ABS/PRIVATE/supervisor/events.jsonl
```

Check `launchctl print gui/$(id -u)/com.cluster2600.m64-g11-supervisor-JOB`
and the persistent event log. Only `verified.json` proves completed archive
verification; the archive stays `collection.partial` until verification passes.
An exclusive process lock prevents duplicate controllers. Byte reservations are
fsynced before transfers and survive restart; uncertain archive transfers are
not automatically retried. Failed metadata requests retain their full reservation.
The independent guard remains responsible for cleanup even if collection fails;
only its receipt and verified provider absence establish the cleanup outcome.
An expired or network-disconnected supervisor does not stop arbitrary jobs.

## Local checks

```sh
python3 -m unittest discover -s tests -p test_m64_g11_supervise.py -v
```

Three tests cover cold collection and restart, immutable snapshots, identity and
deadline rejection, cumulative transfer caps, corrupt archives, clean-exit rules,
bounded SSH transport, and a real detached local producer with the terminal
marker parser. All network/provider operations in these tests are mocked.
