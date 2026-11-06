#!/usr/bin/env python3
"""Generate the SYNTHETIC observation set of the 993 Turbo cooling-fan operational slice.

No vehicle, engine, instrument or measurement stands behind this output. The
generator evaluates its own copy of the quasi-steady fan equations with "truth"
parameters, adds seeded Gaussian noise of the declared instrument uncertainties,
and injects named anomalies so that the replay of issue #511 has something to
reject or decline: a missing value, a source outlier, a sensor fault, a data gap,
late arrivals, an exact duplicate, an out-of-order arrival, and a deliberate
belt-slip change after t = 115 s that the model does not know about.

    python3 twins/993-turbo-cooling-fan-operational-f0/source/make_synthetic_observations.py --write
    python3 twins/993-turbo-cooling-fan-operational-f0/source/make_synthetic_observations.py --check
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import sys
from pathlib import Path

TWIN = Path(__file__).resolve().parents[1]
ROOT = TWIN.parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_operational_twin import canonical_sha256, load_json  # noqa: E402

OUTPUT = TWIN / "fixtures" / "observations-synthetic-0001.json"
SEED = 51011
DURATION_S = 170.0
STEADY_WINDOWS = [[5.0, 40.0], [55.0, 110.0], [125.0, 170.0]]
RPM = math.pi / 30.0

# Truth used only to synthesise data. It equals the synthetic parameter set
# except for the belt slip after t = 115 s, an injected model discrepancy.
TRUTH = {"i_drive": 1.65, "s_belt": 0.015, "s_belt_late": 0.035, "slip_change_s": 115.0,
         "omega_ref": 6000.0 * RPM, "dp_ref": 2400.0, "rho_ref": 1.204, "eta_fan": 0.55,
         "cp_air": 1006.0, "r_air": 287.05}

CHANNELS = [
    # channel, instrument, unit, period, phase, decimals, noise (channel unit)
    ("N_CRANK", "INST-SYN-TACH-01", "rpm", 0.5, 0.000, 1, 2.0),
    ("T_IN", "INST-SYN-RTD-02", "degC", 1.0, 0.003, 2, 0.15),
    ("P_AMB", "INST-SYN-BARO-03", "hPa", 2.0, 0.006, 2, 0.5),
    ("N_FAN", "INST-SYN-OPT-04", "rad/s", 0.5, 0.004, 3, None),
    ("DP_FAN", "INST-SYN-DP-05", "kPa", 0.5, 0.008, 4, None),
    ("T_OUT", "INST-SYN-RTD-06", "degC", 1.0, 0.011, 2, 0.15),
]
IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
MOUNTS = {
    "N_CRANK": None,
    "P_AMB": None,
    "T_IN": {"sensor_frame_id": "S_T_IN", "parent_frame_id": "F_FAN", "rotation_parent_from_sensor": IDENTITY,
             "translation_mm": [0.0, 60.0, -50.0], "position_sensor_mm": [0.0, 0.0, 0.0],
             "status": "synthetic installation"},
    "N_FAN": {"sensor_frame_id": "S_N_FAN", "parent_frame_id": "F_FAN",
              "rotation_parent_from_sensor": [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]],
              "translation_mm": [0.0, 0.0, -40.0], "position_sensor_mm": [0.0, 0.0, 0.0],
              "sensing_axis_sensor": [0.0, 0.0, 1.0],
              "status": "synthetic installation; the tachometer looks forward, so its sensing axis is -Z of F_FAN"},
    "DP_FAN": {"sensor_frame_id": "S_DP_FAN", "parent_frame_id": "F_FAN", "rotation_parent_from_sensor": IDENTITY,
               "translation_mm": [120.0, 0.0, 60.0], "position_sensor_mm": [0.0, 0.0, 0.0],
               "status": "synthetic installation of the outlet tap"},
    "T_OUT": {"sensor_frame_id": "S_T_OUT", "parent_frame_id": "F_FAN",
              "rotation_parent_from_sensor": [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
              "translation_mm": [0.0, 0.0, 80.0], "position_sensor_mm": [150.0, 0.0, 0.0],
              "status": "synthetic installation; probe frame rotated 90 degrees about Z"},
}


def crank_rpm(t: float) -> float:
    if t < 40.0:
        return 800.0
    if t < 50.0:
        return 800.0 + (t - 40.0) / 10.0 * 2200.0
    if t < 110.0:
        return 3000.0
    if t < 120.0:
        return 3000.0 + (t - 110.0) / 10.0 * 1500.0
    return 4500.0


def truth(t: float) -> dict:
    t_in = 295.15 + 0.5 * t / DURATION_S
    p_amb = 98500.0
    slip = TRUTH["s_belt_late"] if t >= TRUTH["slip_change_s"] else TRUTH["s_belt"]
    omega_crank = crank_rpm(t) * RPM
    omega_fan = TRUTH["i_drive"] * (1.0 - slip) * omega_crank
    rho = p_amb / (TRUTH["r_air"] * t_in)
    dp = TRUTH["dp_ref"] * (omega_fan / TRUTH["omega_ref"]) ** 2 * rho / TRUTH["rho_ref"]
    t_out = t_in + dp / (rho * TRUTH["cp_air"] * TRUTH["eta_fan"])
    return {"N_CRANK": crank_rpm(t), "T_IN": t_in - 273.15, "P_AMB": p_amb / 100.0,
            "N_FAN": -omega_fan,  # reported about the tachometer axis, which is -Z of F_FAN
            "DP_FAN": dp / 1000.0, "T_OUT": t_out - 273.15}


def noise_sigma(channel: str, value: float, fixed: float | None) -> float:
    if fixed is not None:
        return fixed
    if channel == "N_FAN":
        return math.hypot(0.5, 0.001 * value)
    return math.hypot(0.01, 0.005 * value)  # DP_FAN in kPa


def build(slice_contract: dict, model_card: dict, parameter_set: dict, register: dict) -> dict:
    rng = random.Random(SEED)
    channels = []
    for name, instrument, unit, period, phase, decimals, fixed in CHANNELS:
        calibration = next(i for i in register["instruments"] if i["instrument_id"] == instrument)
        samples = []
        count = int(round(DURATION_S / period)) + 1
        for seq in range(count):
            t = round(seq * period + phase, 3)
            if t > DURATION_S:
                break
            value = truth(min(t, DURATION_S))[name]
            value = round(value + rng.gauss(0.0, noise_sigma(name, value, fixed)), decimals)
            arrival = round(t + 0.05 + 0.15 * rng.random(), 3)
            samples.append([seq, t, arrival, value, "ok"])
        by_time = {round(s[1] - phase, 3): s for s in samples}
        if name == "T_OUT":
            by_time[20.0][3:] = [None, "missing"]
            samples = [s for s in samples if not 96.0 <= round(s[1] - phase, 3) <= 99.0]
        if name == "DP_FAN":
            by_time[75.0][3:] = [round(by_time[75.0][3] * 3.0, decimals), "source_outlier"]
        if name == "N_FAN":
            for t in (90.0, 90.5, 91.0):
                by_time[t][3:] = [0.0, "sensor_fault"]
        if name == "T_IN":
            for t in (30.0, 31.0):
                by_time[t][2] = round(by_time[t][1] + 2.5, 3)
        if name == "N_CRANK":
            by_time[70.0][2] = 70.6
            by_time[70.5][2] = 70.55
            samples.append(list(by_time[65.0][:2]) + [65.9] + list(by_time[65.0][3:]))
        samples.sort(key=lambda s: (s[2], s[0]))
        channels.append({
            "channel_id": name,
            "instrument_id": instrument,
            "calibration_id": calibration["calibration_id"],
            "timebase_id": "TB-SYN-DAQ-0001",
            "unit": unit,
            "nominal_period_s": period,
            "mount": MOUNTS[name],
            "samples": samples,
        })
    return {
        "document_kind": "observation_set",
        "schema_version": "1.0.0",
        "observation_set_id": "OBS-993T-FAN-SYN-0001",
        "contract_id": slice_contract["contract_id"],
        "contract_revision": slice_contract["contract_revision"],
        "specimen_id": slice_contract["specimen"]["specimen_id"],
        "synchronisation_mode": "offline_replay",
        "provenance": {
            "data_class": "synthetic",
            "label": "SYNTHETIC FIXTURE: generated by software; not a measurement of any vehicle, engine or instrument.",
            "generator": {
                "script": "twins/993-turbo-cooling-fan-operational-f0/source/make_synthetic_observations.py",
                "seed": SEED,
                "truth_note": "Truth equals the synthetic parameter set except belt slip 0.035 instead of 0.015 from t = 115 s, an injected discrepancy the model does not know.",
            },
            "source_rights": {
                "licence": "porscheparts Proprietary License 1.0 (repository licence); synthetic data authored in this repository",
                "rights_holder": "repository maintainer",
                "contributor_consent_ref": None,
                "publication": "public_synthetic",
            },
            "raw_data": {"storage": "inline_synthetic",
                         "note": "Inline only because the data are synthetic; measured samples would be referenced by samples_ref."},
        },
        "model_binding": {
            "model_id": model_card["model_id"],
            "model_revision": model_card["model_revision"],
            "model_card_sha256": canonical_sha256(model_card),
            "parameter_set_id": parameter_set["parameter_set_id"],
            "parameter_set_sha256": canonical_sha256(parameter_set),
        },
        "calibration_register": {"register_id": register["register_id"], "sha256": canonical_sha256(register)},
        "timebase": {
            "timebase_id": "TB-SYN-DAQ-0001",
            "clock": "single_monotonic_acquisition_clock",
            "epoch_utc": "2026-11-06T09:00:00Z",
            "resolution_s": 0.001,
            "max_inter_channel_skew_s": 0.02,
            "drift_bound_ppm": 50.0,
        },
        "operating_case": {
            "case_id": "OC-STATIONARY-HOLDS",
            "duration_s": DURATION_S,
            "steady_windows_s": STEADY_WINDOWS,
            "log_source": "synthetic operator log: holds at 800, 3000 and 4500 rpm with ramps between them",
        },
        "channels": channels,
    }


def render(document: dict) -> str:
    """Indented JSON with one sample per line, so that diffs stay reviewable."""
    shell = copy.deepcopy(document)
    blocks = {}
    for index, channel in enumerate(shell["channels"]):
        marker = f"@@SAMPLES-{index}@@"
        rows = ",\n".join("    " + json.dumps(sample) for sample in channel["samples"])
        blocks[json.dumps(marker)] = "[\n" + rows + "\n   ]"
        channel["samples"] = marker
    text = json.dumps(shell, indent=1, ensure_ascii=False)
    for marker, block in blocks.items():
        text = text.replace(marker, block)
    return text + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    contract = TWIN / "contract"
    document = build(load_json(contract / "slice.json"), load_json(contract / "model-card.json"),
                     load_json(contract / "parameters-synthetic-0001.json"),
                     load_json(TWIN / "fixtures" / "calibration-register-synthetic-0001.json"))
    text = render(document)
    if json.loads(text) != document:
        raise SystemExit("rendering changed the document")
    if args.write:
        OUTPUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
        return 0
    if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != text:
        print(f"{OUTPUT.relative_to(ROOT)} differs from its generator; rerun with --write", file=sys.stderr)
        return 1
    print(f"{OUTPUT.relative_to(ROOT)} is reproduced by its generator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
