"""Accept bounded single-factor experiments; never execute model-generated code."""
import argparse
import json
import math
from pathlib import Path

BOUNDS = {"blade_pitch_deg": (30, 48), "tip_twist_deg": (-16, -4),
          "camber_mm": (-5.5, -2), "sweep_mm": (-8, 16),
          "blade_tip_chord_mm": (60, 80)}


def accept(response, baseline):
    # The selected coding adapter emits this literal prefix; no Python evaluation.
    text = response.strip().removeprefix("root = ")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate parameter")
            result[key] = value
        return result
    values = json.loads(text, object_pairs_hook=unique)
    if not isinstance(values, dict) or set(values) != set(BOUNDS):
        raise ValueError("Exactly five blade parameters required")
    for key, (low, high) in BOUNDS.items():
        value = values[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Out-of-bounds parameter: " + key)
    if sum(values[key] != baseline[key] for key in BOUNDS) != 1:
        raise ValueError("Exactly one parameter must differ from control")
    candidate = baseline | values
    candidate["parameter_evidence"] = baseline["parameter_evidence"] | {
        "qwen": "Bounded single-factor experiment; model output is not aerodynamic evidence"}
    return candidate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = accept(json.loads(args.receipt.read_text())["response"],
                    json.loads(args.baseline.read_text()))
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
