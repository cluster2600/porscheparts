"""Vertical bending of the PicoGK monocoque architecture, on the shell model
of torsion_monocoque.py.

The torsion study chose the architecture; this asks whether the same
members carry the other global load case, the body as a beam between its
axles. Same shell models, same materials and meshes as
torsion_monocoque.py, a different load:

- supports: the suspension patches of torsion.supports(), cut down to a
  strip of +/-SUPPORT_HALF_MM along the car around each axle (wheel
  centres of the PicoGK report), held vertically. One node per side of the
  rear strip is held along the car and one node at each end across it:
  rollers at the front, pins at the rear, no clamp moment;
- load: FORCE_N downward, spread by area over the skin of both sills
  (the sill band of picogk_bands) within +/-LOAD_HALF_MM of mid-wheelbase.
  The sills, not the floor: the floor is modelled by its sandwich faces
  only, and a load on it would measure the faces' plate bending.

Two measures, as in member_study.py: K = force over the mean vertical
deflection of the loaded skin (N/mm), and the cabin's own sag, the
deflection at mid-wheelbase below the chord between d = 400 and 1950 mm,
which leaves out the support patches and the front and rear structure.
Deflections along the car are taken on the sill line (the sill footprint
of the skin, |y| > W - 210 mm and up to 270 mm above the floor, over the
whole length): the mean of a whole section mixes in its distortion, the
roof rising while the floor sinks.

Every value is the one two solves agree on (torsion_monocoque.solve_repeated
explains why), at three densities of the shell; S3 converges from above,
so only ratios that hold across them are used. These are values of this
model under this load, not of a vehicle: no glass, no doors, no
suspension, the supports and the load introduction are idealised.

    python3 bending.py             # cadsim image, the four cases at three densities
    python3 bending.py --members   # then: leave-one-out on the CFRP monocoque, two meshes
    python3 bending.py --pruned    # then: the members torsion found weak, removed together
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

OUT = HERE.parent / "derived" / "bending.json"
OUT_NPZ = HERE.parent / "derived" / "bending-snapshot.npz"
FORCE_N = 2000.0
SUPPORT_HALF_MM, LOAD_HALF_MM = 40.0, 100.0
DENSITIES = [(210, 0.5), (300, 0.71), (bs.N_STATIONS, 1.0)]
PROFILE_D = np.arange(-600, 2451, 50.0)


def axles(rep):
    front, rear = (w["d"] for w in rep["hypotheses"]["wheel_space"])
    return front, rear


def load_case(s, p, tri, rep, profiles):
    """Fixed DOF sets, load nodes and their forces (N, downward)."""
    d, y = -p[:, 0], p[:, 1]
    rear, fl, fr = tr.supports(s, p)
    front_d, rear_d = axles(rep)
    front = np.concatenate([fl, fr])
    front = front[np.abs(d[front] - front_d) < SUPPORT_HALF_MM]
    rear = rear[np.abs(d[rear] - rear_d) < SUPPORT_HALF_MM]
    pin = [r[np.argmin(np.abs(d[r] - rear_d))] for r in (rear[y[rear] > 0], rear[y[rear] < 0])]
    left = lambda ids, at: ids[y[ids] > 0][np.argmin(np.abs(d[ids[y[ids] > 0]] - at))]   # noqa: E731
    fixed = [(np.concatenate([front, rear]), 3, 3), (np.array(pin), 1, 1),
             (np.array([left(rear, rear_d), left(front, front_d)]), 2, 2)]
    sills = next(m for name, m, _ in tm.picogk_bands(p, s, rep, profiles) if name == "sills")
    mid = 0.5 * (front_d + rear_d)
    at = np.where(sills & (np.abs(d - mid) < LOAD_HALF_MM))[0]
    nodal = np.zeros(len(p))
    a = tm.areas(p, tri) / 3
    for k in range(3):
        np.add.at(nodal, tri[:, k], a)
    w = nodal[at] / nodal[at].sum()
    return fixed, at, -FORCE_N * w, mid, p, sill_line(s, p, rep)


def sill_line(s, p, rep):
    """Skin nodes of the sill footprint over the whole length."""
    d, y, z = -p[:, 0], p[:, 1], p[:, 2]
    sill = rep["hypotheses"]["sills_mm"]
    w, zb = np.interp(d, s["stations_d"], s["half_width"]), np.interp(d, s["stations_d"], s["bottom"])
    return (np.abs(y) > w - sill["width"]) & (z < zb + sill["height_above_floor"])


def sag(p, u, line, stations):
    """Mean vertical displacement of the sill-line nodes within 15 mm of
    each station (NaN where the slab is nearly empty)."""
    d = -p[:, 0]
    out = []
    for di in stations:
        m = line & (np.abs(d - di) < 15)
        out.append(float(u[:len(p)][m, 2].mean()) if m.sum() >= 4 else np.nan)
    return np.array(out)


def solve(pts, tri, secs, s, case):
    """K (N/mm), the cabin's sag K (N/mm), displacements and von Mises."""
    fixed, at, f, mid, p, line = case
    u, vm = tr.run(pts, tri, secs, fixed, [(at, 3, f)])
    delta = -float((u[at, 2] * f).sum() / f.sum())
    w0, wm, w1 = sag(p, u, line, (ms.CABIN_D[0], mid, ms.CABIN_D[1]))
    chord = w0 + (w1 - w0) * (mid - ms.CABIN_D[0]) / (ms.CABIN_D[1] - ms.CABIN_D[0])
    return FORCE_N / delta, FORCE_N / -(wm - chord), u, vm


def solve_repeated(pts, tri, secs, s, case, n=tm.REPEATS, most=7):
    """The solve that two runs agree on, within 0.01% on K."""
    runs = []
    while len(runs) < most:
        runs.append(solve(pts, tri, secs, s, case))
        ks = [r[0] for r in runs]
        if len(runs) < n:
            continue
        for i in range(len(ks)):
            if any(abs(ks[i] - ks[j]) <= 1e-4 * abs(ks[i]) for j in range(len(ks)) if j != i):
                return (*runs[i], [round(k, 1) for k in ks])
    sys.exit(f"no two of {len(runs)} solves agree: {[round(k, 1) for k in ks]}")


def model(n, res, rep, profiles, drop=()):
    s = None if n == bs.N_STATIONS and res == 1.0 else bs.structural(n, res)[2]
    s, p, tri = tr.load_shell(s)
    bands = [b for b in tm.picogk_bands(p, s, rep, profiles) if b[0] not in drop]
    pts, all_tri, kind, *_ = tm.build(s, p, tri, lambda q, st: bands)
    return s, p, tri, pts, all_tri, kind, bands


def cases_run(rep, profiles):
    out = {"model": "vertical bending on the shell models of torsion_monocoque.py (members of ../picogk/)",
           "classification": "values of this model under this load, not of a vehicle; prohibited_pending_engineering",
           "load_case": {"force_N": FORCE_N, "axles_d_mm": axles(rep), "support_strip_half_mm": SUPPORT_HALF_MM,
                         "supports": "torsion.supports() patches within the strip, vertical; rear pinned along the car, one node per side; one node per axle across",
                         "load": f"downward, by area on the sill skin within +/-{LOAD_HALF_MM:.0f} mm of mid-wheelbase",
                         "K": "force / mean deflection of the loaded skin (N/mm)",
                         "K_cabin": f"force / sag at mid-wheelbase below the chord between d {ms.CABIN_D[0]:.0f} and {ms.CABIN_D[1]:.0f} mm (N/mm)"},
           "meshes": [], "cases": {}, "profile_d_mm": PROFILE_D.tolist()}
    snap = {}
    for n, res in DENSITIES:
        s, p, tri, pts, all_tri, kind, _ = model(n, res, rep, profiles)
        case = load_case(s, p, tri, rep, profiles)
        out["meshes"].append({"sections": n, "nodes": len(pts), "triangles": len(all_tri),
                              "support_nodes": len(case[0][0][0]), "load_nodes": len(case[1])})
        print(f"{n} sections: {len(pts)} nodes, {len(case[0][0][0])} support and {len(case[1])} load nodes", flush=True)
        for name, (secs, mass) in tm.cases(kind, tm.areas(pts, all_tri)).items():
            k, c, u, vm, reps = solve_repeated(pts, all_tri, secs, s, case)
            row = out["cases"].setdefault(name, {"mass_kg": [], "K": [], "K_cabin": [], "K_repeats": []})
            row["mass_kg"].append(round(mass, 1))
            row["K"].append(round(k))
            row["K_cabin"].append(round(c))
            row["K_repeats"].append(reps)
            if n == bs.N_STATIONS:
                row["profile_mm_per_kN"] = [None if np.isnan(x) else round(x * 1000 / FORCE_N, 4) for x in sag(case[4], u, case[5], PROFILE_D)]
                snap[name] = vm
            print(f"  {name:28s} K = {k:6.0f} N/mm, cabin {c:7.0f} N/mm, {mass:5.1f} kg", flush=True)
        OUT.write_text(json.dumps(out, indent=1) + "\n")
    ratio = lambda a, b, key: [round(x / y, 2) for x, y in zip(out["cases"][a][key], out["cases"][b][key])]   # noqa: E731
    out["ratios"] = {f"monocoque / open shell, {m}, {key}": ratio(f"monocoque, {m}", f"open shell, {m}", key)
                     for m in ("0.8 mm steel", "CFRP layup") for key in ("K", "K_cabin")}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    np.savez_compressed(OUT_NPZ, points=pts.astype(np.float32), triangles=all_tri.astype(np.int32), kind=kind.astype(np.uint8),
                        von_mises_monocoque_cfrp=snap["monocoque, CFRP layup"].astype(np.float32),
                        load_nodes=case[1].astype(np.int32), support_nodes=case[0][0][0].astype(np.int32))
    print("ratios", out["ratios"])


def members_run(rep, profiles):
    """Leave-one-out on the CFRP monocoque, as member_study.py does for torsion."""
    out = json.loads(OUT.read_text())
    res = out["members"] = {"case": ms.CASE, "meshes": [], "members": {}}
    for n, r in ms.DENSITIES:
        s, p, tri, pts, all_tri, kind, bands = model(n, r, rep, profiles)
        case = load_case(s, p, tri, rep, profiles)

        def one(bb):
            q, t, kd, *_ = tm.build(s, p, tri, lambda a, b: bb)
            secs, mass = tm.cases(kd, tm.areas(q, t))[ms.CASE]
            k, c, *_, reps = solve_repeated(q, t, secs, s, case)
            return k, c, mass, reps
        k0, c0, m0, reps0 = one(bands)
        res["meshes"].append({"sections": n, "K_full": round(k0), "K_cabin_full": round(c0), "mass_full_kg": round(m0, 1),
                              "K_full_repeats": reps0})
        print(f"{n} sections: full K = {k0:.0f}, cabin K = {c0:.0f} N/mm, {m0:.1f} kg", flush=True)
        for name, *_ in bands:
            k, c, m, reps = one([b for b in bands if b[0] != name])
            row = res["members"].setdefault(name, {"K_lost_fraction": [], "K_cabin_lost_fraction": [], "mass_kg": [], "K_repeats": []})
            row["K_lost_fraction"].append(round(1 - k / k0, 3))
            row["K_cabin_lost_fraction"].append(round(1 - c / c0, 3))
            row["mass_kg"].append(round(m0 - m, 2))
            row["K_repeats"].append(reps)
            print(f"  without {name:15s} K -{1 - k / k0:6.1%}, cabin K -{1 - c / c0:6.1%}, member {m0 - m:5.2f} kg", flush=True)
            OUT.write_text(json.dumps(out, indent=1) + "\n")
    res["complete"] = True
    OUT.write_text(json.dumps(out, indent=1) + "\n")


def pruned_run(rep, profiles):
    """The members member_study.py --pruned removed together for torsion,
    removed together here: does the pruning hold in bending?"""
    out = json.loads(OUT.read_text())
    res = out.get("members", {})
    if not res.get("complete"):
        sys.exit("run --members first")
    drop = json.loads(ms.OUT.read_text())["pruned"]["removed"]
    pr = res["pruned"] = {"removed": drop, "source": "torsion-members.json, pruned", "K_lost_fraction": [],
                          "K_cabin_lost_fraction": [], "mass_saved_kg": [], "K_repeats": []}
    for (n, r), mesh in zip(ms.DENSITIES, res["meshes"]):
        s, p, tri, pts, all_tri, kind, _ = model(n, r, rep, profiles, drop=drop)
        case = load_case(s, p, tri, rep, profiles)
        secs, mass = tm.cases(kind, tm.areas(pts, all_tri))[ms.CASE]
        k, c, *_, reps = solve_repeated(pts, all_tri, secs, s, case)
        pr["K_lost_fraction"].append(round(1 - k / mesh["K_full"], 3))
        pr["K_cabin_lost_fraction"].append(round(1 - c / mesh["K_cabin_full"], 3))
        pr["mass_saved_kg"].append(round(mesh["mass_full_kg"] - mass, 1))
        pr["K_repeats"].append(reps)
        print(f"{n} sections, without {', '.join(drop)}: K -{1 - k / mesh['K_full']:.1%}, "
              f"cabin K -{1 - c / mesh['K_cabin_full']:.1%}, -{mesh['mass_full_kg'] - mass:.1f} kg", flush=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")


def main():
    rep = json.loads(tm.REPORT.read_text())
    profiles = json.loads(bs.PROFILES.read_text())
    if "--pruned" in sys.argv:
        pruned_run(rep, profiles)
    elif "--members" in sys.argv:
        members_run(rep, profiles)
    else:
        cases_run(rep, profiles)
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
