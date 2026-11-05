"""Screen sampled inward normal chords; retain every ambiguity, never certify walls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def query(binary, vertices, faces, rows, output):
    output.mkdir()
    vertices.astype("<f8").tofile(output / "vertices.f64le")
    faces.astype("<i8").tofile(output / "faces.i64le")
    return query_files(binary, output / "vertices.f64le", output / "faces.i64le",
                       len(vertices), len(faces), rows, output)


def query_files(binary, vertices, faces, nv, nf, rows, output):
    with (output / "queries.txt").open("x") as stream:
        stream.write(str(len(rows)) + "\n")
        np.savetxt(stream, rows, fmt=["%d"] + ["%.17g"] * 6)
    command = [str(binary), str(vertices), str(faces), str(nv), str(nf),
               str(output / "queries.txt"), str(output / "hits.txt"), str(output / "native.json")]
    started = time.monotonic()
    with (output / "native.log").open("x") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    write(output / "execution.json", {"argv": command, "exit_code": result.returncode,
                                      "seconds": time.monotonic() - started})
    if result.returncode:
        raise RuntimeError("Native chord query failed; retained log must be inspected")
    return np.loadtxt(output / "hits.txt", ndmin=2), command


def brute_distance(vertices, faces, point, direction, skip):
    """Independent NumPy Moller-Trumbore search of every non-source triangle."""
    best = float("inf")
    for start in range(0, len(faces), 100000):
        xyz = vertices[faces[start:start + 100000]]
        e1, e2 = xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0]
        cross = np.cross(direction, e2)
        det = np.einsum("ij,ij->i", e1, cross)
        usable = np.abs(det) > 1e-14
        inverse = np.divide(1., det, out=np.zeros_like(det), where=usable)
        delta = point - xyz[:, 0]
        u = np.einsum("ij,ij->i", delta, cross) * inverse
        q = np.cross(delta, e1)
        v = (q @ direction) * inverse
        distance = np.einsum("ij,ij->i", e2, q) * inverse
        usable &= (u >= -1e-10) & (v >= -1e-10) & (u + v <= 1 + 1e-10) & (distance > 1e-9)
        if start <= skip < start + len(xyz):
            usable[skip - start] = False
        if np.any(usable):
            best = min(best, float(distance[usable].min()))
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("mesh", "geometry-report", "vertices", "faces", "binary", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    report = json.loads(args.geometry_report.read_text())
    expected = "05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert sha(args.mesh) == expected == report["input_sha256"]
    assert report["geometry_export_gate_passed"] and report["intersection_pairs"] == 0
    with np.load(args.mesh, allow_pickle=False) as data:
        vertices, faces = data["vertices"], data["triangles"]
    assert sha(args.vertices) == hashlib.sha256(vertices.astype("<f8").tobytes()).hexdigest()
    assert sha(args.faces) == hashlib.sha256(faces.astype("<i8").tobytes()).hexdigest()
    cube_v = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]], float)
    cube_f = np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    rows = np.array([[1,.2,.3,0,0,0,1],[1,.2,.3,0,.1,.1,1],[-1,2,2,2,1,0,0],[-1,0,0,0,1,0,0]], float)
    control, command = query(args.binary, cube_v, cube_f, rows, args.output / "cube")
    assert np.allclose(np.linalg.norm(control[:2,2:] - rows[:2,1:4],axis=1), [1,np.sqrt(1.02)], atol=1e-12,rtol=0)
    assert control[2,1] == -1
    segment_rows = np.array([[-1,.2,0,0,1,0,0]], float)
    segment, _ = query(args.binary, cube_v[:3], np.array([[0,1,2]]), segment_rows, args.output / "segment")
    assert segment[0,1] == -2
    repeated = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert repeated.returncode and "Existing output refused" in repeated.stderr
    thin_v = cube_v * [1,1,.03]
    thin, _ = query(args.binary, thin_v, cube_f, rows[:1], args.output / "thin")
    assert abs(thin[0,4] - .03) < 1e-12
    assert abs(brute_distance(cube_v,cube_f,rows[0,1:4],rows[0,4:],1)-1) < 1e-12
    controls = {"unit_cube": True, "oblique_cube": True, "miss": True,
                "segment_ambiguity": True, "thin_box": True, "existing_output_refused": True,
                "independent_moller_trumbore_cube": True}
    write(args.output / "controls.json", controls)
    double_area = np.empty(len(faces))
    for start in range(0,len(faces),100000):
        xyz = vertices[faces[start:start+100000]]
        double_area[start:start+len(xyz)] = np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)
    assert np.all(double_area > 0)
    rng = np.random.default_rng(935055)
    chosen = np.searchsorted(np.cumsum(double_area),rng.random(5000)*double_area.sum())
    xyz = vertices[faces[chosen]]
    uv = rng.random((len(chosen),2)); root = np.sqrt(uv[:,0])
    bary = np.column_stack([1-root,root*(1-uv[:,1]),root*uv[:,1]])
    points = np.einsum("ij,ijk->ik",bary,xyz)
    normals = np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]); normals /= np.linalg.norm(normals,axis=1)[:,None]
    directions = -normals
    actual = args.output / "head"; actual.mkdir()
    hits, _ = query_files(args.binary,args.vertices,args.faces,len(vertices),len(faces),
                          np.column_stack([chosen,points,directions]),actual)
    assert np.array_equal(hits[:,0],np.arange(len(chosen)))
    hit_ids = hits[:,1].astype(np.int64); valid = hit_ids >= 0
    distance = np.full(len(chosen),np.nan)
    distance[valid] = np.linalg.norm(hits[valid,2:]-points[valid],axis=1)
    hit_xyz = vertices[faces[hit_ids[valid]]]
    hit_normal = np.cross(hit_xyz[:,1]-hit_xyz[:,0],hit_xyz[:,2]-hit_xyz[:,0])
    exit_sign = np.einsum("ij,ij->i",hit_normal,directions[valid])
    forward = np.einsum("ij,ij->i",hits[valid,2:]-points[valid],directions[valid])
    ambiguous = valid.copy(); ambiguous[valid] = (distance[valid] <= 1e-8) | (exit_sign <= 0) | (forward <= 0)
    inspected = np.unique(np.r_[np.flatnonzero(valid)[np.argsort(distance[valid])[:8]],np.flatnonzero(valid)[::max(1,int(valid.sum())//8)][:8]])
    differences = []
    for i in inspected:
        value = brute_distance(vertices,faces,points[i],directions[i],chosen[i])
        differences.append(abs(value-distance[i]))
        assert np.isfinite(value) and abs(value-distance[i]) < 1e-6
    np.savez_compressed(args.output / "private-samples.npz", source_faces=chosen,barycentric=bary,points=points,
                        directions=directions,hit_faces=hit_ids,hit_points=hits[:,2:],distance_mm=distance,ambiguous=ambiguous)
    result = {"mesh_sha256":expected,"source_sha256":sha(Path(__file__)),"binary_sha256":sha(args.binary),
              "geometry_report_sha256":sha(args.geometry_report),"vertices_binary_sha256":sha(args.vertices),"faces_binary_sha256":sha(args.faces),
              "seed":935055,"samples":len(chosen),"sampling":"Area-weighted surface points; inward flat-face normals; source face skipped; no anatomical exclusions",
              "missed":int((hit_ids==-1).sum()),"nonpoint":int((hit_ids==-2).sum()),"ambiguous_hits":int(ambiguous.sum()),
              "all_point_hits_statistics_mm":{k:float(v) for k,v in zip(["minimum","p01","p05","median","p95","maximum"],np.quantile(distance[valid],[0,.01,.05,.5,.95,1]))},
              "point_hits_below_mm":{str(t):int((distance[valid]<t).sum()) for t in [.1,.25,.5,1,2]},
              "independent_full_triangle_search_rays":len(inspected),"independent_max_distance_difference_mm":max(differences),
              "controls":controls,"normal_chords_are_not_global_minimum_wall_or_metrology":True,
              "no_process_wall_threshold_selected":True,"physical_wall_acceptance":False,"manufacturing_qualified":False,
              "new_paid_compute_usd":0,"seconds":time.monotonic()-started}
    write(args.output / "report.json",result)
    print(json.dumps(result),flush=True)


if __name__ == "__main__":
    main()
