#!/usr/bin/env python3
"""Engine-twin policy over the unchanged, hash-checked PicoGK guard engine.

One guard per role (llm, compute). Each destroys only its exact label. The
sibling role of the same session is hidden from this guard's inventory view so
two paired rentals never trigger each other's single-instance contract; any
other rental on the account still does. Calls only instances/show/destroy.
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
PROFILE = "engine-twin-v1"
IMAGES = {
    "llm": "vllm/vllm-openai@sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90",
    "compute": "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699",
}
MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"
REVISION = "dcaee4d4dfc5ee71ad501f01f530e5652438fde0"
MAX_DPH = 2.60
MAX_TRANSFER_RATE = 0.01
MAX_SECONDS = 6 * 60 * 60
MAX_BUDGET_USD = 30.0
LABEL_RE = re.compile(r"3dprinting993-engine-twin-(llm|compute)-([0-9a-f]{20})")
interrupted = False


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
    spec = importlib.util.spec_from_loader("engine_twin_deadline_engine", loader=None)
    engine = importlib.util.module_from_spec(spec)
    engine.__file__ = str(path)
    exec(compile(data, str(path), "exec"), engine.__dict__)
    return engine


engine = load_engine()
_manifest = {}


def sibling_label(label):
    match = LABEL_RE.fullmatch(str(label))
    if not match:
        raise engine.GuardError("invalid engine-twin label")
    other = "compute" if match.group(1) == "llm" else "llm"
    return f"3dprinting993-engine-twin-{other}-{match.group(2)}"


def validate_manifest(manifest):
    match = LABEL_RE.fullmatch(str(manifest.get("attempt_label"))) if isinstance(manifest, dict) else None
    if (match is None or manifest.get("profile") != PROFILE or manifest.get("role") != match.group(1)
        or manifest.get("image_ref") != IMAGES[match.group(1)]
        or manifest.get("model") != MODEL or manifest.get("model_revision") != REVISION
        or manifest.get("sibling_label") != sibling_label(manifest["attempt_label"])
        or type(manifest.get("created_epoch")) is not int
        or type(manifest.get("deadline_epoch")) is not int
        or not manifest["created_epoch"] <= time.time() < manifest["deadline_epoch"]
        or not 600 <= manifest["deadline_epoch"] - manifest["created_epoch"] <= MAX_SECONDS
        or not engine.finite(manifest.get("budget_usd")) or not 1 < manifest["budget_usd"] <= MAX_BUDGET_USD):
        raise engine.GuardError("invalid bounded engine-twin manifest")
    for field, cap in (("download_budget_gb", 80), ("upload_budget_gb", 20)):
        if not engine.finite(manifest.get(field)) or not 0 < manifest[field] <= cap:
            raise engine.GuardError("invalid engine-twin transfer allocation")
    if (Path(manifest["guard_path"]) != Path(__file__).absolute()
        or hashlib.sha256(engine.read_owned(Path(__file__).absolute(), 65536)).hexdigest()
            != manifest["guard_sha256"]):
        raise engine.GuardError("engine-twin guard fingerprint mismatch")
    _manifest.update(manifest)


def cost_valid(instance, manifest, first_price=None):
    price = instance.get("dph_total")
    up, down = instance.get("inet_up_cost_usd_per_gb"), instance.get("inet_down_cost_usd_per_gb")
    if (interrupted or instance.get("api_port") is not None
        or not engine.finite(price) or not 0 < price <= MAX_DPH
        or (first_price is not None and first_price != price)
        or not all(engine.finite(value) and 0 <= value <= MAX_TRANSFER_RATE for value in (up, down))):
        return False
    ceiling = price * (manifest["deadline_epoch"] - manifest["created_epoch"]) / 3600
    return ceiling + down * manifest["download_budget_gb"] + up * manifest["upload_budget_gb"] + 1 <= manifest["budget_usd"]


def only_cost_metadata_missing(instance, first_price):
    if interrupted or instance.get("api_port") is not None:
        return False
    missing = False
    for field, cap in (("dph_total", MAX_DPH), ("inet_up_cost_usd_per_gb", MAX_TRANSFER_RATE),
                       ("inet_down_cost_usd_per_gb", MAX_TRANSFER_RATE)):
        value = instance.get(field)
        if value is None:
            missing = True
        elif (not engine.finite(value) or not 0 <= value <= cap
              or (field == "dph_total" and (value == 0 or first_price is not None and first_price != value))):
            return False
    return missing


initial_startup_pending = engine.startup_pending


def startup_pending(instance):
    """A just-created rental can be listed before Vast reports any state.

    The engine only waits inside its bounded metadata window (120 s); an
    explicit terminal or stopped state still triggers cleanup at once.
    """
    if interrupted:
        return False
    states = instance.get("provider_states")
    if instance.get("status") is None and (states is None or (
            isinstance(states, dict) and all(states.get(key) is None for key in
                                             ("actual_status", "cur_state", "next_state", "intended_status")))):
        return True
    return initial_startup_pending(instance)


initial_wrapper_call = engine.wrapper_call


def wrapper_call(*arguments):
    """Hide only the exact sibling of this session; every other rental stays visible."""
    result = initial_wrapper_call(*arguments)
    if arguments and arguments[0] == "instances" and _manifest.get("sibling_label"):
        if not isinstance(result, list):
            raise engine.GuardError("invalid sanitized inventory")
        siblings = [item for item in result if isinstance(item, dict) and item.get("label") == _manifest["sibling_label"]]
        if len(siblings) > 1:
            raise engine.GuardError("ambiguous sibling ownership")
        result = [item for item in result if not (isinstance(item, dict) and item.get("label") == _manifest["sibling_label"])]
    return result


def request_cleanup(_signal, _frame):
    global interrupted
    interrupted = True


initial_guard = engine.guard


def guard(manifest_path):
    """An uncertain PUT remains watched after the engine's startup timeout."""
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
engine.startup_pending = startup_pending
engine.guard = guard


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, request_cleanup)
    signal.signal(signal.SIGINT, request_cleanup)
    sys.exit(engine.main())
