#!/usr/bin/env python3
"""Additional native-kernel and sampled ligament screens of exported files."""
import argparse
import json
import math
import time
from pathlib import Path

import build123d as b
import numpy as np
import trimesh
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer


def native_bop(step):
    s = b.import_step(step)
    checker = BOPAlgo_ArgumentAnalyzer()
    checker.SetShape1(s.wrapped)
    modes = ["SelfInterMode", "SmallEdgeMode", "RebuildFaceMode", "ContinuityMode", "CurveOnSurfaceMode"]
    for mode in modes:
        setattr(checker, mode, True)
    t = time.monotonic()
    checker.Perform()
    faults = [str(r.GetCheckStatus()) for r in checker.GetCheckResult()]
    result = {"BRep_valid": bool(s.is_valid), "solids": len(s.solids()), "modes": modes,
              "has_faulty": bool(checker.HasFaulty()), "has_errors": bool(checker.HasErrors()),
              "has_warnings": bool(checker.HasWarnings()), "faults": faults, "elapsed_seconds": time.monotonic() - t}
    result["passed"] = result["BRep_valid"] and not any(result[k] for k in ["has_faulty", "has_errors", "has_warnings"])
    return result


def wall_samples(p):
    a, yt, z, r = (p[k] for k in ["gallery_half_spacing", "gallery_turn_y", "gallery_z", "gallery_radius"])
    # Omit the deliberately opened inlet/return zone. This is a stated screen
    # of the interior route only, not a continuous or full-wall certification.
    stations = []
    for y in np.linspace(-70, yt, 22):
        stations += [(np.array([-a, y, z]), np.array([1, 0, 0])), (np.array([a, y, z]), np.array([-1, 0, 0]))]
    for theta in np.linspace(math.pi, 0, 25):
        stations.append((np.array([a * math.cos(theta), yt + a * math.sin(theta), z]), np.array([-math.cos(theta), -math.sin(theta), 0])))
    angles = np.linspace(3 * math.pi / 4, 9 * math.pi / 4, 15)
    profile = [(r * math.cos(t), r * math.sin(t)) for t in angles]
    right = np.array([r / math.sqrt(2), r / math.sqrt(2)])
    apex = np.array([0, math.sqrt(2) * r])
    left = np.array([-r / math.sqrt(2), r / math.sqrt(2)])
    for u in np.linspace(0, 1, 6):
        profile += [tuple(right * (1 - u) + apex * u), tuple(apex * (1 - u) + left * u)]
    return np.array([c + side * n + np.array([0, 0, height]) for c, n in stations for side, height in profile])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--parameters", type=Path, default=Path(__file__).with_name("parameters.json"))
    ap.add_argument("--head-bop", action="store_true")
    args = ap.parse_args()
    output = args.run / ("head-bop.json" if args.head_bop else "additional-checks.json")
    if output.exists():
        raise ValueError("audit_output_must_be_new")
    cad = args.run / "cad"
    if args.head_bop:
        result = native_bop(cad / "head-4v-air-oil-proposal.step")
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
        return
    p = json.loads(args.parameters.read_text())
    report = {"manufacturing_authorized": False, "native_BOP": {}, "wall_screen": None}
    for name in ["oil-gallery-coupon", "coupon-fluid-domain", "turbo-valve-inspection-stand", "head-oil-tool", "head-fluid-domain"]:
        path = cad / f"{name}.step"
        if path.exists():
            print(f"BOP {name}", flush=True)
            report["native_BOP"][name] = native_bop(path)
    source = cad / "head-source-context-concept-only.stl"
    if source.exists():
        print("Sampled gallery ligament screen against the inherited surface", flush=True)
        mesh = trimesh.load_mesh(source, process=True)
        points = wall_samples(p["head"])
        signed = []
        for start in range(0, len(points), 64):
            signed.extend(trimesh.proximity.signed_distance(mesh, points[start:start + 64]))
        distances = np.asarray(signed)
        report["wall_screen"] = {
            "method": "signed_distance_of_sampled_channel_surface_points_to_inherited_STL",
            "source_STL_closed": bool(mesh.is_watertight), "samples": len(points),
            "minimum_sampled_signed_distance_scan_units": float(np.min(distances)),
            "p05_sampled_signed_distance_scan_units": float(np.percentile(distances, 5)),
            "sampled_outside_source_points": int(np.count_nonzero(distances <= 0)),
            "interior_route_sample_screen_3_units_passed": bool(np.min(distances) >= 3),
            "screen_threshold_is_design_choice_not_material_allowable": True,
            "route_excluded_y_less_than": -70, "source_tessellation_tolerance_scan_units": 0.12,
            "CT_or_measurement_based": False, "minimum_continuous_ligament_certified": False,
            "unintended_opening_count_certified": False,
            "physical_scale_verified": False, "hot_strength_verified": False,
        }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(output, flush=True)


if __name__ == "__main__":
    main()
