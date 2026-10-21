"""Independent admission guard for a quality-only proposal, never a head solve."""
import math


def require_quality_objective(before, after):
    """Require strictly fewer bad facets and a non-worsening full-surface minimum."""
    for row in (before, after):
        for key in ("triangles", "below_necessary_bound"):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError("Exact nonnegative quality counts required")
        value = row.get("minimum_triangle_SICN")
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError("Finite positive full-surface triangle SICN required")
        if not row["triangles"] or row["below_necessary_bound"] > row["triangles"]:
            raise ValueError("Complete valid triangle count required")
    if before["triangles"] != after["triangles"]:
        raise ValueError("No split/collapse face-count changes permitted")
    return (after["below_necessary_bound"] < before["below_necessary_bound"]
            and after["minimum_triangle_SICN"] >= before["minimum_triangle_SICN"])


def assess_native_report(report):
    controls = dict(target_edge_length_mm=0, do_split=False, do_collapse=False,
                    do_flip=True, do_project=True, relax_constraints=False,
                    protect_constraints=False, atomic_iterations=1,
                    relaxation_steps=1, projection_reference="immutable_original_surface")
    supplied = report.get("controls")
    if (supplied != controls or any(type(supplied[k]) is not type(value)
                                    for k, value in controls.items())):
        raise ValueError("Predeclared original-source atomic controls changed")
    if not all(report.get(k) is True for k in (
            "fixed_source_vertices_unchanged", "outside_source_faces_unchanged",
            "vertex_and_face_counts_unchanged", "closed_valid_triangle_mesh")):
        raise ValueError("Fixed source or surface invariants changed")
    improves = require_quality_objective(report["full_surface_before"], report["full_surface_after"])
    if report.get("quality_objective_improved") is not improves or report.get("quality_candidate_written") is not improves:
        raise ValueError("Native objective/status disagrees with independent guard")
    return dict(quality_objective_passed=improves, solver_admission_established=False,
                complete_semantic_constraint_map=False, engineering_accepted=False,
                manufacturing_authorized=False)
