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

and the two must agree. R and S carry P17 to P18 and P19. P12 and P21 hang on
diagonals N and O, whose crossed-plan reading disagrees with the scan by 60 to
85 mm at P12 (see scan_tie_50_05a.py); they are kept out of the published chain.

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
    "S": (1328.0, 2.0, "50-03", "P17 to P19, side view"),
}
Y_TOL = {20: 1.0, 3: 0.5, 5: 1.0, 17: 0.5, 18: 0.5, 19: 0.5}   # half of the transverse tolerance


def crossed(diagonal, a, b, y):
    """Longitudinal separation from a crossed plan diagonal between a and b."""
    span = y[a] + y[b]
    return math.sqrt(diagonal ** 2 - span ** 2)


def solve(v, y):
    """One evaluation of the chain. v: dimension values, y: half spacings."""
    d = {1: -v["D722"], 3: -v["D215"], 5: v["D143"]}
    d[20] = d[5] - v["P"]
    via_k = d[20] + crossed(v["K"], 20, 17, y)
    via_l = d[3] + crossed(v["L"], 3, 17, y)
    d[17] = 0.5 * (via_k + via_l)
    d[18] = d[17] + v["R"]
    d[19] = d[17] + v["S"]
    d[16] = v["L3756"] - v["D722"]
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
        d, vk, vl = solve(v, y)
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
        "not_in_published_chain": {
            "P12": "hangs on diagonal N; the crossed-plan reading misses the scan by 60-85 mm",
            "P21": "hangs on diagonal O, same reading, not verified",
            "P6": "plate 50-03 gives its transverse spacing D only",
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
