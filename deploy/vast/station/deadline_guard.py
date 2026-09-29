#!/usr/bin/env python3
"""Persistent Mac guard: exact ownership, wall/monotonic deadline and SSH byte caps.

No secret access. Reuses the unchanged PicoGK ownership/deletion engine and only
calls the approved wrapper plus a fixed read-only SSH network-counter command.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time

ENGINE_HASH = "c1d82cfaf5c8f178b5eaeb32ca5d98774b3dd60502087310f10a2966e53ff3f4"
WRAPPER = Path.home() / ".local/bin/openbao-vastai"
ENGINE_PATH = Path(__file__).resolve().parents[1] / "picogk/deadline_guard.py"
data = ENGINE_PATH.read_bytes()
if hashlib.sha256(data).hexdigest() != ENGINE_HASH:
    raise RuntimeError("PicoGK ownership engine fingerprint changed")
engine = importlib.util.module_from_spec(importlib.util.spec_from_loader("station_guard_engine", loader=None))
exec(compile(data, str(ENGINE_PATH), "exec"), engine.__dict__)
engine.WRAPPER = WRAPPER
interrupted = False


def call(*args):
    if args[0] not in {"instances", "show", "destroy-station", "ssh-endpoints"}:
        raise engine.GuardError("station guard operation is not allowed")
    result = subprocess.run([str(WRAPPER), *args], stdin=subprocess.DEVNULL, capture_output=True, timeout=180)
    if result.returncode or len(result.stdout) > 2 * 1024**2:
        raise engine.GuardError("station wrapper request failed")
    return json.loads(result.stdout)


engine.wrapper_call = call


def write(path, value):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def destroy_exact(instance_id, manifest, path):
    current = call("show", str(instance_id))
    engine.exact_match([current], manifest, instance_id)
    proof = call("destroy-station", str(instance_id), str(path))
    if (not isinstance(proof, dict) or proof.get("instance_id") != instance_id
        or proof.get("verified_absent") is not True or proof.get("destroyed") is not True):
        raise engine.GuardError("station scoped destruction not verified")
    return proof


def network_bytes(instance_id, manifest_path):
    endpoints = call("ssh-endpoints", str(instance_id))
    endpoint = endpoints.get("direct")
    if (endpoints.get("instance_id") != instance_id or not isinstance(endpoint, dict)
        or not re.fullmatch(r"[A-Za-z0-9.:-]{1,253}", str(endpoint.get("host")))
        or type(endpoint.get("port")) is not int or not 0 < endpoint["port"] < 65536):
        raise engine.GuardError("station direct SSH endpoint not ready")
    code = ("import json,pathlib; p=pathlib.Path('/sys/class/net'); "
            "v={x.name:{k:int((x/'statistics'/k).read_text()) for k in ('rx_bytes','tx_bytes')} "
            "for x in p.iterdir() if x.name!='lo'}; print(json.dumps(v,sort_keys=True))")
    known_hosts = manifest_path.with_suffix(".known-hosts")
    command = ["/usr/bin/ssh", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
               "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=accept-new",
               "-o", "UserKnownHostsFile=" + str(known_hosts), "-i", str(Path.home() / ".ssh/id_vastai"),
               "-p", str(endpoint["port"]), "root@" + endpoint["host"], "python3 -c " + shlex.quote(code)]
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
    if result.returncode or len(result.stdout) > 4096:
        raise engine.GuardError("station network metering unavailable")
    counters = json.loads(result.stdout)
    if (not isinstance(counters, dict) or not counters
        or any(not isinstance(v, dict) or set(v) != {"rx_bytes", "tx_bytes"}
               or any(type(n) is not int or n < 0 for n in v.values()) for v in counters.values())):
        raise engine.GuardError("station network counters invalid")
    return counters


def within_transfer_limit(counters, previous, image_bytes):
    if previous is not None and (set(counters) != set(previous)
        or any(counters[n][k] < previous[n][k] for n in counters for k in ("rx_bytes", "tx_bytes"))):
        return False
    # Include every received byte, never subtract the first observed baseline.
    # Docker pulls happen outside the container: reserve two compressed pulls.
    return (sum(v["rx_bytes"] for v in counters.values()) + image_bytes * 2 < 500 * 10**9
            and sum(v["tx_bytes"] for v in counters.values()) < 100 * 10**9)


def guard(path):
    raw = engine.read_owned(path, 65536)
    manifest = json.loads(raw)
    engine.destroy_exact = lambda identifier, m: destroy_exact(identifier, m, path)
    if (manifest.get("profile") != "picogk-station-v1"
        or not re.fullmatch(r"3dprinting993-picogk-station-[0-9a-f]{20}", str(manifest.get("attempt_label")))
        or not re.fullmatch(r"ghcr\.io/cluster2600/3dprinting993-picogk-m64@sha256:[0-9a-f]{64}", str(manifest.get("image_ref")))
        or Path(manifest["guard_path"]) != Path(__file__).absolute()
        or hashlib.sha256(engine.read_owned(Path(__file__).absolute(), 65536)).hexdigest() != manifest["guard_sha256"]
        or type(manifest.get("created_epoch")) is not int or type(manifest.get("deadline_epoch")) is not int
        or not 1800 <= manifest["deadline_epoch"] - manifest["created_epoch"] <= 21600
        or not engine.finite(manifest.get("budget_usd")) or not 0 < manifest["budget_usd"] <= 50):
        raise engine.GuardError("invalid station manifest")
    proof_data = engine.read_owned(Path(manifest["qualification_path"]), 65536)
    if hashlib.sha256(proof_data).hexdigest() != manifest["qualification_sha256"]:
        raise engine.GuardError("station qualification changed")
    qualification = json.loads(proof_data)
    # The approved OpenBao reader lives on this Mac; keep its external guard
    # awake independently of the terminal until this guard PID exits.
    subprocess.Popen(["/usr/bin/caffeinate", "-ims", "-w", str(os.getpid())],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ready_path = Path(manifest["guard_ready_path"])
    if ready_path != path.with_name(manifest["job_id"] + ".guard-ready.json"):
        raise engine.GuardError("invalid guard receipt path")
    inventory = call("instances")
    current = engine.exact_match(inventory, manifest)
    if len(inventory) > int(current is not None):
        raise engine.GuardError("station guard cannot arm alongside another rental")
    ready = {"armed": True, "pid": os.getpid(), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
             "wrapper_sha256": hashlib.sha256(engine.read_owned(WRAPPER, 1024**2)).hexdigest(),
             "label": manifest["attempt_label"], "image_ref": manifest["image_ref"],
             "deadline_epoch": manifest["deadline_epoch"]}
    # A launchd restart must retain the original monotonic deadline, first rate
    # and counters. Otherwise a wall-clock rollback or interface reset extends
    # lifetime or erases already observed traffic.
    prior_ready = json.loads(engine.read_owned(ready_path, 65536)) if ready_path.exists() else {}
    if prior_ready and prior_ready.get("manifest_sha256") != ready["manifest_sha256"]:
        raise engine.GuardError("guard restart manifest changed")
    cutoff = min(prior_ready.get("monotonic_cutoff", float("inf")),
                 time.monotonic() + max(0, manifest["deadline_epoch"] - time.time() - 300))
    boot = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.boottime"], check=True, capture_output=True, timeout=5).stdout.decode().strip()
    if prior_ready and prior_ready.get("boot_time") != boot:
        cutoff = 0  # A reboot loses the original monotonic clock: clean up immediately.
    ready["boot_time"] = boot
    ready["monotonic_cutoff"] = cutoff
    write(ready_path, ready)
    print(json.dumps(ready), flush=True)
    identifier, first_price, previous, absence, reserved_ceiling = None, None, None, 0, None
    network_path = path.with_name(manifest["job_id"] + ".network-ready.json")
    if network_path.exists():
        prior = json.loads(engine.read_owned(network_path, 65536))
        if prior.get("manifest_sha256") != ready["manifest_sha256"]:
            raise engine.GuardError("network receipt manifest changed")
        identifier, previous, first_price = prior["instance_id"], prior["counters"], prior["dph_total"]
    observed_at = None
    while True:
        try:
            inventory = call("instances")
            current = engine.exact_match(inventory, manifest, identifier)
            if current is None:
                if identifier is not None or time.time() >= manifest["deadline_epoch"]:
                    absence += 1
                    if absence >= 5:
                        return {"verified_absent": True, "instance_id": identifier, "reason": "absent"}
                time.sleep(2 if absence else 10)
                continue
            absence = 0
            identifier = current["id"]
            observed_at = observed_at or time.monotonic()
            if reserved_ceiling is None:
                paid = json.loads(engine.read_owned(path.with_name(manifest["job_id"] + ".paid-attempt.json"), 65536))
                reserved_ceiling = paid.get("cost_ceiling_usd")
                if (paid.get("manifest_sha256") != ready["manifest_sha256"]
                    or paid.get("label") != manifest["attempt_label"] or paid.get("image_ref") != manifest["image_ref"]
                    or not engine.finite(reserved_ceiling) or not 0 < reserved_ceiling <= manifest["budget_usd"]):
                    break
            if interrupted or time.monotonic() >= cutoff or time.time() >= manifest["deadline_epoch"] - 300:
                break
            if len(inventory) != 1:
                break
            if current.get("status") in {"stopped", "stopping", "exited", "offline", "error", "destroyed"}:
                break
            price = current.get("dph_total")
            up, down = current.get("inet_up_cost_usd_per_gb"), current.get("inet_down_cost_usd_per_gb")
            if None in (price, up, down) and time.monotonic() - observed_at < 120:
                time.sleep(5)
                continue
            if (not engine.finite(price) or not 0 < price <= 10
                or any(not engine.finite(n) or not 0 <= n <= .01 for n in (up, down))
                or first_price is not None and price != first_price
                or price * (manifest["deadline_epoch"] - manifest["created_epoch"]) / 3600 + 500*down + 100*up + 2 > reserved_ceiling):
                break
            first_price = price
            try:
                counters = network_bytes(identifier, path)
            except (engine.GuardError, subprocess.SubprocessError, ValueError, OSError):
                if previous is not None or time.monotonic() - observed_at > 900:
                    break
                time.sleep(10)
                continue
            if not within_transfer_limit(counters, previous, qualification["image_download_bytes"]):
                break
            previous = counters
            write(network_path,
                  {"instance_id": identifier, "manifest_sha256": ready["manifest_sha256"],
                   "updated_epoch": int(time.time()), "counters": counters, "metering_active": True,
                   "dph_total": first_price})
            time.sleep(10)
        except (engine.GuardError, OSError, subprocess.SubprocessError, ValueError):
            if identifier is not None:
                break
            time.sleep(10)
    return {**engine.cleanup_until_absent(identifier, manifest), "reason": "station_deadline_cost_or_metering_guard"}


def interrupt(_signal, _frame):
    global interrupted
    interrupted = True


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        result = guard(Path(sys.argv[1]))
        write(Path(sys.argv[1]).with_suffix(".guard-result.json"), result)
        print(json.dumps(result), flush=True)
    except (engine.GuardError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        print('{"guard_failed":true,"billing_stop_verified":false}', flush=True)
        sys.exit(1)
