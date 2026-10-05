#!/usr/bin/env python3
"""Verify published bytes and their links to recorded native CAD checks."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODES = {
    "SelfInterMode", "SmallEdgeMode", "RebuildFaceMode",
    "ContinuityMode", "CurveOnSurfaceMode",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = json.loads((ROOT / "delivery-manifest.json").read_text())
    expected = set()
    for row in manifest["files"]:
        relative = Path(row["path"])
        require(not relative.is_absolute() and ".." not in relative.parts,
                "manifest_path_outside_delivery")
        path = ROOT / relative
        require(path.is_file(), f"missing:{relative}")
        require(path.stat().st_size == row["bytes"], f"size_mismatch:{relative}")
        require(digest(path) == row["sha256"], f"digest_mismatch:{relative}")
        require(path.suffix.lower() != ".obj", "raw_scan_in_delivery")
        expected.add(relative.as_posix())
    actual = {
        p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    } - {"delivery-manifest.json"}
    require(actual == expected, "unlisted_or_missing_delivery_file")
    proof = json.loads((ROOT / "checks/additional-checks.json").read_text())
    for name, result in proof["native_BOP"].items():
        require(set(result["modes"]) == MODES, f"incomplete_native_modes:{name}")
        require(result["passed"] and result["BRep_valid"], f"native_check_failed:{name}")
        require(not any(result[k] for k in ("has_faulty", "has_errors", "has_warnings")),
                f"native_faults:{name}")
        require(result["input_sha256"] == digest(ROOT / "cad" / (name + ".step")),
                f"native_proof_does_not_bind_delivered_STEP:{name}")
    report = json.loads((ROOT / "checks/verification.json").read_text())
    require(all(v is False for v in report["release"].values()), "physical_release_claim")
    for name, result in report["geometry"].items():
        require(result["STEP_sha256"] == digest(ROOT / "cad" / (name + ".step")),
                f"STEP_report_mismatch:{name}")
        if "STL_sha256" in result:
            require(result["STL_sha256"] == digest(ROOT / "cad" / (name + "-concept-only.stl")),
                    f"STL_report_mismatch:{name}")
    require(manifest["raw_scan_distributed"] is False, "raw_scan_publication_claim")
    require(manifest["private_source_CAD_distributed"] is False, "source_CAD_publication_claim")
    print(f"Delivery verified: {len(expected)} files; recorded native checks bind delivered STEP bytes.")
    print("Physical scale, fit, thermal/structural performance and manufacturing remain unvalidated.")


if __name__ == "__main__":
    main()
