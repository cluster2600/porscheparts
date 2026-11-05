"""Package only the admitted local hypothesis revision; refuse existing output."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("repository", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    repository = args.repository.resolve()
    output = root / "delivery"
    if output.exists() or (root / "manifest.json").exists():
        raise FileExistsError("Existing delivery or frozen capsule refused")
    read = lambda name: json.loads((root / name).read_text())
    geometry = read("local-printable/digital-geometry-and-export.json")
    supports = read("local-supported/report.json")
    union = read("local-supported-contours/report.json")
    head_cli = read("local-slicing/head-readback.json")
    supported_cli = read("local-supported-contours/readback.json")
    fidelity = read("local-fidelity/report.json")
    construction = read("local-candidate-002/construction.json")
    kali = read("kali-verification/cross-host-receipt.json")
    hypotheses = read("local-support-input/build-hypotheses.json")
    assert geometry["input_sha256"] == "05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594"
    assert geometry["geometry_export_gate_passed"]
    for key in ("intersection_pairs", "zero_area_triangles", "open_edges",
                "nonmanifold_edges", "inconsistently_oriented_edges"):
        assert geometry[key] == 0, key
    assert geometry["connected_components"] == 1 and geometry["vertex_manifold"]
    assert geometry["every_coordinate_index_and_unit_roundtrips_exact"]
    assert supports["reference_head_input_sha256"] == geometry["input_sha256"]
    for key in ("all_resource_geometry_checks_passed", "every_coordinate_and_index_roundtrip_exact",
                "component_graph_readback_passed", "all_supports_have_positive_axial_overlap_with_head",
                "one_connected_union_contact_graph"):
        assert supports[key], key
    assert head_cli["contour_export_gate_passed"] and supported_cli["contour_export_gate_passed"]
    assert union["all_layers_independently_checked"] and union["all_layer_unions_match_independent_geometry"]
    assert union["output_cli_sha256"] == supported_cli["input_sha256"]
    assert union["head_cli_sha256"] == head_cli["input_sha256"]
    assert union["hypotheses_sha256"] == sha(root / "local-support-input/build-hypotheses.json")
    assert kali["native"]["native_topology_volume_check_passed"]
    assert kali["working_vertices_and_faces_match_mac_byte_for_byte"] and kali["remote_manifest_hash_verified"]
    assert kali["runtime"]["mesh_npz_sha256"] == geometry["input_sha256"]
    assert abs(kali["native"]["signed_volume_mm3"] / geometry["signed_volume_mm3"] - 1) < 1e-12
    assert fidelity["all_unselected_parent_faces_preserved"]
    assert construction["selected_provisional_protrusions"] == 11
    assert fidelity["partial_skin_whole_triangle_containment_upper_bound_mm"] < 1e-8
    deliveries = [
        ("local-printable/935-reconstructed-head-hypotheses-mm.3mf", "935-head-hypotheses-mm.3mf", geometry["three_mf_sha256"]),
        ("local-supported/935-supported-composite-mm.3mf", "935-head-supported-hypotheses-mm.3mf", supports["three_mf_sha256"]),
        ("local-build-input/head-build-mm.npz", "head-build-mm.npz", geometry["input_sha256"]),
    ]
    references = [
        ("local-slicing/935-head-hypotheses-50um-fixed.cli", head_cli["input_sha256"]),
        ("local-supported-contours/935-reconstruction-supported-50um.cli", supported_cli["input_sha256"]),
    ]
    for name, _, expected in deliveries:
        assert sha(root / name) == expected, name
    for name, expected in references:
        assert sha(root / name) == expected, name
    output.mkdir(mode=0o700)
    entries = []
    for name, target, expected in deliveries:
        shutil.copy2(root / name, output / target)
        assert sha(output / target) == expected
        entries.append({"path": "delivery/" + target, "sha256": expected,
                        "bytes": (output / target).stat().st_size})
    for name, expected in references:
        entries.append({"path": name, "sha256": expected, "bytes": (root / name).stat().st_size})
    source = repository / "docs/research/935-bare-head-hypothesis-20261105/source"
    shutil.copytree(source, output / "source", ignore=shutil.ignore_patterns("__pycache__"))
    previous = repository / "docs/research/935-hypothesis-study-20261029/source"
    dependencies = ["validate_build_final.py", "build_component_3mf.py", "union_component_layers_parallel.py",
                    "union_component_layers.py", "validate_cli_readback.py", "prepare_exact_union.py"]
    (output / "previous-source").mkdir()
    for name in dependencies:
        shutil.copy2(previous / name, output / "previous-source" / name)
    report = {
        "revision": "935-bare-head-hypothesis-20261105-001",
        "catalogue_source": "catalog/scans/scan-935-xtreme-cylinder-head.json",
        "status": "digitally_checked_hypothesis_reconstruction_and_neutral_contours",
        "original_scan_sha256": "4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486",
        "unit_authority": "Owner instruction: one OBJ unit is one millimetre; not physical metrology",
        "parent_envelope_sha256": fidelity["parent_sha256"],
        "local_source_mesh_sha256": fidelity["candidate_sha256"],
        "local_build_mesh_sha256": geometry["input_sha256"],
        "construction": {key: construction[key] for key in (
            "selected_provisional_protrusions", "retained_parent_triangles_identical", "clipped_skin_triangles",
            "assumed_cap_triangles", "all_unselected_parent_faces_preserved", "coordinate_welding_used")},
        "effective_construction": "Clip the unchanged parent independently by each one plane, select eleven isolated protrusion domains, restore all other parent triangles. The local plan's global-mesh construction sentence belongs to the rejected intermediate assembly.",
        "geometry": geometry,
        "fidelity": fidelity,
        "supports": {key: value for key, value in supports.items() if not isinstance(value, list)},
        "support_assumptions": {key: value for key, value in hypotheses.items() if key not in ("support_columns", "coupon_centre_mm")},
        "head_contours": head_cli,
        "supported_contour_union": union,
        "supported_contours": supported_cli,
        "layer_discretization": read("local-slicing/layer-discretization.json"),
        "kali_independent_check": kali,
        "deliverables": entries,
        "new_geometry_physics_executed": False,
        "machine_job": False,
        "manufacturing_qualified": False,
        "engine_qualified": False,
        "professional_review": False,
        "new_paid_compute_usd": 0,
        "scan_sent_to_external_ai_or_supplier": False,
        "goal_status": "active",
    }
    write(output / "results.json", report)
    write(output / "files.json", {"files": entries, "contours_stay_at_capsule_relative_paths": True})
    (output / "README.md").write_text(
        "# 935 reconstruction under declared hypotheses\n\n"
        "The body 3MF is the preferred millimetre-coordinate surface export. "
        "The supported 3MF is a composite whose intended overlapping resources must be united by the consumer. "
        "Verified neutral 50 micrometre CLI files are indexed in files.json outside this delivery directory to avoid duplicate gigabyte files.\n\n"
        "All mesh checks and every layer readback pass for this revision. Eleven local protrusions were removed under a provisional geometric classification; "
        "all unselected parent triangles, including fins, remain. The parent already contains inferred closures. "
        "This is an editable mesh and reproducible construction recipe, not a complete analytic STEP/FreeCAD master or an identical measured bare head.\n\n"
        "The private capsule retains source provenance, failed candidates, controls, geometry and contour reports, runtime receipts and a SHA-256 manifest. "
        "Source files must be replayed from their original repository paths: relative imports and immutable dependency hashes are intentional. "
        "Use a new output directory; frozen outputs must not be overwritten.\n\n"
        "Material, internal geometry, interfaces, process/exposure, support removal, wall adequacy and thermal/mechanical qualification remain open. "
        "There is no qualified machine job, fabrication approval or engine acceptance. Older simulations do not validate this new geometry.\n"
    )
    print(json.dumps({"delivery_created": True, "files": entries, "machine_job": False}))


if __name__ == "__main__":
    main()
