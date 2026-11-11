#!/usr/bin/env python3
"""Put published strength beside the computed peak temperature of each alloy.

The owner asked on 2026-11-11 for a middle ground between heat dissipation
and strength. Neither screen can choose an alloy, but the two can be read
side by side: for every alloy with a published strength, this script takes
the peak head-alloy temperature the assembly screen computed at that alloy's
conductivity, and the published yield strength at that temperature.

Rules, so that nothing is invented:

* a peak temperature is read only at a conductivity that was solved;
* a yield at temperature is a straight line between two published points,
  and is given only inside the published range: never extrapolated;
* where a source gives room-temperature strength only, the hot yield is
  "not published";
* every alloy is also read at one reference temperature, 250 C, so that
  alloys can be compared even where the computed peak lies beyond every
  published strength;
* a row says whether its conductivity and its strength are for the same
  heat-treatment condition.

Also writes ``media/alloy-ranking.png``: peak temperature against
conductivity for every variant, with the published head-temperature limits.

Usage: alloy_tradeoff.py PARAMS_DIR MEDIA_DIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "935-cad-twin-alloy-tradeoff/1"
REFERENCE_C = 250.0        # the published hot-spot limit: one temperature at which to compare the alloys
LIMITS_C = {"Mackerle, cast aluminium heads": 235.0, "Mackerle, hot spots": 250.0, "Heywood, high heat-flux regions": 300.0}


def yield_at(points: dict, temperature_c: float):
    """Published yield at a temperature by linear interpolation, or None outside the published range."""

    known = sorted((float(t), float(v)) for t, v in points.items())
    if len(known) < 2 or not known[0][0] <= temperature_c <= known[-1][0]:
        return None
    for (t0, v0), (t1, v1) in zip(known, known[1:]):
        if t0 <= temperature_c <= t1:
            return round(v0 + (v1 - v0) * (temperature_c - t0) / (t1 - t0), 1)
    return None


def tradeoff(strength: dict, candidates: dict, assembly: dict) -> list:
    conductivity = {c["id"]: c["conductivity_W_per_mK"] for c in candidates["candidates"]}
    variant = assembly["variants"][assembly["ranking_variant"]]
    peak = {r["alloy_conductivity_W_per_mK"]: r["peak_C"]["alloy"] for r in variant["by_conductivity"]}
    rows = []
    for item in strength["rows"]:
        ks = sorted({conductivity[i] for i in item["conductivity_rows"] if i in conductivity})
        peaks = [peak[k] for k in ks if k in peak]
        published = item["yield_MPa_by_temperature_C"]
        hot = [yield_at(published, t) for t in peaks]
        rows.append({
            "id": item["id"], "alloy": item["alloy"], "condition": item["condition"],
            "conductivity_W_per_mK": ks or None,
            "peak_head_alloy_C": [min(peaks), max(peaks)] if peaks else None,
            "yield_MPa_at_room_temperature": published.get("20"),
            "yield_MPa_published_up_to_C": max(float(t) for t in published),
            "yield_MPa_at_reference_temperature": yield_at(published, REFERENCE_C),
            "peak_C_above_the_coolest_candidate": (None if not peaks else
                                                   [round(min(peaks) - min(peak.values()), 2), round(max(peaks) - min(peak.values()), 2)]),
            "yield_MPa_at_the_computed_peak": (None if not peaks or any(v is None for v in hot) else [min(hot), max(hot)]),
            "hot_yield_status": ("no conductivity published: not on the thermal screens" if not ks else
                                 "interpolated between published points" if peaks and all(v is not None for v in hot) else
                                 "not published at the computed peak temperature"),
            "condition_match": item["condition_match"], "strength_verification": item["verification"],
        })
    return rows


def plot(assembly: dict, candidates: dict, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9.5, 6.4), dpi=110)
    styles = {"declared": ("#8a8a8a", "--", "declared case: gas 900 °C, 400 W/(m²·K); no oil"),
              "declared_oil": ("#4d7ea8", "--", "declared case with the oil film"),
              "published_loading_oil": ("#c0392b", "-", "published wall loading (465 and 145 kW/m²), oil film, air 150 W/(m²·K)"),
              "published_loading_oil_air_233": ("#2e7d32", "-", "the same with air at 233 W/(m²·K)")}
    for name, variant in assembly["variants"].items():
        rows = sorted(variant["by_conductivity"], key=lambda r: r["alloy_conductivity_W_per_mK"])
        colour, line, label = styles.get(name, ("black", "-", name))
        ax.plot([r["alloy_conductivity_W_per_mK"] for r in rows], [r["peak_C"]["alloy"] for r in rows],
                line, marker="o", color=colour, label=label, linewidth=1.8, markersize=4)
    ax.axhspan(235.0, 250.0, color="#f4d03f", alpha=0.35, label="published limit, 235 to 250 °C (Mackerle)")
    ax.axhline(300.0, color="#b7791f", linewidth=1.0, linestyle=":", label="about 300 °C (Heywood)")
    ax.set_xlabel("Head alloy thermal conductivity at room temperature, W/(m·K)")
    ax.set_ylabel("Peak head-alloy temperature, °C")
    ax.set_title("Assembly thermal screen: peak head temperature against conductivity\n"
                 "hypothesis cases, not an engine prediction", fontsize=11)
    ax.grid(True, linewidth=0.3)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main(params, media) -> None:
    params, media = Path(params), Path(media)
    strength = json.loads((params / "alloy-strength.json").read_text())
    candidates = json.loads((params / "alloy-candidates.json").read_text())
    assembly = json.loads((params / "assembly-thermal.json").read_text())
    rows = tradeoff(strength, candidates, assembly)
    (params / "alloy-tradeoff.json").write_text(json.dumps({
        "schema": SCHEMA,
        "ranking_variant": assembly["ranking_variant"],
        "limits_C": LIMITS_C,
        "reference_temperature_C": REFERENCE_C,
        "rule": "peak temperatures are read at solved conductivities only; a hot yield is a straight line between two "
                "published points and is never extrapolated",
        "rows": rows,
        "claims": "published strengths beside computed screen temperatures; no value is a design allowable, no alloy "
                  "is qualified, and the temperatures are those of a hypothesis case",
    }, indent=2) + "\n")
    plot(assembly, candidates, media / "alloy-ranking.png")
    for r in rows:
        print(r["id"], r["conductivity_W_per_mK"], r["peak_head_alloy_C"], r["peak_C_above_the_coolest_candidate"],
              r["yield_MPa_at_room_temperature"], r["yield_MPa_at_reference_temperature"], r["hot_yield_status"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
