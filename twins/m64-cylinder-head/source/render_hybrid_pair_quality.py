"""Render observed mesh defect counts; never a thermal or geometry rendering."""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", action="store_true", help="Render the later 57-group checkpoint.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    evidence = root / "twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json"
    key = "gas_hybrid_group_correction" if args.groups else "gas_hybrid_pair_correction"
    result = json.loads(evidence.read_text())[key]
    comparison = result["mapped_comparison"]
    if result["mesh_quality_accepted"] or result["CFD_qualified"]:
        raise ValueError("This checkpoint must not label the rejected mesh accepted.")
    if comparison["failed_checks_after"] != 5:
        raise ValueError("Review the caption before rendering a different checkpoint.")
    names = ["underdeterminedCells", "lowWeightFaces", "nonOrthoFaces"]
    labels = ["Faible déterminant\n(cellules)", "Faible poids\n(faces)", "Non-orthogonalité > 70°\n(faces, avertissement)"]
    rows = [comparison["sets"][name] for name in names]
    for row in rows:
        if row["candidate_count"] - row["baseline_count"] != row["native_count_delta"]:
            raise ValueError("Inconsistent native counts.")
    before = [r["baseline_count"] for r in rows]
    after = [r["candidate_count"] for r in rows]
    fig, ax = plt.subplots(figsize=(11.5, 6.7))
    fig.patch.set_facecolor("#f6f8fb")
    ax.set_facecolor("#f6f8fb")
    x = list(range(len(names)))
    before_label = "Avant : après les 252 paires" if args.groups else "Avant : candidat V2"
    after_label = "Après : 57 groupes supplémentaires" if args.groups else "Après : 252 unions natives"
    ax.bar([v - .19 for v in x], before, .36, color="#8693a4", label=before_label)
    ax.bar([v + .19 for v in x], after, .36, color="#0072b2", label=after_label)
    for i, row in enumerate(rows):
        for shift, value in [(-.19, before[i]), (.19, after[i])]:
            ax.text(i + shift, value + 45, f"{value:,}".replace(",", " "), ha="center", fontsize=11)
        ax.text(i, max(before[i], after[i]) + 245, f"Δ {row['native_count_delta']}", ha="center",
                fontsize=12, fontweight="bold", color="#26394b")
    ax.set_xticks(x, labels, fontsize=11)
    ax.set_ylim(0, max(before + after) * 1.24)
    ax.set_ylabel("Nombre d'entités signalées", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.18)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False)
    fig.suptitle("M64 — amélioration partielle du maillage d'admission", x=.09, ha="left",
                 fontsize=17, fontweight="bold")
    fig.text(.09, .89, "OpenFOAM natif • comparaison par identifiants remappés • aucune modification de la CAO", fontsize=10)
    fig.text(.09, .075, "5 familles restent en échec. Aucun calcul CFD, thermique, résistance ou LPBF validé.", fontsize=11, color="#8c2d22")
    fig.text(.09, .04, "Ensembles non additionnables • certains indicateurs moyens se dégradent légèrement • reçus dans GitHub", fontsize=9)
    fig.subplots_adjust(left=.09, right=.97, bottom=.21, top=.83)
    kind = "group" if args.groups else "pair"
    output = root / f"docs/images/m64-hybrid-{kind}-quality-20260909.png"
    fig.savefig(output, dpi=150, metadata={"Software": "matplotlib"})
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
