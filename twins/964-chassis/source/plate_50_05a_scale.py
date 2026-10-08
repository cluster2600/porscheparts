"""Scale plate 50-05a to place the points it draws without a dimension.

Plate 50-05a's plan view is an engineering drawing at a fixed scale. Eight of
its markers have a longitudinal position known from published dimensions
(datum_chain_50_05a.py). Fitting scale and offset to them, and checking the
residuals, turns the drawing into a measured source for the markers that carry
no printed dimension: P12, P13, P14, P15.

The marker x coordinates were read by hand on the page rendered at 400 dpi
(local copy of volume V, page 9), on zoomed crops with a 20 px grid: crossing
of the marker's cross-hair, or centre of its dot. They are transcription data,
like the dimensions; the plate itself is not in the repository. Reading
resolution about +/- 2 px, i.e. +/- 2.3 mm at the fitted scale.

Plate 50-02 (underbody, page 6 at 400 dpi) is read the same way for P12, with
its scale set by R between P17 and P18; it carries no other calibration
point near the rear, so it serves as a second opinion on P12 only. The two
drawings together check the rear of the published chain.

Output: ../derived/plate-50-05a-scaled.json. Standard library only.

    python3 plate_50_05a_scale.py
"""
import json
import statistics

CHAIN = json.load(open("../derived/datum-chain-50-05a.json"))
PAGE_X_PX = {           # page 9 at 400 dpi, plan view, left-hand markers
    "zero_line": 1222.8,
    "P1": 579.0,
    "P3": 1030.8,
    "P5": 1348.2,
    "P17": 1616.2,
    "P18": 2717.2,
    "P19": 2794.6,
    "P16": 3905.0,
    "P12": 2707.2,
    "P13": 2780.4,
    "P14": 3251.2,
    "P15": 3895.4,
}
PLATE_50_02_Y_PX = {    # page 6 at 400 dpi, left and right markers (y grows rearward)
    "P17": (1716.4, 1715.0),
    "P18": (2714.6, 2709.8),
    "P12": (2705.6, 2697.8),
}
UNDIMENSIONED = {
    "P12": "Mount - transmission cross member (take-up hole, transmission carrier)",
    "P13": "Mount - outer cross tube, rear axle (marker read on its leader, least certain)",
    "P14": "Mount - rear axle spring strut",
    "P15": "Mount - engine bearing",
}


def main():
    known = {"zero_line": 0.0}
    known.update({name: CHAIN["points"][name]["d_behind_0_line_mm"]
                  for name in ("P1", "P3", "P5", "P17", "P18", "P19", "P16")})
    xs = [PAGE_X_PX[n] for n in known]
    ds = [known[n] for n in known]
    mx, md = statistics.mean(xs), statistics.mean(ds)
    slope = sum((x - mx) * (d - md) for x, d in zip(xs, ds)) / sum((x - mx) ** 2 for x in xs)
    offset = md - slope * mx
    residuals = {n: round(offset + slope * PAGE_X_PX[n] - known[n], 1) for n in known}
    sd = statistics.stdev(residuals.values())
    scaled = {n: {"d_behind_0_line_mm": round(offset + slope * PAGE_X_PX[n], 1),
                  "u_mm": round(2.0 * sd, 1), "what": UNDIMENSIONED[n]}
              for n in UNDIMENSIONED}
    y = {k: statistics.mean(v) for k, v in PLATE_50_02_Y_PX.items()}
    mm_per_px_02 = 1245.0 / (y["P18"] - y["P17"])
    d17 = CHAIN["points"]["P17"]["d_behind_0_line_mm"]
    p12_02 = d17 + (y["P12"] - y["P17"]) * mm_per_px_02
    p12_05a = scaled["P12"]["d_behind_0_line_mm"]
    p12_chain = CHAIN["points"]["P12"]["d_behind_0_line_mm"]
    p12_bracketed = CHAIN["rear_reading"]["bracketed_alternative_d_mm"]["P12"]
    rear_check = {
        "P12_plate_50_05a_mm": p12_05a,
        "P12_plate_50_02_mm": round(p12_02, 1),
        "drawings_differ_by_mm": round(p12_05a - p12_02, 1),
        "P12_chain_unbracketed_mm": p12_chain,
        "P12_chain_bracketed_mm": p12_bracketed,
        "chain_minus_drawings_mm": {
            "unbracketed": round(p12_chain - 0.5 * (p12_05a + p12_02), 1),
            "bracketed": round(p12_bracketed - 0.5 * (p12_05a + p12_02), 1),
        },
        "verdict": "the drawings select the unbracketed reading of N and O",
    }
    report = {
        "schema_version": "1.0.0",
        "twin": "964-chassis",
        "classification": "scaled_from_published_drawing_not_a_dimension",
        "source": "SRC-PORSCHE-WORKSHOP-MANUAL-964-VOL5-BODY, plate 50-05a plan view, page 9 at 400 dpi",
        "fit": {"mm_per_px": round(slope, 5), "drawing_scale": f"1:{slope * 400 / 25.4:.1f}",
                "calibration_points": list(known), "residuals_mm": residuals,
                "residual_sd_mm": round(sd, 1)},
        "page_x_px": PAGE_X_PX,
        "points": scaled,
        "plate_50_02": {"y_px": PLATE_50_02_Y_PX, "mm_per_px": round(mm_per_px_02, 4),
                        "calibration": "R = 1245 between P17 and P18 only"},
        "rear_chain_check": rear_check,
        "reading": "u_mm is twice the calibration residual sd; it covers drawing and reading error, not the plate's own manufacturing tolerance",
    }
    with open("../derived/plate-50-05a-scaled.json", "w") as f:
        json.dump(report, f, indent=1)
        f.write("\n")
    print(f"plate 50-05a: {slope:.4f} mm/px (1:{slope * 400 / 25.4:.1f}), "
          f"calibration residual sd {sd:.1f} mm on {len(known)} published points")
    for n, r in residuals.items():
        print(f"  {n:<10} residual {r:+5.1f} mm")
    print()
    for n, row in scaled.items():
        print(f"{n:<4} {row['d_behind_0_line_mm']:8.1f} +/- {row['u_mm']} mm  {row['what']}")
    print(f"\nP12: plate 50-05a {p12_05a:.1f}, plate 50-02 {p12_02:.1f}; chain {p12_chain:.1f} "
          f"(unbracketed N, O), {p12_bracketed:.1f} (bracketed)")
    print("\nwrote ../derived/plate-50-05a-scaled.json")


if __name__ == "__main__":
    main()
