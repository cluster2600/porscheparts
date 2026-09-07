"""Pure witnesses for signed volume and native ported-head mesh connectivity."""
import copy
import importlib.util
import math
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "twins/m64-cylinder-head/source/mesh_native_ported_head.py"
SPEC = importlib.util.spec_from_file_location("m64_native_ported_mesh", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativePortedMeshTests(unittest.TestCase):
    def setUp(self):
        self.points = {
            11: (0., 0., 0.),
            23: (1., 0., 0.),
            47: (0., 1., 0.),
            89: (0., 0., 1.),
        }
        self.tetrahedra = [(11, 23, 47, 89)]
        self.triangles = [
            (47, 23, 11), (11, 23, 89), (89, 47, 11), (23, 47, 89),
        ]

    def test_quality_count_and_volume_fractions_are_distinct(self):
        report = MODULE.quality_distribution([.01, .5], [6., 54.])
        self.assertEqual(report['bad_tetrahedron_count_fraction'], .5)
        self.assertEqual(report['bad_tetrahedron_absolute_volume_fraction'], .1)
        self.assertEqual(report['minSICN_below_0p1'], 1)
        self.assertEqual(report['nonpositive_Jacobians'], 0)
        for quality, determinants in (([], []), ([.5], []), ([float('nan')], [1.])):
            with self.assertRaises(ValueError):
                MODULE.quality_distribution(quality, determinants)

    def test_positive_tetra_with_noncontiguous_tags_and_complete_boundary(self):
        volume = MODULE.signed_tetra_volume(*(self.points[tag] for tag in self.tetrahedra[0]))
        self.assertAlmostEqual(volume, 1 / 6)
        report = MODULE.connectivity_metrics(self.points, self.tetrahedra, self.triangles)
        self.assertAlmostEqual(report["signed_volume_sum"], 1 / 6)
        self.assertAlmostEqual(report["absolute_volume_sum"], 1 / 6)
        for key in ("count_negative", "count_zero", "repeated_node_tetrahedra",
                    "boundary_missing_triangles", "stored_triangles_not_on_boundary",
                    "duplicate_stored_triangles", "nonmanifold_faces"):
            with self.subTest(metric=key):
                self.assertEqual(report[key], 0)
        self.assertEqual(report["tetra_connected_components"], 1)
        self.assertTrue(report["boundary_matches"])

    def test_inversion_and_missing_boundary_triangle_are_both_reported(self):
        report = MODULE.connectivity_metrics(
            self.points, [(11, 47, 23, 89)], self.triangles[:-1])
        self.assertAlmostEqual(report["signed_volume_sum"], -1 / 6)
        self.assertAlmostEqual(report["absolute_volume_sum"], 1 / 6)
        self.assertEqual(report["count_negative"], 1)
        self.assertEqual(report["count_zero"], 0)
        self.assertEqual(report["boundary_missing_triangles"], 1)
        self.assertEqual(report["stored_triangles_not_on_boundary"], 0)
        self.assertEqual(report["nonmanifold_faces"], 0)
        self.assertFalse(report["boundary_matches"])

    def test_two_separate_tetrahedra_have_two_components(self):
        points = dict(self.points)
        points.update({
            101: (3., 0., 0.), 205: (4., 0., 0.),
            307: (3., 1., 0.), 401: (3., 0., 1.),
        })
        triangles = self.triangles + [
            (101, 205, 307), (101, 205, 401),
            (101, 307, 401), (205, 307, 401),
        ]
        report = MODULE.connectivity_metrics(
            points, self.tetrahedra + [(101, 205, 307, 401)], triangles)
        self.assertEqual(report["tetra_connected_components"], 2)
        self.assertAlmostEqual(report["signed_volume_sum"], 1 / 3)
        self.assertEqual(report["count_negative"], 0)
        self.assertEqual(report["boundary_missing_triangles"], 0)
        self.assertEqual(report["nonmanifold_faces"], 0)
        self.assertTrue(report["boundary_matches"])

    def test_three_tetrahedra_sharing_one_face_are_nonmanifold(self):
        points = dict(self.points)
        points.update({107: (0., 0., -1.), 223: (0., 0., 2.)})
        tetrahedra = [(11, 23, 47, 89), (11, 47, 23, 107), (11, 23, 47, 223)]
        # All nine singly incident faces are present; the shared face has
        # three incident tetrahedra and must independently reject the boundary.
        triangles = [
            (11, 23, 89), (11, 47, 89), (23, 47, 89),
            (11, 23, 107), (11, 47, 107), (23, 47, 107),
            (11, 23, 223), (11, 47, 223), (23, 47, 223),
        ]
        report = MODULE.connectivity_metrics(points, tetrahedra, triangles)
        self.assertEqual(report["nonmanifold_faces"], 1)
        self.assertEqual(report["boundary_missing_triangles"], 0)
        self.assertEqual(report["stored_triangles_not_on_boundary"], 0)
        self.assertEqual(report["count_negative"], 0)
        self.assertFalse(report["boundary_matches"])


class RereadQualityGateTests(unittest.TestCase):
    def test_reread_quality_passes_at_fixed_threshold_with_matching_count(self):
        report = MODULE.reread_quality_gate([1., .1], [6., 12.], 2)
        for key in ("tetrahedron_count_matches", "positive_jacobians",
                    "minSICN_project_limit", "passed"):
            with self.subTest(gate=key):
                self.assertTrue(report[key])
        self.assertEqual(report["quality_distribution"]["tetrahedra"], 2)
        self.assertEqual(report["quality_distribution"]["minimum_minSICN"], .1)

    def test_reread_quality_rejects_low_minsicn_despite_positive_jacobian(self):
        report = MODULE.reread_quality_gate([.099], [6.], 1)
        self.assertTrue(report["tetrahedron_count_matches"])
        self.assertTrue(report["positive_jacobians"])
        self.assertFalse(report["minSICN_project_limit"])
        self.assertFalse(report["passed"])

    def test_reread_quality_rejects_zero_or_negative_jacobian_independently(self):
        for determinant in (0., -6.):
            with self.subTest(determinant=determinant):
                report = MODULE.reread_quality_gate([1.], [determinant], 1)
                self.assertTrue(report["tetrahedron_count_matches"])
                self.assertTrue(report["minSICN_project_limit"])
                self.assertFalse(report["positive_jacobians"])
                self.assertFalse(report["passed"])

    def test_subtolerance_coordinate_motion_can_invert_a_tiny_tetrahedron(self):
        size = 1e-12
        a, b = (0., 0., 0.), (size, 0., 0.)
        c = (size / 2, math.sqrt(3) * size / 2, 0.)
        d = (size / 2, math.sqrt(3) * size / 6, math.sqrt(2 / 3) * size)
        reflected = (d[0], d[1], -d[2])
        self.assertLess(math.dist(d, reflected), 1e-10)
        original_determinant = 6 * MODULE.signed_tetra_volume(a, b, c, d)
        reread_determinant = 6 * MODULE.signed_tetra_volume(a, b, c, reflected)
        self.assertGreater(original_determinant, 0.)
        self.assertLess(reread_determinant, 0.)
        self.assertTrue(MODULE.reread_quality_gate([1.], [original_determinant], 1)["passed"])
        # Holding the synthetic quality input constant isolates the Jacobian
        # gate: the coordinate roundtrip bound alone cannot certify orientation.
        reread = MODULE.reread_quality_gate([1.], [reread_determinant], 1)
        self.assertTrue(reread["minSICN_project_limit"])
        self.assertFalse(reread["positive_jacobians"])
        self.assertFalse(reread["passed"])

    def test_reread_quality_rejects_element_count_mismatch(self):
        report = MODULE.reread_quality_gate([1., .5], [6., 12.], 3)
        self.assertTrue(report["positive_jacobians"])
        self.assertTrue(report["minSICN_project_limit"])
        self.assertFalse(report["tetrahedron_count_matches"])
        self.assertFalse(report["passed"])

    def test_reread_quality_rejects_invalid_or_nonfinite_arrays(self):
        cases = (([], []), ([1.], []), ([float("nan")], [6.]),
                 ([1.], [float("inf")]), ([1.], [float("nan")]))
        for qualities, determinants in cases:
            with self.subTest(qualities=qualities, determinants=determinants):
                with self.assertRaises(ValueError):
                    MODULE.reread_quality_gate(qualities, determinants, 1)


class PreservedSkinMeshAdaptTests(unittest.TestCase):
    def setUp(self):
        self.native_sha = "3e3cc1631612fb9b7c36a34ceb157888ce66fdf3efb95f3ddad8578f74950ec5"
        self.evidence = {
            "post_cut_native_BRep_sha256": self.native_sha,
            "status": "completed",
            "geometry_modified": False,
            "native_tolerances_modified": False,
            "pre_cut_source_unchanged": True,
            "post_cut_source_unchanged": True,
            "face_results": [
                {"post_cut_face_index": tag,
                 "two_way_surface_area_equivalence_verified": True,
                 "outside_both_gas_negatives_by_prior_bound_common": True}
                for tag in (2193, 2194, 2263)
            ],
        }
        # Face tags are neither source indices nor ordered like the evidence.
        self.binding = {
            "descriptor_bijection_verified": True,
            "matches_private": [
                {"source_face_index": 2194, "gmsh_face_tag": 9002},
                {"source_face_index": 50, "gmsh_face_tag": 9010},
                {"source_face_index": 2263, "gmsh_face_tag": 9003},
                {"source_face_index": 2193, "gmsh_face_tag": 9001},
            ],
        }

    def test_meshadapt_targets_only_proven_faces_through_nonidentity_remap(self):
        assignments = MODULE.preserved_skin_meshadapt_assignments(
            self.native_sha, self.evidence, self.binding)
        self.assertCountEqual(assignments, [
            {"source_face_index": 2193, "gmsh_face_tag": 9001, "algorithm": 1},
            {"source_face_index": 2194, "gmsh_face_tag": 9002, "algorithm": 1},
            {"source_face_index": 2263, "gmsh_face_tag": 9003, "algorithm": 1},
        ])

    def test_meshadapt_rejects_another_brep_even_if_evidence_hash_matches_it(self):
        other_sha = "0" * 64
        for native_sha, evidence_sha in ((other_sha, self.native_sha),
                                         (self.native_sha, other_sha),
                                         (other_sha, other_sha)):
            with self.subTest(native_sha=native_sha, evidence_sha=evidence_sha):
                evidence = copy.deepcopy(self.evidence)
                evidence["post_cut_native_BRep_sha256"] = evidence_sha
                with self.assertRaises(ValueError):
                    MODULE.preserved_skin_meshadapt_assignments(native_sha, evidence, self.binding)

    def test_meshadapt_rejects_incomplete_or_modified_source_evidence(self):
        invalid_values = {
            "status": "incomplete",
            "geometry_modified": True,
            "native_tolerances_modified": True,
            "pre_cut_source_unchanged": False,
            "post_cut_source_unchanged": False,
        }
        for key, value in invalid_values.items():
            for missing in (False, True):
                with self.subTest(field=key, missing=missing):
                    evidence = copy.deepcopy(self.evidence)
                    if missing:
                        del evidence[key]
                    else:
                        evidence[key] = value
                    with self.assertRaises(ValueError):
                        MODULE.preserved_skin_meshadapt_assignments(self.native_sha, evidence, self.binding)

    def test_meshadapt_requires_both_geometric_proofs_for_every_face(self):
        for face_index in range(3):
            for key in ("two_way_surface_area_equivalence_verified",
                        "outside_both_gas_negatives_by_prior_bound_common"):
                with self.subTest(face_index=face_index, proof=key):
                    evidence = copy.deepcopy(self.evidence)
                    evidence["face_results"][face_index][key] = False
                    with self.assertRaises(ValueError):
                        MODULE.preserved_skin_meshadapt_assignments(self.native_sha, evidence, self.binding)

    def test_meshadapt_requires_exactly_three_distinct_proven_source_faces(self):
        for case in ("missing", "duplicate", "extra", "different_face"):
            with self.subTest(case=case):
                evidence = copy.deepcopy(self.evidence)
                faces = evidence["face_results"]
                if case == "missing":
                    faces.pop()
                elif case == "duplicate":
                    faces.append(copy.deepcopy(faces[0]))
                elif case == "extra":
                    extra = copy.deepcopy(faces[0]); extra["post_cut_face_index"] = 9999
                    faces.append(extra)
                else:
                    faces[-1]["post_cut_face_index"] = 2193
                with self.assertRaises(ValueError):
                    MODULE.preserved_skin_meshadapt_assignments(self.native_sha, evidence, self.binding)

    def test_meshadapt_rejects_unverified_missing_or_ambiguous_face_binding(self):
        for case in ("unverified", "missing", "ambiguous", "duplicate", "same_gmsh_tag"):
            with self.subTest(case=case):
                binding = copy.deepcopy(self.binding)
                matches = binding["matches_private"]
                if case == "unverified":
                    binding["descriptor_bijection_verified"] = False
                elif case == "missing":
                    matches.pop()
                elif case == "ambiguous":
                    matches.append({"source_face_index": 2193, "gmsh_face_tag": 9020})
                elif case == "duplicate":
                    matches.append(copy.deepcopy(matches[-1]))
                else:
                    matches[0]["gmsh_face_tag"] = 9001
                with self.assertRaises(ValueError):
                    MODULE.preserved_skin_meshadapt_assignments(self.native_sha, self.evidence, binding)


if __name__ == "__main__":
    unittest.main()
