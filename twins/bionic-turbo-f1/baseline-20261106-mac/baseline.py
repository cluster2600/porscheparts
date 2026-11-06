#!/usr/bin/env python3
"""Validate the additive Mac baseline using the unchanged historical validator."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "baseline-20261106"
spec = importlib.util.spec_from_file_location("turbo_baseline_parent", PARENT / "baseline.py")
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)


def check():
    errors = parent.check_all(PARENT) + parent.check_all(HERE)
    manifest = parent.load_json(HERE / "baseline-manifest.json")
    errors += parent.verify_receipt(manifest["parent_manifest"])
    return errors


def evaluate():
    data = parent.load_baseline(HERE)
    results = {}
    for gate in ("G01-baseline-frozen", "G01-execution-contract"):
        attestation = parent.load_json(HERE / (gate + "-attestation.json"))
        accepted, reasons = parent.evaluate_gate(gate, data["ledger"], data["matrix"], attestation)
        results[gate] = {"may_open": accepted, "reasons": reasons}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "evaluate"), default="check", nargs="?")
    args = parser.parse_args()
    errors = check()
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        return 1
    if args.command == "check":
        print("Mac baseline and frozen parent: OK")
        return 0
    results = evaluate()
    print(json.dumps(results, indent=2))
    return 0 if all(result["may_open"] for result in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
