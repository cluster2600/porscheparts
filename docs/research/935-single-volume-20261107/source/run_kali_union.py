"""Run one admitted offline union; recover evidence before removing owned staging."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile
import time

IMAGE = 'sha256:3fc08a038193fd6f7a611111e88909baad09354fe2d0ce09a77c45da991f9a1d'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('head', 'supports', 'preparation-report', 'controls-report', 'worker', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--ssh-destination', required=True)
    parser.add_argument('--host-key-alias', required=True)
    args = parser.parse_args()
    preparation = json.loads(args.preparation_report.read_text())
    assert preparation['every_resource_coordinate_and_index_verified']
    assert preparation['assembly_and_units_verified']
    assert sha(args.head) == preparation['head_sha256']
    assert sha(args.supports) == preparation['supports_sha256']
    controls = json.loads(args.controls_report.read_text())
    assert len(controls) == 5 and all(value is True for value in controls.values())
    control_plan = json.loads((args.controls_report.parent/'plan.json').read_text())
    assert control_plan['source_sha256'] == sha(args.worker)
    args.output.mkdir(mode=0o700, exist_ok=False)
    began = time.monotonic()
    ssh = ['ssh', '-6', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'ForwardAgent=no', '-o', 'UseKeychain=no', '-o', 'ConnectTimeout=8',
           '-o', 'HostKeyAlias='+args.host_key_alias, args.ssh_destination]

    def remote(name, command, payload=None, seconds=60, allow_failure=False):
        result = subprocess.run([*ssh, command], input=payload, capture_output=True, timeout=seconds)
        (args.output/(name+'.stdout')).write_bytes(result.stdout)
        (args.output/(name+'.stderr')).write_bytes(result.stderr)
        (args.output/(name+'-execution.json')).write_text(json.dumps({'exit_code': result.returncode})+'\n')
        assert allow_failure or result.returncode == 0, 'Remote step failed: '+name
        return result.stdout

    capacity_code = "import json,pathlib,shutil; m={k:int(v.split()[0])*1024 for k,v in (x.split(':',1) for x in pathlib.Path('/proc/meminfo').read_text().splitlines())}; print(json.dumps({'memory_available':m['MemAvailable'],'disk_free':shutil.disk_usage(pathlib.Path.home()).free}))"
    capacity = json.loads(remote('capacity', 'python3 -c '+shlex.quote(capacity_code)))
    assert capacity['memory_available'] >= 10*1024**3 and capacity['disk_free'] >= 6*1024**3
    assert remote('image', "docker image inspect --format '{{.Id}}' "+IMAGE).decode().strip() == IMAGE
    work = remote('create', 'umask 077; mktemp -d "$HOME/935-single-volume.XXXXXXXX"').decode().strip()
    assert re.fullmatch(r'/home/[^/]+/935-single-volume\.[A-Za-z0-9]{8}', work)
    paths = {'head.npz': args.head, 'supports.npz': args.supports, 'union.py': args.worker}
    inputs = [{'path': '/work/'+name, 'sha256': sha(path)} for name, path in paths.items()]
    job = {'head': '/work/head.npz', 'supports': '/work/supports.npz', 'inputs': inputs}
    (args.output/'plan.json').write_text(json.dumps(dict(image_id=IMAGE, capacity=capacity,
        private_work_directory=work, job=job, source_sha256=sha(__file__),
        preparation_report_sha256=sha(args.preparation_report), controls_report_sha256=sha(args.controls_report),
        cpus=4, memory_gib=8, additional_swap_gib=0, timeout_seconds=600,
        network='none', disk_floor_before_upload_gib=6, new_paid_compute_usd=0), indent=2)+'\n')
    for name, path in paths.items():
        with path.open('rb') as stream:
            result = subprocess.run([*ssh, 'cat > '+shlex.quote(work+'/'+name)], stdin=stream,
                                    capture_output=True, timeout=180)
        assert result.returncode == 0, 'Input upload failed'
        assert remote('hash-'+name, 'sha256sum '+shlex.quote(work+'/'+name)).decode().split()[0] == sha(path)
    remote('job', 'cat > '+shlex.quote(work+'/job.json'), json.dumps(job).encode())
    command = """set -eu
cid=$(docker create --pull=never --network none --read-only --cpus 4 --memory 8g --memory-swap 8g --pids-limit 256 --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,nosuid,size=128m --mount MOUNT --entrypoint python IMAGE -B /work/union.py --job /work/job.json --output /work/result)
printf '%s\n' "$cid" > WORK/container.id
trap 'docker rm -f "$cid" >/dev/null' EXIT HUP INT TERM
set +e
timeout --kill-after=15s 600s docker start -a "$cid"
status=$?
set -e
docker inspect --format '{{json .State}}' "$cid" > WORK/container-state.json
printf '{"exit_code":%s}\n' "$status" > WORK/execution.json
""".replace('MOUNT', shlex.quote('type=bind,src='+work+',dst=/work')).replace('IMAGE', IMAGE).replace('WORK', shlex.quote(work))
    try:
        remote('union', 'bash -c '+shlex.quote(command), seconds=640, allow_failure=True)
    finally:
        cid = remote('container-id', 'cat '+shlex.quote(work+'/container.id')).decode().strip()
        assert re.fullmatch('[0-9a-f]{64}', cid)
        remote('owned-container-cleanup', 'if docker container inspect '+cid+' >/dev/null 2>&1; then docker rm -f '+cid+'; fi')
        assert not remote('container-closeout', "docker ps -a --filter id="+cid+" --format '{{.ID}}'").strip()
    manifest_code = "import hashlib,json,pathlib; r=pathlib.Path("+repr(work)+"); print(json.dumps({p.name:{'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in r.rglob('*') if p.is_file()}))"
    # Paths are relative: nested result files must not collide with input filenames.
    manifest_code = manifest_code.replace('p.name:', 'str(p.relative_to(r)):')
    manifest = json.loads(remote('manifest', 'python3 -c '+shlex.quote(manifest_code), seconds=120))
    archive_path = args.output/'recovered.tar'
    with archive_path.open('xb') as stream:
        result = subprocess.run([*ssh, 'tar -cf - -C '+shlex.quote(work)+' .'], stdout=stream,
                                stderr=subprocess.PIPE, timeout=180)
    assert result.returncode == 0
    recovered = args.output/'recovered'
    recovered.mkdir()
    with tarfile.open(archive_path) as archive:
        archive.extractall(recovered, filter='data')
    for name, item in manifest.items():
        path = recovered/name
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    for name, path in paths.items():
        assert sha(recovered/name) == sha(path)
    remote('staging-cleanup', 'rm -rf -- '+shlex.quote(work))
    remote('staging-closeout', 'test ! -e '+shlex.quote(work))
    state = json.loads((recovered/'container-state.json').read_text())
    report = dict(source_sha256=sha(__file__), recovered_files_verified=len(manifest),
                  archive_sha256=sha(archive_path), container_state=state,
                  native_report_exists=(recovered/'result/report.json').exists(),
                  owned_container_absent=True, owned_staging_removed_after_verified_recovery=True,
                  new_paid_compute_usd=0, seconds=time.monotonic()-began,
                  manufacturing_qualified=False, engine_qualified=False)
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
