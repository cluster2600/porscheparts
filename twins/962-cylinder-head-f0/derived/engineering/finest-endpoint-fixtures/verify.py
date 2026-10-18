"""Check the sealed tiny fixture payload and saved arrays without native execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def verify():
    receipt = json.loads((BASE / "receipt.json").read_text())
    expected = receipt["payload_sha256"]
    paths = list(BASE.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Symlink payload refused")
    if {str(p.relative_to(BASE)) for p in paths if p.is_file()} != set(expected) | {"receipt.json"}:
        raise ValueError("Exact sealed payload inventory required")
    for name, digest in expected.items():
        if hashlib.sha256((BASE / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Sealed payload changed: " + name)
    source = BASE / "source-snapshots/twins/962-cylinder-head-f0/source/check_finest_endpoint_fixtures.py"
    spec = importlib.util.spec_from_file_location("sealed_endpoint_fixture_oracle", source)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    cases = [
        ("common-neighbor-source001", "common-fixed-neighbor", "common-fixed-neighbor", False),
        ("common-neighbor-source002", "common-fixed-neighbor", "known-centered-cube", True),
        ("all-fixed-source002", "all-fixed-rotated", "all-fixed-rotated", False),
    ]
    recorded = json.loads((BASE / "fixture-array-assessment.json").read_text())["results"]
    for label, original, reference, improves in cases:
        directory = BASE / "data" / label
        checked = oracle.assess_arrays(
            oracle.read(BASE / "inputs" / (original + ".bin")),
            oracle.read(directory / "proposed-surface.bin"),
            oracle.read(BASE / "inputs" / (reference + ".bin")),
            (directory / "vertex-coordinate-origins.u64").read_bytes(),
        )
        oracle.require_native_flags(json.loads((directory / "report.json").read_text()), checked, improves)
        if checked != recorded[label]:
            raise ValueError("Retained full-array assessment differs: " + label)
        candidate = directory / "quality-candidate.bin"
        if candidate.exists() is not improves or (improves and candidate.read_bytes() != (directory / "proposed-surface.bin").read_bytes()):
            raise ValueError("Declared candidate/stagnation output differs: " + label)
    if receipt["fixture_reference_checks_passed"] is not True or receipt["head_execution_credited"] is not False:
        raise ValueError("Fixture-only scope required")
    return "Sealed payload and all three complete reference-array checks pass; no native execution."


if __name__ == "__main__":
    print(verify())
