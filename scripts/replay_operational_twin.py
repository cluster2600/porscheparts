#!/usr/bin/env python3
"""Deterministic offline replay of the 993 Turbo cooling-fan operational slice.

One replay path only. A replay_run document binds the run to exact input
documents (canonical-JSON sha256), a specimen, a timebase, an operating case and
the frame definition. The replay then:

1. refuses the run unless every binding matches and the contract validator
   accepts the bundle;
2. ingests each channel: explicit unit and frame conversion, calibration
   validity and range checks, exact duplicates dropped, out-of-order arrivals
   reordered by sample time, late samples excluded; contradictory duplicates,
   sequence/time contradictions and samples outside the session reject the run;
3. evaluates the twin state at fixed times, predicts N_FAN, DP_FAN and T_OUT
   with first-order uncertainty, and applies the contract's predeclared residual
   rules, keeping every no-claim reason explicit.

    python3 scripts/replay_operational_twin.py --run twins/993-turbo-cooling-fan-operational-f0/replay/run-synthetic-0001.json
    python3 scripts/replay_operational_twin.py --run ... --check     # byte-identical to the committed report
    python3 scripts/replay_operational_twin.py --run ... --print-bindings

The output depends only on the bound inputs and on this implementation: no
wall-clock time, host name, absolute path or random state enters it. A passing
replay is `digitally_checked` at most. It is never a live or physically
correlated twin.
"""
from __future__ import annotations

import argparse
import bisect
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import validate_operational_twin as contract  # noqa: E402

REPLAY_SCHEMA = contract.SCHEMA_DIR / "operational-replay.schema.json"
DEFAULT_RUN = contract.TWIN_DIR / "replay" / "run-synthetic-0001.json"
IMPLEMENTATION = ["scripts/replay_operational_twin.py", "scripts/validate_operational_twin.py"]
INPUT_KINDS = ["slice_contract", "model_card", "parameter_set", "calibration_register", "observation_set"]
ID_FIELDS = {
    "slice_contract": ("contract_id", "contract_revision"),
    "model_card": ("model_id", "model_revision"),
    "parameter_set": ("parameter_set_id", None),
    "calibration_register": ("register_id", None),
    "observation_set": ("observation_set_id", None),
}
HASH_CODES = {
    "slice_contract": "CONTRACT_HASH_MISMATCH",
    "model_card": "MODEL_HASH_MISMATCH",
    "parameter_set": "PARAMETER_HASH_MISMATCH",
    "calibration_register": "CALIBRATION_HASH_MISMATCH",
    "observation_set": "OBSERVATION_HASH_MISMATCH",
}


class ReplayRejected(Exception):
    """The replay fails closed; no report is produced."""

    def __init__(self, code: str, message: str, details: list[str] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.details = details or []


def r(value: float | None) -> float | None:
    """Round to 10 significant digits so that the report bytes are stable."""
    if value is None:
        return None
    rounded = float(f"{value:.10g}")
    return 0.0 if rounded == 0 else rounded


def repo_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as error:
        raise ReplayRejected("PATH_OUTSIDE_REPOSITORY", relative) from error
    return path


def read_repo_json(relative: str) -> Any:
    path = repo_path(relative)
    if not path.is_file():
        raise ReplayRejected("INPUT_MISSING", relative)
    return contract.load_json(path)


def file_sha256(relative: str) -> str:
    data = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def frames_sha256(slice_contract: dict) -> str:
    return contract.canonical_sha256({"frames": slice_contract["frames"], "stations": slice_contract["stations"]})


def utc(text: str) -> dt.datetime:
    return dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


# --------------------------------------------------------------------------- binding

def bind(run: dict, read: Callable[[str], Any]) -> dict[str, Any]:
    validator = contract.SchemaValidator(contract.load_json(REPLAY_SCHEMA))
    errors = validator.errors(run, validator.root["$defs"]["replay_run"])
    if errors:
        raise ReplayRejected("RUN_INVALID", "the run binding does not match its schema", errors)
    documents = {}
    for kind in INPUT_KINDS:
        bound = run["inputs"][kind]
        document = read(bound["path"])
        if contract.canonical_sha256(document) != bound["sha256"]:
            raise ReplayRejected(HASH_CODES[kind], f"{bound['path']} does not match its bound sha256")
        id_field, revision_field = ID_FIELDS[kind]
        if document.get(id_field) != bound["id"] or (revision_field and document.get(revision_field) != bound["revision"]):
            raise ReplayRejected("INPUT_ID_MISMATCH", f"{bound['path']} is not {bound['id']} {bound['revision'] or ''}".strip())
        documents[kind] = document
    errors = contract.validate_documents(documents)
    if errors:
        raise ReplayRejected("CONTRACT_INVALID", "the bound documents fail the operational contract", errors)
    observations = documents["observation_set"]
    if run["specimen_id"] != observations["specimen_id"]:
        raise ReplayRejected("SPECIMEN_MISMATCH", "the run and the observation set name different specimens")
    if run["timebase_id"] != observations["timebase"]["timebase_id"]:
        raise ReplayRejected("TIMEBASE_MISMATCH", "the run and the observation set name different timebases")
    if run["operating_case_id"] != observations["operating_case"]["case_id"]:
        raise ReplayRejected("OPERATING_CASE_MISMATCH", "the run and the observation set name different operating cases")
    if run["geometry"]["frames_sha256"] != frames_sha256(documents["slice_contract"]):
        raise ReplayRejected("GEOMETRY_MISMATCH", "the contract frames or stations changed since the run was bound")
    if run["geometry"]["twin_record"] != documents["slice_contract"]["twin_reference"]["twin_record"]:
        raise ReplayRejected("GEOMETRY_MISMATCH", "the run names another twin record than the contract")
    return documents


# --------------------------------------------------------------------------- ingest

def load_external_samples(channel: dict, external: Path | None) -> list:
    if external is None:
        raise ReplayRejected("EXTERNAL_SAMPLES_REQUIRED", f"channel {channel['channel_id']} samples are held privately")
    folder = external.resolve()
    try:
        folder.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ReplayRejected("RAW_DATA_IN_REPOSITORY", "private samples must be read from outside the repository")
    reference = channel["samples_ref"]
    path = folder / f"{reference['sha256']}.json"
    if not path.is_file():
        raise ReplayRejected("EXTERNAL_SAMPLES_MISSING", f"channel {channel['channel_id']}")
    samples = contract.load_json(path)
    if contract.canonical_sha256(samples) != reference["sha256"] or len(samples) != reference["count"]:
        raise ReplayRejected("EXTERNAL_SAMPLES_MISMATCH", f"channel {channel['channel_id']}")
    validator = contract.SchemaValidator(contract.load_json(contract.SCHEMA_PATH))
    errors = validator.errors(samples, {"type": "array", "items": validator.root["$defs"]["sample"]})
    if errors:
        raise ReplayRejected("EXTERNAL_SAMPLES_INVALID", f"channel {channel['channel_id']}", errors)
    return samples


def ingest(documents: dict, external: Path | None) -> tuple[dict, dict]:
    """Return (per-channel usable timeline, ingest receipts)."""
    slice_contract, observations = documents["slice_contract"], documents["observation_set"]
    register = {i["instrument_id"]: i for i in documents["calibration_register"]["instruments"]}
    specs = {c["channel_id"]: c for c in slice_contract["channels"]}
    stations = {s["station_id"]: s for s in slice_contract["stations"]}
    quantities = {q["quantity_id"]: q for q in slice_contract["quantities"]}
    duration = observations["operating_case"]["duration_s"]
    budget = slice_contract["sample_rules"]["latency_budget_s"]
    epoch = utc(observations["timebase"]["epoch_utc"])
    timelines, receipts = {}, {}
    for channel in observations["channels"]:
        name = channel["channel_id"]
        spec = specs[name]
        instrument = register[channel["instrument_id"]]
        canonical, scale, offset = contract.conversion(slice_contract, channel["unit"])
        if canonical != quantities[spec["quantity_id"]]["canonical_unit"]:
            raise ReplayRejected("UNIT_CONVERSION", f"channel {name} converts to {canonical}")
        sign = 1
        station = stations.get(spec["station_id"]) if spec["station_id"] else None
        if station is not None and station["kind"] == "rotation_axis":
            sign = 1 if contract.mount_in_parent(channel["mount"])["axis"][2] > 0 else -1
        samples = channel["samples"] if "samples" in channel else load_external_samples(channel, external)

        by_seq: dict[int, list] = {}
        by_time: dict[float, int] = {}
        duplicates = 0
        for sample in sorted(samples, key=lambda s: (s[2], s[0])):
            seq, t, arrival, value, flag = sample
            if not 0.0 <= t <= duration:
                raise ReplayRejected("SAMPLE_OUTSIDE_SESSION", f"channel {name} sequence {seq} at {t} s")
            if arrival < t:
                raise ReplayRejected("ARRIVAL_BEFORE_SAMPLE", f"channel {name} sequence {seq}")
            if seq in by_seq:
                kept = by_seq[seq]
                if (kept[1], kept[3], kept[4]) != (t, value, flag):
                    raise ReplayRejected("CONTRADICTORY_DUPLICATE", f"channel {name} sequence {seq} carries two contents")
                duplicates += 1  # the earliest arrival is kept
                continue
            if t in by_time:
                raise ReplayRejected("CONTRADICTORY_DUPLICATE", f"channel {name} has two sequences at {t} s")
            by_seq[seq] = sample
            by_time[t] = seq
        arrival_order = sorted(by_seq.values(), key=lambda s: (s[2], s[0]))
        out_of_order, highest = 0, -1
        for sample in arrival_order:
            if sample[0] < highest:
                out_of_order += 1
            highest = max(highest, sample[0])
        ordered = [by_seq[k] for k in sorted(by_seq)]
        for before, after in zip(ordered, ordered[1:]):
            if not after[1] > before[1]:
                raise ReplayRejected("SEQUENCE_TIME_CONTRADICTION", f"channel {name} sequence {after[0]} is not later than {before[0]}")

        valid_from = (utc(instrument["valid_from_utc"]) - epoch).total_seconds()
        valid_until = (utc(instrument["valid_until_utc"]) - epoch).total_seconds()
        lo_range, hi_range = instrument["range"]
        lo_plausible, hi_plausible = spec["plausible_range_canonical"]
        timeline, late, flagged = [], 0, {}
        for seq, t, arrival, value, flag in ordered:
            if arrival - t > budget:
                late += 1
                continue
            status = {"ok": "usable"}.get(flag, flag)
            canonical_value = u = None
            if value is not None:
                u_raw = math.hypot(instrument["standard_uncertainty_abs"], instrument["standard_uncertainty_rel"] * abs(value))
                canonical_value = sign * (value * scale + offset)
                u = u_raw * scale  # an uncertainty converts by the scale only
                if status == "usable" and not (lo_range <= value <= hi_range and lo_plausible <= canonical_value <= hi_plausible):
                    status = "out_of_range"
            if status == "usable" and not valid_from <= t <= valid_until:
                status = "calibration_invalid"
            if status != "usable":
                flagged[status] = flagged.get(status, 0) + 1
            timeline.append((t, seq, status, canonical_value, u))
        timelines[name] = timeline
        receipts[name] = {
            "unit": channel["unit"], "canonical_unit": canonical, "scale": scale, "offset": offset,
            "frame_sign": sign, "received": len(samples), "exact_duplicates_dropped": duplicates,
            "out_of_order_arrivals": out_of_order, "late_excluded": late,
            "flagged": dict(sorted(flagged.items())),
        }
    return timelines, receipts


# --------------------------------------------------------------------------- model

def predict(inputs: dict, parameters: dict) -> dict:
    """MDL-993T-FAN-QS0D 1.0.0: values and first-order standard uncertainties, canonical units."""
    p = {name: item["value"] for name, item in parameters.items()}
    u = {name: item["standard_uncertainty"] for name, item in parameters.items()}
    omega_crank, u_crank = inputs["N_CRANK"]
    t_in, u_t_in = inputs["T_IN"]
    p_amb, u_p_amb = inputs["P_AMB"]
    omega_fan = p["i_drive"] * (1.0 - p["s_belt"]) * omega_crank
    rel_fan2 = (u["i_drive"] / p["i_drive"]) ** 2 + (u["s_belt"] / (1.0 - p["s_belt"])) ** 2 + (u_crank / omega_crank) ** 2
    rho = p_amb / (p["r_air"] * t_in)
    rel_rho2 = (u_p_amb / p_amb) ** 2 + (u_t_in / t_in) ** 2 + (u["r_air"] / p["r_air"]) ** 2
    speed2 = (omega_fan / p["omega_ref"]) ** 2
    dp = p["dp_ref"] * speed2 * rho / p["rho_ref"]
    rel_common2 = (u["dp_ref"] / p["dp_ref"]) ** 2 + 4.0 * rel_fan2 + 4.0 * (u["omega_ref"] / p["omega_ref"]) ** 2 \
        + (u["rho_ref"] / p["rho_ref"]) ** 2
    rel_dp2 = rel_common2 + rel_rho2
    rise = p["dp_ref"] * speed2 / (p["rho_ref"] * p["cp_air"] * p["eta_fan"])
    rel_rise2 = rel_common2 + (u["cp_air"] / p["cp_air"]) ** 2 + (u["eta_fan"] / p["eta_fan"]) ** 2
    return {
        "N_FAN": (omega_fan, omega_fan * math.sqrt(rel_fan2)),
        "DP_FAN": (dp, dp * math.sqrt(rel_dp2)),
        "T_OUT": (t_in + rise, math.sqrt(u_t_in ** 2 + rise ** 2 * rel_rise2)),
    }


# --------------------------------------------------------------------------- replay

def channel_state(timeline: list, times: list, t_frame: float, skew: float, max_age: float) -> dict:
    index = bisect.bisect_right(times, t_frame + skew) - 1
    if index < 0:
        return {"status": "missing", "value": None, "u": None, "seq": None, "age_s": None}
    t, seq, status, value, u = timeline[index]
    age = t_frame - t
    if age > max_age:
        status = "stale"
    return {"status": status, "value": r(value), "u": r(u), "seq": seq, "age_s": r(age), "_value": value, "_u": u}


def replay(run: dict, read: Callable[[str], Any] = read_repo_json, external: Path | None = None,
           run_sha256: str | None = None) -> dict:
    documents = bind(run, read)
    slice_contract, observations = documents["slice_contract"], documents["observation_set"]
    timelines, receipts = ingest(documents, external)
    specs = {c["channel_id"]: c for c in slice_contract["channels"]}
    case = next(c for c in slice_contract["operating_cases"] if c["case_id"] == observations["operating_case"]["case_id"])
    rules = slice_contract["residual_rules"]
    envelope = slice_contract["operating_envelope"]["inputs_canonical"]
    parameters = {p["name"]: p for p in documents["parameter_set"]["parameters"]}
    skew = observations["timebase"]["max_inter_channel_skew_s"]
    windows = observations["operating_case"]["steady_windows_s"]
    inputs = slice_contract["prediction"]["inputs"]
    outputs = slice_contract["prediction"]["outputs"]
    reference = case["steady_reference_channel"]
    times = {name: [entry[0] for entry in timeline] for name, timeline in timelines.items()}

    medians = []
    for start, end in windows:
        values = sorted(v for t, _, s, v, _ in timelines[reference] if s == "usable" and start <= t <= end)
        if not values:
            medians.append(None)
            continue
        mid = len(values) // 2
        medians.append(values[mid] if len(values) % 2 else 0.5 * (values[mid - 1] + values[mid]))

    period = case["evaluation_period_s"]
    count = int(math.floor(observations["operating_case"]["duration_s"] / period + 1e-9)) + 1
    frames = []
    for k in range(count):
        t_frame = r(k * period)
        window = next((i for i, (a, b) in enumerate(windows) if a <= t_frame <= b), None)
        states = {name: channel_state(timelines[name], times[name], t_frame, skew, specs[name]["max_age_s"])
                  for name in sorted(timelines)}
        frame_reasons = []
        if window is None:
            frame_reasons.append("frame:transient")
        elif states[reference]["status"] == "usable" and medians[window] is not None and \
                abs(states[reference]["_value"] - medians[window]) > case["steady_tolerance_rel"] * medians[window]:
            frame_reasons.append("frame:not_steady")
        input_reasons = []
        for name in inputs:
            state = states[name]
            if state["status"] != "usable":
                input_reasons.append(f"{name}:{state['status']}")
            elif not envelope[name][0] <= state["_value"] <= envelope[name][1]:
                input_reasons.append(f"{name}:outside_envelope")
        prediction = None
        if all(states[name]["status"] == "usable" for name in inputs):
            prediction = predict({name: (states[name]["_value"], states[name]["_u"]) for name in inputs}, parameters)
        frame_outputs = {}
        for output in outputs:
            out_id, compare = output["output_id"], output["compare_channel"]
            reasons = frame_reasons + input_reasons
            predicted = u_predicted = None
            if prediction is None:
                reasons = reasons + ["frame:input_unavailable"]
            else:
                predicted, u_predicted = prediction[out_id]
            observed_state = states[compare]
            observed = u_observed = None
            if observed_state["status"] == "usable":
                observed, u_observed = observed_state["_value"], observed_state["_u"]
            else:
                reasons = reasons + [f"{compare}:{observed_state['status']}"]
            residual = u_residual = z = None
            if predicted is not None and observed is not None:
                residual = observed - predicted
                u_residual = math.hypot(u_predicted, u_observed)
                if u_residual <= 0:
                    raise ReplayRejected("ZERO_UNCERTAINTY", f"{out_id} at {t_frame} s has no uncertainty")
                z = residual / u_residual
            if reasons:
                verdict = "no_claim"
            elif abs(z) <= rules["consistent_max_abs_z"]:
                verdict = "consistent"
            elif abs(z) > rules["discrepant_min_abs_z"]:
                verdict = "discrepant"
            else:
                verdict = "indeterminate"
            frame_outputs[out_id] = {
                "predicted": r(predicted), "u_predicted": r(u_predicted), "observed": r(observed),
                "u_observed": r(u_observed), "residual": r(residual), "u_residual": r(u_residual), "z": r(z),
                "verdict": verdict, "reasons": sorted(set(reasons)),
            }
        for state in states.values():
            state.pop("_value", None)
            state.pop("_u", None)
        frames.append({"t_s": t_frame, "steady_window": window, "channels": states, "outputs": frame_outputs})

    summary = summarise(frames, outputs, windows, rules, slice_contract)
    implementation = {path: file_sha256(path) for path in IMPLEMENTATION}
    report = {
        "document_kind": "replay_report",
        "schema_version": "1.0.0",
        "run_id": run["run_id"],
        "status": "digitally_checked",
        "physical_correlation": "not_claimed",
        "live_twin": "not_claimed",
        "synchronisation_mode": "offline_replay",
        "data_class": observations["provenance"]["data_class"],
        "label": ("SYNTHETIC REPLAY: every observation was generated by software. The verdicts below describe "
                  "software behaviour on a synthetic fixture and say nothing about any Porsche 993."
                  if observations["provenance"]["data_class"] == "synthetic" else
                  "Offline replay of a contributed observation set; not reviewed, not a live twin."),
        "binding": {
            "run_sha256": run_sha256 or contract.canonical_sha256(run),
            "specimen_id": run["specimen_id"],
            "timebase_id": run["timebase_id"],
            "operating_case_id": run["operating_case_id"],
            "inputs": run["inputs"],
            "geometry": run["geometry"],
            "implementation": {"files": implementation,
                               "hash_method": "sha256 of the file bytes with CRLF normalised to LF"},
        },
        "ingest": receipts,
        "rules": {"residual_rules": rules, "latency_budget_s": slice_contract["sample_rules"]["latency_budget_s"],
                  "evaluation_period_s": period, "max_inter_channel_skew_s": skew,
                  "steady_tolerance_rel": case["steady_tolerance_rel"]},
        "frames": frames,
        "summary": summary,
        "limitations": [
            "Offline replay of one immutable observation set; no live cadence, latency or availability is shown.",
            "Parameters are synthetic placeholders; no prediction is a Porsche value.",
            "Frame verdicts share the parameter uncertainty and are not independent trials.",
            "A digitally_checked status means the declared rules executed; it is not physical correlation.",
        ],
    }
    validator = contract.SchemaValidator(contract.load_json(REPLAY_SCHEMA))
    errors = validator.errors(report, validator.root["$defs"]["replay_report"])
    if errors:
        raise ReplayRejected("REPORT_INVALID", "the report does not match its schema", errors)
    return report


def summarise(frames: list, outputs: list, windows: list, rules: dict, slice_contract: dict) -> dict:
    quantities = {q["quantity_id"]: q["canonical_unit"] for q in slice_contract["quantities"]}
    specs = {c["channel_id"]: c for c in slice_contract["channels"]}
    summary = {}
    for output in outputs:
        out_id = output["output_id"]
        states = [frame["outputs"][out_id] for frame in frames]
        counts = {v: sum(1 for s in states if s["verdict"] == v) for v in ("consistent", "indeterminate", "discrepant", "no_claim")}
        evaluated = len(states) - counts["no_claim"]
        reasons: dict[str, int] = {}
        for state in states:
            for reason in state["reasons"]:
                reasons[reason] = reasons.get(reason, 0) + 1
        z_values = [abs(s["z"]) for s in states if s["verdict"] != "no_claim"]
        if evaluated < rules["min_evaluated_frames_per_output"]:
            verdict = "no_claim"
        elif counts["discrepant"] / evaluated >= rules["rejected_min_discrepant_fraction"]:
            verdict = "model_rejected"
        elif counts["discrepant"] / evaluated <= rules["consistent_max_discrepant_fraction"] and \
                counts["indeterminate"] / evaluated <= rules["consistent_max_indeterminate_fraction"]:
            verdict = "consistent"
        else:
            verdict = "indeterminate"
        window_rows = []
        for index, interval in enumerate(windows):
            inside = [frame["outputs"][out_id] for frame in frames if frame["steady_window"] == index]
            judged = [s for s in inside if s["verdict"] != "no_claim"]
            window_rows.append({
                "window": index, "interval_s": interval, "evaluated": len(judged),
                "consistent": sum(1 for s in judged if s["verdict"] == "consistent"),
                "indeterminate": sum(1 for s in judged if s["verdict"] == "indeterminate"),
                "discrepant": sum(1 for s in judged if s["verdict"] == "discrepant"),
                "no_claim": len(inside) - len(judged),
                "mean_residual": r(sum(s["residual"] for s in judged) / len(judged)) if judged else None,
                "mean_z": r(sum(s["z"] for s in judged) / len(judged)) if judged else None,
            })
        summary[out_id] = {
            "unit": quantities[specs[output["compare_channel"]]["quantity_id"]],
            "frames": len(states), "evaluated": evaluated, **counts,
            "no_claim_reasons": dict(sorted(reasons.items())),
            "max_abs_z": r(max(z_values)) if z_values else None,
            "verdict": verdict, "windows": window_rows,
        }
    return summary


def render(report: dict) -> str:
    """Indented JSON with one twin-state frame per line; byte-stable for a given report."""
    shell = dict(report)
    shell["frames"] = "@@FRAMES@@"
    text = json.dumps(shell, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False)
    rows = ",\n".join("  " + json.dumps(frame, sort_keys=True, ensure_ascii=False, allow_nan=False)
                      for frame in report["frames"])
    return text.replace('"@@FRAMES@@"', "[\n" + rows + "\n ]") + "\n"


def bindings_for(run: dict) -> dict:
    """Current hashes of the files a run names, for a maintainer re-binding a changed input."""
    current = {kind: {"path": bound["path"], "sha256": contract.canonical_sha256(read_repo_json(bound["path"]))}
               for kind, bound in run["inputs"].items()}
    current["frames_sha256"] = frames_sha256(read_repo_json(run["inputs"]["slice_contract"]["path"]))
    return current


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN, help="replay_run document")
    parser.add_argument("--out", type=Path, help="report path (default: the run's report path)")
    parser.add_argument("--external-samples", type=Path, help="folder outside the repository holding private samples")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="compare with the committed report byte for byte")
    mode.add_argument("--print-bindings", action="store_true")
    args = parser.parse_args(argv)
    run = contract.load_json(args.run)
    if args.print_bindings:
        print(json.dumps(bindings_for(run), indent=2, sort_keys=True))
        return 0
    try:
        text = render(replay(run, external=args.external_samples))
    except ReplayRejected as rejected:
        print(json.dumps({"rejected": rejected.code, "message": str(rejected), "details": rejected.details},
                         indent=2), file=sys.stderr)
        return 2
    target = args.out or repo_path(run["report"])
    if args.check:
        committed = repo_path(run["report"])
        if not committed.is_file() or committed.read_text(encoding="utf-8") != text:
            print(f"{run['report']} is not reproduced by this replay; rerun without --check after review",
                  file=sys.stderr)
            return 1
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        print(f"{run['report']} reproduced byte for byte (sha256 {digest})")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"wrote {target} (sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
