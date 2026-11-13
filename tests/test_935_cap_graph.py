"""Literal controls for the read-only bounded cap-diagonal diagnostic."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT/relative)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class CapGraphControls(unittest.TestCase):
    def test_exact_graph_controls(self):
        graph = load('docs/research/935-cap-graph-admission-20261107/source/audit_bounded_cap.py')
        exact = load('docs/research/935-condition-directed-20261105/source/verify_surface_peels.py')
        quality = load('docs/research/935-residual-surface-audit-20261107/source/audit_residual_surface.py')
        self.assertTrue(all(graph.controls(exact, quality).values()))

    def test_constrained_lawson_controls(self):
        cap = load('docs/research/935-cap-graph-admission-20261107/source/retessellate_cap.py')
        self.assertTrue(all(cap.controls().values()))

    def test_independent_determinant_controls(self):
        certificate = load('docs/research/935-cap-graph-admission-20261107/source/certify_cap_fixed_point.py')
        self.assertTrue(all(certificate.controls().values()))

    def test_native_oriented_join_controls(self):
        native = load('docs/research/935-cap-graph-admission-20261107/source/check_cap_msh.py')
        self.assertTrue(all(native.controls().values()))


if __name__ == '__main__':
    unittest.main()
