"""Bound the conditional 935 hub annulus using all observed axial circle fits."""

import hashlib
import json
import math
from pathlib import Path
import sys

INPUT_SHA256 = "b45d4eab6d6a6d8ac89035bbf8d23d0f9fb3b110a9fc1a479e2e46430bd8a660"


def run(source: Path, target: Path) -> None:
    source = source.resolve()
    target = target.resolve()
    if target.exists() or not target.is_relative_to((Path.cwd() / "work").resolve()):
        raise ValueError("Use a new private work/ report")
    if hashlib.sha256(source.read_bytes()).hexdigest() != INPUT_SHA256:
        raise ValueError("Pinned metrology input changed")
    data = json.loads(source.read_text())
    if data["scale_verified"] or data["shaft_hub_fit_verified"] or data["torque_path_defined"]:
        raise ValueError("Unexpectedly verified interface; reassess this exploratory screen")
    fits = data["sidewall_circle_fits"]
    drive, rotor = fits["drive_observed"], fits["rotor_candidate"]
    if len(drive) != 4 or len(rotor) != 4:
        raise ValueError("Four paired axial bands required")
    bands = []
    for d, r in zip(drive, rotor):
        if d["z_band_source_units"] != r["z_band_source_units"]:
            raise ValueError("Mismatched axial bands")
        rd, rr = d["radius_source_units"], r["radius_source_units"]
        residual = d["radial_absolute_q95_source_units"] + r["radial_absolute_q95_source_units"]
        centre_offset = math.hypot(*d["centre_xy_source_units"])
        nominal_gap = rr - rd
        lower_screen = nominal_gap - residual - centre_offset
        if lower_screen <= 0 or d["maximum_unsampled_gap_deg"] < 90:
            raise ValueError("Unexpected gap or scan coverage")
        bands.append({"z_band_source_units": d["z_band_source_units"],
                      "drive_fit_radius_source_units": rd,
                      "rotor_fit_bore_radius_source_units": rr,
                      "nominal_radial_gap_source_units": nominal_gap,
                      "screened_gap_after_q95_residuals_and_centre_offset_source_units": lower_screen,
                      "unobserved_drive_arc_deg": d["maximum_unsampled_gap_deg"]})
    result = {"status": "partial_arc_radial_window_screen_only",
              "input_sha256": INPUT_SHA256,
              "radius_method": "Separate circle fits to observed sidewall face centroids in four paired axial bands",
              "lower_screen_method": "Fit radius gap minus both q95 radial residuals and drive centre offset; q95 is not a geometric bound",
              "bands": bands,
              "min_nominal_gap_source_units": min(b["nominal_radial_gap_source_units"] for b in bands),
              "min_screened_gap_source_units": min(b["screened_gap_after_q95_residuals_and_centre_offset_source_units"] for b in bands),
              "full_drive_circumference_observed": False,
              "source_unit_to_mm_verified": False,
              "fit_tolerance_defined": False,
              "torque_transfer_defined": False,
              "manufacturing_authorized": False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "minimum_screened_gap_source_units": result["min_screened_gap_source_units"],
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: screen_hub_radial_window.py METROLOGY_JSON NEW_PRIVATE_JSON")
    run(Path(sys.argv[1]), Path(sys.argv[2]))
