"""Tie the published datum chain to the scan's vehicle frame, and check it.

`datum_chain_50_05a.py` places the datum network along X relative to the
plate's 0 line (the line through the front strut mounts) from published
dimensions only. The scan's vehicle frame puts X = 0 on the fitted front
wheel centres. One offset, delta, links the two: X_vehicle = delta - d.

This script measures, on the scan, features whose published d is known and
that the scan resolves, each in a small window found by inspection:

    P5   outer front cross-member mount: a round boss at |Y| = 385 (C = 770)
    P17  front jacking receptacle: the cup at |Y| ~ 650 (E = 1330)
    P19  rear lifting-platform pad: a ring at |Y| ~ 510-540 (H = 1018)

Each gives delta = X_measured + d. Their spread tests the chain; their mean
ties it. Two more features check the rear without entering delta:

    P21  rear engine-mount cradle: a U in side view at |Y| 280-360 (I = 640),
         whose centre should fall at delta - d(P21)
    carrier bolts at |Y| ~ 145: the transmission carrier's own fixings, kept
         as a diagnostic. They sit 30 mm behind P12 and 50 mm lower than the
         body take-up hole N and O imply, so they are not P12.

The scan is not in the repository (raw-scans/ is ignored). Set TWIN_SCAN to
the OBJ and TWIN_TRANSFORM to vehicle_transform.json; run where numpy,
trimesh and matplotlib exist (the cadsim image does).

Outputs: ../evidence/scan-tie-50-05a.json and ../evidence/scan-tie-50-05a.png.
"""
import json
import os
import statistics

import numpy as np

CHAIN = json.load(open("../derived/datum-chain-50-05a.json"))
D = {name: row["d_behind_0_line_mm"] for name, row in CHAIN["points"].items()}

# feature: (point, x window, |y| window, z window, method, role)
FEATURES = {
    "P5_boss": ("P5", (-200, -130), (360, 410), (300, 360), "circle", "tie"),
    "P17_cup": ("P17", (-530, -410), (600, 700), (100, 240), "circle", "tie"),
    "P19_ring": ("P19", (-1840, -1740), (480, 570), (100, 240), "circle", "tie"),
    "P21_cradle": ("P21", (-3200, -3040), (280, 360), (290, 385), "circle_xz", "check"),
    "carrier_bolts": (None, (-1765, -1705), (120, 170), (230, 290), "centroid", "diagnostic"),
}
WHEEL_CENTRE_U_MM = 7.0   # front wheel centre fit, twin README


def fit_circle(x, y):
    """Kasa fit refined by Cauchy-weighted IRLS: centre and radius."""
    a = np.c_[x, y, np.ones(len(x))]
    b = x ** 2 + y ** 2
    for _ in range(25):
        sol, *_ = np.linalg.lstsq(a, b, rcond=None)
        cx, cy = sol[0] / 2, sol[1] / 2
        r = np.sqrt(sol[2] + cx ** 2 + cy ** 2)
        res = np.abs(np.hypot(x - cx, y - cy) - r)
        w = 1.0 / (1.0 + (res / max(np.median(res) * 3, 0.3)) ** 2)
        a = np.c_[x, y, np.ones(len(x))] * w[:, None]
        b = (x ** 2 + y ** 2) * w
    return float(cx), float(cy), float(r), float(np.median(res))


def load_vehicle_vertices():
    import trimesh
    m = np.array(json.load(open(os.environ["TWIN_TRANSFORM"]))).reshape(4, 4)
    mesh = trimesh.load(os.environ["TWIN_SCAN"], process=False)
    v = np.asarray(mesh.vertices, dtype=np.float64)
    return (m[:3, :3] @ v.T).T + m[:3, 3]


def measure(v):
    rows = {}
    for name, (point, xw, yw, zw, method, role) in FEATURES.items():
        for side, sign in (("left", 1), ("right", -1)):
            sel = ((v[:, 0] > xw[0]) & (v[:, 0] < xw[1]) & (sign * v[:, 1] > yw[0])
                   & (sign * v[:, 1] < yw[1]) & (v[:, 2] > zw[0]) & (v[:, 2] < zw[1]))
            s = v[sel]
            if method == "circle":
                cx, cy, r, res = fit_circle(s[:, 0], s[:, 1])
                row = {"x_mm": cx, "y_mm": cy, "radius_mm": r, "fit_residual_median_mm": res}
            elif method == "circle_xz":
                cx, cz, r, res = fit_circle(s[:, 0], s[:, 2])
                row = {"x_mm": cx, "y_mm": float(s[:, 1].mean()), "z_mm": cz, "radius_mm": r,
                       "fit_residual_median_mm": res}
            else:
                row = {"x_mm": float(s[:, 0].mean()), "y_mm": float(s[:, 1].mean())}
            row.update({"point": point, "role": role, "n_vertices": int(len(s))})
            if point in D:
                row["delta_mm"] = row["x_mm"] + D[point]
            rows[f"{name}_{side}"] = row
    return rows


def plot(v, rows, delta, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = v[(v[:, 2] < 420) & (np.abs(v[:, 1]) < 800)]
    s = s[np.random.default_rng(0).choice(len(s), min(len(s), 900000), replace=False)]
    fig, ax = plt.subplots(figsize=(22, 8), dpi=90)
    ax.scatter(s[:, 0], s[:, 1], s=0.02, c="0.75")
    old = {"P20": 705.1, "P3": 148.2, "P5": 21.3, "P17": -506.0, "P18": -1751.0, "P19": -1834.0}
    for name, row in CHAIN["points"].items():
        y = row["y_half_mm"]
        x = delta - row["d_behind_0_line_mm"]
        if y is None:
            ax.axvline(x, color="tab:blue", lw=0.8, ls=":")
            ax.text(x, 760, name, color="tab:blue", fontsize=8, ha="center")
            continue
        ax.plot([x, x], [y, -y], "o", color="tab:blue", ms=6)
        ax.text(x + 15, y + 25, name, color="tab:blue", fontsize=9)
        if name in old:
            ax.plot([old[name]] * 2, [y, -y], "x", color="tab:red", ms=7)
    drawing = json.load(open("../derived/plate-50-05a-scaled.json"))["points"]
    y_half = {"P13": 600.0, "P14": 308.3, "P15": None}
    for name, row in drawing.items():
        if name not in y_half:
            continue
        x = delta - row["d_behind_0_line_mm"]
        if y_half[name] is None:
            ax.axvline(x, color="tab:green", lw=0.8, ls=":")
            ax.text(x, 760, name, color="tab:green", fontsize=8, ha="center")
            continue
        ax.plot([x, x], [y_half[name], -y_half[name]], "s", color="tab:green", ms=6)
        ax.text(x + 15, y_half[name] + 25, name, color="tab:green", fontsize=9)
    for key, row in rows.items():
        ax.plot(row["x_mm"], row["y_mm"], "+", color="black", ms=12, mew=1.5)
        if row["role"] == "diagnostic":
            ax.text(row["x_mm"] - 15, row["y_mm"] + 20, "carrier bolts", fontsize=7, ha="right")
    ax.axvline(0, color="k", lw=0.8)
    ax.axvline(delta, color="tab:blue", lw=0.8, ls="--")
    ax.text(delta - 10, -770, "plate 0 line", color="tab:blue", fontsize=8, ha="right")
    ax.text(10, -730, "front wheel centres", fontsize=8)
    ax.set_aspect("equal")
    ax.set_xlim(-3400, 950)
    ax.set_ylim(-800, 800)
    ax.set_xlabel("X vehicle (mm, + forward)")
    ax.set_title("964 datum network on the scan, from below. Blue: published chain (plates 50-02/03/05a) "
                 "tied by delta; green: scaled off plate 50-05a; red x: previous network; black +: scan features")
    fig.tight_layout()
    fig.savefig(path)


def main():
    v = load_vehicle_vertices()
    rows = measure(v)
    published = [r["delta_mm"] for r in rows.values() if r["role"] == "tie"]
    delta = statistics.mean(published)
    spread = statistics.stdev(published)
    u_delta = (spread ** 2 / len(published) + WHEEL_CENTRE_U_MM ** 2) ** 0.5
    cradle = [r for r in rows.values() if r["point"] == "P21"]
    cradle_d = statistics.mean(delta - r["x_mm"] for r in cradle)
    bolts = [r for r in rows.values() if r["role"] == "diagnostic"]
    bolts_d = statistics.mean(delta - r["x_mm"] for r in bolts)
    p5_x = delta - D["P5"]
    report = {
        "schema_version": "1.0.0",
        "twin": "964-chassis",
        "classification": "scan_measurement_against_published_chain",
        "scan": "964widebodyunderside2poin13.obj, not in the repository; vehicle frame from vehicle_transform.json",
        "features": rows,
        "delta": {
            "definition": "X of the plate 0 line in the scan vehicle frame; X_vehicle = delta - d",
            "value_mm": round(delta, 1),
            "spread_sd_mm": round(spread, 1),
            "u_mm": round(u_delta, 1),
            "from": "P5, P17 and P19, both sides; the P21 cradle and the carrier bolts are checks, not ties",
            "reading": "the 0 line lies behind the fitted front wheel centres, as a strut-mount line does with 4 deg 25 min caster",
        },
        "points_vehicle_frame_mm": {
            name: {"x_mm": round(delta - row["d_behind_0_line_mm"], 1), "y_half_mm": row["y_half_mm"]}
            for name, row in CHAIN["points"].items()
        },
        "p21_check": {
            "cradle_d_behind_0_line_mm": round(cradle_d, 1),
            "chain_d_mm": D["P21"],
            "bracketed_reading_d_mm": CHAIN["rear_reading"]["bracketed_alternative_d_mm"]["P21"],
            "difference_chain_mm": round(cradle_d - D["P21"], 1),
            "difference_bracketed_mm": round(cradle_d - CHAIN["rear_reading"]["bracketed_alternative_d_mm"]["P21"], 1),
            "reading": "the cradle is read as the rear engine mount at the published 640 mm spacing; its centre is not the take-up hole itself",
        },
        "carrier_bolts_diagnostic": {
            "d_behind_0_line_mm": round(bolts_d, 1),
            "chain_P12_d_mm": D["P12"],
            "reading": "fixings of the removable transmission carrier, not the body take-up hole P12",
        },
        "span_P5_P12_mm": {
            "value": round(D["P12"] - D["P5"], 1),
            "sources": ["MANUAL (50-05a, 143)", "MANUAL (O and N, unbracketed)"],
            "previous_values": {"diagonal_P_and_bracketed_N": 1724.3, "scan_carrier_bolts": 1567.3},
        },
        "p5_vehicle_x_mm": round(p5_x, 1),
    }
    json.dump(report, open("../evidence/scan-tie-50-05a.json", "w"), indent=1)
    plot(v, rows, delta, "../evidence/scan-tie-50-05a.png")
    print(json.dumps({k: report[k] for k in ("delta", "p21_check", "carrier_bolts_diagnostic", "span_P5_P12_mm")}, indent=1))
    for key, row in rows.items():
        print(f"{key:<20} x {row['x_mm']:8.1f}  y {row['y_mm']:7.1f}  delta {row.get('delta_mm', float('nan')):6.1f}  n {row['n_vertices']}")


if __name__ == "__main__":
    main()
