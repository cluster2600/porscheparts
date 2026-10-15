"""Where the carbon pays in torsion, and a first revision of the picogk/
monocoque at the same mass.

member_study.py said which members carry the cabin. This asks the
composite question that follows: with the members fixed, which walls
should get the plies? The walls of the shell model fall into five families:

- free skin: skin not under a closed section;
- box outer walls: the skin that forms the outer wall of a closed section
  (the floor under the tunnel and sills stays with the floor);
- box inner walls: inner and side walls of the closed sections;
- floor: the sandwich floor (faces);
- bulkheads: the sandwich bulkheads (faces).

Each family in turn gets 0.5 mm more CFRP; the K it gains per kilogram
added ranks them. F1 then follows a fixed rule, at the mass of F0:

1. remove the engine-lid ring (member_study.py: worth 0.1-0.2% in torsion);
2. take 0.5 mm off the family with the lowest cabin return, never below
   1.5 mm;
3. give the freed mass to the families in order of cabin return, at most
   0.5 mm each, so that each step stays within the sensitivity measured.

Two meshes, every K the value two solves agree on, K at the load points and
the cabin's own K between d 400 and 1950 mm. Thicknesses and the 1.5 mm
floor are ASSUMED; the run ranks walls, it does not size a laminate
(no strength, buckling, impact or joint check).

    python3 layup_study.py        # cadsim image, about two hours
    python3 layup_study.py --f1   # F1 only, from the sensitivities already written
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import build_shell as bs  # noqa: E402
import member_study as ms  # noqa: E402
import torsion as tr  # noqa: E402
import torsion_monocoque as tm  # noqa: E402

OUT = HERE.parent / "derived" / "torsion-layup.json"
STEP_MM, MIN_MM = 0.5, 1.5
FAMILIES = ["free skin", "box outer walls", "box inner walls", "floor", "bulkheads"]
F0_MM = {"free skin": tm.T_SKIN, "box outer walls": tm.T_SKIN, "box inner walls": tm.T_SECTION,
         "floor": 2 * tm.FACE, "bulkheads": 2 * tm.FACE}


def families(p, tri, kind, bands):
    """Family index per triangle of the shell model."""
    depth, _ = tm.member_depths(len(p), bands)
    base = np.arange(len(kind)) < len(tri)
    region = np.zeros(len(kind), bool)
    region[:len(tri)] = (depth > 0)[tri].all(axis=1) & (kind[:len(tri)] != 2)   # as build() selects its bands
    fam = np.full(len(kind), -1)
    fam[base & ~region & (kind == 0)] = 0
    fam[base & region & (kind == 0)] = 1
    fam[kind == 1] = 2
    fam[kind == 3] = 3                                # the floor stays sandwich, under a section or not
    fam[kind == 2] = 4
    assert (fam >= 0).all()
    return fam


def solve(model, mm):
    """K, cabin K and mass with family thicknesses mm (sandwich families
    carry their core in the mass, not in the stiffness)."""
    s, p, rear, fl, fr, pts, all_tri, fam, area = model
    secs, mass = [], 0.0
    core = tm.CORE * tm.CORE_RHO
    for j, name in enumerate(FAMILIES):
        m = fam == j
        t = mm[name]
        secs.append((m, t, tm.CARBON["E"], tm.CARBON["nu"]))
        mass += float(area[m].sum() * 1e-6 * (t * tm.CARBON["rho"] + (core if name in ("floor", "bulkheads") else 0.0)))
    k, u, _, reps = tm.solve_repeated(pts, all_tri, secs, rear, fl, fr)
    torque = tr.FORCE_N * float(p[fl, 1].mean() - p[fr, 1].mean()) / 1000.0
    front, back = tm.twist(pts, u, s, ms.CABIN_D)
    return k, torque / (front - back), mass, [round(x) for x in reps]


def model(n, res, drop=()):
    rep = json.loads(tm.REPORT.read_text())
    profiles = json.loads(bs.PROFILES.read_text())
    s = None if n == bs.N_STATIONS else bs.structural(n, res)[2]
    s, p, tri = tr.load_shell(s)
    rear, fl, fr = tr.supports(s, p)
    bands = [b for b in tm.picogk_bands(p, s, rep, profiles) if b[0] not in drop]
    pts, all_tri, kind, *_ = tm.build(s, p, tri, lambda q, st: bands)
    fam = families(p, tri, kind, bands)
    return s, p, rear, fl, fr, pts, all_tri, fam, tm.areas(pts, all_tri)


def main():
    if "--f1" in sys.argv:                       # sensitivities already in OUT
        return f1(json.loads(OUT.read_text()))
    out = {"model": "family thickness sensitivity and an F1 revision, on the shell model of torsion_monocoque.py (members of ../picogk/)",
           "classification": "values of this model under this load, not of a vehicle; prohibited_pending_engineering",
           "f0_mm": F0_MM, "step_mm": STEP_MM, "min_mm": MIN_MM, "meshes": [], "sensitivity": {}}
    models = {}
    for n, res in ms.DENSITIES:
        models[n] = m0 = model(n, res)
        k0, c0, w0, reps = solve(m0, F0_MM)
        out["meshes"].append({"sections": n, "K_F0": round(k0), "K_cabin_F0": round(c0), "mass_F0_kg": round(w0, 1), "K_F0_repeats": reps})
        print(f"{n} sections, F0: K {k0:.0f}, cabin {c0:.0f}, {w0:.1f} kg", flush=True)
        for name in FAMILIES:
            k, c, w, reps = solve(m0, dict(F0_MM, **{name: F0_MM[name] + STEP_MM}))
            row = out["sensitivity"].setdefault(name, {"area_m2": [], "K_per_kg": [], "K_cabin_per_kg": [], "K_repeats": []})
            row["area_m2"].append(round(float(m0[8][m0[7] == FAMILIES.index(name)].sum()) / 1e6, 2))
            row["K_per_kg"].append(round((k - k0) / (w - w0)))
            row["K_cabin_per_kg"].append(round((c - c0) / (w - w0)))
            row["K_repeats"].append(reps)
            print(f"  +{STEP_MM} mm {name:16s} +{w - w0:5.2f} kg: K +{(k - k0) / (w - w0):6.0f}/kg, "
                  f"cabin +{(c - c0) / (w - w0):6.0f}/kg", flush=True)
        OUT.write_text(json.dumps(out, indent=1) + "\n")
    f1(out)


def f1(out):
    """The F1 revision from the sensitivities in out, at the F0 mass: the
    freed mass goes to the families in order of cabin return, at most
    STEP_MM each, within the sensitivity measured."""
    finest = {f: r["K_cabin_per_kg"][-1] for f, r in out["sensitivity"].items()}
    order = sorted(finest, key=finest.get, reverse=True)
    worst = min((f for f in finest if F0_MM[f] - STEP_MM >= MIN_MM and f != order[0]), key=finest.get)
    out["F1"] = {"rule": f"engine-lid ring removed; worst cabin-return family thinned by {STEP_MM} mm; freed mass to the "
                         f"families in order of cabin return, at most +{STEP_MM} mm each; same mass as F0",
                 "thinned": worst, "order": order, "mm": [], "K": [], "K_cabin": [], "mass_kg": [],
                 "K_gain_fraction": [], "K_cabin_gain_fraction": [], "K_repeats": []}
    for (n, res), mesh in zip(ms.DENSITIES, out["meshes"]):
        m1 = model(n, res, drop=("engine_lid",))
        mm = dict(F0_MM, **{worst: F0_MM[worst] - STEP_MM})
        area = {f: float(m1[8][m1[7] == j].sum()) * 1e-6 for j, f in enumerate(FAMILIES)}
        mass_f0_shells = mesh["mass_F0_kg"] - sum(area[f] * tm.CORE * tm.CORE_RHO for f in ("floor", "bulkheads"))
        spare = mass_f0_shells - sum(area[f] * mm[f] * tm.CARBON["rho"] for f in FAMILIES)
        for f in order:
            if f == worst or spare <= 0:
                continue
            add = min(STEP_MM, spare / (area[f] * tm.CARBON["rho"]))
            mm[f] += add
            spare -= add * area[f] * tm.CARBON["rho"]
        k, c, w, reps = solve(m1, mm)
        f1 = out["F1"]
        f1["mm"].append({f: round(v, 2) for f, v in mm.items()})
        f1["K"].append(round(k))
        f1["K_cabin"].append(round(c))
        f1["mass_kg"].append(round(w, 1))
        f1["K_gain_fraction"].append(round(k / mesh["K_F0"] - 1, 3))
        f1["K_cabin_gain_fraction"].append(round(c / mesh["K_cabin_F0"] - 1, 3))
        f1["K_repeats"].append(reps)
        print(f"{n} sections, F1 {f1['mm'][-1]}: K {k:.0f} ({k / mesh['K_F0'] - 1:+.1%}), "
              f"cabin {c:.0f} ({c / mesh['K_cabin_F0'] - 1:+.1%}), {w:.1f} kg", flush=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
