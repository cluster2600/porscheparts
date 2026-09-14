#!/usr/bin/env python3
"""Read two pinned F58 logs on 0–40 us; do not infer solver exit or validity."""
import argparse
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path

PARSER_SHA = "65d07baa7d0f4395849263c1fcd62e28a281ad406453c51fa7c1faeb2bd73824"
DT, END, COUNT = 2.5e-8, 4e-5, 1600
KEYS = ("sensible_storage_j", "latent_storage_j", "boundary_diffusion_in_j",
        "laser_in_j", "advective_out_j", "limiter_sink_j")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_parser(path):
    require(digest(path) == PARSER_SHA, "parser_sha_mismatch")
    spec = importlib.util.spec_from_file_location("f58_pinned_parser", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze(path, parser):
    historical = parser.evaluate(path, DT)  # Its 120 us criterion is unchanged.
    require(not historical["fatal_error_in_log"], "fatal_error_in_log")
    rows = [list(map(Decimal, line.split()[1:])) for line in path.read_text().splitlines()
            if line.startswith("F58_BALANCE ")]
    require(len(rows) == COUNT, "expected_1600_samples")
    require(all(len(r) == 10 and all(v.is_finite() for v in r) for r in rows), "invalid_decimal_sample")
    require(math.isclose(float(rows[-1][0]), END, rel_tol=0, abs_tol=1e-13), "wrong_common_end_time")
    # Reparse the printed decimal tokens independently; no public residual reused.
    with localcontext() as ctx:
        ctx.prec = 80
        residuals, differences, energies = [], [], [Decimal(0)] * 6
        previous = 0.0
        for row in rows:
            require(math.isclose(float(row[1]), DT, rel_tol=1e-10), "wrong_dt")
            require(math.isclose(float(row[0])-previous, DT, rel_tol=1e-7, abs_tol=1e-15), "unordered_or_missing_step")
            previous = float(row[0])
            terms = (row[3], row[4], -row[5], -row[6], row[7], row[8])
            residual = sum(terms, Decimal(0))
            difference = abs(residual - row[9])
            tolerance = Decimal("1e-12") + Decimal("5e-15") * sum(map(abs, terms))
            require(difference <= tolerance, "decimal_component_residual_disagreement")
            require(row[7] == 0, "nonzero_advection_in_thermal_coupon")
            residuals.append(residual * row[1])
            differences.append(difference)
            energies = [a + w * row[1] for a, w in zip(energies, row[3:9])]
        integrals = dict(zip(KEYS, map(float, energies)))
        integrals["equation_residual_j"] = float(sum(residuals, Decimal(0)))
        absolute_residual = float(sum(map(abs, residuals), Decimal(0)))
    require(all(math.isfinite(v) for v in integrals.values()), "nonfinite_integral")
    laser = integrals["laser_in_j"]
    capped = [r for r in rows if r[2] >= Decimal(3299)]
    return {"historical_evaluation_120us_criterion_unchanged": historical,
        "common_window_complete_40us": True, "energy_log_consistent": True,
        "independent_method": "80_digit_Decimal_reparse_of_six_printed_components",
        "integrated_terms": integrals, "absolute_residual_energy_j": absolute_residual,
        "max_logged_decimal_residual_difference_w": float(max(differences)),
        "incident_energy_j": 0.0152, "absorbed_fraction_of_incident": laser / 0.0152,
        "limiter_fraction_of_absorbed": integrals["limiter_sink_j"] / laser if laser else None,
        "max_temperature_k": float(max(r[2] for r in rows)),
        "temperature_censored": bool(capped),
        "first_cap_time_s": float(capped[0][0]) if capped else None,
        "temperature_validated": False}, [r[0] for r in rows], [float(r[2]) for r in rows]


def compare(q10_log, q10_sha256, q20_log, q20_sha256, parser, output):
    q10_log, q20_log, parser, output = map(Path, (q10_log, q20_log, parser, output))
    require(not output.exists() and not output.is_symlink(), "output_must_be_new")
    inputs = {q10_log: q10_sha256, q20_log: q20_sha256, parser: PARSER_SHA}
    require(q10_log.resolve() != q20_log.resolve(), "distinct_log_paths_required")
    for path, expected in inputs.items():
        require(path.is_file() and path.stat().st_size <= 128 * 1024**2, "input_missing_or_oversize")
        require(digest(path) == expected, "input_sha_mismatch")
    public = load_parser(parser)
    a, ta, temp_a = analyze(q10_log, public)
    b, tb, temp_b = analyze(q20_log, public)
    require(ta == tb, "paired_sample_times_differ")
    deltas = {}
    for key in (*KEYS, "equation_residual_j"):
        x, y = a["integrated_terms"][key], b["integrated_terms"][key]
        deltas[key] = {"absolute": abs(x-y), "relative_to_q20": abs(x-y)/abs(y) if y else None}
    for path, expected in inputs.items():
        require(digest(path) == expected, "input_changed_during_read")
    report = {"schema": "m64-f58-quadrature-40us-energy/v1",
        "status": "postprocessed_NOT_NATIVE_EXIT_VERIFIED", "postprocessing_completed": True,
        "parser_sha256": PARSER_SHA, "adapter_sha256": digest(Path(__file__)),
        "log_sha256": {"q10": q10_sha256, "q20": q20_sha256}, "inputs_unchanged": True,
        "cases": {"q10": a, "q20": b}, "common_window_complete_40us": True,
        "paired_samples": COUNT, "energy_log_consistent": True, "integral_differences": deltas,
        "max_paired_temperature_difference_k": max(abs(x-y) for x, y in zip(temp_a, temp_b)),
        "zero_denominator_relative_is_null": True, "native_executed": False,
        "solver_exit_status_verified": False, "convergence_order_established": False,
        "CFD_authorized": False, "manufacturing_authorized": False, "full_head_simulated": False}
    with output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("q10-log", "q10-sha256", "q20-log", "q20-sha256", "parser", "output"):
        parser.add_argument("--" + flag, required=True)
    report = compare(**vars(parser.parse_args()))
    print(json.dumps({"status": report["status"], "paired_samples": COUNT,
                      "manufacturing_authorized": False}))


if __name__ == "__main__":
    main()
