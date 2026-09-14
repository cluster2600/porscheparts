#!/usr/bin/env python3
"""Garde de budget local, jamais un ordonnanceur de phases.

Usage : --manifest /chemin/manifest.json --state-dir /nouveau/dossier-prive
Le manifeste et le wrapper installé sont figés par SHA256 à l'armement.
À l'échéance absolue : collecte (300 s), suppression ciblée, preuve d'absence.

Arrêt anticipé, après collecte et suppression manuelles via le wrapper : créer
state-dir/stop.json (0600) contenant exactement job_id, instance_id, label,
image, manifest_sha256 et collection_receipt (chemin absolu du reçu de collecte).
Le garde vérifie ce reçu et l'absence distante ; un simple touch ne l'arrête pas.
Le marqueur n'autorise ni une nouvelle location, ni une commande de phase.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time


WRAPPER = Path("/Users/maxime/.local/bin/openbao-vastai")
POLL_SECONDS = 30
READ_TIMEOUT = 45
COLLECT_TIMEOUT = 300
DESTROY_TIMEOUT = 90
MAX_LIFETIME = 7200


class GuardError(Exception):
    """Fixed non-secret diagnostic, never raw wrapper output."""


def read_private_source(path: Path, maximum: int = 1024 * 1024) -> bytes:
    if not path.is_absolute():
        raise GuardError("absolute_path_required")
    try:
        for part in (*reversed(path.parents), path):
            if stat.S_ISLNK(part.lstat().st_mode):
                raise GuardError("symlink_rejected")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1 or before.st_mode & 0o022 or before.st_size > maximum:
                raise GuardError("unsafe_local_metadata")
            value = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
            if len(value) != before.st_size or len(value) > maximum or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise GuardError("local_file_changed")
            return value
    except OSError as exc:
        raise GuardError("local_file_unavailable") from exc


def strict_json(value: bytes):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("duplicate")
            result[key] = item
        return result

    def nonfinite(_):
        raise ValueError("nonfinite")

    try:
        return json.loads(value, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise GuardError("invalid_json") from exc


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_receipt(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def wrapper_call(arguments: list[str], timeout: int):
    """Only four installed-wrapper operations, with bounded streams and time."""
    valid = (
        arguments == ["instances"]
        or (len(arguments) == 2 and arguments[0] == "show" and arguments[1].isdigit())
        or (len(arguments) == 3 and arguments[0] == "destroy" and arguments[1].isdigit() and arguments[2] == "--confirm")
        or (len(arguments) == 4 and arguments[0] == "m64-collect" and arguments[1].isdigit())
    )
    if not valid or type(timeout) is not int or not 1 <= timeout <= COLLECT_TIMEOUT:
        raise GuardError("operation_outside_guard_scope")
    try:
        process = subprocess.Popen(
            [str(WRAPPER), *arguments], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
            env={"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"},
        )
    except OSError as exc:
        raise GuardError("wrapper_unavailable") from exc
    selector = selectors.DefaultSelector()
    output = bytearray()
    error_bytes = 0
    deadline = time.monotonic() + timeout
    try:
        for stream in (process.stdout, process.stderr):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise GuardError("wrapper_timeout")
            for key, _ in selector.select(min(remaining, 0.25)):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if key.fileobj is process.stdout:
                    output.extend(data)
                    if len(output) > 4 * 1024 * 1024:
                        raise GuardError("wrapper_output_limit")
                else:
                    error_bytes += len(data)
                    if error_bytes > 65536:
                        raise GuardError("wrapper_error_limit")
        code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
        if code != 0:
            raise GuardError("wrapper_operation_failed")
        return strict_json(bytes(output))
    except BaseException as exc:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=2)
        if isinstance(exc, (GuardError, KeyboardInterrupt, SystemExit)):
            raise
        raise GuardError("wrapper_transport_failed") from exc
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()


def load_target(manifest_path: Path) -> tuple[dict, str]:
    data = read_private_source(manifest_path)
    manifest = strict_json(data)
    if not isinstance(manifest, dict) or manifest.get("profile") != "m64-omni-static-v1":
        raise GuardError("manifest_profile_mismatch")
    target = {name: manifest.get(name) for name in ("job_id", "instance_id", "label", "image")}
    if type(target["instance_id"]) is not int or target["instance_id"] <= 0:
        raise GuardError("manifest_instance_invalid")
    if not isinstance(target["job_id"], str) or not re.fullmatch(r"m64-[a-z0-9][a-z0-9-]{0,63}", target["job_id"]):
        raise GuardError("manifest_job_invalid")
    if not isinstance(target["label"], str) or not re.fullmatch(r"3dprinting993-simready-local-ai-[0-9a-f]{20}", target["label"]):
        raise GuardError("manifest_label_invalid")
    if not isinstance(target["image"], str) or not re.fullmatch(r"ghcr\.io/cluster2600/3dprinting993-simready-m64-runtime@sha256:[0-9a-f]{64}", target["image"]):
        raise GuardError("manifest_image_invalid")
    created, deadline = manifest.get("created_epoch"), manifest.get("deadline_epoch")
    if type(created) is not int or type(deadline) is not int or created <= 0 or not 0 < deadline - created <= MAX_LIFETIME or created > time.time():
        raise GuardError("manifest_lifetime_invalid")
    for key, cap in (("max_dph", 2.5), ("budget_usd", 20)):
        value = manifest.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= cap:
            raise GuardError("manifest_budget_invalid")
    target.update(deadline_epoch=deadline, created_epoch=created)
    return target, digest(data)


def exact_instance(response, target: dict) -> None:
    if not isinstance(response, dict) or type(response.get("id")) is not int or response["id"] != target["instance_id"] or any(response.get(field) != target[field] for field in ("label", "image")):
        raise GuardError("exact_instance_identity_mismatch")


def absent(inventory, target: dict) -> bool:
    if not isinstance(inventory, list) or any(not isinstance(item, dict) or type(item.get("id")) is not int or item["id"] <= 0 or (item.get("label") is not None and not isinstance(item["label"], str)) for item in inventory):
        raise GuardError("inventory_invalid")
    return not any(item["id"] == target["instance_id"] or item["label"] == target["label"] for item in inventory)


def valid_stop(marker: Path, target: dict, manifest_sha: str) -> bool:
    try:
        value = strict_json(read_private_source(marker))
        fields = {"job_id", "instance_id", "label", "image", "manifest_sha256", "collection_receipt"}
        if not isinstance(value, dict) or set(value) != fields or any(value[name] != target[name] for name in ("job_id", "instance_id", "label", "image")) or value["manifest_sha256"] != manifest_sha or not isinstance(value["collection_receipt"], str):
            return False
        receipt = strict_json(read_private_source(Path(value["collection_receipt"])))
        return isinstance(receipt, dict) and receipt.get("operation") == "collect" and receipt.get("job_id") == target["job_id"] and type(receipt.get("instance_id")) is int and receipt["instance_id"] == target["instance_id"] and receipt.get("manifest_sha256") == manifest_sha and isinstance(receipt.get("files"), dict) and bool(receipt["files"])
    except (GuardError, TypeError, ValueError):
        return False


def run_guard(manifest_path: Path, state_dir: Path) -> int:
    target, manifest_sha = load_target(manifest_path)
    wrapper_sha = digest(read_private_source(WRAPPER))
    # Independent monotonic cap prevents a wall-clock rollback extending rent.
    monotonic_deadline = time.monotonic() + max(0, target["deadline_epoch"] - time.time())
    if not state_dir.is_absolute() or state_dir.exists() or state_dir.is_symlink() or state_dir.parent.resolve() != state_dir.parent:
        raise GuardError("new_private_state_directory_required")
    state_dir.mkdir(mode=0o700)
    write_receipt(state_dir / "guard.json", {**target, "manifest_sha256": manifest_sha, "wrapper_sha256": wrapper_sha, "poll_seconds": POLL_SECONDS, "collection_timeout_seconds": COLLECT_TIMEOUT})

    def call(arguments, timeout=READ_TIMEOUT):
        if digest(read_private_source(WRAPPER)) != wrapper_sha:
            raise GuardError("installed_wrapper_changed")
        return wrapper_call(arguments, timeout)

    def remaining():
        return min(target["deadline_epoch"] - time.time(), monotonic_deadline - time.monotonic())

    final = {"job_id": target["job_id"], "instance_id": target["instance_id"], "manifest_sha256": manifest_sha, "collection_verified": False, "absence_verified": False}
    instance_id = str(target["instance_id"])
    try:
        while remaining() > 0:
            marker = state_dir / "stop.json"
            if valid_stop(marker, target, manifest_sha) and absent(call(["instances"]), target):
                final.update(status="manual_collection_and_absence_verified", collection_verified=True, absence_verified=True)
                return 0
            try:
                exact_instance(call(["show", instance_id]), target)
            except GuardError as exc:
                if str(exc) in {"exact_instance_identity_mismatch", "installed_wrapper_changed"}:
                    raise
                # Read failure is not permission to delete or to abandon the deadline.
                try:
                    if absent(call(["instances"]), target):
                        final.update(status="unexpected_absence_collection_unverified", absence_verified=True)
                        return 1
                except GuardError:
                    final["last_read_error"] = "transient_inventory_read_failed"
            time.sleep(max(0, min(POLL_SECONDS, remaining())))

        # Recheck identity both before collection and immediately before destruction.
        exact_instance(call(["show", instance_id]), target)
        try:
            if digest(read_private_source(manifest_path)) != manifest_sha:
                raise GuardError("collection_manifest_changed")
            collection = call(["m64-collect", instance_id, str(manifest_path), str(state_dir / "deadline-collection")], COLLECT_TIMEOUT)
            if not isinstance(collection, dict) or collection.get("operation") != "collect" or collection.get("job_id") != target["job_id"] or type(collection.get("instance_id")) is not int or collection["instance_id"] != target["instance_id"] or collection.get("manifest_sha256") != manifest_sha:
                raise GuardError("collection_receipt_mismatch")
            final["collection_verified"] = True
            final["retrieval_complete"] = collection.get("retrieval_complete") is True
        except GuardError as exc:
            final["collection_error"] = str(exc)
        exact_instance(call(["show", instance_id]), target)
        destroyed = call(["destroy", instance_id, "--confirm"], DESTROY_TIMEOUT)
        if not isinstance(destroyed, dict) or type(destroyed.get("instance_id")) is not int or destroyed["instance_id"] != target["instance_id"] or destroyed.get("destroyed") is not True or destroyed.get("verified_absent") is not True:
            raise GuardError("destruction_not_attested")
        if not absent(call(["instances"]), target):
            raise GuardError("absence_not_verified")
        final.update(status="deadline_destroyed_verified_absent", absence_verified=True)
        return 0 if final["collection_verified"] else 1
    except (GuardError, KeyboardInterrupt) as exc:
        final.update(status="guard_failed_attention_required", error=str(exc) if isinstance(exc, GuardError) else "guard_interrupted")
        return 1
    finally:
        write_receipt(state_dir / "final.json", final)
        print(json.dumps(final, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        return run_guard(args.manifest, args.state_dir)
    except (GuardError, OSError) as exc:
        # Do not expose filesystem errors, private wrapper output or secret data.
        print(json.dumps({"status": "guard_not_armed", "error": str(exc) if isinstance(exc, GuardError) else "local_state_error"}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
