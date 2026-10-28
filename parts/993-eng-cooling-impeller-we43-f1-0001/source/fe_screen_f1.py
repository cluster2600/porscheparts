#!/usr/bin/env python3
"""3D finite-element screen of the F1 cooling impeller: centrifugal stress and
rotation-prestressed modes (Campbell diagram), WE43, gmsh C3D10 + CalculiX.

The engineering screen (cooling_impeller_f1.py) checks the rotor with beam and
ring formulas, and its modal pass is a single blade as a cantilever. This
screen meshes the whole rotor from its STEP and asks the two questions those
formulas cannot answer: where the stress concentrates (windows, bolt holes,
blade roots) and where the cup/web modes sit against the engine orders.

    python3 fe_screen_f1.py benchmark WORKDIR
    python3 fe_screen_f1.py rotor STEP WORKDIR --size 3.0 [--size-min 1.2]
    python3 fe_screen_f1.py report WORKDIR... --out evidence/fe-screen/fe-screen.json

Run it in the cadsim image (gmsh 4.15, CalculiX 2.21). CalculiX is forced to
one thread: multi-threaded SPOOLES has returned wrong solutions on this
project (see the CalculiX memory notes in the 964 FEA README).

Units: mm, N, tonne, s, MPa. Every boundary condition is an assumption: the
joint between the rotor and its bearing hub is not measured.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cooling_impeller_f1 as f1  # noqa: E402

WE43 = f1.MATERIALS[f1.PRIMARY_MATERIAL]
RHO = WE43["density_kg_m3"] * 1e-12          # t/mm3
E_MPA = WE43["elastic_modulus_pa"] * 1e-6
NU = 0.27                                     # generic magnesium, assumption
YIELD_MPA = WE43["yield_strength_pa"] * 1e-6
SPEEDS_RPM = [0, 3000, 6000, 8500, 10000, 12000]
MODES = 24
BORE_R = f1.HUB_BORE_DIAMETER_MM / 2.0
WEB_T = f1.HUB_WEB_THICKNESS_MM
CUP_R = f1.HUB_OUTER_DIAMETER_MM / 2.0
CUP_IN = CUP_R - f1.HUB_RIM_THICKNESS_MM
BOLT_RC = f1.BOLT_CIRCLE_RADIUS_MM
BOLT_RH = f1.BOLT_HOLE_RADIUS_MM
BLADES = f1.BLADE_COUNT
# Assumed bearing-hub contact: the hub (64 mm, FVD commercial envelope) clamps
# the web's z = 0 face between the bore and its own radius.
HUB_CONTACT_R = 32.0
# Stationary excitations: engine orders 1-4, the six housing spokes and their
# second harmonic, the
# 17-vane stator (case with stator).
EXCITATION_ORDERS = [1, 2, 3, 4, 6, 12, 17]
# Blade-root refinement. On the rotor as published the eleven blades cross the
# rim outer face in 37 curves: blade 0 is unrotated and shares the cylinder's
# parametric seam, so its root splits into 7 against 3 for each of the other
# ten. A blended root has a different count, so what is asserted is the
# invariant that holds for both: the curves fall into one cluster per blade.
ROOT_CURVE_COUNT = 37
ROOT_FIELD_SAMPLING = 400
ROOT_FIELD_DIST_MIN = 1.0
ROOT_FIELD_DIST_MAX = 8.0
ENV = dict(os.environ, OMP_NUM_THREADS="1", CCX_NPROC_EQUATION_SOLVER="1", CCX_NPROC_STIFFNESS="1")


# ---------------------------------------------------------------- meshing

def root_curve_tags(gmsh):
    """Tags of the curves where the blades cross the rim outer face (r = CUP_R).

    These are the blade-root junctions. The two full rim circles lie on the
    same cylinder and are excluded by their constant z."""
    import numpy as np
    tags = []
    for _dim, tag in gmsh.model.getEntities(1):
        try:
            t0, t1 = gmsh.model.getParametrizationBounds(1, tag)
        except Exception:
            continue
        ts = [t0[0] + (t1[0] - t0[0]) * k / 8.0 for k in range(9)]
        pts = np.array(gmsh.model.getValue(1, tag, ts)).reshape(-1, 3)
        if np.max(np.abs(np.hypot(pts[:, 0], pts[:, 1]) - CUP_R)) > 0.25:
            continue
        if np.ptp(pts[:, 2]) < 1e-6:
            continue
        tags.append(tag)
    return tags


def root_curve_clusters(gmsh, tags):
    """The blade indices the given root curves belong to.

    The refinement is only comparable between geometries if it reaches every
    blade, so the selection is checked against the blade count rather than
    against a curve count that the blend changes."""
    import numpy as np
    seen = set()
    for tag in tags:
        t0, t1 = gmsh.model.getParametrizationBounds(1, tag)
        p = np.array(gmsh.model.getValue(1, tag, [0.5 * (t0[0] + t1[0])])).reshape(3)
        a = math.degrees(math.atan2(p[1], p[0])) % 360.0
        seen.add(round(a / (360.0 / BLADES)) % BLADES)
    return sorted(seen)


def mesh_step(step, out, size, size_min, root_size=None):
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 4)
    gmsh.model.occ.importShapes(str(step))
    gmsh.model.occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.MeshSizeMin", min(size_min, root_size) if root_size else size_min)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 16)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    if root_size:
        # Local refinement around the blade roots only: the rest of the rotor
        # keeps the baseline sizing, so the ladder isolates the root.
        curves = root_curve_tags(gmsh)
        clusters = root_curve_clusters(gmsh, curves)
        if len(clusters) != BLADES:
            raise SystemExit(f"blade-root curves cover {len(clusters)} of {BLADES} blades "
                             f"({len(curves)} curves found)")
        dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(dist, "CurvesList", curves)
        gmsh.model.mesh.field.setNumber(dist, "Sampling", ROOT_FIELD_SAMPLING)
        th = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(th, "InField", dist)
        gmsh.model.mesh.field.setNumber(th, "SizeMin", root_size)
        gmsh.model.mesh.field.setNumber(th, "SizeMax", size)
        gmsh.model.mesh.field.setNumber(th, "DistMin", ROOT_FIELD_DIST_MIN)
        gmsh.model.mesh.field.setNumber(th, "DistMax", ROOT_FIELD_DIST_MAX)
        gmsh.model.mesh.field.setAsBackgroundMesh(th)
    gmsh.model.mesh.generate(3)
    gmsh.model.mesh.optimize("Netgen")
    gmsh.option.setNumber("Mesh.HighOrderOptimize", 1)
    gmsh.model.mesh.setOrder(2)
    nodes, coords = _gmsh_nodes(gmsh)
    types, _tags, enodes = gmsh.model.mesh.getElements(3)
    if list(types) != [11]:      # 10-node tetrahedra only
        raise SystemExit(f"unexpected element types {list(types)}")
    tets = enodes[0].reshape(-1, 10)
    gmsh.finalize()
    return nodes, coords, tets


def _gmsh_nodes(gmsh):
    import numpy as np
    tags, xyz, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tags)
    return tags[order], xyz.reshape(-1, 3)[order]


def mesh_primitive(kind, size, size_min):
    """Benchmark solids: an annular disc and a cantilever plate."""
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    occ = gmsh.model.occ
    if kind == "disc":
        outer = occ.addCylinder(0, 0, 0, 0, 0, WEB_T, CUP_R)
        inner = occ.addCylinder(0, 0, -1, 0, 0, WEB_T + 2, BORE_R)
        occ.cut([(3, outer)], [(3, inner)])
    else:
        occ.addBox(0, 0, 0, 60.0, 20.0, 3.0)
    occ.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", size)
    gmsh.option.setNumber("Mesh.MeshSizeMin", size_min)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.model.mesh.generate(3)
    nodes, coords = _gmsh_nodes(gmsh)
    _t, _tags, enodes = gmsh.model.mesh.getElements(3)
    tets = enodes[0].reshape(-1, 10)
    gmsh.finalize()
    return nodes, coords, tets


# ------------------------------------------------------------ CalculiX deck

def write_mesh(path, nodes, coords, tets):
    # gmsh and CalculiX share the C3D10 node order except the last two
    # mid-side nodes (gmsh 9-10 are edges 3-4 and 2-4; CalculiX 9-10 are 2-4 and 3-4).
    with open(path, "w") as f:
        f.write("*NODE, NSET=Nall\n")
        for n, (x, y, z) in zip(nodes, coords):
            f.write(f"{int(n)},{x:.6f},{y:.6f},{z:.6f}\n")
        f.write("*ELEMENT, TYPE=C3D10, ELSET=Eall\n")
        for i, e in enumerate(tets, 1):
            e = [int(v) for v in e]
            e[8], e[9] = e[9], e[8]
            f.write(f"{i}," + ",".join(map(str, e)) + "\n")


def read_mesh(path):
    """Inverse of write_mesh (back to gmsh node order)."""
    import numpy as np
    nodes, coords, tets, mode = [], [], [], None
    for line in open(path):
        if line.startswith("*"):
            mode = "n" if line.startswith("*NODE") else "e"
            continue
        v = line.split(",")
        if mode == "n":
            nodes.append(int(v[0]))
            coords.append([float(x) for x in v[1:4]])
        else:
            e = [int(x) for x in v[1:11]]
            e[8], e[9] = e[9], e[8]
            tets.append(e)
    return np.array(nodes), np.array(coords), np.array(tets)


def nset(name, ids):
    ids = sorted(int(i) for i in ids)
    if not ids:
        raise SystemExit(f"empty node set {name}")
    lines = [",".join(map(str, ids[i:i + 12])) for i in range(0, len(ids), 12)]
    return f"*NSET, NSET={name}\n" + "\n".join(lines) + "\n"


MATERIAL = (f"*MATERIAL, NAME=WE43\n*ELASTIC\n{E_MPA:.6g},{NU}\n*DENSITY\n{RHO:.6g}\n"
            "*SOLID SECTION, ELSET=Eall, MATERIAL=WE43\n")


def deck(work, sets, fixed, rpm, modes, extra_bc=""):
    bc = "*BOUNDARY\n" + "".join(f"{s},1,3\n" for s in fixed) + extra_bc
    head = f"*INCLUDE, INPUT=mesh.inp\n{sets}{MATERIAL}{bc}"
    if rpm:
        w2 = (rpm * math.pi / 30.0) ** 2
        static = (f"*STEP, NLGEOM\n*STATIC\n*DLOAD\nEall,CENTRIF,{w2:.10g},0,0,0,0,0,1\n"
                  "*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n")
    else:
        static = ""
    freq = ""
    if modes:
        freq = (("*STEP, PERTURBATION\n" if rpm else "*STEP\n") +
                f"*FREQUENCY\n{modes}\n*NODE FILE\nU\n*END STEP\n")
    name = f"rpm{rpm:05d}"
    (work / f"{name}.inp").write_text(head + static + freq)
    return name


def run_ccx(work, name):
    t = time.time()
    with open(work / f"{name}.log", "w") as log:
        r = subprocess.run(["ccx", "-i", name], cwd=work, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    if r.returncode or "Job finished" not in (work / f"{name}.log").read_text():
        raise SystemExit(f"ccx {name} failed, see {work / (name + '.log')}")
    return time.time() - t


# ------------------------------------------------------------- frd reading

def read_frd(path):
    """Return the list of result blocks: (name, {node: values})."""
    blocks, cur, name = [], None, None
    with open(path) as f:
        for line in f:
            if line.startswith(" -4"):
                name = line.split()[1]
                cur = {}
            elif line.startswith(" -1") and cur is not None:
                n = int(line[3:13])
                vals = [float(line[13 + 12 * i:25 + 12 * i]) for i in range((len(line.rstrip()) - 13) // 12)]
                cur[n] = vals
            elif line.startswith(" -3") and cur is not None:
                blocks.append((name, cur))
                cur = None
    return blocks


def von_mises(s):
    xx, yy, zz, xy, yz, zx = s[:6]
    return math.sqrt(0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3 * (xy * xy + yz * yz + zx * zx))


def read_frequencies(dat):
    text = Path(dat).read_text().split("E I G E N V A L U E   O U T P U T")
    if len(text) < 2:
        raise SystemExit(f"no eigenvalues in {dat}")
    freqs = []
    for line in text[-1].splitlines():
        parts = line.split()
        if len(parts) == 5 and parts[0].isdigit():
            freqs.append(float(parts[3]))
        elif freqs and not parts:
            break
    return freqs


# --------------------------------------------------------------- the rotor

def region(x, y, z):
    r = math.hypot(x, y)
    if r > CUP_R + 0.5:
        return "blade"
    if z <= WEB_T + 0.5 and r < CUP_IN - 0.5:
        if math.hypot(r - BOLT_RC, 0) < BOLT_RH + 3.0 and _near_bolt(x, y) < BOLT_RH + 3.0:
            return "web_bolt_hole"
        if r < BORE_R + 3.0:
            return "web_bore"
        if abs(r - f1.VENT_RADIUS_MM) < f1.VENT_RADIAL_HALFWIDTH_MM + 3.0:
            return "web_window"
        return "web"
    return "cup_rim"


def _near_bolt(x, y):
    best = 1e9
    for k in range(f1.BOLT_COUNT):
        a = 2 * math.pi * k / f1.BOLT_COUNT
        best = min(best, math.hypot(x - BOLT_RC * math.cos(a), y - BOLT_RC * math.sin(a)))
    return best


def rotor_sets(nodes, coords, case):
    import numpy as np
    x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]
    r = np.hypot(x, y)
    bolt = np.zeros(len(nodes), bool)
    for k in range(f1.BOLT_COUNT):
        a = 2 * math.pi * k / f1.BOLT_COUNT
        d = np.hypot(x - BOLT_RC * math.cos(a), y - BOLT_RC * math.sin(a))
        bolt |= (np.abs(d - BOLT_RH) < 0.05) & (z > -0.01) & (z < WEB_T + 0.01)
    face = (np.abs(z) < 1e-3) & (r <= HUB_CONTACT_R) & (r >= BORE_R - 0.01)
    bore = (np.abs(r - BORE_R) < 0.05) & (z > -0.01) & (z < WEB_T + 0.01)
    if case == "clamped":
        fixed = bolt | face
    elif case == "bore":
        fixed = bore
    else:
        raise SystemExit(case)
    tip = r > f1.blade_tip_radius_mm() - 3.0
    lip = (np.abs(r - CUP_R) < 0.3) & (z > f1.CUP_DEPTH_MM - 1.0)
    return {"FIXED": nodes[fixed], "TIP": nodes[tip], "LIP": nodes[lip]}


def ring_phase(ids, coords_by_node, count):
    """Angle of the first of `count` identical features (circular mean of count*theta)."""
    c = sum(math.cos(count * math.atan2(coords_by_node[n][1], coords_by_node[n][0])) for n in ids)
    s = sum(math.sin(count * math.atan2(coords_by_node[n][1], coords_by_node[n][0])) for n in ids)
    return math.atan2(s, c) / count


def nodal_diameter(ids, coords_by_node, disp, bins, phase=0.0):
    """Dominant nodal diameter of the axial displacement sampled on a ring:
    nodes are grouped into `bins` sectors centred on `phase` + k 2 pi / bins."""
    acc = [0.0] * bins
    cnt = [0] * bins
    for n in ids:
        x, y, _ = coords_by_node[n]
        b = round((math.atan2(y, x) - phase) / (2 * math.pi) * bins) % bins
        acc[b] += disp[n][2]
        cnt[b] += 1
    w = [a / c if c else 0.0 for a, c in zip(acc, cnt)]
    amp = []
    for k in range(bins // 2 + 1):
        re = sum(v * math.cos(2 * math.pi * k * i / bins) for i, v in enumerate(w))
        im = sum(v * math.sin(2 * math.pi * k * i / bins) for i, v in enumerate(w))
        amp.append(math.hypot(re, im))
    k = max(range(len(amp)), key=amp.__getitem__)
    return k, amp


def rotor(args):
    import numpy as np
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    t = time.time()
    previous = json.loads((work / "result.json").read_text()) if (work / "result.json").exists() else None
    if (work / "mesh.inp").exists():
        # Resume: keep the mesh the earlier speeds were solved on.
        nodes, coords, tets = read_mesh(work / "mesh.inp")
    else:
        nodes, coords, tets = mesh_step(args.step, work, args.size, args.size_min,
                                        getattr(args, "root_size", None))
        write_mesh(work / "mesh.inp", nodes, coords, tets)
    mesh_s = previous["mesh_seconds"] if previous else time.time() - t
    sets = rotor_sets(nodes, coords, args.case)
    sets_txt = "".join(nset(k, v) for k, v in sets.items())
    vol = _tet_volume(coords, tets, nodes)
    cbn = {int(n): c for n, c in zip(nodes, coords)}
    tip_ids = [int(n) for n in sets["TIP"]]
    lip_ids = [int(n) for n in sets["LIP"]]
    fixed_xyz = coords[np.isin(nodes, sets["FIXED"])]
    tip_phase = ring_phase(tip_ids, cbn, BLADES)
    out = {"case": args.case, "size_mm": args.size, "size_min_mm": args.size_min,
           "root_size_mm": getattr(args, "root_size", None),
           "nodes": int(len(nodes)), "elements": int(len(tets)), "volume_mm3": vol,
           "mass_g": vol * RHO * 1e6, "fixed_nodes": int(len(sets["FIXED"])),
           "mesh_seconds": mesh_s, "speeds": previous["speeds"] if previous else []}
    done = {s["rpm"] for s in out["speeds"]}
    for rpm in SPEEDS_RPM if not args.speeds else args.speeds:
        if rpm in done:
            continue
        name = deck(work, sets_txt, ["FIXED"], rpm, args.modes)
        sec = run_ccx(work, name)
        blocks = read_frd(work / f"{name}.frd")
        rec = {"rpm": rpm, "solve_seconds": sec,
               "frequencies_hz": read_frequencies(work / f"{name}.dat") if args.modes else []}
        disp_blocks = [b for n, b in blocks if n == "DISP"]
        if rpm:
            stress = [b for n, b in blocks if n == "STRESS"][0]
            u0 = disp_blocks[0]
            rec.update(_static_summary(stress, u0, cbn, fixed_xyz))
        modes = disp_blocks[-len(rec["frequencies_hz"]):]
        rec["modes"] = []
        for f, d in zip(rec["frequencies_hz"], modes):
            kt, _ = nodal_diameter(tip_ids, cbn, d, BLADES, tip_phase)
            kl, _ = nodal_diameter(lip_ids, cbn, d, 36)
            blade_u = max(math.dist((0, 0, 0), d[n][:3]) for n in tip_ids)
            lip_u = max(math.dist((0, 0, 0), d[n][:3]) for n in lip_ids)
            rec["modes"].append({"hz": f, "nd_blade_tips": kt, "nd_cup_lip": kl,
                                 "tip_to_lip_amplitude": blade_u / max(lip_u, 1e-30)})
        out["speeds"].append(rec)
        f1_txt = f"{rec['frequencies_hz'][0]:.0f} Hz" if rec["frequencies_hz"] else "-"
        print(f"{args.case} {args.size} mm {rpm} rpm: {sec:.0f} s, f1 = {f1_txt}"
              + (f", peak {rec['peak_von_mises_mpa']:.1f} MPa ({rec['peak_region']})" if rpm else ""), flush=True)
        (work / f"{name}.frd").unlink()
        out["speeds"].sort(key=lambda s: s["rpm"])
        (work / "result.json").write_text(json.dumps(out, indent=1))


def _tet_volume(coords, tets, nodes):
    import numpy as np
    idx = {int(n): i for i, n in enumerate(nodes)}
    c = np.array([[coords[idx[int(v)]] for v in e[:4]] for e in tets])
    return float(np.abs(np.einsum("ij,ij->i", c[:, 1] - c[:, 0], np.cross(c[:, 2] - c[:, 0], c[:, 3] - c[:, 0]))).sum() / 6.0)


def _static_summary(stress, disp, cbn, fixed_xyz):
    import numpy as np
    from scipy.spatial import cKDTree
    tree = cKDTree(fixed_xyz)
    by_region, by_region_far = {}, {}
    for n, s in stress.items():
        vm = von_mises(s)
        x, y, z = cbn[n]
        reg = region(x, y, z)
        if vm > by_region.get(reg, (0,))[0]:
            by_region[reg] = (vm, n)
        if tree.query((x, y, z))[0] > 3.0 and vm > by_region_far.get(reg, (0,))[0]:
            by_region_far[reg] = (vm, n)
    peak_reg = max(by_region, key=lambda k: by_region[k][0])
    peak_far = max(by_region_far, key=lambda k: by_region_far[k][0])
    tip_growth = max(
        (u[0] * cbn[n][0] + u[1] * cbn[n][1]) / math.hypot(cbn[n][0], cbn[n][1])
        for n, u in disp.items() if math.hypot(cbn[n][0], cbn[n][1]) > f1.blade_tip_radius_mm() - 1.0)
    umax = max(math.sqrt(u[0] ** 2 + u[1] ** 2 + u[2] ** 2) for u in disp.values())
    loc = lambda n: [round(v, 2) for v in cbn[n]]
    return {
        "peak_von_mises_mpa": by_region[peak_reg][0], "peak_region": peak_reg,
        "peak_location_mm": loc(by_region[peak_reg][1]),
        "peak_von_mises_3mm_from_constraints_mpa": by_region_far[peak_far][0],
        "peak_region_3mm_from_constraints": peak_far,
        "peak_location_3mm_from_constraints_mm": loc(by_region_far[peak_far][1]),
        "peak_by_region_mpa": {k: v[0] for k, v in sorted(by_region.items())},
        "peak_by_region_3mm_from_constraints_mpa": {k: v[0] for k, v in sorted(by_region_far.items())},
        "max_displacement_mm": umax, "blade_tip_radial_growth_mm": tip_growth,
    }


# ----------------------------------------------------------- benchmarks

def benchmark(args):
    import numpy as np
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    res = {}
    # 1. Free annular disc spinning at 12,000 rpm, plane stress.
    d = work / "disc"
    d.mkdir(exist_ok=True)
    nodes, coords, tets = mesh_primitive("disc", 2.5, 1.0)
    write_mesh(d / "mesh.inp", nodes, coords, tets)
    x, y, z = coords.T
    bottom = nodes[np.abs(z) < 1e-6]
    ix = nodes[np.argmin(np.hypot(x - CUP_R, y) + np.abs(z))]
    iy = nodes[np.argmin(np.hypot(x, y - CUP_R) + np.abs(z))]
    sets = nset("BOTTOM", bottom) + nset("NX", [ix]) + nset("NY", [iy])
    bc = "NX,2,2\nNY,1,1\n"
    (d / "disc.inp").write_text(
        f"*INCLUDE, INPUT=mesh.inp\n{sets}{MATERIAL}*BOUNDARY\nBOTTOM,3,3\n{bc}"
        f"*STEP\n*STATIC\n*DLOAD\nEall,CENTRIF,{(12000 * math.pi / 30) ** 2:.10g},0,0,0,0,0,1\n"
        "*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n")
    run_ccx(d, "disc")
    blocks = dict(read_frd(d / "disc.frd"))
    w = 12000 * math.pi / 30
    a, b = BORE_R, CUP_R
    analytic = (3 + NU) / 4 * RHO * w * w * (b * b + (1 - NU) / (3 + NU) * a * a)
    hoop = []
    for n, s in blocks["STRESS"].items():
        i = int(np.searchsorted(nodes, n))
        xx, yy = coords[i][:2]
        r = math.hypot(xx, yy)
        if abs(r - a) < 0.05:
            c, sn = xx / r, yy / r
            hoop.append(s[0] * sn * sn + s[1] * c * c - 2 * s[3] * sn * c)
    fe = float(np.mean(hoop))
    res["spinning_disc_bore_hoop"] = {"analytic_mpa": analytic, "fe_mean_mpa": fe,
                                      "relative_error": fe / analytic - 1, "nodes": int(len(nodes))}
    # 2. Cantilever plate 60 x 20 x 3 mm, first bending mode.
    p = work / "plate"
    p.mkdir(exist_ok=True)
    nodes, coords, tets = mesh_primitive("plate", 1.5, 0.75)
    write_mesh(p / "mesh.inp", nodes, coords, tets)
    root = nodes[np.abs(coords[:, 0]) < 1e-6]
    (p / "plate.inp").write_text(
        f"*INCLUDE, INPUT=mesh.inp\n{nset('ROOT', root)}{MATERIAL}*BOUNDARY\nROOT,1,3\n"
        "*STEP\n*FREQUENCY\n3\n*END STEP\n")
    run_ccx(p, "plate")
    f_fe = read_frequencies(p / "plate.dat")[0]
    L, bw, t = 60.0, 20.0, 3.0
    eb = 1.87510407 ** 2 / (2 * math.pi) * math.sqrt(E_MPA * bw * t ** 3 / 12 / (RHO * bw * t * L ** 4))
    res["cantilever_plate_first_mode"] = {"euler_bernoulli_hz": eb, "fe_hz": f_fe,
                                          "relative_error": f_fe / eb - 1, "nodes": int(len(nodes))}
    # 3. Same plate solved twice: SPOOLES on one thread must repeat exactly.
    run_ccx(p, "plate")
    res["cantilever_plate_first_mode"]["repeat_hz"] = read_frequencies(p / "plate.dat")[0]
    (work / "benchmark.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


# --------------------------------------------------------------- variant

RIB_WIDTH_MM = 3.4       # rebuild rib: 1.7 mm half-width (picogk-reference/Program.cs)
RIB_HEIGHT_MM = 6.0      # rebuild rib: 6 mm above the web
RIB_INNER_R_MM = 32.0    # rebuild rib starts at r 32
GUSSET_MM = 6.0          # web-to-rim corner, 45 deg triangle


def variant(args):
    """F1 with the rebuild's web stiffeners restored: twelve radial ribs on the
    inner web face between the windows, and a gusset ring in the web-to-rim
    corner. Blades, cup, windows, bolt holes and bore are unchanged."""
    from build123d import Align, Box, Polyline, Pos, Rot, Axis, make_face, revolve, export_step
    body = f1.build_geometry()
    rim_in = CUP_IN
    length = rim_in - RIB_INNER_R_MM + 1.0      # 1 mm into the rim
    rib = Box(length, RIB_WIDTH_MM, RIB_HEIGHT_MM, align=(Align.MIN, Align.CENTER, Align.MIN))
    for k in range(f1.VENT_COUNT):
        angle = (k + 0.5) * 360.0 / f1.VENT_COUNT     # windows sit at k * 30 deg
        body = body + Rot(0, 0, angle) * Pos(RIB_INNER_R_MM, 0, WEB_T - 0.5) * rib
    tri = make_face(Polyline((rim_in + 0.5, 0, WEB_T - 0.5), (rim_in - GUSSET_MM, 0, WEB_T - 0.5),
                             (rim_in + 0.5, 0, WEB_T + GUSSET_MM), close=True))
    body = body + revolve(tri, Axis.Z, 360)
    if not body.is_valid:
        raise SystemExit("variant solid is not valid")
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out = work / "f1-ribbed.step"
    export_step(body, str(out))
    base = f1.build_geometry().volume
    print(json.dumps({"step": str(out), "volume_mm3": body.volume, "added_mm3": body.volume - base,
                      "added_mass_g": (body.volume - base) * RHO * 1e6}))


# ------------------------------------------------- root mesh convergence

ROOT_CONV_TOL = 0.02        # successive relative change accepted as converged


def rootconv(args):
    """Peak stress against blade-root element size.

    A re-entrant corner with no blend has no finite peak stress: the exact
    solution is singular there, so the computed peak rises without limit as
    the mesh is refined and no value of it is a stress. This command measures
    that rise, and for a blended root measures whether the peak settles.

    The fitted exponent is the slope of log(peak) against log(1/h). It is
    about zero for a convergent peak and positive for a singular one."""
    runs = []
    for w in args.work:
        d = json.loads((Path(w) / "result.json").read_text())
        speeds = [s for s in d["speeds"] if s["rpm"] == args.rpm]
        if not speeds:
            raise SystemExit(f"{w} has no {args.rpm} rpm result")
        s0 = speeds[0]
        runs.append({"work": str(w), "root_size_mm": d.get("root_size_mm") or d["size_min_mm"],
                     "root_refined": d.get("root_size_mm") is not None,
                     "nodes": d["nodes"], "elements": d["elements"],
                     "peak_von_mises_mpa": s0["peak_von_mises_mpa"],
                     "peak_region": s0["peak_region"],
                     "peak_location_mm": s0["peak_location_mm"],
                     "peak_by_region_mpa": s0["peak_by_region_mpa"]})
    runs.sort(key=lambda r: -r["root_size_mm"])
    # The ladder is the refined family alone: an unrefined baseline sits on a
    # different sizing and cannot be a step in it.
    refined = [r for r in runs if r["root_refined"]]
    baseline = [r for r in runs if not r["root_refined"]]
    for a, b in zip(refined, refined[1:]):
        b["relative_change"] = (b["peak_von_mises_mpa"] - a["peak_von_mises_mpa"]) / a["peak_von_mises_mpa"]
    slope = None
    if len(refined) >= 2:
        xs = [math.log(1.0 / r["root_size_mm"]) for r in refined]
        ys = [math.log(r["peak_von_mises_mpa"]) for r in refined]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        den = sum((x - mx) ** 2 for x in xs)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None
    changes = [abs(r["relative_change"]) for r in refined if "relative_change" in r]
    converged = bool(changes) and all(c <= ROOT_CONV_TOL for c in changes[-2:]) and len(changes) >= 2
    out = {"rpm": args.rpm, "geometry": args.geometry,
           "convergence_tolerance": ROOT_CONV_TOL,
           "runs": refined, "unrefined_baseline": baseline,
           "fitted_log_log_slope": slope,
           "peak_converged": converged,
           "note": ("the peak settles within the tolerance" if converged else
                    "the peak does not settle: no converged peak stress exists for this geometry"),
           "yield_mpa": YIELD_MPA}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1))
    for r in baseline:
        print(f"  baseline (no root refinement, size_min {r['root_size_mm']:.2f} mm): "
              f"elements={r['elements']:7d}  peak={r['peak_von_mises_mpa']:7.2f} MPa ({r['peak_region']})")
    for r in refined:
        ch = f"{r['relative_change']:+7.2%}" if "relative_change" in r else "      -"
        print(f"  h={r['root_size_mm']:4.2f} mm  elements={r['elements']:7d}  "
              f"peak={r['peak_von_mises_mpa']:7.2f} MPa ({r['peak_region']})  {ch}")
    print(f"log-log slope {slope if slope is None else round(slope, 4)}  converged={converged}")


# ---------------------------------------------------------- root fillet

ROOT_FILLET_MM = 1.0        # blade-root blend radius of the filleted variant
BLEND_AREA_REL_TOL = 1e-3   # blade-to-blade agreement of the blend surface, relative
BLEND_RADIUS_TOL = 1e-3     # mm, median blend curvature radius vs the request


def _root_edges(solid):
    """The blade-root edges: on the rim outer cylinder, excluding its two
    circles (which have constant z)."""
    rim_circ = 2.0 * math.pi * CUP_R
    out = []
    for e in solid.edges():
        try:
            pts = [e.position_at(t) for t in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
        except Exception:
            continue
        if max(abs(math.hypot(p.X, p.Y) - CUP_R) for p in pts) > 0.25:
            continue
        if abs(e.length - rim_circ) < 1.0:
            continue
        out.append(e)
    return out


def _blend_faces(solid):
    """The blend surfaces a root fillet adds: free-form faces centred on the
    rim radius. The base rotor has none there."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    out = []
    for face in solid.faces():
        a = BRepAdaptor_Surface(face.wrapped)
        if str(a.GetType()).split("_")[-1] != "BSplineSurface":
            continue
        c = face.center()
        if abs(math.hypot(c.X, c.Y) - CUP_R) < 3.0:
            out.append(face)
    return out


def _blend_curvature_radii(faces):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepLProp import BRepLProp_SLProps
    radii = []
    for b in faces:
        a = BRepAdaptor_Surface(b.wrapped)
        u0, u1 = a.FirstUParameter(), a.LastUParameter()
        v0, v1 = a.FirstVParameter(), a.LastVParameter()
        for i in range(1, 4):
            for j in range(1, 4):
                p = BRepLProp_SLProps(a, u0 + (u1 - u0) * i / 4.0, v0 + (v1 - v0) * j / 4.0, 2, 1e-6)
                if not p.IsCurvatureDefined():
                    continue
                for cv in (p.MaxCurvature(), p.MinCurvature()):
                    if abs(cv) > 1e-9:
                        radii.append(abs(1.0 / cv))
    return sorted(r for r in radii if r < 50.0)


def blade_of_edge(e, count):
    a = math.degrees(math.atan2(e.position_at(0.5).Y, e.position_at(0.5).X)) % 360.0
    return round(a / (360.0 / count)) % count


def build_root_fillet(radius):
    """F1 with a constant-radius blend at the eleven blade roots.

    Acceptance is measured on the blend *surface*, never on the solid volume:
    the eleven sequential blade unions leave a tolerance drift of order
    10 mm3 in `Solid.volume`, which is the same size as the fillet itself, so
    a volume difference cannot decide whether the blend is right. The blend
    area and its curvature radius are local and do decide it.

    The blend runs out where the blade's leading and trailing edges meet the
    rim, and those terminations are much sharper than the nominal radius (at
    r = 1 mm the sampled minimum is about 0.03 mm). A radius the root cannot
    take makes those terminations fold over: at 2 mm the blend surfaces
    self-intersect and gmsh refuses the solid ("a segment and a facet
    intersect"), while every radius up to 1.5 mm meshes as imported. No OCC
    healing is used to get round this - `Geometry.OCCSewFaces` in particular
    discards the volume outright and yields an empty mesh that looks like a
    successful `generate(3)`."""
    from build123d import fillet
    import collections
    body = f1.build_geometry()
    edges = _root_edges(body)
    if len(edges) != ROOT_CURVE_COUNT:
        raise SystemExit(f"found {len(edges)} blade-root edges, expected {ROOT_CURVE_COUNT}")
    filleted = fillet(edges, radius)
    if not filleted.is_valid or len(filleted.solids()) != 1:
        raise SystemExit("root fillet did not produce one valid solid")
    blends = _blend_faces(filleted)
    radii = _blend_curvature_radii(blends)
    if not radii:
        raise SystemExit("root fillet produced no measurable blend curvature")
    median = radii[len(radii) // 2]
    if abs(median - radius) > BLEND_RADIUS_TOL:
        raise SystemExit(f"blend median curvature radius {median:.4f} != requested {radius}")
    # Independent symmetry check: the eleven blades are identical by
    # construction, so one blade's blend must reproduce across all of them.
    groups = collections.defaultdict(list)
    for e in edges:
        groups[blade_of_edge(e, BLADES)].append(e)
    per_blade = {}
    for k in sorted(groups):
        one = fillet(groups[k], radius)
        per_blade[k] = sum(f.area for f in _blend_faces(one))
    spread = max(per_blade.values()) - min(per_blade.values())
    mean_area = sum(per_blade.values()) / len(per_blade)
    # Relative, because OCC's own surface integration carries a small absolute
    # error that grows with the blend area; blade 0 is unrotated and its root
    # is split into a different number of faces, which moves the area between
    # faces without changing the blend.
    relative = spread / mean_area
    if relative > BLEND_AREA_REL_TOL:
        raise SystemExit(f"blend area varies by {relative:.2e} relative "
                         f"({spread:.6f} mm2) between identical blades")
    return filleted, {
        "radius_mm": radius,
        "blend_faces": len(blends),
        "blend_area_mm2": sum(f.area for f in blends),
        "blend_curvature_radius_median_mm": median,
        "blend_curvature_radius_min_mm": radii[0],
        "blend_curvature_radius_max_mm": radii[-1],
        "per_blade_blend_area_mm2": {str(k): v for k, v in per_blade.items()},
        "per_blade_blend_area_spread_mm2": spread,
        "per_blade_blend_area_relative_spread": relative,
    }


def rootfillet(args):
    from build123d import export_step
    solid, checks = build_root_fillet(args.radius)
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out = work / f"f1-rootfillet-{args.radius:g}mm.step"
    export_step(solid, str(out))
    checks["step"] = str(out)
    print(json.dumps(checks, indent=1))


# --------------------------------------------------------------- report

def nd_matches(order, mode):
    """A stationary disturbance of engine order `order` drives nodal diameter
    `order` in the continuous cup, and +-order modulo the blade count on the
    eleven blades."""
    k = order % BLADES
    return mode["nd_cup_lip"] == order or mode["nd_blade_tips"] in (k, (BLADES - k) % BLADES)


def crossings(run):
    """Engine-order crossings of each mode branch (branches followed by sorted
    index; veering between close modes is not tracked)."""
    speeds = run["speeds"]
    out = []
    for i in range(min(len(s["frequencies_hz"]) for s in speeds)):
        for order in EXCITATION_ORDERS:
            for a, b in zip(speeds, speeds[1:]):
                ga = a["frequencies_hz"][i] - order * a["rpm"] / 60.0
                gb = b["frequencies_hz"][i] - order * b["rpm"] / 60.0
                if ga > 0 >= gb:
                    rpm = a["rpm"] + (b["rpm"] - a["rpm"]) * ga / (ga - gb)
                    near = a if rpm - a["rpm"] < b["rpm"] - rpm else b
                    m = near["modes"][i]
                    out.append({"mode_index": i + 1, "engine_order": order, "rpm": round(rpm),
                                "hz": round(order * rpm / 60.0, 1), "nd_cup_lip": m["nd_cup_lip"],
                                "nd_blade_tips": m["nd_blade_tips"], "nodal_diameter_matched": nd_matches(order, m)})
    return sorted(out, key=lambda c: c["rpm"])


def report(args):
    runs = [json.loads((Path(w) / "result.json").read_text()) for w in args.work]
    bench = json.loads(Path(args.benchmark).read_text())
    step = Path(args.step)
    import hashlib
    out = {
        "schema_version": 1,
        "part_id": f1.PART_ID,
        "status": "screen_unvalidated",
        "method": "gmsh 4.15 second-order tetrahedra (C3D10), CalculiX 2.21 single-thread SPOOLES; "
                  "NLGEOM static under CENTRIF, then *FREQUENCY in a PERTURBATION step (stress-stiffened modes)",
        "geometry": {"step": str(step), "sha256": hashlib.sha256(step.read_bytes()).hexdigest(),
                     "note": "functional F1 CAD; the published PicoGK bionic variant is not analysed here"},
        "material": {"name": "WE43 LPBF T6 (comparison)", "density_kg_m3": WE43["density_kg_m3"],
                     "modulus_gpa": E_MPA / 1e3, "poisson": NU, "yield_mpa": YIELD_MPA,
                     "basis": "engineering-screen values; Poisson 0.27 generic magnesium assumption"},
        "boundary_conditions": {
            "clamped": f"web face z = 0 bonded to the bearing hub from the bore (r {BORE_R} mm) to r {HUB_CONTACT_R} mm, "
                       "plus the three bolt-hole bores, all DOF fixed. Assumption: hub contact radius from the "
                       "FVD 64 mm hub envelope; the real joint (bolt preload, friction, hub stiffness) is not modelled",
            "bore": "the bore surface fixed, all DOF (the boundary of the 2026-10-03 rebuild alloy comparison)",
        },
        "solver_benchmarks": bench,
        "excitation_orders": {"orders": EXCITATION_ORDERS,
                              "basis": "1-4 engine orders; 6 housing spokes and their 12th-order harmonic; 17 stator vanes (with stator)"},
        "runs": [],
        "limits": [
            "boundary conditions are assumptions: the bolted joint is idealised as bonded or as a fixed bore",
            "linear elastic, no plasticity, room-temperature WE43 coupon data, no notch, HCF or creep allowable",
            "mode branches are followed by sorted index; crossings near veering modes may be misattributed",
            "Coriolis (gyroscopic) splitting of forward and backward travelling waves is not computed",
            "aerodynamic and alternator loads, temperature and bolt preload are not applied",
            "one mesh (4 mm, 1.5 mm minimum, about 164,000 nodes): mesh independence is not demonstrated; the "
            "peak sits at the unfilleted blade-root/rim corner of the CAD, where it can grow with refinement",
            "the PicoGK bionic web and the ribbed variant (fe_screen_f1.py variant) are not analysed here",
        ],
        "mesh_independence_demonstrated": False,
        "manufacturing_authorized": False,
        "engine_operation_authorized": False,
    }
    for run in runs:
        rec = {k: run[k] for k in ("case", "size_mm", "size_min_mm", "nodes", "elements", "volume_mm3", "mass_g")}
        rec["speeds"] = run["speeds"]
        rec["engine_order_crossings"] = crossings(run)
        top = [s for s in run["speeds"] if s["rpm"]]
        worst = max(top, key=lambda s: s["rpm"])
        rec["at_max_speed"] = {
            "rpm": worst["rpm"],
            "peak_von_mises_mpa": worst["peak_von_mises_mpa"],
            "peak_region": worst["peak_region"],
            "yield_over_peak": YIELD_MPA / worst["peak_von_mises_mpa"],
            "peak_away_from_constraints_mpa": worst["peak_von_mises_3mm_from_constraints_mpa"],
            "yield_over_peak_away_from_constraints": YIELD_MPA / worst["peak_von_mises_3mm_from_constraints_mpa"],
            "blade_tip_radial_growth_mm": worst["blade_tip_radial_growth_mm"],
        }
        out["runs"].append(rec)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    if args.plot:
        plot(runs, Path(args.plot))


def plot(runs, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(runs), figsize=(6.2 * len(runs), 5.2), squeeze=False)
    for ax, run in zip(axes[0], runs):
        rpm = [s["rpm"] for s in run["speeds"]]
        n = min(len(s["frequencies_hz"]) for s in run["speeds"])
        for i in range(n):
            # blade-dominated when the blade tips move 3x more than the cup lip
            blade = run["speeds"][0]["modes"][i]["tip_to_lip_amplitude"] > 3.0
            ax.plot(rpm, [s["frequencies_hz"][i] for s in run["speeds"]], "-o", ms=3, lw=1.2,
                    color="#c05621" if blade else "#2f5d8a",
                    label=("blade modes" if blade else "cup / web modes"))
        top = max(rpm)
        for order in EXCITATION_ORDERS:
            ax.plot([0, top], [0, order * top / 60.0], "--", lw=0.9, color="#718096")
            y = order * top / 60.0
            if y < 3500:
                ax.text(top, y, f" {order}E", va="center", fontsize=8, color="#4a5568")
        for c in crossings(run):
            if c["nodal_diameter_matched"] and c["mode_index"] % 2:
                ax.plot(c["rpm"], c["hz"], "o", ms=9, mfc="none", mec="#c53030", mew=1.6)
                ax.annotate(f"{c['engine_order']}E x ND{c['nd_blade_tips']}\n{c['rpm']:,} rpm",
                            (c["rpm"], c["hz"]), xytext=(-8, 10), textcoords="offset points",
                            ha="right", fontsize=7.5, color="#c53030",
                            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
        handles, labels = ax.get_legend_handles_labels()
        uniq = dict(zip(labels, handles))
        ax.legend(uniq.values(), uniq.keys(), loc="upper left", fontsize=8, framealpha=0.9)
        ax.axvspan(0, 10000, color="#2f855a", alpha=0.06, lw=0)
        ax.set_xlim(0, top * 1.08)
        ax.set_ylim(0, 3500)
        ax.set_xlabel("fan speed, rpm")
        ax.set_ylabel("frequency, Hz")
        ax.set_title(f"F1 WE43, {run['case']} hub ({run['mass_g']:.0f} g), {run['size_mm']:g} mm mesh", fontsize=10)
        ax.grid(alpha=0.25)
    fig.suptitle("Campbell diagram, stress-stiffened modes. Red: frequency and nodal diameter both match\n"
                 "Shaded: 0-10,000 rpm nominal range. Screen only, not a validated vibration analysis", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("benchmark")
    b.add_argument("work")
    r = sub.add_parser("rotor")
    r.add_argument("step")
    r.add_argument("work")
    r.add_argument("--case", choices=["clamped", "bore"], default="clamped")
    r.add_argument("--size", type=float, default=3.0)
    r.add_argument("--size-min", type=float, default=1.2)
    r.add_argument("--root-size", type=float,
                   help="local element size at the blade-root junction (mm)")
    r.add_argument("--speeds", type=int, nargs="*")
    r.add_argument("--modes", type=int, default=MODES, help="0: static only")
    p = sub.add_parser("report")
    p.add_argument("work", nargs="+")
    p.add_argument("--step", required=True)
    p.add_argument("--benchmark", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--plot")
    v = sub.add_parser("variant")
    v.add_argument("work")
    rc = sub.add_parser("rootconv")
    rc.add_argument("work", nargs="+")
    rc.add_argument("--rpm", type=int, default=12000)
    rc.add_argument("--geometry", default="f1-as-published")
    rc.add_argument("--out", required=True)
    rf = sub.add_parser("rootfillet")
    rf.add_argument("work")
    rf.add_argument("--radius", type=float, default=ROOT_FILLET_MM)
    a = ap.parse_args()
    {"benchmark": benchmark, "rotor": rotor, "report": report, "variant": variant,
     "rootfillet": rootfillet, "rootconv": rootconv}[a.cmd](a)


if __name__ == "__main__":
    main()
