"""Scoped four-GPU extension, loaded by fingerprint inside the existing wrapper.

Authentication remains in openbao-vastai. Only this command's process adapts the
existing engine-twin launch/reconciliation primitives; legacy commands bypass it.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

PROFILE = "picogk-station-v1"
MODEL = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
REVISION = "c1209bda15a6bbc4c68b585e93d40c0d85f50306"
IMAGE_RE = re.compile(r"ghcr\.io/cluster2600/3dprinting993-picogk-m64@sha256:[0-9a-f]{64}")
LABEL_RE = re.compile(r"3dprinting993-picogk-station-[0-9a-f]{20}")
OPERATIONS = {"station-offers", "launch-station", "reconcile-station", "destroy-station", "station-show"}
HARDWARE = (("RTX PRO 6000 S", "RTX PRO 6000 WS", "RTX PRO 6000 Blackwell Max-Q"), 95000, 64, 512000, 1000)
PORTS = frozenset({"22/tcp", "47998/udp"})
MAX_SECONDS = 21600
MAX_BUDGET = 50.0
DOWNLOAD_GB = 500
UPLOAD_GB = 100
CLEANUP_USD = 2.0


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def specification(image):
    return {"image": image, "model": MODEL, "revision": REVISION, "hardware": HARDWARE,
            "num_gpus": 4, "max_dph": 10.0, "download_cap_gb": DOWNLOAD_GB,
            "ports": PORTS, "weights_access": "gated"}


def qualification_valid(proof):
    expected = {"platform": "linux/amd64", "anonymous_registry_verified": True,
                "gated_read_access_verified": True, "model": MODEL, "model_revision": REVISION}
    sizes = [proof.get(key) for key in ("image_download_bytes", "model_download_bytes")]
    return (IMAGE_RE.fullmatch(str(proof.get("image_ref"))) is not None
            and all(type(proof.get(key)) is type(value) and proof[key] == value for key, value in expected.items())
            and all(type(value) is int and value > 0 for value in sizes)
            and sum(sizes) * 2 + 10 * 10**9 <= DOWNLOAD_GB * 10**9
            and proof.get("published_ports") == sorted(PORTS))


def read_json(w, path, limit=65536):
    data = w["m64_read_file"](Path(path), limit)
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError):
        raise w["SafeError"]("station JSON is invalid") from None
    if not isinstance(value, dict):
        raise w["SafeError"]("station JSON must be an object")
    return value, hashlib.sha256(data).hexdigest()


def session(w, directory):
    value, _ = read_json(w, Path(directory) / "session.json")
    if (set(value) != {"profile", "created_epoch", "deadline_epoch", "budget_usd"}
        or value["profile"] != PROFILE or value["budget_usd"] != MAX_BUDGET
        or type(value["created_epoch"]) is not int or type(value["deadline_epoch"]) is not int
        or not 1800 <= value["deadline_epoch"] - value["created_epoch"] <= MAX_SECONDS
        or value["created_epoch"] > time.time()):
        raise w["SafeError"]("station fixed session bounds are invalid")
    return value


def reserved_cost(w, directory):
    # ponytail: never refund a reservation; add metered refunds only with billing evidence.
    total = 0.0
    for path in Path(directory).glob("station-*.paid-attempt.json"):
        receipt, _ = read_json(w, path)
        cost = receipt.get("cost_ceiling_usd")
        if not number(cost) or not 0 < cost <= MAX_BUDGET:
            raise w["SafeError"]("station paid-attempt reservation is missing or invalid")
        total += cost
    if total > MAX_BUDGET:
        raise w["SafeError"]("station cumulative reservations exceed USD 50")
    return total


def budget_cost(w, manifest, price, up, down):
    if (not number(price) or not 0 < price <= 10
        or any(not number(rate) or not 0 <= rate <= .01 for rate in (up, down))):
        raise w["SafeError"]("station hourly or transfer tariff exceeds its fixed cap")
    cost = price * (manifest["deadline_epoch"] - manifest["created_epoch"]) / 3600
    cost += down * DOWNLOAD_GB + up * UPLOAD_GB + CLEANUP_USD
    if cost > manifest["budget_usd"]:
        raise w["SafeError"]("station compute, storage, transfers and cleanup exceed the remaining budget")
    return cost


def prepare(w, operation, pins):
    name = operation[0]
    expected_length = (1, 2) if name == "station-offers" else ((3,) if name in {"launch-station", "destroy-station"} else (2,))
    if name not in OPERATIONS or len(operation) not in expected_length:
        raise w["SafeError"]("invalid bounded station command")
    if name == "station-offers" and len(operation) == 2 or name in {"launch-station", "destroy-station"}:
        w["positive_id"](operation[1], "station offer id")
    proof, proof_hash = read_json(w, pins["qualification_path"])
    if proof_hash != pins["qualification_sha256"] or not qualification_valid(proof):
        raise w["SafeError"]("station pinned image or weights qualification changed")
    if name == "station-offers":
        return {"proof": proof, "pins": pins}
    path = Path(operation[-1])
    directory = Path(pins["session_directory"])
    if path.parent != directory:
        raise w["SafeError"]("station manifest must belong to the installed session directory")
    manifest, digest = read_json(w, path)
    required = {"schema_version", "profile", "role", "variant", "job_id", "attempt_label", "sibling_label",
                "image_ref", "model", "model_revision", "created_epoch", "deadline_epoch", "budget_usd",
                "download_budget_gb", "upload_budget_gb", "qualification_path", "qualification_sha256",
                "guard_path", "guard_sha256", "guard_ready_path", "guard_service_name"}
    bounds = session(w, directory)
    if (set(manifest) != required or manifest["schema_version"] != "1.0.0" or manifest["profile"] != PROFILE
        or manifest["role"] != "llm" or manifest["variant"] != PROFILE or manifest["sibling_label"] != ""
        or not LABEL_RE.fullmatch(str(manifest["attempt_label"]))
        or manifest["job_id"] != "station-" + manifest["attempt_label"].rsplit("-", 1)[1]
        or path.name != manifest["job_id"] + ".json"
        or manifest["guard_service_name"] != "com.3dprinting993." + manifest["job_id"]
        or manifest["image_ref"] != proof["image_ref"]
        or manifest["model"] != MODEL or manifest["model_revision"] != REVISION
        or type(manifest["created_epoch"]) is not int or type(manifest["deadline_epoch"]) is not int
        or not bounds["created_epoch"] <= manifest["created_epoch"] <= time.time()
        or not manifest["created_epoch"] + 1800 <= manifest["deadline_epoch"] <= bounds["deadline_epoch"]
        or not number(manifest["budget_usd"]) or not 0 < manifest["budget_usd"] <= MAX_BUDGET
        or manifest["download_budget_gb"] != DOWNLOAD_GB or manifest["upload_budget_gb"] != UPLOAD_GB
        or any(manifest[key] != pins[key] for key in ("qualification_path", "qualification_sha256", "guard_path", "guard_sha256"))
        or manifest["guard_ready_path"] != str(directory / (manifest["job_id"] + ".guard-ready.json"))):
        raise w["SafeError"]("station manifest differs from the installed immutable contract")
    if hashlib.sha256(w["m64_read_file"](Path(pins["guard_path"]), 65536)).hexdigest() != pins["guard_sha256"]:
        raise w["SafeError"]("station guard source changed")
    if name == "launch-station" and time.time() >= manifest["deadline_epoch"] - 1500:
        raise w["SafeError"]("station setup and cleanup allowance exhausted")
    return {"manifest": {**manifest, "_manifest_path": str(path)}, "digest": digest, "proof": proof, "pins": pins}


def install_policy(w, bundle):
    """Reuse the reviewed engine-twin lifecycle only for one station CLI process."""
    spec = specification(bundle["proof"]["image_ref"])
    w["engine_twin_spec"] = lambda role, variant=None: spec
    w["ENGINE_TWIN_PROFILE"] = PROFILE
    w["engine_twin_budget_cost"] = lambda manifest, price, up, down: budget_cost(w, manifest, price, up, down)
    # The station owns one rental and has no permitted background sibling.
    w["engine_twin_singleton"] = w["picogk_singleton"]


def run(w, api_key, operation, bundle):
    install_policy(w, bundle)
    name = operation[0]
    if name == "station-offers":
        offers = w["get_engine_twin_offers"](api_key, "llm", int(operation[1]) if len(operation) == 2 else None, PROFILE)
        w["print_json"]([w["safe_offer"](offer) for offer in offers[:20]])
        return 0
    manifest, digest, pins = bundle["manifest"], bundle["digest"], bundle["pins"]
    if name in {"reconcile-station", "destroy-station"}:
        expected_id = int(operation[1]) if name == "destroy-station" else None
        created_path = Path(pins["session_directory"]) / (manifest["job_id"] + ".provider-created.json")
        if created_path.exists():
            created, _ = read_json(w, created_path)
            identifier = created.get("instance_id")
            if (type(identifier) is not int or identifier <= 0 or created.get("manifest_sha256") != digest
                or created.get("label") != manifest["attempt_label"] or created.get("image_ref") != manifest["image_ref"]
                or expected_id is not None and expected_id != identifier):
                raise w["SafeError"]("station cleanup ID differs from its exact provider-created receipt")
            expected_id = identifier
        proof = w["engine_twin_reconcile"](api_key, manifest, digest, expected_instance_id=expected_id)
        # Preserve the launcher's cleanup receipt even when it recorded an
        # earlier uncertain outcome; verified absence is a separate fact.
        path = Path(pins["session_directory"]) / (manifest["job_id"] + ".verified-absence.json")
        receipt = {**proof, "manifest_sha256": digest, "label": manifest["attempt_label"], "image_ref": manifest["image_ref"]}
        if path.exists():
            previous, _ = read_json(w, path)
            if previous != receipt:
                raise w["SafeError"]("station previous absence receipt differs from this ownership proof")
        else:
            write_json(path, receipt)
        w["print_json"](proof)
        return 0
    if name == "station-show":
        receipt, _ = read_json(w, Path(pins["session_directory"]) / (manifest["job_id"] + ".paid-attempt.json"))
        if receipt.get("manifest_sha256") != digest:
            raise w["SafeError"]("station inspection requires its exact paid attempt")
        matches = [raw for raw in w["strict_instance_inventory"](api_key) if raw.get("label") == manifest["attempt_label"]]
        if len(matches) != 1 or matches[0].get("image_uuid") != manifest["image_ref"]:
            raise w["SafeError"]("station inspection ownership is not unique")
        w["print_json"](w["picogk_safe_instance"](matches[0]))
        return 0
    original_consume = w["picogk_consume_attempt"]
    original_guard = w["research_verify_guard"]

    def guard_ready(m, sha):
        original_guard(m, sha)
        ready, _ = read_json(w, m["guard_ready_path"])
        service = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{m['guard_service_name']}"],
                                 capture_output=True, text=True, timeout=10)
        if service.returncode or not re.search(r"\bpid = " + str(ready["pid"]) + r"\b", service.stdout):
            raise w["SafeError"]("station destruction guard is not managed by its persistent LaunchAgent")

    def consume(m, sha, offer_id):
        directory = pins["session_directory"]
        offers = w["get_engine_twin_offers"](api_key, "llm", offer_id, PROFILE)
        if len(offers) != 1:
            raise w["SafeError"]("station offer disappeared before reservation")
        offer = offers[0]
        cost = budget_cost(w, m, offer["dph_total"], offer["inet_up_cost"], offer["inet_down_cost"])
        already_reserved = reserved_cost(w, directory)
        if already_reserved + cost > MAX_BUDGET or m["budget_usd"] > MAX_BUDGET - already_reserved:
            raise w["SafeError"]("station cumulative paid attempts exceed USD 50")
        # O_EXCL consumes the paid attempt before PUT. Complete its reservation
        # atomically before returning; any interruption leaves fail-closed state.
        path = original_consume(m, sha, offer_id)
        receipt, _ = read_json(w, path)
        receipt["cost_ceiling_usd"] = cost
        write_json(path, receipt, replace=True)
        return path

    w["research_verify_guard"] = guard_ready
    w["picogk_consume_attempt"] = consume
    return w["launch_engine_twin"](api_key, int(operation[1]), manifest, digest)


def write_json(path, value, *, replace=False):
    path = Path(path)
    target = path.with_name(path.name + ".tmp") if replace else path
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        os.replace(target, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
