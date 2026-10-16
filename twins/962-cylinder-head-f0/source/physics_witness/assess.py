"""Independent uniaxial references for a hypothetical MOOSE software witness."""
import argparse
import base64
import csv
import hashlib
import json
import math
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frozen_reference(card, contract, plastic=False):
    """Enforce the retained pre-native laws, tolerances and both full histories."""
    if (card["classification"] != "HYPOTHETICAL_SOFTWARE_VERIFICATION_ONLY"
            or card["not_a_physical_material_or_head_simulation"] is not True
            or card["units"] != dict(length="mm", stress="MPa", temperature="K", time="synthetic_step")
            or contract["classification"] != card["classification"]
            or contract["frozen_before_native_run"] is not True):
        raise ValueError("The frozen witness must remain explicitly hypothetical with unchanged units")
    tolerances = card["predeclared_absolute_tolerances"]
    if (tolerances != contract["predeclared_absolute_tolerances"]
            or set(tolerances) != {"stress_MPa", "displacement_mm", "temperature_K", "plastic_strain"}
            or any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
                   for value in tolerances.values())):
        raise ValueError("Frozen positive finite tolerances changed")
    elastic = reference(card)
    inelastic = reference(card, plastic=True)
    if elastic != contract["elastic_reference"] or inelastic != contract["plastic_reference"]:
        raise ValueError("Reference differs from the predeclared contract")
    return inelastic if plastic else elastic


def reference(card, plastic=False):
    """Use engineering length ratios and a 1-D perfect-plastic return map."""
    rows = []
    plastic_zz = 0.0
    stress_free = card["stress_free_temperature_K"]
    cte_ref = card["mean_cte_reference_temperature_K"]
    alpha_sf = card["mean_cte_at_300K_per_K"]
    base_expansion = alpha_sf * (stress_free - cte_ref)
    for time, temperature in enumerate(card["temperature_history_K"]):
        delta = temperature - stress_free
        young = card["youngs_modulus_at_300K_MPa"] + card["youngs_modulus_slope_MPa_per_K"] * delta
        poisson = card["poissons_ratio_at_300K"] + card["poissons_ratio_slope_per_K"] * delta
        alpha_mean = alpha_sf + card["mean_cte_slope_per_K2"] * delta
        thermal_strain = (alpha_mean * (temperature - cte_ref) - base_expansion) / (1.0 + base_expansion)
        trial = young * (-thermal_strain - plastic_zz)
        yield_stress = card["yield_at_300K_MPa"] + card["yield_slope_MPa_per_K"] * delta
        stress = max(-yield_stress, min(yield_stress, trial)) if plastic else trial
        if plastic:
            plastic_zz = -thermal_strain - stress / young
        lateral_strain = thermal_strain - poisson * stress / young - plastic_zz / 2.0
        fields = {"temperature_min": temperature, "temperature_max": temperature}
        for component in ("xx", "yy", "xy", "xz", "yz", "zz"):
            for extreme in ("min", "max"):
                fields[f"stress_{component}_{extreme}"] = stress if component == "zz" else 0.0
        for component, length in zip(("x", "y", "z"), card["geometry_mm"]):
            end = length * lateral_strain if component != "z" else 0.0
            fields[f"disp_{component}_min"] = min(0.0, end)
            fields[f"disp_{component}_max"] = max(0.0, end)
        if plastic:
            fields["plastic_zz_min"] = plastic_zz
            fields["plastic_zz_max"] = plastic_zz
        rows.append({"time": float(time), "youngs_modulus_MPa": young, "poissons_ratio": poisson,
                     "mean_cte_per_K": alpha_mean, "thermal_strain": thermal_strain,
                     "yield_MPa": yield_stress, "fields": fields})
    return rows


def assess(csv_path, card, contract, plastic=False):
    expected = frozen_reference(card, contract, plastic)
    with Path(csv_path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(expected):
        raise ValueError("Incomplete or additional native time history")
    checks = []
    tolerances = card["predeclared_absolute_tolerances"]
    for row, target in zip(rows, expected):
        if float(row["time"]) != target["time"]:
            raise ValueError("Missing, duplicate or out-of-order native time")
        for field, value in target["fields"].items():
            actual = float(row[field])
            key = ("temperature_K" if field.startswith("temperature") else
                   "displacement_mm" if field.startswith("disp") else
                   "plastic_strain" if field.startswith("plastic") else "stress_MPa")
            tolerance = tolerances[key]
            checks.append({"time": target["time"], "field": field, "expected": value,
                           "actual": actual, "absolute_tolerance": tolerance,
                           "absolute_error": abs(actual - value),
                           "pass": math.isfinite(actual) and abs(actual - value) <= tolerance})
    return {"passed": all(check["pass"] for check in checks),
            "classification": card["classification"], "plastic": plastic,
            "native_times": len(rows), "checks_count": len(checks), "checks": checks,
            "reference": expected, "native_csv_sha256": hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
            "scope": "Synthetic constitutive/field verification only; prescribed uniform temperature, no heat equation, no head geometry or manufacturing prediction."}


def native_proof(csv_path, card, contract, manifest, contract_path, plastic=False):
    """Bind fields to the original native SSH capture, not an after-the-fact CSV."""
    frozen_reference(card, contract, plastic)
    csv_path = Path(csv_path)
    directory = csv_path.parent
    receipt = json.loads((directory / "native-execution.json").read_text())
    log = (directory / "native.log").read_bytes()
    inputs = receipt["input_sha256"]
    required = {"variable-thermoelastic.i", "hypothetical-material.json"}
    if plastic:
        required.add("variable-yield.i")
    if set(inputs) != required:
        raise ValueError("Native input artifact set changed")
    mode = "plastic" if plastic else "elastic"
    csv_name = ("variable-yield" if plastic else "variable-thermoelastic") + "_out.csv"
    exodus_name = csv_name[:-4] + ".e"
    capture = manifest["runs"][mode]
    artifact_names = required | {"native.log", "native-execution.json", csv_name, exodus_name}
    order = capture["artifact_order"]
    if (set(order) != artifact_names or len(order) != len(artifact_names)
            or set(capture["artifacts_sha256"]) != artifact_names):
        raise ValueError("Original native capture artifact set changed")
    ssh = json.loads((directory / "ssh-execution.json").read_text())
    # This exact encoding was used by the executed capture command. Its digest
    # authenticates the retained output bytes against the original SSH receipt.
    captured = {**receipt, "artifacts_base64": {
        name: base64.b64encode((directory / name).read_bytes()).decode() for name in order}}
    captured_sha = hashlib.sha256((json.dumps(captured) + "\n").encode()).hexdigest()
    checks = {
        "manifest_classification": manifest["classification"] == card["classification"],
        "frozen_contract_hash": sha256(contract_path) == manifest["predeclared_contract_sha256"],
        "capture_directory": capture["directory"] == directory.name,
        "assessed_csv_is_native_artifact": csv_path.name == csv_name,
        "capture_artifact_hashes": all(sha256(directory / name) == digest
                                       for name, digest in capture["artifacts_sha256"].items()),
        "original_ssh_capture": (ssh["returncode"] == 0
            and sha256(directory / "ssh-execution.json") == capture["ssh_execution_sha256"]
            and captured_sha == ssh["stdout_sha256"] == capture["ssh_stdout_sha256"]),
        "native_execution_hash": sha256(directory / "native-execution.json") == capture["native_execution_sha256"],
        "native_returncode": receipt["returncode"] == 0,
        "pinned_binary": receipt["binary_sha256"] == card["native_binary_sha256"],
        "binary_unchanged": receipt["binary_unchanged"] is True,
        "inputs_unchanged": receipt["inputs_unchanged"] is True,
        "bounded_runtime": 0 < receipt["wall_seconds"] <= card["max_runtime_seconds_per_witness"],
        "bounded_deadline": 0 < receipt["deadline_seconds"] <= card["max_runtime_seconds_per_witness"],
        "native_log_hash": hashlib.sha256(log).hexdigest() == receipt["log_sha256"],
        "six_converged_steps": log.count(b"Solve Converged!") == len(card["temperature_history_K"]) - 1,
        "complete_input_set": set(inputs) == required,
        "input_hashes_match": all(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
                                  for name, digest in inputs.items()),
        "native_inputs_frozen_before_run": all(digest == contract["source_sha256"][name]
                                                for name, digest in inputs.items()),
        "assessed_card_matches_native": json.loads((directory / "hypothetical-material.json").read_text()) == card,
    }
    return {"passed": all(checks.values()), "checks": checks,
            "receipt_sha256": sha256(directory / "native-execution.json"),
            "original_capture_sha256": captured_sha,
            "frozen_reference_assessor_sha256": contract["source_sha256"]["assess.py"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--card", type=Path, default=Path(__file__).with_name("hypothetical-material.json"))
    parser.add_argument("--contract", type=Path, help="Retained pre-native contract; default beside run directories")
    parser.add_argument("--manifest", type=Path, help="Original SSH capture manifest; default beside run directories")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plastic", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("Assessment output must be new; preserve previous evidence")
        contract_path = args.contract or args.csv.parent.parent / "predeclared-contract.json"
        manifest_path = args.manifest or args.csv.parent.parent / "native-capture-manifest.json"
        card = json.loads(args.card.read_text())
        contract = json.loads(contract_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        result = assess(args.csv, card, contract, args.plastic)
        result["native_proof"] = native_proof(args.csv, card, contract, manifest, contract_path, args.plastic)
        result["passed"] = result["passed"] and result["native_proof"]["passed"]
        result["assessor_sha256"] = sha256(__file__)
        result["predeclared_contract_sha256"] = sha256(contract_path)
        result["native_capture_manifest_sha256"] = sha256(manifest_path)
        with args.output.open("x") as stream:
            stream.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
        print(json.dumps({key: result[key] for key in ("passed", "native_times", "checks_count", "plastic")}))
        return 0 if result["passed"] else 1
    except (ValueError, OSError, KeyError, TypeError, ZeroDivisionError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
