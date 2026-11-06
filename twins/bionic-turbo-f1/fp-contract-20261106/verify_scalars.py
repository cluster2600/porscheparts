"""Independent exact-decimal checks for the prescribed native token controls."""

from fractions import Fraction
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def verify(cases, receipt):
    expected = {case["id"]: case for case in cases}
    runs = receipt["runs"]
    if len(expected) != len(cases) or len(runs) != len(cases) or {r["id"] for r in runs} != set(expected):
        raise ValueError("exact unique control coverage required")
    if receipt["precision"] != 16 or receipt["locale"] != "C" or receipt["function_entries_enabled"]:
        raise ValueError("substituted execution configuration")
    results = []
    for run in runs:
        case = expected[run["id"]]
        source = ("value " + case["input"] + ";\n").encode()
        if hashlib.sha256(source).hexdigest() != run["input_sha256"]:
            raise ValueError("input bytes changed")
        criterion = case["criterion"]
        if "command not found" in run["stderr"]:
            raise ValueError("unexpected setup diagnostic")
        if criterion == "reject":
            passed = (run["exit_code"] == 1 and "FOAM FATAL IO ERROR" in run["stderr"]
                      and "ill defined primitiveEntry" in run["stderr"])
            result = {"id": run["id"], "rejected_by_native_parser": passed}
        else:
            text = run["stdout"].strip()
            value = Fraction(text)
            original = Fraction(case["input"])
            passed = (run["exit_code"] == 0 and run["stderr"].strip()
                      == "Not expanding variables or dictionary directives")
            if criterion in ("zero", "positive_zero"):
                passed = passed and value == 0
                if criterion == "positive_zero":
                    passed = passed and not text.startswith("-")
            elif criterion == "positive":
                passed = passed and value > 0
            elif criterion == "bounded_error":
                passed = passed and abs(value - original) <= abs(original) / 10**15
            elif criterion != "boundary_observation":
                raise ValueError("unknown prescribed criterion")
            result = {"id": run["id"], "output_rational": str(value),
                      "absolute_decimal_change": str(abs(value - original)),
                      "boundary_qualified": False}
        if not passed:
            raise ValueError("control failed: " + run["id"])
        results.append(result)
    return {"status": "prescribed_token_controls_passed", "controls": results,
            "method": "exact Fraction decimal parsing; no binary float conversion",
            "full_conversion_or_arithmetic_qualification": False,
            "engineering_gate_passed": False}


if __name__ == "__main__":
    cases = json.loads((HERE / "scalar-cases.json").read_text())
    receipt = json.loads((HERE / "native-scalar-receipt.json").read_text())
    for name, field in (("scalar-cases.json", "cases_sha256"),
                        ("SCALAR-PLAN.md", "plan_sha256"),
                        ("SCALAR-RETRY.md", "retry_plan_sha256"),
                        ("source-bindings.json", "source_bindings_sha256")):
        if hashlib.sha256((HERE / name).read_bytes()).hexdigest() != receipt[field]:
            raise ValueError("stale source or prescribed control: " + name)
    report = verify(cases, receipt)
    report["reader_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report["native_receipt_sha256"] = hashlib.sha256((HERE / "native-scalar-receipt.json").read_bytes()).hexdigest()
    print(json.dumps(report, indent=2))
