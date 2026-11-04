#!/usr/bin/env python3
"""USD 5 / 90-minute policy for the existing SimReady validation-only launcher.

Reuse the frozen engine-twin guard, including exact ownership, monotonic time,
cleanup reserve, late-creation reconciliation and signal-triggered cleanup.
Neither the installed OpenBao wrapper nor either parent guard is modified.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

PARENT_SHA256 = "ecc1021eecca65af2787d171694c649f36197a4ffe57447fbd24ad7b2a11bab9"
IMAGE = "ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699"
FIELDS = {
    "profile", "job_id", "attempt_label", "image_ref", "created_epoch",
    "deadline_epoch", "budget_usd", "download_budget_gb", "upload_budget_gb",
    "guard_path", "guard_sha256", "guard_ready_path",
}


def load_policy():
    path = Path(__file__).resolve().parents[1] / "engine-twin/deadline_guard.py"
    if any(p.is_symlink() for p in (*path.parents, path)):
        raise RuntimeError("Guard policy symlinks are forbidden")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022 or info.st_nlink != 1 or info.st_size > 65536):
            raise RuntimeError("Unsafe guard policy metadata")
        data = stream.read(65537)
    if hashlib.sha256(data).hexdigest() != PARENT_SHA256:
        raise RuntimeError("Parent guard fingerprint changed")
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("review_guard_parent", loader=None))
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module


policy = load_policy()


def contract(_manifest):
    # The frozen image exposes idle service ports; the launcher starts no LLM.
    return {"image": IMAGE, "max_dph": 2.5, "api_port_allowed": True}


def validate_manifest(manifest):
    error = policy.engine.GuardError
    if not isinstance(manifest, dict) or set(manifest) != FIELDS:
        raise error("Unexpected review manifest fields")
    if (manifest["profile"] != "964-omniverse-review-v1"
        or not isinstance(manifest["job_id"], str)
        or not re.fullmatch(r"964-omniverse-[a-z0-9-]{1,48}", manifest["job_id"])
        or not isinstance(manifest["attempt_label"], str)
        or not re.fullmatch(r"3dprinting993-simready-local-ai-[0-9a-f]{20}", manifest["attempt_label"])
        or manifest["image_ref"] != IMAGE
        or type(manifest["created_epoch"]) is not int
        or type(manifest["deadline_epoch"]) is not int
        or not manifest["created_epoch"] <= time.time() < manifest["deadline_epoch"]
        or not 600 <= manifest["deadline_epoch"] - manifest["created_epoch"] <= 5400
        or not policy.engine.finite(manifest["budget_usd"])
        or not 1 < manifest["budget_usd"] <= 5):
        raise error("Invalid approved review bounds or identity")
    for field, cap in (("download_budget_gb", 40), ("upload_budget_gb", 15)):
        if not policy.engine.finite(manifest[field]) or not 0 < manifest[field] <= cap:
            raise error("Invalid review transfer allocation")
    source = Path(__file__).absolute()
    if (manifest["guard_path"] != str(source)
        or hashlib.sha256(policy.engine.read_owned(source, 65536)).hexdigest() != manifest["guard_sha256"]):
        raise error("Review guard fingerprint mismatch")
    policy._manifest.clear()
    policy._manifest.update(manifest)


def observed_wrapper_call(*arguments):
    result = policy.wrapper_call(*arguments)
    if arguments and arguments[0] == "instances" and isinstance(result, list) and len(result) > 1:
        print(policy.engine.json.dumps({"event": "nonexclusive_inventory", "epoch": time.time(),
              "instance_ids": [item.get("id") for item in result if isinstance(item, dict)]}), flush=True)
    return result


def observed_cost_valid(instance, manifest, first_price=None):
    accepted = policy.cost_valid(instance, manifest, first_price)
    if not accepted:
        fields = ("id", "dph_total", "inet_up_cost_usd_per_gb", "inet_down_cost_usd_per_gb")
        print(policy.engine.json.dumps({"event": "cost_contract_rejected", "epoch": time.time(),
              "observed": {key: instance.get(key) for key in fields},
              "first_price": first_price, "interrupted": policy.interrupted,
              "api_port_forbidden": policy.api_port_forbidden(instance)}), flush=True)
    return accepted


policy.engine.wrapper_call = observed_wrapper_call
policy.engine.cost_valid = observed_cost_valid
policy.spec = contract
policy.validate_manifest = validate_manifest
policy.engine.validate_manifest = validate_manifest

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, policy.request_cleanup)
    signal.signal(signal.SIGINT, policy.request_cleanup)
    sys.exit(policy.engine.main())
