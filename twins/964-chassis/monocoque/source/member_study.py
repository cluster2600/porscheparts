"""What each member of the picogk/ monocoque is worth in torsion.

Leave-one-out on the shell model of torsion_monocoque.py: the full
architecture, then the same with one member removed at a time (its skin
band no longer gets an inner wall and side walls). For each member, the
stiffness it carries (K lost when it goes), the mass it costs, and the
return, K per kilogram of member. The same method as ../../fea/ring_study.py
on the box cell, on the 911 shell.

Assumed CFRP layup, two meshes (300 and 420 sections), every K the median
of three solves. Two measures: K at the load points, as everywhere in this
folder, and the cabin's own K, torque over the rotation difference between
d = 400 and d = 1950 mm, which leaves out the load introduction at the front
wheel houses and the clamped rear. Members near the load (front arches, front
lid, front rails) look far better on the first than on the second.

Leave-one-out measures a member's marginal worth in the
complete structure: members that only work together (the ring study found
the roof and the windscreen frame worth 1.6 times their sum) can each look
cheap to remove. It ranks candidates for pruning; it does not license
removing two at once without a run.

    python3 member_study.py            # cadsim image, two to three hours
    python3 member_study.py --pruned   # then: the low-return members removed together
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parents[1] / "fea"))          # after source/: fea has its own build_shell
import build_shell as bs  # noqa: E402
import torsion as tr  # noqa: E402
import torsion_monocoque as tm  # noqa: E402

OUT = HERE.parent / "derived" / "torsion-members.json"
CASE = "monocoque, CFRP layup"
DENSITIES = [(300, 0.71), (bs.N_STATIONS, 1.0)]
CABIN_D = (400.0, 1950.0)      # just behind the front bulkhead, just ahead of the rear one
PRUNE_BELOW = 0.05


def run(s, p, tri, rear, fl, fr, bands):
    """K at the load points, the cabin's own K between the bulkheads, the
    mass, and the three solves."""
    pts, all_tri, kind, *_ = tm.build(s, p, tri, lambda q, st: bands)
    secs, mass = tm.cases(kind, tm.areas(pts, all_tri))[CASE]
    k, u, _, reps = tm.solve_repeated(pts, all_tri, secs, rear, fl, fr)
    torque = tr.FORCE_N * float(p[fl, 1].mean() - p[fr, 1].mean()) / 1000.0
    front, back = tm.twist(pts, u, s, CABIN_D)
    return k, torque / (front - back), mass, reps


def prune():
    """Remove together every member under PRUNE_BELOW on both measures and
    both meshes, and solve that: leave-one-out alone does not license it."""
    out = json.loads(OUT.read_text())
    if not out.get("complete"):
        sys.exit("run the leave-one-out study first")
    drop = sorted(n for n, r in out["members"].items()
                  if max(r["K_lost_fraction"] + r["K_cabin_lost_fraction"]) < PRUNE_BELOW)
    rep = json.loads(tm.REPORT.read_text())
    profiles = json.loads(bs.PROFILES.read_text())
    res = {"removed": drop, "criterion": f"K and cabin K lost < {PRUNE_BELOW:.0%} on both meshes, one at a time",
           "K": [], "K_cabin": [], "mass_kg": [], "K_lost_fraction": [], "K_cabin_lost_fraction": [], "mass_saved_kg": []}
    for (n, res_), mesh in zip(DENSITIES, out["meshes"]):
        s = None if n == bs.N_STATIONS else bs.structural(n, res_)[2]
        s, p, tri = tr.load_shell(s)
        rear, fl, fr = tr.supports(s, p)
        bands = [b for b in tm.picogk_bands(p, s, rep, profiles) if b[0] not in drop]
        k, c, m, _ = run(s, p, tri, rear, fl, fr, bands)
        res["K"].append(round(k))
        res["K_cabin"].append(round(c))
        res["mass_kg"].append(round(m, 1))
        res["K_lost_fraction"].append(round(1 - k / mesh["K_full"], 3))
        res["K_cabin_lost_fraction"].append(round(1 - c / mesh["K_cabin_full"], 3))
        res["mass_saved_kg"].append(round(mesh["mass_full_kg"] - m, 1))
        print(f"{n} sections, without {', '.join(drop)}: K {k:.0f} (-{1 - k / mesh['K_full']:.1%}), "
              f"cabin K {c:.0f} (-{1 - c / mesh['K_cabin_full']:.1%}), {m:.1f} kg (-{mesh['mass_full_kg'] - m:.1f})", flush=True)
    out["pruned"] = res
    OUT.write_text(json.dumps(out, indent=1) + "\n")


def main():
    if "--pruned" in sys.argv:
        return prune()
    rep = json.loads(tm.REPORT.read_text())
    profiles = json.loads(bs.PROFILES.read_text())
    out = {"model": "leave-one-out on the shell model of torsion_monocoque.py (members of ../picogk/)",
           "classification": "values of this model under this load, not of a vehicle; prohibited_pending_engineering",
           "case": CASE, "meshes": [], "members": {}, "complete": False,
           "note": ("K_lost and mass_kg are what removing the member costs and saves, per mesh (300, 420 sections). "
                    "The whole architecture's return is K_full / mass_full; members above it pay for themselves.")}
    for n, res in DENSITIES:
        s = None if n == bs.N_STATIONS else bs.structural(n, res)[2]
        s, p, tri = tr.load_shell(s)
        rear, fl, fr = tr.supports(s, p)
        bands = tm.picogk_bands(p, s, rep, profiles)
        k0, c0, m0, reps0 = run(s, p, tri, rear, fl, fr, bands)
        out["meshes"].append({"sections": n, "K_full": round(k0), "K_cabin_full": round(c0), "mass_full_kg": round(m0, 1),
                              "K_full_repeats": [round(x) for x in reps0]})
        print(f"{n} sections: full K = {k0:.0f}, cabin K = {c0:.0f} N.m/deg, {m0:.1f} kg", flush=True)
        for name, *_ in bands:
            k, c, m, reps = run(s, p, tri, rear, fl, fr, [b for b in bands if b[0] != name])
            row = out["members"].setdefault(name, {"K_lost": [], "K_lost_fraction": [], "K_cabin_lost_fraction": [],
                                                   "mass_kg": [], "return_N_m_deg_per_kg": [], "K_repeats": []})
            dk, dm = k0 - k, m0 - m
            row["K_lost"].append(round(dk))
            row["K_lost_fraction"].append(round(dk / k0, 3))
            row["K_cabin_lost_fraction"].append(round((c0 - c) / c0, 3))
            row["mass_kg"].append(round(dm, 2))
            row["return_N_m_deg_per_kg"].append(round(dk / dm) if dm > 0.05 else None)
            row["K_repeats"].append([round(x) for x in reps])
            print(f"  without {name:15s} K -{dk / k0:6.1%}, cabin K -{(c0 - c) / c0:6.1%}, member {dm:5.2f} kg, "
                  f"return {dk / max(dm, 1e-9):7.0f} N.m/deg/kg", flush=True)
            OUT.write_text(json.dumps(out, indent=1) + "\n")       # after each member: an interrupted run keeps what it has
    out["complete"] = True
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
