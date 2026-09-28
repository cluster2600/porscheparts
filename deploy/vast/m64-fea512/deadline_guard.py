#!/usr/bin/env python3
"""Fixed $5 FEA512 policy over the unchanged, hash-checked PicoGK guard.

The exact background VM is read-only and excluded from this additional job's
budget. A changed or unexpected identity stays visible and cannot be hidden.
Only sanitized instances/show/destroy operations use the approved wrapper.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

ENGINE_SHA256 = "c1d82cfaf5c8f178b5eaeb32ca5d98774b3dd60502087310f10a2966e53ff3f4"
PROFILE = "m64-fea512-v1"
BACKGROUND = {"id": 52810563, "label": "3dprinting993-cad-recode-vm-20260926",
              "image": "docker.io/vastai/kvm:cuda-12.9.1-auto"}
interrupted = False
_initial_inventory = True


def load_engine():
    path = Path(__file__).resolve().parents[1] / "picogk" / "deadline_guard.py"
    for entry in (*reversed(path.parents), path):
        if entry.is_symlink():
            raise RuntimeError("guard engine symlinks forbidden")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022 or info.st_nlink != 1 or info.st_size > 65536):
            raise RuntimeError("unsafe guard engine metadata")
        data = stream.read(65537)
    if hashlib.sha256(data).hexdigest() != ENGINE_SHA256:
        raise RuntimeError("guard engine changed; requalification required")
    spec = importlib.util.spec_from_loader("fea512_deadline_engine", loader=None)
    loaded = importlib.util.module_from_spec(spec)
    loaded.__file__ = str(path)
    exec(compile(data, str(path), "exec"), loaded.__dict__)
    return loaded


engine = load_engine()


def validate_manifest(manifest):
    if (not isinstance(manifest, dict) or manifest.get("profile") != PROFILE
        or manifest.get("schema_version") != "1.0.0"
        or not re.fullmatch(r"m64-fea512-[a-z0-9][a-z0-9-]{0,63}", str(manifest.get("job_id")))
        or not re.fullmatch(r"3dprinting993-m64-fea512-[0-9a-f]{20}", str(manifest.get("attempt_label")))
        or not re.fullmatch(r"ghcr\.io/cluster2600/3dprinting993-picogk-m64@sha256:[0-9a-f]{64}", str(manifest.get("image_ref")))
        or manifest.get("background_instance") != BACKGROUND
        or type(manifest["background_instance"].get("id")) is not int
        or type(manifest.get("created_epoch")) is not int
        or type(manifest.get("deadline_epoch")) is not int
        or not manifest["created_epoch"] <= time.time() < manifest["deadline_epoch"]
        or not 60 <= manifest["deadline_epoch"] - manifest["created_epoch"] <= 10800
        or not engine.finite(manifest.get("budget_usd")) or not 1 < manifest["budget_usd"] <= 5):
        raise engine.GuardError("invalid bounded FEA512 manifest")
    for field, cap in (("image_download_gb", 20), ("max_input_gb", 2), ("max_output_gb", 2)):
        if not engine.finite(manifest.get(field)) or not 0 <= manifest[field] <= cap:
            raise engine.GuardError("invalid FEA512 transfer allocation")
    if manifest["image_download_gb"] <= 0:
        raise engine.GuardError("FEA512 requires a measured image size")
    if (not isinstance(manifest.get("guard_path"), str)
        or Path(manifest["guard_path"]) != Path(__file__).absolute()
        or hashlib.sha256(engine.read_owned(Path(__file__).absolute(), 65536)).hexdigest()
            != manifest.get("guard_sha256")):
        raise engine.GuardError("FEA512 guard fingerprint mismatch")


def resources_valid(instance, *, permit_missing=False):
    for key, floor in (("cpu_cores_effective", 32), ("cpu_ram_mb", 512000), ("disk_space_gb", 500)):
        value = instance.get(key)
        if value is None and permit_missing:
            continue
        if not engine.finite(value) or value < floor:
            return False
    for key in ("num_gpus", "gpu_fraction"):
        value = instance.get(key)
        if value is None and permit_missing:
            continue
        if not engine.finite(value) or value != 1:
            return False
    return True


def cost_valid(instance, manifest, first_price=None):
    price = instance.get("dph_total")
    up, down = instance.get("inet_up_cost_usd_per_gb"), instance.get("inet_down_cost_usd_per_gb")
    if (interrupted or not resources_valid(instance)
        or not engine.finite(price) or not 0 < price <= 1
        or (first_price is not None and first_price != price)
        or not all(engine.finite(value) and 0 <= value <= 0.01 for value in (up, down))):
        return False
    ceiling = price * (manifest["deadline_epoch"] - manifest["created_epoch"]) / 3600
    ceiling += down * (manifest["image_download_gb"] + manifest["max_input_gb"])
    return ceiling + up * manifest["max_output_gb"] + 1 <= manifest["budget_usd"]


def only_cost_metadata_missing(instance, first_price):
    if interrupted or not resources_valid(instance, permit_missing=True):
        return False
    missing = not resources_valid(instance)
    for field, cap in (("dph_total", 1), ("inet_up_cost_usd_per_gb", 0.01), ("inet_down_cost_usd_per_gb", 0.01)):
        value = instance.get(field)
        if value is None:
            missing = True
        elif (not engine.finite(value) or not 0 <= value <= cap
              or (field == "dph_total" and (value == 0 or first_price is not None and first_price != value))):
            return False
    return missing


initial_wrapper_call = engine.wrapper_call


def wrapper_call(*arguments):
    global _initial_inventory
    if arguments and arguments[0] == "destroy" and len(arguments) > 1 and arguments[1] == str(BACKGROUND["id"]):
        raise engine.GuardError("the background VM is never a destruction target")
    result = initial_wrapper_call(*arguments)
    if arguments and arguments[0] == "instances":
        if not isinstance(result, list):
            raise engine.GuardError("invalid sanitized inventory")
        ids = [item.get("id") for item in result if isinstance(item, dict)]
        valid_ids = (len(ids) == len(result) and all(type(value) is int and value > 0 for value in ids)
                     and len(set(ids)) == len(ids))
        background = [item for item in result if isinstance(item, dict) and item.get("id") == BACKGROUND["id"]]
        exact = (valid_ids and len(background) == 1
                 and {key: background[0].get(key) for key in BACKGROUND} == BACKGROUND)
        if _initial_inventory:
            if not exact:
                raise engine.GuardError("exact background VM must be freshly verified before arming")
            _initial_inventory = False
        if exact:
            result = [item for item in result if item["id"] != BACKGROUND["id"]]
        # Mismatches stay visible: the engine rejects arming or cleans up only
        # its own exact attempt. The foreign row is never a cleanup target.
    return result


def request_cleanup(_signal, _frame):
    global interrupted
    interrupted = True


initial_guard = engine.guard


def guard(manifest_path):
    """Keep watching an uncertain paid PUT through its entire original deadline."""
    manifest = engine.json.loads(engine.read_owned(manifest_path, 65536))
    validate_manifest(manifest)
    monotonic_deadline = time.monotonic() + max(0, manifest["deadline_epoch"] - time.time())
    result = initial_guard(manifest_path)
    if result.get("reason") != "no_instance_observed":
        return result
    absent = 0
    while True:
        try:
            current = engine.exact_match(engine.wrapper_call("instances"), manifest)
        except (engine.GuardError, OSError, subprocess.SubprocessError):
            absent = 0
            time.sleep(15)
            continue
        if current is not None:
            return {**engine.cleanup_until_absent(current["id"], manifest), "reason": "late_creation_cleanup"}
        if time.monotonic() >= monotonic_deadline or time.time() >= manifest["deadline_epoch"]:
            absent += 1
            if absent >= 5:
                return {"verified_absent": True, "instance_id": None, "reason": "no_creation_by_deadline"}
            time.sleep(2)
        else:
            time.sleep(min(15, max(0, monotonic_deadline - time.monotonic())))


engine.validate_manifest = validate_manifest
engine.cost_valid = cost_valid
engine.only_cost_metadata_missing = only_cost_metadata_missing
engine.wrapper_call = wrapper_call
engine.guard = guard

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, request_cleanup)
    signal.signal(signal.SIGINT, request_cleanup)
    sys.exit(engine.main())
