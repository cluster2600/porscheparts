"""Reject topology defects independently of a zero-intersection result."""
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "twins/962-cylinder-head-f0/source"
sys.path.insert(0, str(SOURCE))
SPEC = importlib.util.spec_from_file_location("quality_topology_guard", SOURCE / "audit_quality_topology.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TopologyGuard(unittest.TestCase):
    def test_closed_oriented_connected_original_topology_and_positive_volume_required(self):
        good = dict(boundary_edges=0, nonmanifold_edges=0, orientation_imbalanced_edges=0,
                    euler_characteristic=-208, signed_volume_mm3=1.)
        MODULE.require_topology(good, 1)
        for patch, count in [(dict(boundary_edges=1), 1), (dict(nonmanifold_edges=1), 1),
                (dict(orientation_imbalanced_edges=1), 1), (dict(euler_characteristic=-206), 1),
                (dict(signed_volume_mm3=0), 1), (dict(signed_volume_mm3=-1), 1),
                (dict(signed_volume_mm3=float("nan")), 1),
                (dict(signed_volume_mm3=float("inf")), 1),
                (dict(boundary_edges=False), 1), (dict(signed_volume_mm3=True), 1),
                ({}, 2), ({}, True)]:
            with self.subTest(patch=patch, count=count), self.assertRaises(ValueError):
                MODULE.require_topology(dict(good, **patch), count)


if __name__ == "__main__":
    unittest.main()
