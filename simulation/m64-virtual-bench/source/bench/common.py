"""Shared constants and helpers for the M64/60 virtual test bench (0D model).

Provenance tags used everywhere (same vocabulary as
docs/research/m64-public-engine-data-2026-09-27.md):
  FACT_public      published by Porsche
  CROSSCHECKED     two independent secondary sources agree
  SINGLE_SOURCE    one secondary source
  HYPOTHESIS       documented modelling hypothesis (this file or modules)
  ASSUMPTION       engineering assumption, flagged
  REPO             taken from an existing repository artefact (path given)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

BENCH_ROOT = Path(__file__).resolve().parents[1]   # simulation/m64-virtual-bench
REPO_ROOT = BENCH_ROOT.parents[1]                  # repository root

# --- engine baseline (FACT_public, docs/research/m64-public-engine-data-2026-09-27.md) ---
DISPLACEMENT_M3 = 0.0036          # 3600 cc
STROKES = 4
CYLINDERS = 6
TURBOS = 2
COMPRESSION_RATIO = 9.5           # FACT_public (not used directly by the 0D torque model)

# --- public calibration anchor (FACT_public values; rpm positions ASSUMPTION) ---
PUBLIC_CASE = {
    "peak_power_kw": 300.0,        # 408 PS (FACT_public)
    "peak_power_rpm": 5750.0,      # ASSUMPTION: rpm of peak not in repo files
    "peak_torque_nm": 540.0,       # FACT_public
    "peak_torque_rpm": 4050.0,     # ASSUMPTION: plateau start, not in repo files
    "boost_bar_gauge": 0.8,        # FACT_public retained reading (brochure setpoint 1.0)
    "source": "docs/research/m64-public-engine-data-2026-09-27.md",
}

# --- charge conditions (REPO: simulation/993-turbo-dyno/dyno-reference.json airflow_envelope) ---
P_AMB_PA = 101325.0
T_AMB_K = 303.15                  # 30 degC ambient (ASSUMPTION)
P_MAN_ABS_PA = 181300.0           # REPO envelope (= 0.8 bar gauge + ambient)
T_MAN_K = 323.15                  # REPO envelope, post-intercooler charge temp
R_AIR = 287.05
GAMMA_AIR = 1.4
CP_AIR = 1005.0
RHO_AMB = P_AMB_PA / (R_AIR * T_AMB_K)

# --- fuel (ASSUMPTION: pump petrol LHV; REPO has no fuel card) ---
LHV_FUEL_J_KG = 44.0e6
AFR_STOICH = 14.7

# --- cooling fan (FACT_public: 1010 l/s at 6100 rpm engine, OBD-1996 supplement) ---
FAN_FLOW_REF_M3_S = 1.010
FAN_REF_RPM = 6100.0
FAN_DRIVE_RATIO = 1.6             # FACT_public belt ratio

# --- oil (capacity FACT_public; specific heat/density from REPO oil-return doc) ---
OIL_CAPACITY_L = 12.0
OIL_RHO = 850.0                   # REPO docs/993/993_TURBO_OIL_RETURN_LINE_IN625_F0.md synthetic point
OIL_CP = 2100.0                   # ASSUMPTION (typical 15W-50 range, not sourced)

# --- K16 compressor envelope (SINGLE_SOURCE Invasion Auto via REPO
#     simulation/993-k16-cold-side-baseline/parameters.json) ---
K16_COMP_INDUCER_MM = 40.6
K16_COMP_EXDUCER_MM = 60.5
K16_ENVELOPE_MM = [280.0, 190.0, 210.0]
# variants anchor flow per turbo (REPO simulation/993-turbo-variants/variants.json)
VARIANTS_FLOW_ANCHOR_KG_S = 0.156


def interp(x: float, xp: list[float], fp: list[float]) -> float:
    """Deterministic linear interpolation with edge clamping."""
    return float(np.interp(x, np.asarray(xp, dtype=float), np.asarray(fp, dtype=float)))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)]
    for r in rows:
        lines.append(",".join(f"{v:.6g}" if isinstance(v, float) else str(v) for v in r))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def versions() -> dict:
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "solver": "deterministic 0D quasi-steady closed-form evaluation (no iterative solver)",
    }
