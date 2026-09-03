#!/usr/bin/env python3
"""Compile une matrice traçable de coupons à chaud pour la culasse F38."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_plan(contract: dict, contract_path: Path) -> dict:
    rows = []
    total = 0
    for family in contract["test_families"]:
        count = (
            len(family["temperatures_degC"])
            * len(family["orientations"])
            * int(family["replicates"])
        )
        total += count
        rows.append(
            {
                "id": family["id"],
                "standard": family["standard"],
                "temperatures_degC": family["temperatures_degC"],
                "orientations": family["orientations"],
                "replicates_per_condition": family["replicates"],
                "coupon_count": count,
                "outputs": family["outputs"],
            }
        )

    return {
        "schema_version": "1.0.0",
        "phase": "F38",
        "kind": "physical_coupon_qualification_plan",
        "inputs": {
            "contract": str(contract_path),
            "contract_sha256": sha256(contract_path),
        },
        "candidate": contract["candidate"],
        "matrix": rows,
        "coupon_count_total": total,
        "acceptance_logic": contract["acceptance_logic"],
        "official_sources": contract["official_sources"],
        "result": {
            "campaign_executed": False,
            "material_card_qualified": False,
            "manufacturing_authorized": False,
            "reason": "plan compiled; no physical specimen result supplied",
        },
        "release_gates": contract["release_gates"],
    }


def render(plan: dict, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = plan["matrix"]
    labels = [row["id"].replace("_", "\n") for row in rows]
    counts = [row["coupon_count"] for row in rows]
    fig, ax = plt.subplots(figsize=(12, 6.75), facecolor="#101820")
    ax.set_facecolor("#101820")
    bars = ax.bar(labels, counts, color="#d4a64a", edgecolor="#f4d58d", linewidth=0.8)
    ax.set_title("F38 — matrice physique de qualification CP1 à chaud", color="white", fontsize=17, weight="bold")
    ax.set_ylabel("Nombre minimal de coupons", color="#d9e2e8")
    ax.tick_params(axis="x", colors="#d9e2e8", labelsize=8)
    ax.tick_params(axis="y", colors="#d9e2e8")
    for spine in ax.spines.values():
        spine.set_color("#50606b")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, count + 0.8, str(count), ha="center", color="white", weight="bold")
    ax.text(
        0.01,
        0.98,
        f"Total: {plan['coupon_count_total']} coupons — plan uniquement, essais physiques non exécutés",
        transform=ax.transAxes,
        va="top",
        color="#ff9b85",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(output, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    plan = build_plan(contract, args.contract)
    report = args.output / "f38-hot-coupon-qualification-plan.json"
    report.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render(plan, args.output / "917-head-f38-hot-coupon-matrix.png")
    print(json.dumps({"report": str(report), "coupon_count_total": plan["coupon_count_total"], "qualified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
