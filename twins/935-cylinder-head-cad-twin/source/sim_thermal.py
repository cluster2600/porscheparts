"""T3: steady thermal screen of the bare-head twin (Gmsh + CalculiX).

Runs inside the cadsim image (gmsh Python API, ccx 2.21). Every boundary
condition is a declared hypothesis, not a measured engine condition:
  * gas-side wall: fixed temperature on the combustion-chamber surface
    (boundary nodes within the chamber shoulder radius and below CHAMBER_Z);
  * every other external face: forced-air film coefficient and air temperature.
Units: mm, W, degC. Conductivity W/(mm K), film W/(mm^2 K).

Usage: sim_thermal.py (SURFACE.stl | TETS.npz) WORKDIR SIZE_MM [LABEL]
  .stl: Gmsh HXT meshes the closed surface (surface must be intersection-free)
  .npz: fTetWild tetrahedra from tetmesh.py are used as they are
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

CASE = {
    "material": "generic cast aluminium alloy (hypothesis; specimen alloy unknown)",
    "conductivity_W_per_mmK": 0.150,
    "chamber_wall_temperature_C": 220.0,
    "film_coefficient_W_per_mm2K": 80.0e-6,
    "air_temperature_C": 40.0,
    "chamber_radius_mm": 46.4,
    "chamber_z_max_mm": 30.0,
    "status": "declared hypotheses; uncorrelated with any engine measurement",
}

# Gmsh tetra face numbering -> CalculiX C3D4 face ids (S1..S4).
C3D4_FACES = {(0, 1, 2): 1, (0, 1, 3): 2, (1, 2, 3): 3, (0, 2, 3): 4}


def mesh(surface, work, size):
    import gmsh

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 8)
    gmsh.merge(str(surface))
    surf = gmsh.model.getEntities(2)
    loop = gmsh.model.geo.addSurfaceLoop([s[1] for s in surf])
    gmsh.model.geo.addVolume([loop])
    gmsh.model.geo.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.MeshSizeMin", size / 4)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT
    gmsh.option.setNumber("Mesh.Optimize", 1)
    t0 = time.time()
    gmsh.model.mesh.generate(3)
    tag, nodes, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tag)
    tag = np.asarray(tag)[order]
    xyz = nodes.reshape(-1, 3)[order]
    etypes, etags, enodes = gmsh.model.mesh.getElements(3)
    tets = np.asarray(enodes[list(etypes).index(4)], dtype=np.int64).reshape(-1, 4)
    etag = np.asarray(etags[list(etypes).index(4)], dtype=np.int64)
    q = gmsh.model.mesh.getElementQualities(etag.tolist(), "minSICN")
    gmsh.finalize()
    return tag.astype(np.int64), xyz, tets, np.asarray(q), time.time() - t0


def from_npz(path):
    d = np.load(path)
    v, t = d["v"], d["t"]
    p = v[t]
    vol = np.einsum("ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), p[:, 3] - p[:, 0]) / 6.0
    e = [p[:, b] - p[:, a] for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))]
    lrms = np.sqrt(sum((x * x).sum(axis=1) for x in e) / 6.0)
    q = 6.0 * np.sqrt(2.0) * vol / lrms ** 3
    return np.arange(1, len(v) + 1, dtype=np.int64), v, t.astype(np.int64) + 1, q


def boundary_faces(tets):
    """Faces used by exactly one tetrahedron: (element index, CalculiX face id, node tags)."""

    loc = list(C3D4_FACES.items())
    tri = np.concatenate([tets[:, list(l)] for l, _ in loc])
    elem = np.tile(np.arange(len(tets)), len(loc))
    fid = np.repeat([f for _, f in loc], len(tets))
    key = np.sort(tri, axis=1)
    _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    once = cnt[inv.ravel()] == 1
    return elem[once], fid[once], tri[once]


def write_inp(path, tag, xyz, tets, bfaces):
    c = CASE
    elem, fid, tri = bfaces
    p = xyz[np.searchsorted(tag, tri)].mean(axis=1)
    in_chamber = (np.hypot(p[:, 0], p[:, 1]) < c["chamber_radius_mm"]) & (p[:, 2] < c["chamber_z_max_mm"])
    chamber_nodes = np.unique(tri[in_chamber])
    film = list(zip(elem[~in_chamber] + 1, fid[~in_chamber]))
    with open(path, "w") as fh:
        fh.write("*HEADING\n935 bare-head twin steady thermal screen (hypothesis case)\n*NODE\n")
        for t, p in zip(tag, xyz):
            fh.write(f"{t},{p[0]:.6f},{p[1]:.6f},{p[2]:.6f}\n")
        fh.write("*ELEMENT,TYPE=C3D4,ELSET=EALL\n")
        for i, t in enumerate(tets):
            fh.write(f"{i + 1},{t[0]},{t[1]},{t[2]},{t[3]}\n")
        fh.write("*NSET,NSET=NCHAMBER\n")
        cn = chamber_nodes.tolist()
        for i in range(0, len(cn), 12):
            fh.write(",".join(map(str, cn[i:i + 12])) + "\n")
        fh.write("*MATERIAL,NAME=AL\n*CONDUCTIVITY\n%g\n" % c["conductivity_W_per_mmK"])
        fh.write("*SOLID SECTION,ELSET=EALL,MATERIAL=AL\n")
        fh.write("*INITIAL CONDITIONS,TYPE=TEMPERATURE\nNALL,%g\n" % c["air_temperature_C"])
        fh.write("*STEP\n*HEAT TRANSFER,STEADY STATE\n1.,1.\n")
        fh.write("*BOUNDARY\nNCHAMBER,11,11,%g\n" % c["chamber_wall_temperature_C"])
        fh.write("*FILM\n")
        for e, fid in film:
            fh.write(f"{e},F{fid},{c['air_temperature_C']:g},{c['film_coefficient_W_per_mm2K']:g}\n")
        fh.write("*NODE FILE\nNT\n*NODE PRINT,NSET=NCHAMBER,TOTALS=YES\nRFL\n*END STEP\n")
    return len(cn), len(film)


def read_frd_temperatures(frd):
    temps, on = [], False
    for line in open(frd):
        if line.startswith("    1PSTEP") or line.startswith(" -4  NDTEMP"):
            on = line.startswith(" -4  NDTEMP")
            continue
        if on and line.startswith(" -1"):
            temps.append(float(line[13:25]))
        elif on and line.startswith(" -3"):
            on = False
    return np.array(temps)


def main(surface, work, size, label="thermal"):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    size = float(size)
    if str(surface).endswith(".npz"):
        t0 = time.time()
        tag, xyz, tets, q = from_npz(surface)
        mesh_s, mesher, qname = time.time() - t0, "fTetWild (tetmesh.py)", "normalised_volume"
    else:
        tag, xyz, tets, q, mesh_s = mesh(surface, work, size)
        mesher, qname = "Gmsh HXT", "minSICN"
    bf = boundary_faces(tets)
    n_ch, n_film = write_inp(work / "head.inp", tag, xyz, tets, bf)
    t0 = time.time()
    run = subprocess.run(["ccx", "-i", "head"], cwd=work, capture_output=True, text=True,
                         env={"OMP_NUM_THREADS": "1", "CCX_NPROC_EQUATION_SOLVER": "1", "PATH": "/usr/bin:/bin"})
    solve_s = time.time() - t0
    (work / "ccx.log").write_text(run.stdout + run.stderr)
    temps = read_frd_temperatures(work / "head.frd") if (work / "head.frd").exists() else np.array([])
    vols = np.abs(np.einsum("ij,ij->i", np.cross(xyz[np.searchsorted(tag, tets[:, 1])] - xyz[np.searchsorted(tag, tets[:, 0])],
                                                  xyz[np.searchsorted(tag, tets[:, 2])] - xyz[np.searchsorted(tag, tets[:, 0])]),
                            xyz[np.searchsorted(tag, tets[:, 3])] - xyz[np.searchsorted(tag, tets[:, 0])])) / 6.0
    result = {
        "schema": "935-cad-twin-thermal/1",
        "label": label,
        "case": CASE,
        "mesh": {"mesher": mesher, "size_max_mm": size, "nodes": int(len(tag)), "tets": int(len(tets)),
                 "volume_mm3": round(float(vols.sum()), 1),
                 "quality_measure": qname,
                 "quality": {"min": round(float(q.min()), 4), "p1": round(float(np.percentile(q, 1)), 4),
                             "share_below_0p1": round(float((q < 0.1).mean()), 6),
                             "nonpositive": int((q <= 0).sum())},
                 "seconds": round(mesh_s, 1)},
        "boundary": {"chamber_nodes": n_ch, "film_faces": n_film},
        "solver": {"returncode": run.returncode, "seconds": round(solve_s, 1),
                   "ccx_version_line": next((l for l in run.stdout.splitlines() if "Version" in l), None)},
        "temperature_C": ({"min": round(float(temps.min()), 3), "max": round(float(temps.max()), 3),
                           "mean_nodal": round(float(temps.mean()), 3),
                           "p95": round(float(np.percentile(temps, 95)), 3)} if temps.size else None),
        "claims": "numerical screen under declared hypotheses; not an engine temperature prediction",
    }
    (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("mesh", "solver", "temperature_C")}))


if __name__ == "__main__":
    main(*sys.argv[1:5])
