"""Decode actual native STL coordinates, preserving the recorded local frame."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from translation import translate


def decode(case):
    plan = json.loads((case/"plan.json").read_text())
    source = case/"output/dilated-local.stl"
    out = case/"decoded-001"
    if out.exists():
        raise ValueError("Fresh output required")
    with source.open("rb") as stream:
        stream.read(80)
        count = struct.unpack("<I", stream.read(4))[0]
    if source.stat().st_size != 84 + 50*count:
        raise ValueError("Invalid binary STL size")
    dt = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    data = np.memmap(source, dtype=dt, mode="r", offset=84, shape=(count,))
    flat = np.ascontiguousarray(data["vertices"]).reshape(-1, 3)
    if not np.isfinite(flat).all():
        raise ValueError("Nonfinite native coordinates")
    local, inverse = np.unique(flat, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3)
    repeated = np.any(faces == np.roll(faces, 1, axis=1), axis=1)
    retained = faces[~repeated]
    for face in faces[repeated]:
        ids = np.unique(face)
        if len(ids) == 1:
            covered = np.any(retained == ids[0])
        else:
            covered = np.any(np.isin(retained, ids).sum(axis=1) == 2)
        if not covered:
            raise ValueError("Zero face image is not retained")
    # The independent exact kernel remains the final degeneracy/embedding check.
    zeros = []
    for start in range(0, len(retained), 250000):
        t = local[retained[start:start+250000]].astype(np.float64)
        bad = np.flatnonzero(np.all(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]) == 0, axis=1))
        zeros.extend((bad+start).tolist())
    if zeros:
        raise ValueError("Non-repeated collinear faces need an explicit partition proof")
    world, residual, translation_report = translate(local, plan["origin_mm"])
    out.mkdir()
    np.savez(out/"candidate.npz", vertices=world, triangles=retained)
    with (out/"candidate.meshbin").open("wb") as stream:
        stream.write(struct.pack("<QQ", len(world), len(retained)))
        world.astype("<f8").tofile(stream)
        retained.astype("<u8").tofile(stream)
    report = dict(status="native_output_decoded_independent_checks_pending", source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  source_faces=count, repeated_zero_faces_removed=int(repeated.sum()),
                  removed_face_images_covered=True, complete_cleanup_geometric_change_bound_mm=0,
                  exact_local_world_round_trip=translation_report["all_additions_exact"], translation=translation_report, vertices=len(world), faces=len(retained),
                  output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    if plan["scope"] == "analytical_cube_control":
        volume = 0.
        residual = 0.
        for start in range(0, len(retained), 250000):
            t = world[retained[start:start+250000]]
            volume += float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum()/6)
            centre = t.mean(axis=1)
            d = np.abs(centre)-1.
            sdf = np.linalg.norm(np.maximum(d, 0), axis=1)+np.minimum(d.max(axis=1), 0)
            cover = np.linalg.norm(t-centre[:, None, :], axis=2).max(axis=1)
            residual = max(residual, float((np.abs(sdf-plan["dilation_mm"])+cover).max()))
        error = abs(volume-plan["analytic_dilated_volume_mm3"])/plan["analytic_dilated_volume_mm3"]
        report.update(volume_mm3=volume, analytic_dilated_volume_mm3=plan["analytic_dilated_volume_mm3"], relative_volume_error=error,
                      complete_directed_signed_distance_residual_bound_mm=residual,
                      analytic_control_passed=bool(error < plan["maximum_relative_volume_error"] and residual < plan["complete_signed_distance_residual_limit_mm"]))
        if not report["analytic_control_passed"]:
            report["status"] = "analytical_dilation_control_refused"
    (out/"assessment.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    print(json.dumps(decode(parser.parse_args().case.resolve())))
