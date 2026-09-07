#!/usr/bin/env python3
"""Arm before PicoGK rental; destroy its exact ownership label before deadline.

No API key, OpenBao identity or secret is read here. Only the approved wrapper's
sanitized instances/show/destroy operations are called. This guard does not
claim that a stopped container ends billing; only verified absence does.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time


WRAPPER = Path("/Users/maxime/.local/bin/openbao-vastai")


class GuardError(Exception):
    pass


def read_owned(path: Path, maximum: int) -> bytes:
    if not path.is_absolute():
        raise GuardError("absolute path required")
    for entry in (*reversed(path.parents), path):
        if entry.is_symlink():
            raise GuardError("symlinks forbidden")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022 or info.st_nlink != 1 or not 0 < info.st_size <= maximum):
            raise GuardError("unsafe file metadata")
        data = stream.read(maximum + 1)
        if len(data) != info.st_size:
            raise GuardError("file changed during read")
        return data


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_manifest(manifest: dict) -> None:
    if (not isinstance(manifest, dict) or manifest.get("profile") != "picogk-m64-v1"
        or not isinstance(manifest.get("attempt_label"), str)
        or not re.fullmatch(r"3dprinting993-picogk-m64-[0-9a-f]{20}", manifest["attempt_label"])
        or not isinstance(manifest.get("image_ref"), str)
        or not re.fullmatch(r"ghcr\.io/cluster2600/3dprinting993-picogk-m64@sha256:[0-9a-f]{64}", manifest["image_ref"])
        or type(manifest.get("created_epoch")) is not int
        or type(manifest.get("deadline_epoch")) is not int
        or not manifest["created_epoch"] <= time.time() < manifest["deadline_epoch"]
        or not 60 <= manifest["deadline_epoch"] - manifest["created_epoch"] <= 10800
        or not finite(manifest.get("budget_usd")) or not 1 < manifest["budget_usd"] <= 4):
        raise GuardError("invalid bounded PicoGK manifest")
    for field, cap in (("image_download_gb", 20), ("max_input_gb", 2), ("max_output_gb", 2)):
        if not finite(manifest.get(field)) or not 0 <= manifest[field] <= cap:
            raise GuardError("invalid transfer allocation")


def wrapper_call(*arguments):
    if not arguments or arguments[0] not in {"instances", "show", "destroy"}:
        raise GuardError("operation outside guard allowlist")
    result = subprocess.run([str(WRAPPER), *arguments], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180,
                            env={"LC_ALL": "C", "PATH": os.environ.get("PATH", os.defpath)})
    if result.returncode or len(result.stdout) > 2 * 1024 * 1024:
        raise GuardError("approved wrapper failed; private diagnostics withheld")
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeError):
        raise GuardError("approved wrapper returned invalid JSON") from None


def exact_match(inventory, manifest, instance_id=None):
    if not isinstance(inventory, list):
        raise GuardError("invalid sanitized inventory")
    ids = [item.get("id") for item in inventory if isinstance(item, dict)]
    if len(ids) != len(inventory) or any(type(item) is not int or item <= 0 for item in ids) or len(set(ids)) != len(ids):
        raise GuardError("invalid or duplicate instance identity")
    matches = [item for item in inventory if item.get("label") == manifest["attempt_label"]]
    if len(matches) > 1:
        raise GuardError("ambiguous ownership; no automatic destruction")
    if not matches:
        if instance_id is not None and instance_id in ids:
            raise GuardError("observed instance label changed; no automatic destruction")
        return None
    match = matches[0]
    if match.get("image") != manifest["image_ref"] or (instance_id is not None and match["id"] != instance_id):
        raise GuardError("observed instance identity changed; no automatic destruction")
    return match


def cost_valid(instance, manifest, first_price=None):
    price = instance.get("dph_total")
    up, down = instance.get("inet_up_cost_usd_per_gb"), instance.get("inet_down_cost_usd_per_gb")
    if not finite(price) or not 0 < price <= 0.8:
        return False
    if first_price is not None and price != first_price:
        return False
    if not all(finite(value) and 0 <= value <= 0.01 for value in (up, down)):
        return False
    seconds = manifest["deadline_epoch"] - manifest["created_epoch"]
    ceiling = price * seconds / 3600 + down * (manifest["image_download_gb"] + manifest["max_input_gb"])
    return ceiling + up * manifest["max_output_gb"] + 1 <= manifest["budget_usd"]


def destroy_exact(instance_id: int, manifest: dict):
    current = wrapper_call("show", str(instance_id))
    exact_match([current], manifest, instance_id)
    proof = wrapper_call("destroy", str(instance_id), "--confirm")
    if (not isinstance(proof, dict) or proof.get("instance_id") != instance_id
        or proof.get("destroyed") is not True or proof.get("verified_absent") is not True):
        raise GuardError("provider destruction not verified")
    return proof


def stable_absence(manifest: dict, instance_id: int | None):
    for _ in range(5):
        if exact_match(wrapper_call("instances"), manifest, instance_id) is not None:
            return False
        time.sleep(2)
    return True


def cleanup_until_absent(instance_id: int, manifest: dict):
    """Stay alive across transport errors and reconcile an uncertain DELETE."""
    absent = 0
    announced = False
    while True:
        try:
            inventory = wrapper_call("instances")
        except (GuardError, OSError, subprocess.SubprocessError):
            absent = 0
            if not announced:
                print(json.dumps({"cleanup_retrying": True, "instance_id": instance_id,
                                  "billing_stop_verified": False}), flush=True)
                announced = True
            time.sleep(15)
            continue
        # Ownership failures are not transient and must never authorize a
        # different deletion. A vanished response alone also proves nothing.
        current = exact_match(inventory, manifest, instance_id)
        if current is None:
            absent += 1
            if absent >= 5:
                return {"instance_id": instance_id, "verified_absent": True,
                        "destroyed": True, "delete_acknowledgement_may_have_been_lost": announced}
            time.sleep(2)
            continue
        absent = 0
        try:
            return destroy_exact(instance_id, manifest)
        except (GuardError, OSError, subprocess.SubprocessError):
            # Do not blindly repeat DELETE: next iteration re-reads the full
            # inventory, then the exact show identity before another request.
            if not announced:
                print(json.dumps({"cleanup_retrying": True, "instance_id": instance_id,
                                  "billing_stop_verified": False}), flush=True)
                announced = True
            time.sleep(15)


def guard(manifest_path: Path):
    data = read_owned(manifest_path, 65536)
    manifest = json.loads(data)
    validate_manifest(manifest)
    wrapper_data = read_owned(WRAPPER, 1024 * 1024)
    ready_path = Path(manifest["guard_ready_path"])
    if ready_path.parent != manifest_path.parent or ready_path.name != manifest["job_id"] + ".guard-ready.json":
        raise GuardError("invalid sibling guard readiness path")
    # Arm only after a live sanitized inventory read and before the paid PUT.
    if wrapper_call("instances") != []:
        raise GuardError("guard requires no existing instance before arming")
    ready = {"armed": True, "pid": os.getpid(), "manifest_sha256": hashlib.sha256(data).hexdigest(),
             "wrapper_sha256": hashlib.sha256(wrapper_data).hexdigest(),
             "label": manifest["attempt_label"], "image_ref": manifest["image_ref"],
             "deadline_epoch": manifest["deadline_epoch"]}
    fd = os.open(ready_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(ready, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(ready, sort_keys=True), flush=True)
    # Wall-clock corrections can shorten, never extend, this rental lifetime.
    monotonic_deadline = time.monotonic() + max(0, manifest["deadline_epoch"] - time.time() - 300)
    startup_deadline = min(monotonic_deadline, time.monotonic() + 1200)
    instance_id, first_price = None, None
    reason = "deadline_cleanup_reserve"
    while True:
        try:
            inventory = wrapper_call("instances")
        except (GuardError, OSError, subprocess.SubprocessError):
            # Once ownership is known, attempt a fresh exact lookup and end
            # billing on a monitoring failure. Never blindly delete an ID.
            if instance_id is not None:
                proof = cleanup_until_absent(instance_id, manifest)
                return {**proof, "reason": "inventory_read_failed", "label": manifest["attempt_label"]}
            if time.monotonic() >= startup_deadline:
                print(json.dumps({"inventory_retrying": True, "billing_stop_verified": False,
                                  "label": manifest["attempt_label"]}), flush=True)
            time.sleep(15)
            continue
        current = exact_match(inventory, manifest, instance_id)
        if current is None:
            if instance_id is not None:
                proof = cleanup_until_absent(instance_id, manifest)
                return {**proof, "reason": "already_destroyed", "label": manifest["attempt_label"]}
            if time.monotonic() >= startup_deadline:
                try:
                    gone = stable_absence(manifest, None)
                except (GuardError, OSError, subprocess.SubprocessError):
                    time.sleep(15)
                    continue
                if gone:
                    return {"verified_absent": True, "instance_id": None,
                            "reason": "no_instance_observed"}
            time.sleep(15)
            continue
        instance_id = current["id"]
        if current.get("status") not in {"created", "loading", "running"}:
            reason = "instance_left_active_states"
            break
        if not cost_valid(current, manifest, first_price) or len(inventory) != 1:
            reason = "contract_or_cost_guard"
            break
        if first_price is None:
            first_price = current["dph_total"]
        if time.monotonic() >= monotonic_deadline or time.time() >= manifest["deadline_epoch"] - 300:
            break
        time.sleep(min(30, max(0, monotonic_deadline - time.monotonic())))
    proof = cleanup_until_absent(instance_id, manifest)
    return {**proof, "reason": reason, "label": manifest["attempt_label"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        result = guard(args.manifest)
    except (GuardError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        print(json.dumps({"guard_failed": True, "billing_stop_verified": False,
                          "action": "inspect_exact_attempt_before_any_new_rental"}), flush=True)
        return 1
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
