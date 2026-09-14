#!/usr/bin/env python3
"""Passe chaque ressort catalogue dans le modèle V1 et produit un classement.

uv run --no-project --with numpy python twins/m64-cylinder-head/source/valvetrain/spring_selection.py

Sélection sur fiches publiées, pas qualification. Le logement (hauteur montée,
Ø maxi) et la masse ressort/coupelle sont des paramètres NON sourcés.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import valvetrain as vt  # noqa: E402

ROOT = HERE.parents[3]
CANDIDATES = HERE / "spring_candidates.json"
OUT = ROOT / "twins/m64-cylinder-head/evidence/valvetrain-v1/spring-selection-results.json"
LBF = 4.4482216152605
INCH = 25.4

CRITERIA = {
    "margin_rpm": 8000.0, "required_margin": 1.25,
    "bind_reserve_mm": 1.0,
    "sdof_rpm": 7500.0, "max_separation_mm": 0.05,
    "stress_limit_MPa": None,
    "stress_limit_source": "aucune : aucun fournisseur ne publie le diamètre de fil, la contrainte n'est calculée pour aucun candidat",
}

HOUSING = {  # paramètres de logement non sourcés
    "installed_height_mm": vt.P(None, "mm", "assumed",
                                "Logement non conçu : on monte chaque ressort à la hauteur de sa fiche (calage supposé possible)."),
    "max_outer_diameter_mm": vt.P(30.0, "mm", "assumed",
                                  "Ø maxi de lamage supposé, entraxe soupapes 4V non conçu ; à remplacer par la CAO."),
    "spring_mass_kg": vt.P(0.045, "kg", "assumed", "Masse ressort non publiée ; estimation ressort double acier."),
}


def rate_N_per_mm(c: dict) -> tuple[float, str]:
    """Raideur : dérivée de deux points publiés si possible, sinon valeur publiée."""
    if c.get("open_load_lbf") is not None and c.get("open_lift_mm"):
        return (c["open_load_lbf"] - c["seat_load_lbf"]) * LBF / c["open_lift_mm"], "derived_seat_open"
    r = c.get("rate_published")
    if r:
        f = {"lbf/mm": LBF, "lbf/in": LBF / INCH, "N/mm": 1.0}[r["unit"]]
        return r["value"] * f, "published_unit_inferred" if r.get("unit_inferred") else "published"
    raise ValueError(f"{c['id']}: no_rate")


def spring_from_candidate(c: dict, lift_mm: float, installed_mm: float | None = None,
                          spring_mass_kg: float = HOUSING["spring_mass_kg"]["value"]) -> dict:
    k_mm, rate_src = rate_N_per_mm(c)
    inst = c["installed_height_mm"] if installed_mm is None else installed_mm
    seat = c["seat_load_lbf"] * LBF + k_mm * (c["installed_height_mm"] - inst)
    k = k_mm * 1e3
    return {"rate_N_m": k, "rate_source": rate_src, "mass_kg": spring_mass_kg, "preload_N": seat,
            "preload_deflection_m": seat / k, "installed_length_m": inst * 1e-3,
            "solid_length_m": c["coil_bind_mm"] * 1e-3,
            "coil_bind_clearance_m": (inst - lift_mm - c["coil_bind_mm"]) * 1e-3,
            "force_at_max_lift_N": seat + k_mm * lift_mm}


def evaluate(c: dict, kind: str, params: dict | None = None, sdof_steps: int = 7200) -> dict:
    params = copy.deepcopy(params or vt.default_parameters())
    vp = params[kind]
    lift = vp["max_lift_mm"]["value"]
    sp = spring_from_candidate(c, lift)
    m = vt.effective_mass(vp, sp)
    cold, hot = vt.CamLaw.from_params(vp), vt.CamLaw.from_params(vp, hot=True)
    margin = vt.spring_margin(cold, sp, m, CRITERIA["margin_rpm"])["min_margin"]
    sdof = vt.simulate_sdof(hot, vp, sp, m, CRITERIA["sdof_rpm"], cycles=3, steps_per_cycle=sdof_steps)
    sep = max(sdof["max_separation_mm"], sdof["max_bounce_mm"])
    bind = sp["coil_bind_clearance_m"] * 1e3
    od = c.get("outer_od_mm")
    od_max = HOUSING["max_outer_diameter_mm"]["value"]
    lift_pub = c.get("max_lift_published_mm")
    checks = {
        "margin_8000": margin >= CRITERIA["required_margin"],
        "bind_reserve": bind >= CRITERIA["bind_reserve_mm"],
        "separation_7500": sep <= CRITERIA["max_separation_mm"],
        "stress": "not_computable" if not c.get("wire_diameter_mm") else None,
        "housing_od": "unknown_od" if od is None else od <= od_max,
        "within_published_max_lift": "not_published" if lift_pub is None else lift <= lift_pub,
    }
    hard = [checks["margin_8000"], checks["bind_reserve"], checks["separation_7500"]]
    soft_fail = [v is False for v in (checks["housing_od"], checks["within_published_max_lift"])]
    return {"kind": kind, "rate_N_mm": sp["rate_N_m"] / 1e3, "rate_source": sp["rate_source"],
            "seat_N": sp["preload_N"], "force_at_max_lift_N": sp["force_at_max_lift_N"],
            "effective_mass_kg": m, "margin_8000": margin,
            "limit_rpm_margin_1_25": vt.float_rpm_quasistatic(cold, sp, m, required=CRITERIA["required_margin"]),
            "separation_7500_mm": sep, "bind_reserve_mm": bind,
            "bind_reserve_plus20pct_lift_mm": bind - 0.2 * lift,
            "checks": checks, "passes_hard": all(hard), "n_hard_pass": sum(hard),
            "passes_all_known": all(hard) and not any(soft_fail)}


def rank(results: list[dict]) -> list[dict]:
    def key(r):
        i, e = r["intake"], r["exhaust"]
        ok = i["passes_all_known"] and e["passes_all_known"]
        return (not ok, -(i["n_hard_pass"] + e["n_hard_pass"]), -min(i["margin_8000"], 99))
    out = sorted(results, key=key)
    for n, r in enumerate(out, 1):
        r["rank"] = n
    return out


def main() -> None:
    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    rows = [{"id": c["id"], "supplier": c["supplier"], "type": c["type"],
             "intake": evaluate(c, "intake"), "exhaust": evaluate(c, "exhaust")} for c in data["candidates"]]
    ranked = rank(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"status": "catalogue_screening_not_qualification", "criteria": CRITERIA,
                               "housing_parameters": HOUSING, "ranking": ranked}, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    for r in ranked:
        i, e = r["intake"], r["exhaust"]
        print(r["rank"], r["id"], f"k={i['rate_N_mm']:.1f} seat={i['seat_N']:.0f} M8000={i['margin_8000']:.2f}/{e['margin_8000']:.2f}",
              f"N1.25={i['limit_rpm_margin_1_25']:.0f} sep={i['separation_7500_mm']:.3f}/{e['separation_7500_mm']:.3f}",
              f"bind={i['bind_reserve_mm']:.2f}/{e['bind_reserve_mm']:.2f} +20%={i['bind_reserve_plus20pct_lift_mm']:.2f}",
              i["checks"]["housing_od"], i["checks"]["within_published_max_lift"], i["passes_all_known"], e["passes_all_known"])


if __name__ == "__main__":
    main()
