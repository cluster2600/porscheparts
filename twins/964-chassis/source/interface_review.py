"""Vue de recherche des interfaces, sans inventer de hauteur ou identifier un ancrage.

Les 18 identites documentaires restent dans la fiche, meme sans coordonnees.
Les XY hypotheses admissibles sont projetes sur un plan GRAPHIQUE sous le scan ;
ce plan et les traits verticaux ne sont ni des surfaces CAO ni des cotes Z.
"""
import argparse
import csv
import io
import json
import math
from pathlib import Path
import textwrap

import numpy as np

from tunnel_probe import sha256

ROOT = Path(__file__).resolve().parents[3]
TWIN = ROOT / "twins/964-chassis"
CONTRACT = TWIN / "derived/monocoque-interface.json"
LEDGER = ROOT / "catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json"
REGISTRATION = TWIN / "derived/scan-recalage-20260925.json"
COLOURS = {"DETERMINE": "#0072B2", "PARAMETRIQUE": "#D55E00",
           "MESURE_DESSIN": "#009E73", "MESURE_SCAN": "#CC79A7"}


def review_rows(contract, ledger):
    if any(contract["release_flags"].values()):
        raise ValueError("this review accepts only an unreleased interface contract")
    rows = []
    for value in ledger["declared_values"]:
        if value["details"]["kind"] != "datum_point":
            continue
        key = f"P{value['details']['point']}"
        point = contract["points"].get(key, {})
        if point and point["designation_source_value_id"] != value["value_id"]:
            raise ValueError(f"datum identity mismatch: {key}")
        status = point.get("x_statut", "MANQUANT")
        if status not in {*COLOURS, "MANQUANT", "INVALIDE"}:
            raise ValueError(f"unknown coordinate status: {key}")
        x, y = point.get("x_vehicle_mm_provisoire"), point.get("y_half_mm")
        for number in (x, y, point.get("x_local_mm"), point.get("transverse_span_mm"),
                       point.get("transverse_tolerance_mm")):
            if number is not None and (isinstance(number, bool) or not math.isfinite(number)):
                raise ValueError(f"non-finite coordinate or dimension: {key}")
        # A located status must carry its X; Y may be legitimately unpublished
        # (P15 on plate 50-05a): such a point is listed, not projected.
        if status in COLOURS and x is None:
            raise ValueError(f"missing hypothesis coordinate: {key}")
        plotted = status in COLOURS and y is not None
        rows.append({
            "datum_id": key, "designation": value["value_text"],
            "designation_source_value_id": value["value_id"],
            "transverse_source_value_id": point.get("transverse_source_value_id"),
            "transverse_span_mm": point.get("transverse_span_mm"),
            "transverse_tolerance_mm": point.get("transverse_tolerance_mm"),
            "x_relative_status": status, "x_relative_source": point.get("x_source", "UNKNOWN"),
            "x_relative_mm": point.get("x_local_mm") if status != "INVALIDE" else None,
            "x_vehicle_hypothesis_mm": x if plotted else None,
            "y_half_hypothesis_mm": y, "z_mm": None,
            "xyz_validated": False, "shown_as_xy_hypothesis": plotted,
            "measurement_required": "Identifier la surface fonctionnelle ; relever XYZ, axes et incertitudes des deux cotes.",
        })
    if not rows or not set(contract["points"]).issubset({r["datum_id"] for r in rows}):
        raise ValueError("interface identities missing from the measurement ledger")
    return rows


def measurement_csv(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def render(vertices, rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # ponytail: deterministic vertex subsampling is display-only, not a surface fit.
    points = vertices[::max(1, math.ceil(len(vertices) / 110000))]
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    display_z = float(low[2] - 250)
    plotted = [r for r in rows if r["shown_as_xy_hypothesis"]]
    withheld = textwrap.fill(", ".join(r["datum_id"] for r in rows if not r["shown_as_xy_hypothesis"]), width=44)
    legend = ("BLEU : X relatif documentaire seulement\n"
              "VERT : X releve a l'echelle sur la planche 50-05a\n"
              "ORANGE : X relatif derive non verifie\n"
              "Tous : recalage global non valide ; Z inconnu\n\n"
              "Hors projection (pas de XY exploitable) :\n" + withheld + "\n\n"
              "P6 : X manquant\nP15 : ecartement non publie\n"
              "P12 : traverse de BOITE, pas essieu arriere\n\n"
              "Les ecartements sont ceux des paires.\n"
              "La tolerance n'est pas celle de chaque Y.\n"
              "Aucune fixation identifiee par ces traits.\n\n"
              "A relever aussi : tunnel interieur, tringlerie,\n"
              "arbre/tube C4 et enveloppes en mouvement.\n"
              "Compatibilite 993 non etablie.")

    for mode in ("3d", "plan"):
        fig = plt.figure(figsize=(17, 10), facecolor="white")
        ax = fig.add_axes((0.04, 0.16, 0.69, 0.71), projection="3d" if mode == "3d" else None)
        if mode == "3d":
            ax.scatter(*points.T, c=points[:, 2], cmap="Greys", s=0.3, alpha=0.3,
                       depthshade=False, rasterized=True)
            for row in plotted:
                x, y = row["x_vehicle_hypothesis_mm"], row["y_half_hypothesis_mm"]
                colour = COLOURS[row["x_relative_status"]]
                ax.plot([x, x], [-y, y], [display_z, display_z], "o--", color=colour, ms=3)
                for side in (-y, y):
                    ax.plot([x, x], [side, side], [display_z, high[2]], ":", color=colour, alpha=0.45)
                label_y = -y - 90 if row["datum_id"] in ("P5", "P18") else y + 90
                ax.text(x, label_y, display_z, row["datum_id"], color=colour, fontsize=10)
            ax.set_zlim(display_z - 80, high[2])
            ax.set_zlabel("Z haut (mm de travail)", fontsize=9)
            ax.set_box_aspect((high[0] - low[0], high[1] - low[1], high[2] - display_z))
            ax.set_proj_type("ortho")
            ax.view_init(elev=-27, azim=-62)
        else:
            ax.scatter(points[:, 0], points[:, 1], c="#b1b6bb", s=0.3, alpha=0.35, rasterized=True)
            for row in plotted:
                x, y = row["x_vehicle_hypothesis_mm"], row["y_half_hypothesis_mm"]
                colour = COLOURS[row["x_relative_status"]]
                ax.plot([x, x], [-y, y], "o--", color=colour, ms=5, lw=1)
                # Place close longitudinal stations on alternating sides of the plan.
                side = -1 if row["datum_id"] in ("P5", "P18") else 1
                ax.annotate(row["datum_id"], (x, side * y), (x, side * (1050 if row["datum_id"] == "P19" else 900)),
                            ha="center", color=colour, fontsize=11,
                            arrowprops={"arrowstyle": "-", "color": colour, "lw": 0.8})
            ax.set_aspect("equal")
            ax.set_ylim(-1150, max(1250, high[1]))
            ax.grid(alpha=0.2)
        ax.set_xlim(low[0] - 100, high[0] + 100)
        ax.set_xlabel("X avant (mm de travail)", fontsize=10)
        ax.set_ylabel("Y gauche (mm de travail)", fontsize=10)
        ax.tick_params(labelsize=8)
        fig.text(0.74, 0.80, legend, va="top", fontsize=10, linespacing=1.7)
        fig.suptitle("964 — zones de recherche des interfaces, PAS des ancrages identifies", y=0.95, fontsize=17)
        fig.text(0.05, 0.07, "Pointilles : hypotheses XY ; leur longueur verticale ne borne PAS la hauteur d'un ancrage.\n"
                 "Plan de projection 3D place sous le scan pour la lecture : Z purement graphique. Aucun contact avec la peau n'est utilise.\n"
                 "Scan de dessous seulement — surfaces cachees inconnues ; ni CAO de fabrication, ni preuve de montage.", fontsize=11)
        fig.savefig(output / f"interface-review-{mode}.png", dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(REGISTRATION.read_text())
    if sha256(args.vertices) != registration["outputs"]["verts_vehicle.npy"]:
        raise ValueError("registered vertices do not match the recorded scan run")
    vertices = np.load(args.vertices, allow_pickle=False)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError("expected nonempty finite Nx3 vertices")
    rows = review_rows(json.loads(CONTRACT.read_text()), json.loads(LEDGER.read_text()))
    args.output.mkdir(parents=True, exist_ok=False)
    render(vertices, rows, args.output)
    sheet = args.output / "interface-measurements.csv"
    with sheet.open("w", newline="", encoding="utf-8") as stream:
        stream.write(measurement_csv(rows))
    report = {
        "classification": "interface_search_review_not_registered_hardpoints",
        "source_scan_sha256": registration["source_sha256"],
        "vertices_sha256": sha256(args.vertices),
        "input_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in
                         (CONTRACT, LEDGER, REGISTRATION, Path(__file__).resolve(), TWIN / "source/tunnel_probe.py")},
        "measurement_sheet_sha256": sha256(sheet),
        "documentary_identities": len(rows),
        "xy_hypothesis_pairs": sum(r["shown_as_xy_hypothesis"] for r in rows),
        "not_projected": [r["datum_id"] for r in rows if not r["shown_as_xy_hypothesis"]],
        "validated_xyz_points": 0,
        "missing_z_policy": "null; display projection plane is not a measurement",
        "scan_figures_publication": "local_only_redistribution_rights_unconfirmed",
        "release_flags": {"registered_hardpoints": False, "geometry_released": False,
                          "compatibility_993_validated": False, "manufacturing_released": False},
    }
    (args.output / "interface-review.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in ("documentary_identities", "xy_hypothesis_pairs", "validated_xyz_points")}))


if __name__ == "__main__":
    main()
