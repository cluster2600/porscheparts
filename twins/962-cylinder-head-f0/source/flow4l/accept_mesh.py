"""Fail closed on OpenFOAM mesh quality before accepting any solver result."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def accept(case):
    log = (case / "log.checkMesh").read_text()
    if "Mesh OK." not in log or "Failed " in log or "FOAM FATAL" in log:
        raise ValueError("Mesh quality rejected; solver must not run")
    count = re.search(r"^\s*cells:\s+(\d+)\s*$", log, re.MULTILINE)
    if not count:
        raise ValueError("Missing cell count")
    boundary_path = case / "0/polyMesh/boundary"
    if not boundary_path.exists():
        boundary_path = case / "constant/polyMesh/boundary"
    boundary = boundary_path.read_text()
    for name, kind in (("inlet", "patch"), ("outlet", "patch"), ("walls", "wall")):
        match = re.search(r"\b" + name + r"\s*\{([^}]+)\}", boundary)
        if not match or not re.search(r"\btype\s+" + kind + r"\s*;", match[1]):
            raise ValueError("Invalid physical patch type: " + name)
        faces = re.search(r"\bnFaces\s+(\d+)\s*;", match[1])
        if not faces or int(faces[1]) == 0:
            raise ValueError("Empty physical patch: " + name)
    path = case / "mesh-report.json"
    if path.exists():
        raise ValueError("Do not replace a mesh receipt")
    files = [Path(__file__), case / "case-report.json", case / "log.checkMesh"]
    for folder in (case / "constant/polyMesh", case / "0/polyMesh"):
        if folder.exists(): files.extend(folder.iterdir())
    report = dict(status="mesh_numerical_gate_passed_not_physical_validation", cells=int(count[1]),
        source_hashes={str(p.relative_to(case)) if p.is_relative_to(case) else p.name:
                       hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},
        boundary_instance=str(boundary_path.relative_to(case)), manufacturing_authorized=False)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("case", type=Path)
    args = parser.parse_args(); accept(args.case.resolve())
