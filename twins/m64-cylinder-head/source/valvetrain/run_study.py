#!/usr/bin/env python3
"""Étude V1 distribution : produit le JSON de résultats (avec empreintes) et des figures légères.

uv run --no-project --with numpy --with scipy --with matplotlib \
    python twins/m64-cylinder-head/source/valvetrain/run_study.py
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import valvetrain as vt  # noqa: E402

ROOT = HERE.parents[3]
OUT = ROOT / "twins/m64-cylinder-head/evidence/valvetrain-v1"
DYN_RPMS = list(range(4000, 9751, 250))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valve_study(params: dict, kind: str) -> dict:
    vp, eng = params[kind], params["engine"]
    spring = vt.spring_properties(vp, eng)
    m = vt.effective_mass(vp, spring)
    target = eng["target_rpm"]["value"]
    required = eng["required_spring_margin"]["value"]
    cold, hot = vt.CamLaw.from_params(vp), vt.CamLaw.from_params(vp, hot=True)
    phi = np.linspace(0, 4 * math.pi, 7201)
    kin = cold.valve_kinematics(phi, target)
    res = {
        "effective_mass_kg": m,
        "spring": spring,
        "kinematics_at_target": {
            "rpm": target,
            "max_lift_mm": float(kin["lift_m"].max() * 1e3),
            "max_velocity_m_s": float(np.abs(kin["velocity_m_s"]).max()),
            "max_positive_acceleration_m_s2": float(kin["acceleration_m_s2"].max()),
            "max_negative_acceleration_m_s2": float(kin["acceleration_m_s2"].min()),
            "max_abs_jerk_m_s3": float(np.abs(kin["jerk_m_s3"]).max()),
            "max_inertia_force_N": float(m * np.abs(kin["acceleration_m_s2"]).max()),
        },
        "lash_events_cold": cold.open_close_events(target),
        "lash_events_hot": hot.open_close_events(target),
        "margin_at_target": vt.spring_margin(cold, spring, m, target),
        "float_rpm_quasistatic_margin_1": vt.float_rpm_quasistatic(cold, spring, m),
        "limit_rpm_required_margin": vt.float_rpm_quasistatic(cold, spring, m, required=required),
        "margin_sweep": [{"rpm": r, "min_margin": vt.spring_margin(cold, spring, m, r)["min_margin"]}
                         for r in range(3000, int(eng["overrev_sweep_max_rpm"]["value"]) + 1, 500)],
        "piston_interference_cold_hot_timing_sweep": [
            {"lash": name, **vt.interference(law, vp, eng, advance_deg=adv)}
            for name, law in (("cold", cold), ("hot", hot)) for adv in (-10, -5, 0, 5, 10)],
    }
    thr = eng["separation_threshold_mm"]["value"]
    gross = eng["gross_float_threshold_mm"]["value"]
    dyn, onset, gross_onset = [], None, None
    for r in DYN_RPMS:
        s = vt.simulate_sdof(hot, vp, spring, m, r, cycles=3, steps_per_cycle=7200)
        dyn.append({k: s[k] for k in ("rpm", "max_separation_mm", "max_bounce_mm", "contact_loss_fraction_of_open")})
        worst = max(s["max_separation_mm"], s["max_bounce_mm"])
        if onset is None and worst > thr:
            onset = r
        if gross_onset is None and worst > gross:
            gross_onset = r
    res["sdof_sweep_hot_lash"] = dyn
    res["sdof_onset_rpm_threshold"] = onset
    res["sdof_gross_float_rpm"] = gross_onset
    return res


def sensitivity(params: dict, kind: str) -> list:
    base = vt.float_rpm_quasistatic(vt.CamLaw.from_params(params[kind]),
                                    vt.spring_properties(params[kind], params["engine"]),
                                    vt.effective_mass(params[kind], vt.spring_properties(params[kind], params["engine"])))
    rows = []
    for name in ("valve_mass_kg", "follower_equivalent_mass_kg", "spring_preload_N", "spring_wire_diameter_mm",
                 "max_lift_mm", "main_event_duration_crank_deg", "profile_fullness_c"):
        for f in (0.8, 1.2):
            p = copy.deepcopy(params)
            p[kind][name]["value"] *= f
            try:
                vp = p[kind]; sp = vt.spring_properties(vp, p["engine"])
                n = vt.float_rpm_quasistatic(vt.CamLaw.from_params(vp), sp, vt.effective_mass(vp, sp))
                rows.append({"parameter": name, "factor": f, "float_rpm": n, "delta_pct": 100 * (n / base - 1),
                             "coil_bind_ok": sp["coil_bind_ok"]})
            except ValueError as exc:
                rows.append({"parameter": name, "factor": f, "error": str(exc)})
    return rows


def figures(params: dict, results: dict) -> list[Path]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    eng = params["engine"]; target = eng["target_rpm"]["value"]
    fig, ax = plt.subplots(3, 1, figsize=(7, 7.5), sharex=True)
    phi = np.linspace(0, 4 * math.pi, 3601)
    for kind, col in (("intake", "tab:blue"), ("exhaust", "tab:red")):
        law = vt.CamLaw.from_params(params[kind]); kin = law.valve_kinematics(phi, target)
        ax[0].plot(np.degrees(phi), kin["lift_m"] * 1e3, col, label=kind)
        ax[1].plot(np.degrees(phi), kin["acceleration_m_s2"] / 1e3, col)
        gap = vt.piston_valve_gap(phi, kin["lift_m"], params[kind], eng)
        ax[2].plot(np.degrees(phi), gap * 1e3, col)
    ax[0].set_ylabel("levée mm"); ax[0].legend(); ax[1].set_ylabel("accél. km/s² @6500")
    ax[2].set_ylabel("jeu piston mm"); ax[2].set_ylim(-2, 25); ax[2].axhline(0, color="k", lw=.5)
    ax[2].set_xlabel("vilebrequin ° (0 = PMH croisement)")
    fig.suptitle("V1 distribution — paramètres supposés, pas M64"); fig.tight_layout()
    p1 = OUT / "valvetrain-v1-kinematics.png"; fig.savefig(p1, dpi=80); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.5))
    for kind, col in (("intake", "tab:blue"), ("exhaust", "tab:red")):
        r = results["valves"][kind]
        ax.plot([d["rpm"] for d in r["sdof_sweep_hot_lash"]],
                [max(d["max_separation_mm"], d["max_bounce_mm"]) for d in r["sdof_sweep_hot_lash"]], col, marker=".", label=f"{kind} 1-ddl")
        ax.axvline(r["float_rpm_quasistatic_margin_1"], color=col, ls="--", lw=.8)
    ax.axvline(target, color="k", lw=.8); ax.set_yscale("symlog", linthresh=0.01)
    ax.set_xlabel("tr/min"); ax.set_ylabel("décollement/rebond max mm"); ax.legend(); fig.tight_layout()
    p2 = OUT / "valvetrain-v1-float-sweep.png"; fig.savefig(p2, dpi=80); plt.close(fig)
    return [p1, p2]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    params = vt.default_parameters()
    errors = vt.check_provenance(params)
    if errors:
        raise SystemExit(f"provenance: {errors}")
    pfile = OUT / "valvetrain-v1-parameters.json"
    pfile.write_text(json.dumps(params, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    results = {
        "schema_version": 1, "study": "M64 V1 distribution — cinématique/dynamique simplifiée",
        "status": "sensitivity_study_not_qualification",
        "m64_cam_data_used": False, "bench_correlation": False, "manufacturing_authorized": False,
        "valves_per_cylinder": 4,
        "valve_instances": {"I1": "intake", "I2": "intake", "E1": "exhaust", "E2": "exhaust"},
        "valve_instances_note": "Les deux soupapes d'un même côté partagent loi et paramètres (pas de déphasage modélisé).",
        "valves": {k: valve_study(params, k) for k in ("intake", "exhaust")},
        "sensitivity_float_rpm_pm20pct": {k: sensitivity(params, k) for k in ("intake", "exhaust")},
    }
    pngs = figures(params, results)
    results["fingerprints_sha256"] = {
        "valvetrain.py": sha256(HERE / "valvetrain.py"), "run_study.py": sha256(HERE / "run_study.py"),
        pfile.name: sha256(pfile), **{p.name: sha256(p) for p in pngs}}
    (OUT / "valvetrain-v1-results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k in ("intake", "exhaust"):
        r = results["valves"][k]
        print(k, round(r["float_rpm_quasistatic_margin_1"]), round(r["limit_rpm_required_margin"]), r["sdof_onset_rpm_threshold"],
              round(r["margin_at_target"]["min_margin"], 3), r["spring"]["coil_bind_clearance_m"] * 1e3,
              r["kinematics_at_target"], r["lash_events_hot"], min(x["min_gap_mm"] for x in r["piston_interference_cold_hot_timing_sweep"]))


if __name__ == "__main__":
    main()
