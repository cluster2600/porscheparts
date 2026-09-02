#!/usr/bin/env python3
"""Publie le rapport et les figures techniques du criblage EF F31."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORT = ROOT / "work/917-head-reference-cae-f31/report.json"
DEFAULT_OUTPUT = ROOT / "twins/reference-917-engine/evidence/f31"


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") != "passed_reference_solver_screening_not_physical_validation":
        raise ValueError("F31 source report is not a passed reference screening")
    if any(report.get("release_gates", {}).values()):
        raise ValueError("F31 source report has an open release gate")
    return report


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_text(value: str, project_root: Path, physical_ai_home: str) -> str:
    replacements = {
        str(project_root): "${PROJECT_ROOT}",
        str(project_root.resolve()): "${PROJECT_ROOT}",
    }
    if physical_ai_home:
        replacements[physical_ai_home] = "${PHYSICAL_AI_SKILL_HOME}"
    sanitized = value
    for source, replacement in sorted(
        replacements.items(), key=lambda item: len(item[0]), reverse=True
    ):
        sanitized = sanitized.replace(source, replacement)
    return sanitized


def sanitize_value(value: Any, project_root: Path, physical_ai_home: str) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, project_root, physical_ai_home)
    if isinstance(value, list):
        return [sanitize_value(item, project_root, physical_ai_home) for item in value]
    if isinstance(value, dict):
        return {
            key: sanitize_value(item, project_root, physical_ai_home)
            for key, item in value.items()
        }
    return value


def labels(report: dict[str, Any]) -> tuple[list[str], list[str]]:
    short = []
    ids = []
    for variant in report["variants"]:
        scenario = "NA" if variant["scenario_id"] == "type_912_5_0_na" else "Turbo"
        short.append(f"{scenario} {variant['architecture'].upper()}")
        ids.append(variant["id"])
    return short, ids


def render_architecture_comparison(report: dict[str, Any], path: Path) -> None:
    short, _ = labels(report)
    combined = [
        variant["finest_mesh_summary"]["load_cases"]["combined"]
        for variant in report["variants"]
    ]
    stress = [item["p95_von_mises_mpa"] for item in combined]
    displacement = [item["maximum_displacement_mm"] for item in combined]
    colors = ["#8c564b" if "2V" in label else "#1f77b4" for label in short]
    x = np.arange(len(short))

    figure, axes = plt.subplots(1, 2, figsize=(12.6, 5.4), constrained_layout=True)
    axes[0].bar(x, stress, color=colors, edgecolor="#222222", linewidth=0.7)
    axes[0].axhline(250.0, color="#d62728", linestyle="--", linewidth=1.4, label="Rp0,2 écran 20 °C: 250 MPa")
    axes[0].set_ylabel("Contrainte de von Mises P95 [MPa]")
    axes[0].set_title("Cas combiné pression + champ thermique")
    axes[0].legend(frameon=False, fontsize=8)

    axes[1].bar(x, displacement, color=colors, edgecolor="#222222", linewidth=0.7)
    axes[1].set_ylabel("Déplacement maximal [mm]")
    axes[1].set_title("Déformation du deck défeaturé")

    for axis, values in zip(axes, (stress, displacement)):
        axis.set_xticks(x, short)
        axis.grid(axis="y", alpha=0.25)
        for index, value in enumerate(values):
            axis.text(index, value * 1.015, f"{value:.3g}", ha="center", va="bottom", fontsize=8)

    figure.suptitle(
        "Porsche 917 — criblage EF F31 des architectures 2V/4V\n"
        "CalculiX 2.21, maille 5,5 mm; géométrie de deck conceptuelle, non corrélée",
        fontsize=12,
    )
    figure.savefig(path, dpi=180, metadata={"Software": "3dprinting993 F31"})
    plt.close(figure)


def render_convergence(report: dict[str, Any], path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12.6, 5.4), constrained_layout=True)
    scenario_axes = {
        "type_912_5_0_na": axes[0],
        "917_30_1973_turbo_5374": axes[1],
    }
    scenario_titles = {
        "type_912_5_0_na": "Type 912 5,0 L atmosphérique",
        "917_30_1973_turbo_5374": "917/30 5,374 L turbo",
    }
    for variant in report["variants"]:
        cases = sorted(variant["cases"], key=lambda item: item["mesh_size_mm"], reverse=True)
        mesh_sizes = [item["mesh_size_mm"] for item in cases]
        values = [
            item["load_cases"]["combined"]["maximum_displacement_mm"]
            for item in cases
        ]
        axis = scenario_axes[variant["scenario_id"]]
        axis.plot(
            mesh_sizes,
            values,
            marker="o",
            linewidth=1.8,
            label=variant["architecture"].upper(),
        )
    for scenario_id, axis in scenario_axes.items():
        axis.invert_xaxis()
        axis.set_title(scenario_titles[scenario_id])
        axis.set_xlabel("Taille maximale de maille [mm] (plus fin vers la droite)")
        axis.set_ylabel("Déplacement maximal combiné [mm]")
        axis.grid(alpha=0.25)
        axis.legend(frameon=False)
    figure.suptitle(
        "Convergence de maille F31 — déplacement du deck 2V/4V\n"
        "Seuil accepté: variation relative ≤ 10 % entre 6,5 et 5,5 mm",
        fontsize=12,
    )
    figure.savefig(path, dpi=180, metadata={"Software": "3dprinting993 F31"})
    plt.close(figure)


def publish(
    report_path: Path,
    output_root: Path,
    preflight_json: Path | None = None,
    preflight_markdown: Path | None = None,
) -> dict[str, Any]:
    report = load_report(report_path)
    figures = output_root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    published_report = output_root / "report.json"
    published_report.write_bytes(report_path.read_bytes())
    comparison = figures / "reference-fea-2v-4v.png"
    convergence = figures / "mesh-convergence.png"
    render_architecture_comparison(report, comparison)
    render_convergence(report, convergence)
    if (preflight_json is None) != (preflight_markdown is None):
        raise ValueError("preflight JSON and Markdown must be provided together")
    if preflight_json is not None and preflight_markdown is not None:
        preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
        if preflight.get("status") != "blocked":
            raise ValueError("F31 publication expects the observed blocked preflight")
        physical_ai_home = str(preflight.get("paths", {}).get("home", ""))
        sanitized = sanitize_value(preflight, ROOT, physical_ai_home)
        omniverse_root = output_root / "omniverse"
        omniverse_root.mkdir(parents=True, exist_ok=True)
        (omniverse_root / "preflight.json").write_text(
            json.dumps(sanitized, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown = sanitize_text(
            preflight_markdown.read_text(encoding="utf-8"), ROOT, physical_ai_home
        )
        (omniverse_root / "preflight.md").write_text(markdown, encoding="utf-8")
    files = {
        "report.json": sha256(published_report),
        "figures/reference-fea-2v-4v.png": sha256(comparison),
        "figures/mesh-convergence.png": sha256(convergence),
    }
    for relative_path in ("omniverse/preflight.json", "omniverse/preflight.md"):
        path = output_root / relative_path
        if path.is_file():
            files[relative_path] = sha256(path)
    publication = {
        "schema_version": "1.0.0",
        "phase": "F31",
        "status": "published_reference_solver_evidence_not_physical_validation",
        "files": files,
        "release_gates": report["release_gates"],
    }
    (output_root / "publication.json").write_text(
        json.dumps(publication, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return publication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight-json", type=Path)
    parser.add_argument("--preflight-markdown", type=Path)
    args = parser.parse_args()
    result = publish(
        args.report.resolve(),
        args.output.resolve(),
        args.preflight_json.resolve() if args.preflight_json else None,
        args.preflight_markdown.resolve() if args.preflight_markdown else None,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
