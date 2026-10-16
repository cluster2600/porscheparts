"""Linear buckling of the picogk/ monocoque walls, in torsion and bending.

The layups of this folder are ASSUMED thin: 2.0 mm skin, 2.5 mm section
walls, 1.2 mm sandwich faces. The stiffness studies cannot see whether
such walls buckle first; this asks it of the same shell model (S6, CFRP
layup F0), under the two load cases already in place:

- torsion: torsion.solve()'s rear clamp and +/-1 kN at the front
  wheel-house tops (1.14 kN.m);
- bending: bending.load_case(), 2 kN on the sills at mid-wheelbase.

CalculiX *BUCKLE returns the lowest factors lambda such that lambda times
the load buckles the shell. Each mode is classified by where its amplitude
lies: the wall family (layup_study.families), the member band and the
station of its largest displacement.

Sandwich floor and bulkheads count by their two faces only, as everywhere
in this folder: a 2.4 mm plate, which buckles far below the sandwich, so
their modes here are a lower bound and are reported apart from the thin
walls' (skin and box walls). The sandwich cannot be put in the eigen-solve
as itself: a 25 mm composite shell section inverts the expanded S6
elements, as the 41 mm equivalent shell did in S3, and CalculiX's
composite shell ignores core shear anyway (on a 500 mm sandwich plate it
finds 2,800 N/mm against 411 by sandwich theory). It is checked by hand
instead, from the stress the static run puts in its faces: shear
crimping, N = G_c h^2 / c, and face wrinkling, 0.5 (E_f E_c G_c)^(1/3).
Core: ASSUMED PVC foam of the 48 kg/m3 class (E 50 MPa, nu 0.32). The
face stress is taken two ways, both the 99th percentile over the
sandwich: the nodal von Mises of OUTPUT=2D (mid-surface, no bending
stress, but averaged at each node with the walls that share it, which
may be more loaded), and the largest principal stress magnitude at the
integration points of the sandwich elements themselves (with the
faces-only plate's bending). The smaller margin of the two is the one to
read. Neither is a CFRP failure criterion.

Every buckling solve is repeated and the factors must agree within
0.01%; the static base state CalculiX writes before the modes is left
out (shell_s6.buckling_results).

The service loads are ASSUMED orders of magnitude, not a specification:
torsion 12 kN.m (one front wheel load of 2.85 kN over a 1.4 m track,
three times), bending 40 kN (three times 1,350 kg). Linear buckling of a
perfect shell over-estimates real buckling of thin composite shells, often
by a factor of two or more, so a factor near one is a failure, not a pass.

    python3 buckling.py          # cadsim image, both meshes, one SPOOLES thread
    python3 buckling.py 300      # only the meshes with these section counts
"""
import json
import pathlib
import sys
import tempfile

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import bending as bd  # noqa: E402
import build_shell as bs  # noqa: E402
import layup_study as ls  # noqa: E402
import member_study as ms  # noqa: E402
import shell_s6 as s6  # noqa: E402
import strength_audit as sa  # noqa: E402
import torsion as tr  # noqa: E402
import torsion_monocoque as tm  # noqa: E402

OUT = HERE.parent / "derived" / "buckling.json"
OUT_NPZ = HERE.parent / "derived" / "buckling-modes.npz"
N_MODES = 16
THIN = ("free skin", "box outer walls", "box inner walls")
SANDWICH_SECTIONS = (2, 3)                             # floor and bulkheads in sections()
CORE_E, CORE_NU = 50.0, 0.32
SERVICE = {"torsion": {"value": 12000.0, "unit": "N.m", "basis": "ASSUMED: 2.85 kN front wheel load x 1.4 m track x 3"},
           "bending": {"value": 40000.0, "unit": "N", "basis": "ASSUMED: 3 x 1,350 kg"}}


def sandwich_limits():
    g = CORE_E / (2 * (1 + CORE_NU))
    h = tm.CORE + tm.FACE
    return {"crimping_N_per_mm": g * h ** 2 / tm.CORE,
            "wrinkling_MPa": 0.5 * (tm.CARBON["E"] * CORE_E * g) ** (1 / 3)}


def sections(kind):
    """CFRP layup F0, sandwich families by their faces."""
    cf = (tm.CARBON["E"], tm.CARBON["nu"])
    return [(kind == 0, tm.T_SKIN, *cf), (kind == 1, tm.T_SECTION, *cf), (kind == 2, 2 * tm.FACE, *cf),
            (kind == 3, 2 * tm.FACE, *cf)]


def free_edge_nodes(tri):
    """Nodes on an edge that only one triangle has: the free edges of the
    model (aperture rims, the top of the rear bulkhead)."""
    e = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    edges, count = np.unique(e, axis=0, return_counts=True)
    free = np.zeros(tri.max() + 1, bool)
    free[edges[count == 1].ravel()] = True
    return free


def classify(u, pts, n_skin, fam, all_tri, bands, free):
    """Family, member and place of a mode's amplitude, and whether its
    largest displacement is on a free edge."""
    amp = np.linalg.norm(u, axis=1)
    top = amp >= np.percentile(amp[amp > 0], 99)
    node_fam = np.full(len(pts), -1)
    for k in range(3):
        node_fam[all_tri[:, k]] = fam
    counts = np.bincount(node_fam[top & (node_fam >= 0)], minlength=len(ls.FAMILIES))
    i = int(np.argmax(amp))
    skin = i if i < n_skin else int(np.argmin(np.linalg.norm(pts[:n_skin] - pts[i], axis=1)))
    member = [name for name, mask, _ in bands if mask[skin]]
    d = -pts[i, 0]
    return {"family": ls.FAMILIES[int(np.argmax(counts))],
            "family_share_of_top_1pct": round(float(counts.max() / max(counts.sum(), 1)), 2),
            "members": member, "free_edge": bool(free[i]), "d_mm": round(float(d)), "y_mm": round(float(pts[i, 1])), "z_mm": round(float(pts[i, 2]))}


def mesh(n, res, rep, profiles):
    s = None if n == bs.N_STATIONS and res == 1.0 else bs.structural(n, res)[2]
    s, p, tri = s6.load_shell(s)
    bands = tm.picogk_bands(p, s, rep, profiles)
    pts, all_tri, kind, *_ = tm.build(s, p, tri, lambda q, st: bands)
    return s, p, tri, pts, all_tri, kind, bands


def buckle_repeated(pts, all_tri, secs, fixed, loads):
    """Factors and modes of two *BUCKLE solves that agree within 0.01%."""
    f1, modes = s6.run(pts, all_tri, secs, fixed, loads, buckle=N_MODES)
    f2, _ = s6.run(pts, all_tri, secs, fixed, loads, buckle=N_MODES)
    if len(f1) != N_MODES or len(f2) != N_MODES or np.max(np.abs(f1 - f2) / np.abs(f1)) > 1e-4:
        sys.exit(f"buckling factors do not repeat: {f1.round(3).tolist()} against {f2.round(3).tolist()}")
    return f1, modes


def face_stress(pts, all_tri, secs, fixed, loads, sandwich):
    """99th percentiles over the sandwich (faces-only) shells: nodal von
    Mises of OUTPUT=2D (mid-surface) and the largest principal stress
    magnitude at the integration points (shell.dat, GLOBAL), MPa."""
    with tempfile.TemporaryDirectory() as tmp:
        _, vm = s6.run(pts, all_tri, secs, fixed, loads, output_dir=pathlib.Path(tmp, "run"),
                       print_sections=SANDWICH_SECTIONS)
        stress = sa.read_dat(pathlib.Path(tmp, "run", "shell.dat"))["stress"]
    ids = set((np.where(sandwich)[0] + 1).tolist())
    a = np.array([v for (el, _), v in stress.items() if el in ids])
    if not len(a):
        sys.exit("no integration-point stresses in the sandwich")
    xx, yy, zz, xy, zx, yz = a.T                          # .dat order (strength_audit.stress_summary)
    tensor = np.array([[xx, xy, zx], [xy, yy, yz], [zx, yz, zz]]).transpose(2, 0, 1)
    principal = np.abs(np.linalg.eigvalsh(tensor)).max(axis=1)
    return (float(np.percentile(vm[np.unique(all_tri[sandwich])], 99)), float(np.percentile(principal, 99)),
            len(a))


def main():
    rep = json.loads(tm.REPORT.read_text())
    profiles = json.loads(bs.PROFILES.read_text())
    out = {"model": "linear buckling (*BUCKLE) of the CFRP monocoque shell model of torsion_monocoque.py, S6; sandwich by its faces only",
           "classification": "values of this model under these loads, not of a vehicle; prohibited_pending_engineering",
           "layup_mm": {"skin": tm.T_SKIN, "section_walls": tm.T_SECTION, "sandwich_faces": tm.FACE, "core": tm.CORE},
           "core": {"E_MPa": CORE_E, "nu": CORE_NU, "basis": "ASSUMED PVC foam, 48 kg/m3 class"},
           "service_loads": SERVICE, "sandwich_limits": {k: round(v, 1) for k, v in sandwich_limits().items()},
           "sandwich_stress": ("99th percentile over the faces-only sandwich shells: 'mid_surface' is the nodal von Mises of "
                               "OUTPUT=2D (membrane, no bending stress), 'integration_points' the largest principal stress "
                               "magnitude at the integration points (with the faces-only plate's bending); neither is a "
                               "CFRP failure criterion"),
           "repeat_check": "every *BUCKLE solved twice, factors agree within 0.01%; static base state excluded",
           "meshes": [], "cases": {}}
    wanted = [int(a) for a in sys.argv[1:]] or [n for n, _ in ms.DENSITIES]
    if not set(wanted) <= {n for n, _ in ms.DENSITIES}:
        sys.exit(f"sections must be among {[n for n, _ in ms.DENSITIES]}")
    for n, res in [(n, r) for n, r in ms.DENSITIES if n in wanted]:
        keep = {}
        s, p, tri, pts, all_tri, kind, bands = mesh(n, res, rep, profiles)
        fam = ls.families(p, tri, kind, bands)
        rear, fl, fr = tr.supports(s, p)
        arm = float(p[fl, 1].mean() - p[fr, 1].mean())
        bfixed, bat, bf, *_ = bd.load_case(s, p, tri, rep, profiles)
        cases = {"torsion": ([(rear, 1, 6)], [(fl, 3, np.full(len(fl), tr.FORCE_N / len(fl))),
                                               (fr, 3, np.full(len(fr), -tr.FORCE_N / len(fr)))], tr.FORCE_N * arm / 1000.0),
                 "bending": (bfixed, [(bat, 3, bf)], bd.FORCE_N)}
        out["meshes"].append({"sections": n, "nodes": len(pts), "triangles": len(all_tri)})
        sandwich = (kind == 2) | (kind == 3)
        free = free_edge_nodes(all_tri)
        for name, (fixed, loads, ref) in cases.items():
            factors, modes = buckle_repeated(pts, all_tri, sections(kind), fixed, loads)
            face, face_ip, n_ip = face_stress(pts, all_tri, sections(kind), fixed, loads, sandwich)
            row = out["cases"].setdefault(name, {"reference_load": ref, "unit": SERVICE[name]["unit"], "meshes": []})
            scale = SERVICE[name]["value"] / ref
            lim = sandwich_limits()
            modes_out = [dict(factor=round(float(f), 2), critical=round(float(f) * ref), **classify(u, pts, len(p), fam, all_tri, bands, free))
                         for f, u in zip(factors, modes)]
            thin = next((m for m in modes_out if m["family"] in THIN), None)
            row["meshes"].append({
                "sections": n,
                "modes": modes_out,
                "first_thin_wall_critical_over_service": thin and round(thin["critical"] / SERVICE[name]["value"], 2),
                "first_faces_only_sandwich_critical_over_service": next(
                    (round(m["critical"] / SERVICE[name]["value"], 2) for m in modes_out if m["family"] not in THIN), None),
                "sandwich_face_stress_at_service_MPa_p99": {"mid_surface": round(face * scale, 1),
                                                            "integration_points": round(face_ip * scale, 1)},
                "sandwich_integration_points": n_ip,
                "sandwich_crimping_margin": {"mid_surface": round(lim["crimping_N_per_mm"] / (face * scale * 2 * tm.FACE), 2),
                                             "integration_points": round(lim["crimping_N_per_mm"] / (face_ip * scale * 2 * tm.FACE), 2)},
                "sandwich_wrinkling_margin": {"mid_surface": round(lim["wrinkling_MPa"] / (face * scale), 2),
                                              "integration_points": round(lim["wrinkling_MPa"] / (face_ip * scale), 2)}})
            m = row["meshes"][-1]
            first = f"{thin['family']} at d {thin['d_mm']} {thin['members']}{' (free edge)' * thin['free_edge']}" if thin else f"none in {N_MODES} modes"
            print(f"{n} sections, {name}: first thin-wall mode x{m['first_thin_wall_critical_over_service']} service, {first}; "
                  f"faces-only sandwich x{m['first_faces_only_sandwich_critical_over_service']}; sandwich crimping "
                  f"x{m['sandwich_crimping_margin']}, wrinkling x{m['sandwich_wrinkling_margin']}", flush=True)
            keep[f"{name}_first"] = modes[0]
            if thin:
                keep[f"{name}_first_thin_wall"] = modes[modes_out.index(thin)]
        OUT.write_text(json.dumps(out, indent=1) + "\n")       # after each mesh: an interrupted run keeps what it has
        np.savez_compressed(OUT_NPZ, sections=n, points=pts.astype(np.float32), triangles=all_tri.astype(np.int32),
                            kind=kind.astype(np.uint8), **{f"mode_{k}": v.astype(np.float32) for k, v in keep.items()})
        print(f"wrote {OUT.name} and {OUT_NPZ.name} ({n} sections)", flush=True)


if __name__ == "__main__":
    main()
