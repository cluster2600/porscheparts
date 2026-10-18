"""Read-only preparation; this command never compiles or changes a surface."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SOURCE = "work/962-engineering/analysis-envelope-025-003/exact-input.bin"
CANDIDATE = "work/962-engineering/quality-patch-head-001/native/quality-candidate.bin"
READBACK = "work/962-engineering/quality-volume-hxt-sized-readback-001/readback-report.json"
OLD_CONTRACT = "work/962-engineering/quality-patch-head-001/frozen-execution-contract.json"
OLD_EXECUTION = "work/962-engineering/quality-patch-head-001/execution-receipt.json"
IDENTITY = "work/962-engineering/quality-patch-fixtures-001/original-indexed-identity.json"
EXPECTED = {
    SOURCE: "894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95",
    CANDIDATE: "7f0d96988684f7d36dab8f65c5b63b1919c2c2121768cf9caec466867a5c2b43",
    READBACK: "b1658ea3e226e35d70c4cb0131cca8fcf2da786908495d19b231a77d269fd951",
    OLD_CONTRACT: "07c3c8705ea7d5051fdf0317cd0a93ce08a951b347236ae55256360b7115778a",
    IDENTITY: "c0b6744764da5b3a451029ecbb28eb9f58ad600cd2ca42174b280266589a733a",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def boundary_coordinate(tag, recorded, actual):
    if type(tag) is not int or tag <= 0 or len(recorded) != 3 or len(actual) != 3:
        raise ValueError("Exact positive boundary tag and three coordinates required")
    if not all(type(v) in (int, float) and math.isfinite(v) for v in recorded):
        raise ValueError("Finite diagnostic coordinates required")
    if list(recorded) != list(actual):
        raise ValueError("Saved diagnostic does not match the actual candidate boundary point")


def association_kind(candidate, original_at_lineage, exact_original_matches, lineage_verified):
    if list(candidate) == list(original_at_lineage) and len(exact_original_matches) == 1:
        return "unique_exact_original_coordinate_match"
    if not lineage_verified:
        raise ValueError("An index or nearest point alone cannot establish original association")
    return "preserved_helper_vertex_lineage_not_original_coordinate_identity"


def prepare(output):
    if output.exists() or output.is_symlink():
        raise ValueError("Existing preparation preserved")
    # Hash-bind before any array interpretation. All original records stay in place.
    for name, expected in EXPECTED.items():
        if digest(ROOT/name) != expected:
            raise ValueError("Original preparation input changed: "+name)
    old = json.loads((ROOT/OLD_CONTRACT).read_text())
    for name, expected in old["input_hashes"].items():
        if digest(ROOT/name) != expected:
            raise ValueError("Retained original-pass input changed: "+name)
    execution = json.loads((ROOT/OLD_EXECUTION).read_text())
    if execution["contract_sha256"] != EXPECTED[OLD_CONTRACT] or execution["native_returncode"] != 0:
        raise ValueError("Bound completed original pass required for descriptor lineage")
    if execution["deadline_exceeded"] or execution["container_state"]["Running"] or execution["container_state"]["OOMKilled"]:
        raise ValueError("Stopped complete original pass required")
    for name, expected in execution["output_sha256"].items():
        if digest(ROOT/Path(OLD_EXECUTION).parent/name) != expected:
            raise ValueError("Original-pass output changed")
    if old["controls"]["do_split"] or old["controls"]["do_collapse"]:
        raise ValueError("The recorded helper must preserve its vertex descriptors")
    import numpy as np
    from audit_quality_head import canonical_faces, qualities, read
    p, f = read(ROOT/SOURCE); q, g = read(ROOT/CANDIDATE)
    if p.shape != q.shape or f.shape != g.shape:
        raise ValueError("Recorded descriptor-preserving pass counts changed")
    quality = qualities(p, f); seed_faces = quality < 2/29
    seeds = np.unique(f[seed_faces]); patch = np.isin(f, seeds).any(axis=1)
    fixed = np.zeros(len(p), dtype=bool); fixed[np.unique(f[~patch])] = True
    fixed |= (p[:, 0] == -76) | (p[:, 0] == 76)
    counts = dict(source_seed_faces=int(seed_faces.sum()), seed_vertices=len(seeds),
                  patch_faces=int(patch.sum()), patch_vertices=len(np.unique(f[patch])),
                  fixed_vertices=int(fixed.sum()))
    if counts != dict(source_seed_faces=744, seed_vertices=1284, patch_faces=4704,
                      patch_vertices=3858, fixed_vertices=900845):
        raise ValueError("The original exact-incidence patch changed")
    if not np.array_equal(p[fixed], q[fixed]):
        raise ValueError("Original fixed-anchor coordinate identity lost")
    if not np.array_equal(canonical_faces(f[~patch]), canonical_faces(g[~patch])):
        raise ValueError("Original exterior oriented-face identity lost")
    readback = json.loads((ROOT/READBACK).read_text()); cells = []
    for cell in readback["nonpositive_SICN_tetrahedra"]:
        points = []
        for tag, xyz in zip(cell["node_tags"], cell["coordinates_mm"]):
            i = tag-1
            boundary_coordinate(tag, xyz, q[i].tolist())
            exact = np.flatnonzero(np.all(p == q[i], axis=1)).tolist()
            incident = np.flatnonzero(np.any(f == i, axis=1))
            candidate_incident = np.flatnonzero(np.any(g == i, axis=1))
            if not np.any(patch[incident]):
                raise ValueError("Bad-cell source association would require a different patch")
            points.append(dict(boundary_node_tag=tag, candidate_coordinate_mm=q[i].tolist(),
                               actual_candidate_coordinate_verified=True,
                               exact_original_coordinate_matches=exact,
                               association_kind=association_kind(q[i], p[i], exact, True),
                               preserved_original_vertex_descriptor=i,
                               original_lineage_coordinate_mm=p[i].tolist(),
                               vertex_displacement_mm=float(np.linalg.norm(q[i]-p[i])),
                               vertex_displacement_is_continuous_surface_distance=False,
                               original_seed_vertex=bool(np.isin(i, seeds)),
                               original_fixed_vertex=bool(fixed[i]),
                               original_incident_face_ids=incident.tolist(),
                               candidate_incident_face_ids=candidate_incident.tolist(),
                               incident_oriented_connectivity_exact=bool(np.array_equal(
                                   canonical_faces(f[incident]), canonical_faces(g[candidate_incident])))))
        cells.append(dict(tetrahedron_tag=cell["tetrahedron_tag"], points=points))
    if len(cells) != 2 or sum(len(c["points"]) for c in cells) != 8:
        raise ValueError("The two recorded four-node diagnostics are required")
    cpp = "twins/962-cylinder-head-f0/source/analysis-cgal/finest_endpoint.cpp"
    test = "tests/test_962_finest_surface.py"
    pins = dict(EXPECTED)
    for name in [OLD_EXECUTION, cpp, test, str(Path(__file__).resolve().relative_to(ROOT)),
                 "twins/962-cylinder-head-f0/source/analysis-cgal/quality_patch.cpp",
                 "twins/962-cylinder-head-f0/source/audit_quality_head.py",
                 "work/962-engineering/cgal-envelope-runtime-002/runtime.json"]:
        pins[name] = digest(ROOT/name)
    api_files = ["Polyhedral_envelope.h", "Polyhedral_envelope_filter.h", "Bounded_normal_change_filter.h"]
    for name in api_files:
        path = "work/962-engineering/cgal-envelope-runtime-002/package-metadata/"+name
        pins[path] = digest(ROOT/path)
    for name in ["coolant.stl", "dry-passages.stl"]:
        path = "work/962-family/bore-95-run-001/inspected-bound-002/"+name
        pins[path] = old["input_hashes"][path]
    output.mkdir(parents=True)
    association = dict(schema="962-sized-badcell-original-association/v1", cells=cells,
        basis="Actual candidate coordinates, original indexed/STL identity receipt and completed pinned descriptor-preserving helper; index alone is not geometric identity.",
        lineage_limit="The old helper creates vertices only during import, disables splitting/collapse, performs no garbage collection, and writes active descriptors in unchanged order. Source/code/run hashes support procedural lineage; no native per-vertex lineage log was originally emitted.",
        original_patch_unchanged=True, complete_semantic_feature_map=False)
    with (output/"bad-cell-association.json").open("x") as stream:
        json.dump(association, stream, indent=2); stream.write("\n")
    contract = dict(schema="962-finest-endpoint-preparation/v1", status="prepared_source_only_root_review_required",
        input_sha256=pins, association_sha256=digest(output/"bad-cell-association.json"),
        starting_surface=SOURCE, original_patch=counts,
        controls=dict(placement="one existing endpoint only; no new coordinate, fitting, welding, relaxation, projection move or split",
                      selection="Only the unchanged original744-seed exact-incidence region; neither endpoint may be exterior/clip-fixed. No expanded box or diagnostic nearest-vertex mapping.",
                      constraints="Fix every vertex incident to an original exterior face and exact source x=-76/+76mm; reject either-fixed endpoints; preserve exterior oriented faces and fixed coordinates exactly.",
                      envelope="Build once from complete immutable original; test every complete surviving fan triangle, not just vertices.",
                      geometry_budget_mm=0.0625, normal_rule="CGAL5.6 Bounded_normal_change_filter: strictly positive old/new normal dot product",
                      topology_rule="CGAL5.6 SMS link/topological and geometric checks before collapse; no zero-length-edge fast-path allowed",
                      local_quality="Each accepted collapse strictly reduces affected faces below2/29 and cannot reduce their minimum. Disappearing edge faces are included in the before set; unchanged global faces imply full count decreases and full minimum cannot worsen.",
                      priority="Largest local incompatible-face reduction, then largest local minimum, then smallest exact source-coordinate origin ID; no edge-size threshold or face quota.",
                      stop="One queue traversal until no admissible local operation or declared bound; no automatic extra pass or relaxed fallback.",
                      source_vertex_origin_map="Output vertex order maps to the original coordinate ID; not an ancestry map for all removed vertices."),
        proposed_native_bounds_for_review=dict(cpus=2, memory_bytes=4294967296, swap_bytes=0, hard_wall_seconds=300,
                                             soft_stop_seconds=285, network="none", fresh_outputs=True, read_only_input=True),
        mandatory_independent_gates=dict(full_actual_arrays_quality_and_fixed_exterior_audit=True,
            finite_nondegenerate_closed_oriented_edge_and_vertex_manifold=True,
            components=1, euler_characteristic=-208, global_self_intersection_pairs=0,
            whole_surface_bidirectional_continuous_distance_upper_mm=0.0625,
            each_interval_gap_mm=0.0001, recompute_exact_shared_face_partition=True,
            vertex_sampling_sufficient=False, rounded_error_certificate_claimed=False,
            unchanged_fluid_hashes=True, eight_dry_opening_probes=True,
            original_sampled_water_dry_clearance_minimum_mm=4.0,
            independent_feature_channel_BCC_review=True,
            actual_tetrahedron_minimum_SICN=0.1, exact_oriented_volume_boundary=True,
            finite_positive_Jacobians_and_volumes=True, relative_volume_bookkeeping_bound=1e-6),
        limitations=["Complete Porsche interface/semantic constraints remain unknown; this conservative analysis patch is not such a map.",
                     "A candidate can satisfy the face screen and still fail tetrahedron quality or either continuous distance direction.",
                     "The old candidate's directed surface-distance lower0.07185669700547284mm already excludes0.0625mm; moved-vertex displacement is a different quantity.",
                     "Endpoint-only collapses may stagnate. Preserve that failure; any larger method or region needs a distinct reviewed proposal."],
        compile_authorized=False, native_trial_authorized=False, compile_or_native_executed=False,
        candidate_geometry_written=False, solver_admission_established=False,
        head_thermal_strength_LPBF_accepted=False, engineering_accepted=False, manufacturing_authorized=False)
    for name, expected in pins.items():
        if digest(ROOT/name) != expected:
            raise ValueError("An input changed during read-only preparation: "+name)
    with (output/"preflight-contract.json").open("x") as stream:
        json.dump(contract, stream, indent=2); stream.write("\n")
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))
