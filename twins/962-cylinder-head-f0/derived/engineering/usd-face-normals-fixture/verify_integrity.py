"""Capsule integrity and analytic reference consistency; no USD execution."""
import hashlib
import json
import math
from pathlib import Path
import struct


def verify(root):
    receipt = json.loads((root / "receipt.json").read_text())
    expected_files = set(receipt["payload_sha256"]) | {"receipt.json"}
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    if actual != expected_files or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("Payload closure or symlink refusal")
    for name, expected in receipt["payload_sha256"].items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe payload path")
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Payload hash mismatch: {name}")
    reference = json.loads((root / "fixture/expected-arrays.json").read_text())
    array_hashes = {}
    for name in ["points", "face_counts", "face_indices", "expected_normals"]:
        item = reference[name]
        values = item["values"]
        flat = [v for row in values for v in row] if isinstance(values[0], list) else values
        kind = "f" if item["dtype"] == "<f4" else "i"
        raw = struct.pack("<" + kind * len(flat), *flat)
        if raw.hex() != item["bytes_hex"]:
            raise ValueError(f"Reference values/bytes mismatch: {name}")
        array_hashes[name] = hashlib.sha256(raw).hexdigest()
    a = 1 + 2**-23
    v, length = 1 / math.sqrt(3), math.sqrt(1 + 2*a*a)
    analytic = [v, v, v, -v, -v, -v, 1/length, a/length, a/length, v, v, v, 0, 0, 1]
    if struct.pack("<15f", *analytic).hex() != reference["expected_normals"]["bytes_hex"]:
        raise ValueError("Independent analytic normal reference differs")
    known = json.loads((root / "reports/known-arrays.json").read_text())
    for stage in known["stages"]:
        wanted = dict(array_hashes)
        if stage["role"] == "source":
            wanted.pop("expected_normals")
        if stage["array_sha256"] != wanted or not stage["full_expected_bytes_equal"]:
            raise ValueError("Native report/reference inconsistency")
    peer = json.loads((root / "independent-review.json").read_text())
    projection = json.loads((root / "projections.json").read_text())
    shared = peer["final53_pin_projection"]["sha256"]
    if len(shared) != 53 or sum(len(v) for v in peer["original_capture_artifact_sha256"].values()) != 130:
        raise ValueError("Original inventory or deduplicated pin count differs")
    for stage in projection["executions"]:
        members = stage["pin_aliases_before_and_after"]
        if (len(members) != stage["input_count"] or len(set(members)) != len(members)
                or any(p not in shared for p in members) or not stage["all_pins_unchanged"]):
            raise ValueError("Projected full pin-map membership differs")
    if not receipt["software_fixture_only"] or receipt["head_or_physical_qualification"]:
        raise ValueError("Scope flags differ")
    return {"payload_files_verified": len(receipt["payload_sha256"]),
            "normal_components_checked": len(analytic), "native_USD_reopened": False}


if __name__ == "__main__":
    print(json.dumps(verify(Path(__file__).resolve().parent), sort_keys=True))
