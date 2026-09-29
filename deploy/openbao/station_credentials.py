"""Scoped station callbacks for the existing OpenBao HF and GitHub wrappers.

No credential-store reader: authentication stays in the approved wrappers.
Image publication uses the GitHub Actions job token on a one-job Kali2 runner.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

MODEL = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
REVISION = "c1209bda15a6bbc4c68b585e93d40c0d85f50306"


def validate_network_receipt(receipt, manifest_sha, instance_id, now):
    if (not isinstance(receipt, dict) or receipt.get("manifest_sha256") != manifest_sha
        or receipt.get("instance_id") != instance_id
        or receipt.get("metering_active") is not True
        or type(receipt.get("updated_epoch")) is not int
        or not 0 <= now - receipt["updated_epoch"] <= 30):
        raise ValueError("fresh exact-instance network guard receipt required")


def validate_guard(manifest, manifest_path, pins, now):
    """Bind current guard PID, its exact command and launchd service before secrets."""
    try:
        ready = json.loads(Path(manifest["guard_ready_path"]).read_bytes())
        pid = ready.get("pid")
        if (ready.get("armed") is not True or type(pid) is not int or pid <= 0
            or ready.get("manifest_sha256") != pins["manifest_sha256"]
            or ready.get("wrapper_sha256") != pins["vast_wrapper_sha256"]
            or ready.get("label") != manifest["attempt_label"] or ready.get("image_ref") != manifest["image_ref"]
            or ready.get("deadline_epoch") != manifest["deadline_epoch"]
            or not manifest["created_epoch"] <= now < manifest["deadline_epoch"] - 1200
            or hashlib.sha256(Path(manifest["guard_path"]).read_bytes()).hexdigest() != manifest["guard_sha256"]):
            raise ValueError("station guard identity or deadline is invalid")
        os.kill(pid, 0)
        process = subprocess.run(["/bin/ps", "-ww", "-p", str(pid), "-o", "command="],
                                 capture_output=True, text=True, timeout=5)
        if process.returncode or shlex.split(process.stdout.strip())[-2:] != [manifest["guard_path"], str(manifest_path)]:
            raise ValueError("station guard PID is not executing the pinned manifest")
        service = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{manifest['guard_service_name']}"],
                                 capture_output=True, text=True, timeout=5)
        if service.returncode or not re.search(r"\bpid = " + str(pid) + r"\b", service.stdout):
            raise ValueError("station guard is not owned by its persistent LaunchAgent")
    except (OSError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        raise ValueError("station external destruction guard is unavailable") from None


def dispatch_hf(values, wrapper, pins):
    """Use only the existing HF wrapper's token callback, never a new reader."""
    error = wrapper["WrapperError"]
    if values == ["station-model-check"]:
        def inspect(token, version):
            hf = wrapper["_load_hf"]()
            api = hf.HfApi(token=token)
            api.auth_check(repo_id=MODEL, repo_type="model", write=False)
            info = api.repo_info(repo_id=MODEL, revision=REVISION, files_metadata=True, timeout=30)
            sizes = [s.size for s in info.siblings]
            if info.sha != REVISION or not sizes or any(type(n) is not int or n < 0 for n in sizes):
                raise error("pinned model size metadata is incomplete")
            return {"model": MODEL, "model_revision": REVISION, "model_download_bytes": sum(sizes),
                    "gated_read_access_verified": True, "secret_version": version}
        return wrapper["_with_token"](inspect)
    if not pins or values != ["start-station", pins["manifest_path"]]:
        raise error("start-station requires the exact pinned qualification manifest")
    manifest_path = Path(pins["manifest_path"])
    vast = Path(pins["vast_wrapper"])
    raw = manifest_path.read_bytes()
    if (hashlib.sha256(raw).hexdigest() != pins["manifest_sha256"]
        or hashlib.sha256(vast.read_bytes()).hexdigest() != pins["vast_wrapper_sha256"]):
        raise error("station manifest or lifecycle wrapper changed")
    manifest = json.loads(raw)

    def vast_call(*args):
        result = subprocess.run([str(vast), *args], check=True, capture_output=True, timeout=120)
        return json.loads(result.stdout)

    current = vast_call("station-show", str(manifest_path))
    identifier = current["id"]
    if current.get("status") != "running" or time.time() >= manifest["deadline_epoch"] - 1200:
        raise error("station is not running with enough guarded qualification time")
    network = manifest_path.with_name(manifest["job_id"] + ".network-ready.json")
    try:
        validate_network_receipt(json.loads(network.read_bytes()), pins["manifest_sha256"], identifier, time.time())
        validate_guard(manifest, manifest_path, pins, time.time())
    except ValueError as exc:
        raise error(str(exc)) from None
    endpoints = vast_call("ssh-endpoints", str(identifier))
    direct = endpoints.get("direct", {})
    if (endpoints.get("instance_id") != identifier
        or not re.fullmatch(r"[A-Za-z0-9.:-]{1,253}", str(direct.get("host")))
        or type(direct.get("port")) is not int or not 0 < direct["port"] < 65536):
        raise error("invalid station SSH endpoint")
    # The destination was authenticated by the metering guard. Store a workload
    # token only in root's runtime directory, never in the image or worker account.
    # /run is not assumed to be tmpfs; the rented container is destroyed afterward.
    code = "\n".join([
        "import os,pathlib,re,sys",
        "token=sys.stdin.read(8193)",
        "assert re.fullmatch(r'hf_[A-Za-z0-9]{8,}',token) and len(token)<=8192",
        "path=pathlib.Path('/run/station-secrets')",
        "path.mkdir(mode=0o700,exist_ok=True)",
        "assert not path.is_symlink() and path.stat().st_uid==0 and path.stat().st_mode & 0o777==0o700",
        "fd=os.open(path/'hf_token',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)",
        "with os.fdopen(fd,'w') as stream: stream.write(token)",
    ])
    command = "python3 -c " + shlex.quote(code) + " && station-onstart && supervisorctl -c /opt/station/supervisord.conf start qwen"

    def start(token, version):
        try:
            validate_network_receipt(json.loads(network.read_bytes()), pins["manifest_sha256"], identifier, time.time())
            validate_guard(manifest, manifest_path, pins, time.time())
        except ValueError as exc:
            raise error(str(exc)) from None
        result = subprocess.run([
            "ssh", "-i", str(wrapper["VAST_SSH_KEY"]), "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10",
            "-o", "UserKnownHostsFile=" + str(manifest_path.with_suffix(".known-hosts")),
            "-p", str(direct["port"]), "root@" + direct["host"], command,
        ], input=token, text=True, capture_output=True, timeout=90)
        if result.returncode:
            raise error("station model startup failed; inspect non-secret service logs")
        return {"started": True, "instance_id": identifier, "model": MODEL, "revision": REVISION,
                "secret_version": version}
    return wrapper["_with_token"](start)


def render_hf_hook(source, module_path, pins=None):
    marker = "        args = parser.parse_args(values)\n"
    if source.count(marker) != 1 or "station-model-check" in source:
        raise ValueError("HF wrapper entry point changed or already extended")
    module_path = module_path.resolve(strict=True)
    digest = hashlib.sha256(module_path.read_bytes()).hexdigest()
    hook = f'''        if values and values[0] in {{"station-model-check", "start-station"}}:
            import hashlib
            module_path = Path({str(module_path)!r})
            data = module_path.read_bytes()
            if hashlib.sha256(data).hexdigest() != {digest!r}:
                raise WrapperError("station HF hook fingerprint changed")
            namespace = {{"__file__": str(module_path), "__name__": "station_credentials"}}
            exec(compile(data, str(module_path), "exec"), namespace)
            emit(namespace["dispatch_hf"](values, globals(), {pins!r}))
            return 0
'''
    result = source.replace(marker, hook + marker)
    compile(result, "station-hf-wrapper", "exec")
    return result


REPOSITORY = "cluster2600/porscheparts"
RUNNER_NAME = "picogk-station-publisher-20260928-r8kj70sz"
RUNNER_LABEL = "picogk-station-publish-20260928-r8kj70sz"
RUNNER_DIR = "/home/lolman/picogk-station-publisher-r8kj70sz"


def github_dispatch(operation, token, wrapper, remote):
    error, request = wrapper["SafeError"], wrapper["github_request"]
    if operation not in (["station-publisher-check"], ["station-publisher-start"], ["station-publisher-status"], ["station-publisher-cleanup"]):
        raise error("invalid fixed station publisher operation")
    _, repository = request(token, f"/repos/{REPOSITORY}")
    if repository.get("full_name") != REPOSITORY or repository.get("permissions", {}).get("admin") is not True:
        raise error("station ephemeral publisher requires repository administration access")
    if operation == ["station-publisher-check"]:
        print(json.dumps({"repository": REPOSITORY, "runner_admin": True, "registry_auth": "GitHub Actions job token"}))
        return 0
    _, runners = request(token, f"/repos/{REPOSITORY}/actions/runners?per_page=100")
    if runners.get("total_count", 101) > 100:
        raise error("runner inventory exceeds the fixed inspection limit")
    matches = [item for item in runners["runners"] if item.get("name") == RUNNER_NAME]
    if operation == ["station-publisher-cleanup"]:
        if len(matches) > 1 or any(item.get("busy") is not False or item.get("status") != "offline"
            or RUNNER_LABEL not in [label.get("name") for label in item.get("labels", [])] for item in matches):
            raise error("cleanup requires the exact unique idle offline station runner")
        for item in matches:
            status, _ = request(token, f"/repos/{REPOSITORY}/actions/runners/{int(item['id'])}", method="DELETE")
            if status != 204:
                raise error("station runner removal was not acknowledged")
        print(json.dumps({"removed_runner_ids": [item["id"] for item in matches]}))
        return 0
    if operation == ["station-publisher-status"]:
        _, runs = request(token, f"/repos/{REPOSITORY}/actions/runs?branch=codex%2Fpicogk-vast-station&per_page=20")
        print(json.dumps({"runners": [{k: item.get(k) for k in ("id", "name", "status", "busy", "ephemeral")} for item in matches],
                          "runs": [{k: run.get(k) for k in ("id", "name", "status", "conclusion", "html_url", "head_sha")}
                                   for run in runs["workflow_runs"] if run.get("path") == ".github/workflows/picogk-station-publish.yml"]}))
        return 0
    if matches:
        raise error("the exact station runner already exists; inspect it before retrying")
    if set(remote) != {"host", "user", "jump", "identity"} or not all(isinstance(v, str) and v for v in remote.values()):
        raise error("invalid pinned station build host")
    status, result = request(token, f"/repos/{REPOSITORY}/actions/runners/generate-jitconfig", method="POST",
                             payload={"name": RUNNER_NAME, "runner_group_id": 1, "labels": [RUNNER_LABEL], "work_folder": "_work"})
    runner = result.get("runner", {})
    encoded = result.get("encoded_jit_config", "")
    if (status != 201 or runner.get("name") != RUNNER_NAME or runner.get("ephemeral", True) is not True
        or type(runner.get("id")) is not int or not isinstance(encoded, str)
        or not re.fullmatch(r"[A-Za-z0-9+/=]{20,1048576}", encoded)):
        raise error("GitHub did not return the fixed ephemeral station runner")
    # Native runner auth stays inside the official application. Never emit its
    # JIT configuration, application credential files, or authentication logs.
    code = "\n".join([
        "import json,os,pathlib,re,subprocess,sys,time",
        "os.umask(0o077)",
        "encoded=sys.stdin.read(1048577)",
        "assert re.fullmatch(r'[A-Za-z0-9+/=]{20,1048576}',encoded)",
        f"directory=pathlib.Path({RUNNER_DIR!r})",
        "assert directory.is_dir() and not directory.is_symlink() and directory.stat().st_mode&0o777==0o700",
        "assert (directory/'run.sh').is_file() and not (directory/'.runner').exists()",
        "temporary=directory/'tmp'; temporary.mkdir(mode=0o700,exist_ok=True)",
        "assert not temporary.is_symlink() and temporary.stat().st_mode&0o777==0o700",
        "environment=dict(os.environ,ACTIONS_RUNNER_INPUT_JITCONFIG=encoded,TMPDIR=str(temporary))",
        "with (directory/'station-runner.log').open('xb') as log:",
        "    child=subprocess.Popen(['timeout','--signal=TERM','--kill-after=30','5400','./run.sh'],cwd=directory,env=environment,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)",
        "time.sleep(2)",
        "assert child.poll() is None, 'native runner exited during initialization'",
        "print(json.dumps({'started':True,'pid':child.pid}))",
    ])
    try:
        started = subprocess.run(["ssh", "-J", remote["jump"], "-i", remote["identity"],
            "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=10", f'{remote["user"]}@{remote["host"]}',
            "python3 -c " + shlex.quote(code)], input=encoded, text=True, capture_output=True, timeout=30)
        result = json.loads(started.stdout) if started.returncode == 0 else {}
        if result.get("started") is not True or type(result.get("pid")) is not int:
            raise error("station native publisher startup failed; authentication logs withheld")
    except (OSError, ValueError, subprocess.SubprocessError):
        raise error("station native publisher startup failed; authentication logs withheld") from None
    print(json.dumps({"started": True, "runner_id": runner["id"], "name": RUNNER_NAME, "label": RUNNER_LABEL,
                      "pid": result["pid"], "maximum_jobs": 1, "maximum_lifetime_seconds": 5400}))
    return 0


def render_github_hook(source, module_path, remote_config):
    marker = '            if operation == ["--auth-check"]:\n'
    if source.count(marker) != 1 or "station-publisher-start" in source:
        raise ValueError("GitHub wrapper entry point changed or already extended")
    module_path, remote_config = module_path.resolve(strict=True), remote_config.resolve(strict=True)
    hook = '\n'.join([
        '            if operation and operation[0] in {"station-publisher-check", "station-publisher-start", "station-publisher-status", "station-publisher-cleanup"}:',
        '                import hashlib',
        f'                module_path = Path({str(module_path)!r})',
        f'                config_path = Path({str(remote_config)!r})',
        '                code, config = module_path.read_bytes(), config_path.read_bytes()',
        f'                if hashlib.sha256(code).hexdigest() != {hashlib.sha256(module_path.read_bytes()).hexdigest()!r} or hashlib.sha256(config).hexdigest() != {hashlib.sha256(remote_config.read_bytes()).hexdigest()!r}:',
        '                    raise SafeError("station publisher code or fixed build host changed")',
        '                namespace = {}',
        '                exec(compile(code, str(module_path), "exec"), namespace)',
        '                return namespace["github_dispatch"](operation, token, globals(), json.loads(config))',
        '',
    ])
    result = source.replace(marker, hook + marker)
    compile(result, 'station-github-wrapper', 'exec')
    return result
