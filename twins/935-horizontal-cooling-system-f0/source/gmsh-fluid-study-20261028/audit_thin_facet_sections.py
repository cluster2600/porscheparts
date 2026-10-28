"""Locate thin rotor facets relative to acquired blade-section stations."""

import hashlib
import json
import math
from pathlib import Path
import sys

import trimesh


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if len(sys.argv) != 6:
    raise SystemExit("Usage: audit_thin_facet_sections.py CANDIDATE_OFF SECTIONS_JSON PROXIMITY_JSON FRAME_JSON NEW_PRIVATE_JSON")
candidate, sections_path, proximity_path, frame_path, output = (Path(value).resolve() for value in sys.argv[1:])
if output.exists() or not output.is_relative_to((Path.cwd() / "work").resolve()):
    raise SystemExit("Use a fresh private output under work/")
expected = {
    candidate: "5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a",
    sections_path: "308f95fa80ac19703e3f8d4a375250070c4723cc775137cf9f14a8c105ea3777",
    proximity_path: "0a65e716aa0f9f62c4950c26c48ede84db5647c713a2d5fa0230bc2a9dc427bf",
    frame_path: "c9e86cbbc1fb0e1faa7add119bc69dfa87e8def68d67a5b7d1f7cf661c832e3f",
}
if any(sha(path) != digest for path, digest in expected.items()):
    raise SystemExit("Input hash mismatch")
sections = json.loads(sections_path.read_text())
proximity = json.loads(proximity_path.read_text())
frame = json.loads(frame_path.read_text())
if (sections["source_sha256"] != frame["original_obj_sha256"]
        or proximity["aligned_scan_sha256"] != frame["aligned_npz_sha256"]
        or sections["scale_verified"] is not False):
    raise SystemExit("Scan lineage or scale status mismatch")
blades = []
for blade in sections["blades"]:
    acquired = [float(row["station_source_units"]) for row in blade["provenance"]
                if row["classification"] == "registered_acquired_reference_section"]
    if not acquired:
        raise SystemExit("Blade has no acquired reference station")
    blades.append((blade["id"], float(blade["phase_radians"]), max(acquired)))
if len(blades) != 9 or len({row[0] for row in blades}) != 9:
    raise SystemExit("Expected nine distinct blade regions")
mesh = trimesh.load_mesh(candidate, process=False)
rows = []
for item in proximity["per_facet"]:
    if item["quality"] >= 0.01:
        continue
    point = mesh.triangles[item["face_id"]].mean(axis=0)
    angle = math.atan2(point[1], point[0])
    phase_delta = lambda phase: math.atan2(math.sin(angle - phase), math.cos(angle - phase))
    blade_id, phase, last_station = min(blades, key=lambda blade: abs(phase_delta(blade[1])))
    station = float(point[0] * math.cos(phase) + point[1] * math.sin(phase))
    rows.append({"face_id": item["face_id"], "nearest_blade_id": blade_id,
                 "angular_offset_degrees": abs(math.degrees(phase_delta(phase))),
                 "projected_station_source_units": station,
                 "last_acquired_station_source_units": last_station,
                 "beyond_last_acquired_station": station > last_station,
                 "maximum_sample_scan_distance_source_units": max(item["sample_distances"])})
if len(rows) != 24:
    raise SystemExit("Unexpected worst-facet count")
report = {
    "status": "station_screen_not_measured_surface_classification",
    "candidate_sha256": expected[candidate], "sections_sha256": expected[sections_path],
    "proximity_sha256": expected[proximity_path], "frame_audit_sha256": expected[frame_path],
    "worst_facets": len(rows),
    "beyond_nearest_blade_last_acquired_station": sum(row["beyond_last_acquired_station"] for row in rows),
    "sample_distance_over_one_unit": sum(row["maximum_sample_scan_distance_source_units"] > 1 for row in rows),
    "both_conditions": sum(row["beyond_last_acquired_station"] and row["maximum_sample_scan_distance_source_units"] > 1 for row in rows),
    "maximum_angular_offset_degrees": max(row["angular_offset_degrees"] for row in rows),
    "rows": rows, "source_units_calibrated": False,
    "physical_registration_and_functional_datum_verified": False,
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: value for key, value in report.items() if key != "rows"}))
