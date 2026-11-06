"""Prepare a new English F34b context without rewriting historical evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


GENERATION = Path(__file__).resolve().parent
ROOT = GENERATION.parents[1]
MANIFEST = "twins/reference-917-engine/evidence/f34/doe-case-manifest.json"
SEEDS = "twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json"
GENERATOR = "scripts/run_917_doe_f34.py"


def differences(old, new, path=()):
    if type(old) is not type(new):
        return {path}
    if isinstance(old, dict):
        if old.keys() != new.keys():
            return {path}
        return set().union(*(differences(old[k], new[k], path + (k,)) for k in old))
    if isinstance(old, list):
        if len(old) != len(new):
            return {path}
        return set().union(*(differences(a, b, path + (i,)) for i, (a, b) in enumerate(zip(old, new))))
    return set() if old == new else {path}


def prepare(destination):
    destination = destination.absolute()
    if destination.is_symlink() or destination.exists():
        raise ValueError("context destination must not exist")
    destination = destination.resolve()
    if destination.is_relative_to(ROOT):
        raise ValueError("context must be outside the repository")
    inputs = json.loads((GENERATION / "inputs.lock.json").read_text())
    # Validate every input before creating any output.
    contents = {}
    for entry in inputs["files"]:
        source = ROOT / entry["source"]
        target = Path(entry["target"])
        if target.is_absolute() or ".." in target.parts:
            raise ValueError("unsafe context target")
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT):
            raise ValueError("unsafe context source")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"source hash mismatch: {entry['source']}")
        if target in contents:
            raise ValueError("duplicate context target")
        contents[target] = data
    destination.mkdir(mode=0o700)
    for target, data in contents.items():
        output = destination / target
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
    for script, output in ((GENERATOR, MANIFEST), ("scripts/export_917_air_oil_seeds_f34b.py", SEEDS)):
        subprocess.run([sys.executable, str(destination / script), "--output", str(destination / output)], check=True, cwd=destination)
    allowed = {
        MANIFEST: {("generator", "script_sha256")},
        SEEDS: {("$comment",), ("bundle_payload_sha256",), ("parents", 2, "sha256"), ("parents", 3, "sha256")},
    }
    outputs = {}
    for relative, expected in allowed.items():
        historical = json.loads((ROOT / relative).read_text())
        generated = json.loads((destination / relative).read_text())
        changed = differences(historical, generated)
        if changed != expected:
            raise ValueError(f"unexpected generation changes in {relative}: {changed}")
        data = (destination / relative).read_bytes()
        outputs[relative] = {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
    receipt = {
        "schema_version": 1,
        "inputs_lock_sha256": hashlib.sha256((GENERATION / "inputs.lock.json").read_bytes()).hexdigest(),
        "outputs": outputs,
        "numerical_inputs_and_authority_unchanged": True,
        "canonical_doe_cases_executed": 0,
        "physical_qualification": False,
    }
    (destination / "generation.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.destination), indent=2, sort_keys=True))
