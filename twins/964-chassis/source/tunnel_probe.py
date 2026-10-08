"""Diagnostic du relief VISIBLE, jamais preuve de tunnel absent ou de volume libre.

Le scan de dessous ne renseigne ni les surfaces cachees, ni la variante C2/C4.
Les bandes historiques sont conservees pour comparer les resultats ; leurs
medians sont ponderes par les sommets, pas par l'aire ni par une incertitude.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(vertices):
    vertices = np.asarray(vertices)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("expected finite Nx3 vertices in the provisional vehicle frame")
    stations = []
    for x in range(-1400, 1, 200):
        points = vertices[(np.abs(vertices[:, 0] - x) < 50)
                          & (vertices[:, 2] > 60) & (vertices[:, 2] < 600)]
        bands = {
            "centre": points[np.abs(points[:, 1]) < 60],
            "left": points[(points[:, 1] > 250) & (points[:, 1] < 400)],
            "right": points[(points[:, 1] < -250) & (points[:, 1] > -400)],
        }
        stats = {}
        for name, band in bands.items():
            stats[name] = {"vertex_count": len(band), "z_p05_p50_p95_mm":
                           np.percentile(band[:, 2], [5, 50, 95]).tolist() if len(band) > 50 else None}
        enough = all(v["z_p05_p50_p95_mm"] is not None for v in stats.values())
        flanks = np.concatenate((bands["left"], bands["right"]))
        relief = float(np.median(bands["centre"][:, 2]) - np.median(flanks[:, 2])) if enough else None
        stations.append({"x_mm": x, "zone": "cabin" if x <= -400 else "front_axle_region",
                         "status": "observed_surface_only" if enough else "insufficient_coverage",
                         "bands": stats, "visible_relief_mm": relief})
    cabin = [s["visible_relief_mm"] for s in stations if s["zone"] == "cabin" and s["visible_relief_mm"] is not None]
    return {
        "classification": "visible_underbody_diagnostic_not_clearance_validation",
        "units": "mm, echelle de travail et repere F1 non qualifies en metrologie",
        "method": {"station_half_width_mm": 50, "z_interval_mm": [60, 600],
                   "centre_abs_y_below_mm": 60, "flanks_abs_y_between_mm": [250, 400],
                   "minimum_vertices_per_band": 51, "weighting": "vertex_count_not_surface_area"},
        "stations": stations,
        "cabin_summary": {"observed_stations": len(cabin), "expected_stations": 6,
                          "relief_min_max_mm": [min(cabin), max(cabin)] if cabin else None},
        "limits": ["Les coupes sont des bandes de sommets visibles, pas des sections de solide ferme.",
                   "Une surface plate peut masquer un tunnel, un carenage ou des organes internes.",
                   "Le residu de symetrie n'est pas une incertitude d'instrument.",
                   "Aucune interpolation des zones sans couverture, aucun rebouchage.",
                   "Tringlerie C2/C4, tube/arbre C4, debattements et acces restent a relever par variante."],
        "release_flags": {"tunnel_absence_proven": False, "free_volume_proven": False,
                          "c2_clearance_validated": False, "c4_clearance_validated": False,
                          "compatibility_993_validated": False, "manufacturing_released": False},
    }


def render(vertices, report, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharex=True, sharey=True)
    for ax, station in zip(axes.flat, report["stations"]):
        p = vertices[(np.abs(vertices[:, 0] - station["x_mm"]) < 50)
                     & (np.abs(vertices[:, 1]) < 500)
                     & (vertices[:, 2] > 60) & (vertices[:, 2] < 600)]
        p = p[::max(1, len(p) // 12000)]
        ax.scatter(p[:, 1], p[:, 2], s=0.5, alpha=0.35, color="#264653", rasterized=True)
        ax.axvspan(-60, 60, alpha=0.12, color="#e76f51")
        ax.axvspan(-400, -250, alpha=0.08, color="#2a9d8f")
        ax.axvspan(250, 400, alpha=0.08, color="#2a9d8f")
        value = station["visible_relief_mm"]
        label = f"relief median {value:+.1f} mm" if value is not None else "couverture insuffisante"
        ax.set_title(f"X = {station['x_mm']} mm\n{label}", fontsize=10)
        ax.set(xlim=(-500, 500), ylim=(60, 600), xlabel="Y gauche (mm de travail)", ylabel="Z haut (mm de travail)")
        ax.grid(alpha=0.2)
    fig.suptitle("964 — bandes transversales visibles, epaisseur 100 mm\nNi volume libre, ni profil interieur du tunnel", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(output / "visible-sections.png", dpi=150)
    plt.close(fig)

    p = vertices[::max(1, len(vertices) // 180000)]
    fig, ax = plt.subplots(figsize=(13, 7))
    dots = ax.scatter(p[:, 0], p[:, 1], c=p[:, 2], s=0.35, cmap="viridis", rasterized=True)
    for station in report["stations"]:
        ax.plot([station["x_mm"]] * 2, [-500, 500], color="#e76f51", lw=0.8)
    ax.axhspan(-60, 60, color="#e76f51", alpha=0.12)
    ax.set(aspect="equal", xlabel="X avant (mm de travail)", ylabel="Y gauche (mm de travail)",
           title="Scan 964 recale — rouge : bandes d'analyse, PAS un passage de transmission valide")
    fig.colorbar(dots, ax=ax, label="Z (mm de travail, sol non qualifie)")
    fig.tight_layout()
    fig.savefig(output / "scan-plan.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vertices", type=Path, required=True)
    parser.add_argument("--scan", type=Path, required=True)
    parser.add_argument("--registration-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration_report.read_text())
    vertices_hash, scan_hash = sha256(args.vertices), sha256(args.scan)
    if scan_hash != registration["source_sha256"] or vertices_hash != registration["outputs"][args.vertices.name]:
        raise ValueError("scan or registered vertices do not match the registration report")
    vertices = np.load(args.vertices, allow_pickle=False)
    report = probe(vertices)
    report["provenance"] = {"scan_sha256": scan_hash, "vertices_sha256": vertices_hash,
                            "registration_report_sha256": sha256(args.registration_report),
                            "script_sha256": sha256(__file__),
                            "input_binding_verified_not_physical_accuracy": True}
    args.output.mkdir(parents=True, exist_ok=False)
    render(vertices, report, args.output)
    (args.output / "tunnel-visibility.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(report["cabin_summary"]))
    print("Visible-surface diagnostic complete; all clearance and release gates remain closed.")


if __name__ == "__main__":
    main()
