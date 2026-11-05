#!/usr/bin/env python3
"""Run bounded local clipping with fixed inputs and distinguish construction hypotheses."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def basic_check(root):
    info = json.loads((root / "native.json").read_text())
    v = np.fromfile(root / "vertices.f64le", dtype="<f8").reshape(-1, 3)
    f = np.fromfile(root / "faces.i64le", dtype="<i8").reshape(-1, 3)
    assert len(v) == info["vertices"] and len(f) == info["triangles"]
    assert np.all(np.isfinite(v)) and np.all(f >= 0) and np.all(f < len(v))
    xyz = v[f]
    volume = np.einsum("ij,ij->i", xyz[:, 0], np.cross(xyz[:, 1], xyz[:, 2])).sum() / 6
    edge = np.concatenate((f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]))
    keys = (np.minimum(edge[:, 0], edge[:, 1]).astype(np.uint64) << np.uint64(32)) | np.maximum(edge[:, 0], edge[:, 1]).astype(np.uint64)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    assert len(keys) % 2 == 0 and np.all(keys[::2] == keys[1::2])
    assert np.all(keys[1:-1:2] != keys[2::2])
    directions = edge[:, 0] < edge[:, 1]
    assert np.all(directions[order[::2]] != directions[order[1::2]])
    return {"closed_oriented_edges": True, "signed_volume_mm3": float(volume)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("envelope", "parent-manifest", "plane-records", "plan", "executable", "source", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    root = args.output.resolve()
    plan = json.loads(args.plan.read_text())
    manifest = json.loads(args.parent_manifest.read_text())
    expected = [row for row in manifest["files"] if (args.parent_manifest.parent / row["path"]).resolve() == args.envelope.resolve()]
    if len(expected) != 1 or sha(args.envelope) != expected[0]["sha256"]:
        raise ValueError("Frozen parent envelope hash mismatch")
    if plan["stock_mm"] != 0.75:
        raise ValueError("Unexpected predeclared machining-stock hypothesis")
    shutil.copy2(args.executable, root / "clip-head")
    shutil.copy2(args.source, root / "clip_head.cpp")
    shutil.copy2(args.plan, root / "plan.json")
    shutil.copy2(args.plane_records, root / "source-plane-fits.json")
    write(root / "input-admission.json", {"parent_envelope_sha256": sha(args.envelope),
          "parent_manifest_sha256": sha(args.parent_manifest), "source_planes_sha256": sha(args.plane_records),
          "plan_sha256": sha(args.plan), "native_source_sha256": sha(args.source),
          "native_executable_sha256": sha(args.executable), "driver_sha256": sha(Path(__file__)),
          "input_admitted_for_declared_hypothesis": True, "input_accepted_as_physical_head": False})
    executable = root / "clip-head"
    controls = root / "controls"
    controls.mkdir()
    cube_v = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]], dtype="<f8")
    cube_f = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]], dtype="<i8")
    cube_v.tofile(controls / "vertices.f64le")
    cube_f.tofile(controls / "faces.i64le")
    (controls / "planes.txt").write_text("3\n1 0 0 -0.5\n0 -1 0 0.25\n0 0 1 -0.75\n")
    argv = [str(executable),str(controls / "vertices.f64le"),str(controls / "faces.i64le"),"8","12",str(controls / "planes.txt"),str(controls / "clipped")]
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    (controls / "native.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError("Native cube clipping failed")
    checked = basic_check(controls / "clipped")
    assert abs(checked["signed_volume_mm3"] - 0.28125) < 1e-12
    again = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    assert again.returncode != 0 and "Existing output refused" in again.stderr
    (controls / "outside.txt").write_text("1\n1 0 0 1\n")
    rejected = subprocess.run(argv[:-2] + [str(controls / "outside.txt"), str(controls / "outside-output")], capture_output=True, text=True, timeout=30)
    assert rejected.returncode != 0 and not (controls / "outside-output").exists()
    write(controls / "checks.json", {**checked, "three_plane_analytic_volume_matches": True,
          "existing_output_refused": True, "empty_outside_result_refused": True})
    plane_rows = {row["id"]: row for row in json.loads(args.plane_records.read_text())}
    coefficients = []
    semantic = []
    for name in plan["planes"]:
        row = plane_rows[name]
        normal = np.array(row["normal_xyz"], dtype=float)
        offset = row["offset_mm"]
        margin = plan["stock_mm"] * np.linalg.norm(normal)
        if name == "high_B_flange_candidate":
            values = [*normal, -(offset + margin)]
        else:
            values = [*(-normal), offset - margin]
        coefficients.append(values)
        semantic.append({"source_fit": name, "keep_negative_halfspace_coefficients": values,
                         "stock_mm": plan["stock_mm"], "physical_datum_accepted": False})
    (root / "planes.txt").write_text(str(len(coefficients)) + "\n" + "\n".join(" ".join(format(x,".17g") for x in p) for p in coefficients) + "\n")
    write(root / "private-construction-hypotheses.json", semantic)
    with np.load(args.envelope, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    vertices.astype("<f8").tofile(root / "input-vertices.f64le")
    faces.astype("<i8").tofile(root / "input-faces.i64le")
    argv = [str(executable),str(root / "input-vertices.f64le"),str(root / "input-faces.i64le"),str(len(vertices)),str(len(faces)),str(root / "planes.txt"),str(root / "candidate")]
    del vertices, faces
    begin = time.monotonic()
    peak = 0
    terminal = "running"
    with (root / "native-clipping.log").open("w") as log:
        child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        write(root / "running.json", {"pid":child.pid,"argv":argv,"wall_limit_s":1800,"rss_limit_gib":24})
        try:
            while child.poll() is None:
                time.sleep(2)
                usage = subprocess.run(["ps","-o","rss=","-p",str(child.pid)],capture_output=True,text=True)
                if usage.stdout.strip():
                    peak = max(peak, int(usage.stdout.strip()))
                if time.monotonic()-begin > 1800 or peak > 24*1024*1024:
                    terminal = "limit_exceeded"
                    os.killpg(child.pid, signal.SIGTERM)
                    break
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        if terminal == "running":
            terminal = "success" if child.returncode == 0 else "failed"
    report = {"stage":"hypothetical_bare_head_clipping","argv":argv,"exit_code":child.returncode,
              "terminal":terminal,"seconds":time.monotonic()-begin,"peak_rss_kib":peak,
              "log_sha256":sha(root / "native-clipping.log"),"new_paid_compute":False,
              "physical_acceptance":False,"manufacturing_release_authorized":False}
    write(root / "execution.json", report)
    print(json.dumps(report))
    if terminal != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
