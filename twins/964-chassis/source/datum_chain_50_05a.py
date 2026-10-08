"""Longitudinal datum chain of the 964 body, from published dimensions only.

Supersedes the longitudinal part of `datum_solve.py`, which read dimension P
as a crossed plan diagonal. Plate 50-02 draws P as a straight fore-aft
dimension from the P20 line to the P5 line, so P is longitudinal.

Plate 50-05a ("Dimensions for assembly - from Model 91 onward") adds what the
chain was missing: three longitudinal dimensions measured from the same
transverse "0" line, the line drawn through the front spring-strut mounts P4:

    722 +/- 2   P1 (front bumper absorber tube centre) ahead of the 0 line
    215         P3 (front axle side-member mount) ahead of the 0 line
    143 +/- 2   P5 (outer front cross-member mount) behind the 0 line

with 3756.5 +/- 4 from the P1 plane to the rear (P16) plane.

The chain is then closed twice to P17, independently:

    P5 -> P20 (P, longitudinal) -> P17 (K, crossed plan diagonal)
    P3 -> P17 (L, crossed plan diagonal)

and the two must agree. R and S carry P17 to P18 and P19.

The rear hangs on diagonals O (P18 to P21) and N (P12 to P21), both crossed.
Plate 50-03 gives each twice, e.g. O = 1696 +/- 3 (1653 +/- 3), and says the
values in brackets are "measured vertically". Read as plan distances, the
bracketed values put P12 38 mm ahead of where plates 50-05a and 50-02 both
draw it, and the two diagonals then disagree at P21 by 37 mm. Read as direct
distances between holes at slightly different heights, the unbracketed
values close: N and O meet within 5 mm of each other once P12 is taken from
the drawings, and P21 lands on the rear engine-mount cradle the scan shows
(plate_50_05a_scale.py, scan_tie_50_05a.py). The chain uses the unbracketed
values, with the unknown height differences (0 to 150 mm on O, 0 to 100 mm on
N) carried in the uncertainty; the bracketed reading is reported, not used.

Positions are distances behind the 0 line, d (mm, + rearward). Tolerances are
propagated by Monte Carlo, uniform within the published band; 215 carries no
published tolerance and is given +/- 2 like its neighbours (assumed).

Output: ../derived/datum-chain-50-05a.json. Standard library only.

    python3 datum_chain_50_05a.py
"""
import json
import math
import random
import statistics

SOURCE = "SRC-PORSCHE-WORKSHOP-MANUAL-964-VOL5-BODY"
Y_HALF = {20: 440 / 2, 3: 610 / 2, 5: 770 / 2, 17: 1330 / 2, 18: 1236 / 2,
          19: 1018 / 2, 12: 278 / 2, 21: 640 / 2}

# name: (nominal, half tolerance, plate, what it is)
DIMENSIONS = {
    "D722": (722.0, 2.0, "50-05a", "P1 plane ahead of the 0 line"),
    "D215": (215.0, 2.0, "50-05a", "P3 ahead of the 0 line (tolerance assumed)"),
    "D143": (143.0, 2.0, "50-05a", "P5 behind the 0 line"),
    "L3756": (3756.5, 4.0, "50-05a", "P1 plane to the rear (P16) plane"),
    "P": (913.0, 1.5, "50-02/50-03", "P20 to P5, longitudinal (913, oblique 914.5)"),
    "K": (1500.0, 3.0, "50-03", "P20 to P17, crossed plan diagonal"),
    "L": (1170.0, 2.0, "50-03", "P3 to P17, crossed plan diagonal (1170 plan, 1174 oblique)"),
    "R": (1245.0, 2.0, "50-03", "P17 to P18, side view"),
    "O": (1696.0, 3.0, "50-03", "P18 to P21, crossed diagonal, unbracketed (bracketed 1653)"),
    "N": (1492.0, 3.0, "50-03", "P12 to P21, crossed diagonal, unbracketed (bracketed 1482)"),
    "S": (1328.0, 2.0, "50-03", "P17 to P19, side view"),
}
Y_TOL = {20: 1.0, 3: 0.5, 5: 1.0, 17: 0.5, 18: 0.5, 19: 0.5, 12: 0.5, 21: 0.5}
DZ_MAX = {"O": 150.0, "N": 100.0}   # unknown height difference along each rear diagonal
BRACKETED = {"O": 1653.0, "N": 1482.0}


def crossed(diagonal, a, b, y, dz=0.0):
    """Longitudinal separation from a crossed diagonal between a and b, with an
    optional height difference dz between the two holes."""
    span = y[a] + y[b]
    return math.sqrt(diagonal ** 2 - span ** 2 - dz ** 2)


def solve(v, y, dz=None):
    """One evaluation of the chain. v: dimension values, y: half spacings,
    dz: height differences along O and N (zero by default)."""
    dz = dz or {"O": 0.0, "N": 0.0}
    d = {1: -v["D722"], 3: -v["D215"], 5: v["D143"]}
    d[20] = d[5] - v["P"]
    via_k = d[20] + crossed(v["K"], 20, 17, y)
    via_l = d[3] + crossed(v["L"], 3, 17, y)
    d[17] = 0.5 * (via_k + via_l)
    d[18] = d[17] + v["R"]
    d[19] = d[17] + v["S"]
    d[16] = v["L3756"] - v["D722"]
    d[21] = d[18] + crossed(v["O"], 18, 21, y, dz["O"])
    d[12] = d[21] - crossed(v["N"], 12, 21, y, dz["N"])
    return d, via_k, via_l


def main():
    nominal = {k: val[0] for k, val in DIMENSIONS.items()}
    d0, k0, l0 = solve(nominal, Y_HALF)

    rng = random.Random(964)
    samples = {p: [] for p in d0}
    closure = []
    for _ in range(20000):
        v = {k: val[0] + rng.uniform(-val[1], val[1]) for k, val in DIMENSIONS.items()}
        y = {p: h + rng.uniform(-Y_TOL.get(p, 0.5), Y_TOL.get(p, 0.5)) for p, h in Y_HALF.items()}
        dz = {k: rng.uniform(0.0, m) for k, m in DZ_MAX.items()}
        d, vk, vl = solve(v, y, dz)
        for p, value in d.items():
            samples[p].append(value)
        closure.append(vk - vl)

    points = {}
    for p in sorted(d0, key=lambda q: d0[q]):
        s = sorted(samples[p])
        points[f"P{p}"] = {
            "d_behind_0_line_mm": round(d0[p], 1),
            "x_from_P17_mm": round(d0[17] - d0[p], 1),
            "y_half_mm": Y_HALF.get(p),
            "u95_mm": round(0.5 * (s[int(0.975 * len(s))] - s[int(0.025 * len(s))]), 1),
        }
    closure_sd = statistics.pstdev(closure)
    bracketed = dict(nominal, O=BRACKETED["O"], N=BRACKETED["N"])
    db, _, _ = solve(bracketed, Y_HALF)
    report = {
        "schema_version": "1.0.0",
        "twin": "964-chassis",
        "source_id": SOURCE,
        "classification": "published_dimension_chain_not_measurement",
        "zero_line": "transverse line through the front spring-strut mounts P4, as drawn on plates 50-05 and 50-05a",
        "sign": "d > 0 behind the 0 line; x_from_P17 > 0 ahead of P17 (the old local chain's sign)",
        "dimensions": {k: {"value_mm": val[0], "half_tolerance_mm": val[1], "plate": val[2], "meaning": val[3]}
                       for k, val in DIMENSIONS.items()},
        "p_is_longitudinal": "plate 50-02 draws P as a fore-aft dimension from the P20 line to the P5 line; datum_solve.py read it as a crossed diagonal and put P5 230 mm out",
        "p17_closure": {
            "via_P5_P20_K_mm": round(k0, 1),
            "via_P3_L_mm": round(l0, 1),
            "difference_mm": round(k0 - l0, 1),
            "difference_sd_from_tolerances_mm": round(closure_sd, 1),
            "verdict": "the two published paths agree" if abs(k0 - l0) <= 2.0 * closure_sd else "the two published paths disagree",
        },
        "points": points,
        "rear_reading": {
            "used": "unbracketed O and N as direct distances, height differences unknown (0-150, 0-100 mm) and carried in u95",
            "bracketed_alternative_d_mm": {"P12": round(db[12], 1), "P21": round(db[21], 1)},
            "why_not_bracketed": "it places P12 38 mm ahead of plates 50-05a and 50-02, which agree with each other within 4 mm, and splits P21 by 37 mm between O and N",
            "checks": "plate_50_05a_scale.py (drawings) and scan_tie_50_05a.py (engine-mount cradle)",
        },
        "not_in_published_chain": {
            "P6": "plate 50-03 gives its transverse spacing D only",
            "P13, P14, P15": "drawn on 50-05a without a dimension; scaled in plate_50_05a_scale.py",
        },
        "monte_carlo": {"samples": 20000, "seed": 964, "distribution": "uniform within each published band"},
    }
    with open("../derived/datum-chain-50-05a.json", "w") as f:
        json.dump(report, f, indent=1)
        f.write("\n")

    print("964 longitudinal datum chain, published dimensions only (plates 50-02, 50-03, 50-05a)\n")
    print(f"P17 via P5-P20-K = {k0:.1f} mm, via P3-L = {l0:.1f} mm behind the 0 line: "
          f"difference {k0 - l0:+.1f} mm (tolerance sd {closure_sd:.1f} mm)\n")
    print(f"{'point':<6}{'d behind 0':>12}{'x from P17':>12}{'+/- (95 %)':>12}")
    for name, row in points.items():
        print(f"{name:<6}{row['d_behind_0_line_mm']:12.1f}{row['x_from_P17_mm']:12.1f}{row['u95_mm']:12.1f}")
    print("\nwrote ../derived/datum-chain-50-05a.json")


if __name__ == "__main__":
    main()
