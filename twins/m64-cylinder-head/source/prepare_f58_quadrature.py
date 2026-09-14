#!/usr/bin/env python3
"""Prepare two pinned F58 thermal decks; never execute an engineering solver."""
import argparse
import hashlib
import json
from pathlib import Path
import re

REFERENCE_SHA = "7448656ae19242c05e47761117df488e9b4594c12f73b62c020912d68aea75da"
HISTORICAL = {"system/controlDict", "system/fvSolution"}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_read(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink_input")
    require(path.is_file(), "missing_input")
    return path.read_bytes()


def replace_once(data, pattern, replacement):
    result, count = re.subn(pattern, replacement, data, flags=re.MULTILINE)
    require(count == 1, "ambiguous_or_missing_dictionary_entry")
    return result


def thermal_guards(payload):
    expected = {
        "system/controlDict": ((b"startFrom", b"startTime"), (b"startTime", b"0"),
            (b"stopAt", b"endTime"), (b"deltaT", b"2.5e-08"),
            (b"adjustTimeStep", b"no"), (b"writeInterval", b"0.00004")),
        "system/fvSolution": ((b"nOuterCorrectors", b"0"),
            (b"explicitSolve", b"true"), (b"Tmax", b"3300.0")),
    }
    for name, fields in expected.items():
        data = payload[name]
        if name == "system/controlDict":
            data = re.split(rb"^\s*functions\s*$", data, maxsplit=1, flags=re.M)[0]
        for key, value in fields:
            matches = re.findall(rb"^\s*" + key + rb"\s+([^;\r\n]+);", data, re.M)
            require(matches == [value], "unexpected_thermal_dictionary_entry:" + key.decode())


def prepare(reference, source_case, historical_system, output):
    reference, source_case, historical_system, output = map(
        Path, (reference, source_case, historical_system, output))
    raw_reference = checked_read(reference)
    require(digest(raw_reference) == REFERENCE_SHA, "reference_sha_mismatch")
    pins = json.loads(raw_reference)["source_inputs_sha256"]
    require(len(pins) == 29 and HISTORICAL <= pins.keys(), "source_whitelist_mismatch")
    payload, paths = {}, {}
    for name, expected in pins.items():
        rel = Path(name)
        require(not rel.is_absolute() and ".." not in rel.parts
                and rel.parts[0] in ("0", "constant", "system"), "invalid_whitelist_path")
        path = historical_system / rel.name if name in HISTORICAL else source_case / rel
        payload[name], paths[name] = checked_read(path), path
        require(digest(payload[name]) == expected, "source_sha_mismatch:" + name)
    thermal_guards(payload)
    common = dict(payload)
    common["system/controlDict"] = replace_once(payload["system/controlDict"],
        rb"^(\s*endTime\s+)0\.00012(;)", rb"\g<1>0.00004\2")
    fine = dict(common)
    fine["constant/heatSourceDict"] = replace_once(common["constant/heatSourceDict"],
        rb"^(\s*nPoints\s+)\(10 10 10\)(;)", rb"\g<1>(20 20 20)\2")
    require({k for k in pins if common[k] != fine[k]} == {"constant/heatSourceDict"},
            "quadrature_only_difference_failed")
    require(not output.exists() and not output.is_symlink(), "output_must_be_new")
    require(not any(p.is_symlink() for p in output.parents), "symlink_output_parent")
    for root in (source_case, historical_system, reference.parent):
        require(not output.resolve().is_relative_to(root.resolve()), "output_inside_inputs")
    output.mkdir(parents=False, exist_ok=False)
    cases = {}
    for case, contents in (("q10", common), ("q20", fine)):
        for name, data in contents.items():
            destination = output / case / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            require(checked_read(destination) == data, "written_deck_mismatch")
        observed = {str(p.relative_to(output / case)) for p in (output / case).rglob("*") if p.is_file()}
        require(observed == pins.keys(), "written_whitelist_mismatch")
        cases[case] = {"inputs_sha256": {k: digest(v) for k, v in contents.items()},
                       "changed_from_source": sorted(k for k in pins if contents[k] != payload[k])}
    require(checked_read(reference) == raw_reference, "reference_changed_during_preparation")
    for name, path in paths.items():
        require(checked_read(path) == payload[name], "source_changed_during_preparation")
    report = {"schema": "m64-f58-quadrature-preparation/v1", "status": "prepared_NOT_RUN",
        "source_reference_sha256": REFERENCE_SHA, "source_inputs_sha256": pins,
        "source_paths_private": {k: str(v) for k, v in paths.items()}, "cases": cases,
        "script_sha256": digest(Path(__file__).read_bytes()),
        "dt_s": 2.5e-8, "end_time_s": 4e-5, "expected_steps": 1600,
        "source_inputs_unchanged": True, "only_between_case_difference": "constant/heatSourceDict:nPoints",
        "native_executed": False, "ready_for_execution": False,
        "runtime_and_40us_countercheck_required": True, "manufacturing_authorized": False}
    (output / "preparation-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("reference", "source-case", "historical-system", "output"):
        parser.add_argument("--" + flag, required=True)
    args = vars(parser.parse_args())
    report = prepare(**args)
    print(json.dumps({"status": report["status"], "cases": 2, "native_executed": False}))


if __name__ == "__main__":
    main()
