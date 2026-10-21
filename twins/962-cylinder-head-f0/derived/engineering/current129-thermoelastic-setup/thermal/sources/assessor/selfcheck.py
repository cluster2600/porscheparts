"""UNRUN manufactured stdlib guards; no native/output/scientific import required."""
from pathlib import Path
from itertools import product
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import hashlib
import math
import unittest

SOURCE = Path(__file__).with_name('assess.py')
SOURCE_SHA = '7f2d5fbb873ed82df80d133314edc98cf57aa353057d8b9db08ea92358657af1'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
spec = importlib.util.spec_from_file_location('fixed_coupon_assessor_guard', SOURCE)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)  # Stdlib-only top level. Root alone may run this guard.
POLICY = dict(strain=1e-10, stress_Pa=.1, force_N=1e-7, moment_Nm=1e-7,
              temperature_K=1e-10, displacement_m=1e-12, QP_coordinate_m=2e-13)
POINTS = list(product((0., .125), (0., .25), (0., .25)))


def affine(A, points):
    return [[sum(row[j] * p[j] for j in range(3)) for row in A] for p in points]


def fake_family():
    points = list(product((i / 8 for i in range(17)), (i / 4 for i in range(5)), (i / 4 for i in range(5))))
    geometry = {13 * i + 7: p for i, p in enumerate(points)}
    inverse = {p: tag for tag, p in geometry.items()}
    corners = ((0., 0., 0.), (.125, 0., 0.), (.125, .25, 0.), (0., .25, 0.), (0., 0., .25), (.125, 0., .25), (.125, .25, .25), (0., .25, .25))
    cells = {11 * i + 3: [inverse[(x + dx, y + dy, z + dz)] for dx, dy, dz in corners]
             for i, (x, y, z) in enumerate(product((i / 8 for i in range(16)), (i / 4 for i in range(4)), (i / 4 for i in range(4))))}
    names = (*a.DISP, *a.FORCE, 'temperature', 'born_reference_temperature', 'inactive_placeholder')
    def member(first, last):
        times = [i / 400 for i in range(first, last + 1)]
        return dict(nodes=geometry, cells=cells,
                    blocks={tag: 2 if max(geometry[n][0] for n in conn) <= 1. else 1 if first < 80 else 3 for tag, conn in cells.items()},
                    times=times, node_map=[t + 1 for t in geometry], element_map=[t + 1 for t in cells],
                    fields={name: [[0.] * 425 for _ in times] for name in names}, block_ids=[1, 2] if first < 80 else [2, 3], block_status=[1, 1])
    return geometry, member(0, 79), member(80, 160)


class Guards(unittest.TestCase):
    def test_Q1_affine_all_eight_points_and_rigid_rotation(self):
        A = [[.002, .0003, -.0001], [.0007, -.001, .0002], [.0004, -.0008, .003]]
        u = affine(A, POINTS)
        for _, shape, grad, weight in a.hex_rule(POINTS):
            self.assertAlmostEqual(sum(shape), 1.)
            self.assertEqual(weight, .125 * .25 * .25 / 8)
            e = a.symgrad(u, grad)
            for i, j in a.COMP: self.assertAlmostEqual(e[i][j], (A[i][j] + A[j][i]) / 2, places=15)
        spin = [[0., .003, -.002], [-.003, 0., .004], [.002, -.004, 0.]]
        for _, _, grad, _ in a.hex_rule(POINTS):
            self.assertLess(max(abs(x) for row in a.symgrad(affine(spin, POINTS), grad) for x in row), 1e-16)

    def test_isotropic_three_dimensional_shear_and_thermal_reference(self):
        eps = [[.001, .0002, .0003], [.0002, -.002, .0004], [.0003, .0004, .003]]
        sigma = a.hooke(eps)
        self.assertAlmostEqual(sigma[0][1], 2 * a.MU * .0002)
        self.assertAlmostEqual(sigma[1][1], 2 * a.MU * -.002 + a.LAM * .002)
        delta = 17.
        u = [[a.ALPHA * delta * x for x in p] for p in POINTS]
        state = a.mechanical_state(POINTS, u, [417.] * 8, [[0.] * 3 for _ in POINTS], [400.] * 8)
        self.assertLess(max(abs(x) for row in state for line in row[3]['stress'] for x in line), 1e-7)

    def test_born_nonzero_displacement_and_nonuniform_T_reference(self):
        base = affine([[.004, .002, .001], [.001, -.003, .002], [0., .001, .006]], POINTS)
        reference = [350. + 40. * p[1] + 7. * p[2] for p in POINTS]
        born = a.mechanical_state(POINTS, base, reference, base, reference)
        self.assertEqual([row[3]['stress'] for row in born], [[[0.] * 3 for _ in range(3)]] * 8)
        wrong = a.mechanical_state(POINTS, base, reference, [[0.] * 3 for _ in POINTS], reference)
        self.assertGreater(max(abs(x) for row in wrong for line in row[3]['stress'] for x in line), 1e6)

    def test_consistent_Q1_force_and_moment_constant_symmetric_stress(self):
        sigma = [[12., 3., 4.], [3., 27., 5.], [4., 5., 39.]]
        f = {i: [0.] * 3 for i in range(8)}
        for _, _, g, w in a.hex_rule(POINTS): a.accumulate(f, range(8), g, w, sigma)
        for j in range(3):
            self.assertAlmostEqual(sum(v[j] for v in f.values()), 0., places=13)
            self.assertAlmostEqual(sum(p[(j+1)%3] * f[i][(j+2)%3] - p[(j+2)%3] * f[i][(j+1)%3] for i, p in enumerate(POINTS)), 0., places=13)
        self.assertGreater(max(abs(x) for row in f.values() for x in row), 0.)

    def test_manufactured_free_expansion_full_tensor_and_free_residual(self):
        u = [[a.ALPHA * 20. * x for x in p] for p in POINTS]
        state = a.mechanical_state(POINTS, u, [420.] * 8, [[0.] * 3 for _ in POINTS], [400.] * 8)
        qp = {(3, q): (q, row[3]) for q, row in enumerate(state)}
        nodes = {i: dict(zip((*a.DISP, 'temperature'), (*u[i], 420.))) for i in range(8)}
        forces, energy, _ = a.field_phase(a.Audit(POLICY), dict(enumerate(POINTS)), {3: list(range(8))}, {3}, nodes,
                                         {i: [0.] * 3 for i in range(8)}, {i: 400. for i in range(8)}, qp, set())
        self.assertLess(max(abs(x) for row in forces.values() for x in row), 1e-7)
        self.assertLess(energy, 1e-20)
        qp[(3, 0)][1]['stress'][0][0] += 1.
        with self.assertRaises(ValueError):
            a.field_phase(a.Audit(POLICY), dict(enumerate(POINTS)), {3: list(range(8))}, {3}, nodes,
                          {i: [0.] * 3 for i in range(8)}, {i: 400. for i in range(8)}, qp, set())

    def test_observed_external_IDs_full_mesh_family_and_transition(self):
        geometry, before, after = fake_family()
        transfer = {'node_rows': [dict(source_node_id=t, coordinates_m=list(p)) for t, p in geometry.items()]}
        with TemporaryDirectory() as name:
            directory = Path(name); filenames = ['thermoelastic_out.e', 'thermoelastic_out.e-s002']
            for fn in filenames: (directory / fn).write_bytes(b'CDF\x02')
            with patch.object(a, 'read_exodus', side_effect=[before, after]):
                got = a.geometry_family(directory, filenames, transfer)
                self.assertEqual(len(got[0]), 425); self.assertEqual(len(got[1]), 256); self.assertEqual(len(got[2]), 161)
            bad = dict(before, nodes={t + 1: xyz for t, xyz in geometry.items()})
            with patch.object(a, 'read_exodus', return_value=bad), self.assertRaises(ValueError): a.geometry_family(directory, filenames, transfer)
            with patch.object(a, 'read_exodus', side_effect=[before, dict(after, blocks=before['blocks'])]), self.assertRaises(ValueError): a.geometry_family(directory, filenames, transfer)

    def test_format_missing_node_duplicate_QP_and_nonfinite_refusals(self):
        for value in (True, False, 'nan', 'inf', '-inf'):
            with self.assertRaises(ValueError): a.number(value)
        with self.assertRaises(ValueError): a.integer('.5')
        with TemporaryDirectory() as name:
            p = Path(name) / 'file.e'
            for magic in (b'CDF\x01', b'CDF\x02'):
                p.write_bytes(magic); self.assertEqual(a.cdf_magic(p), magic.hex())
            for magic in (b'\x89HDF', b'CDF\x05', b'CDF'):
                p.write_bytes(magic)
                with self.assertRaises(ValueError): a.cdf_magic(p)
            p = Path(name) / 'nodes.csv'; p.write_text('id,x,y,z,temperature\n0,0,0,0,400\n')
            with self.assertRaises(ValueError): a.node_sample(p, {0: (0., 0., 0.), 8: (.125, 0., 0.)}, {0, 8}, ('temperature',))
            p.write_text('id,x,y,z,temperature\n0,-0,0,0,400\n')
            with self.assertRaises(ValueError): a.node_sample(p, {0: (0., 0., 0.)}, {0}, ('temperature',))
            p = Path(name) / 'fields.csv'
            header = ','.join(('elem_id', 'qp_id', 'x', 'y', 'z', *a.QP_FIELDS))
            samples = [','.join(('3', str(7 - q), *(format(x, '.17g') for x in item[0]), *('0' for _ in a.QP_FIELDS))) for q, item in enumerate(a.hex_rule(POINTS))]
            p.write_text('\n'.join([header, *samples]) + '\n')
            got = a.quadrature_sample(p, dict(enumerate(POINTS)), {3: list(range(8))}, {3}, {}, POLICY['QP_coordinate_m'])
            self.assertEqual(got[(3, 7)][0], 0)
            p.write_text('\n'.join([header, *samples, samples[0]]) + '\n')
            with self.assertRaises(ValueError): a.quadrature_sample(p, dict(enumerate(POINTS)), {3: list(range(8))}, {3}, {}, POLICY['QP_coordinate_m'])
        for width in (.13, .25):
            with self.assertRaises(ValueError): a.hex_rule(list(product((0., width), (0., .25), (0., .25))))
        canonical = [POINTS[i] for i in (0, 4, 6, 2, 1, 5, 7, 3)]
        a.ordered_hex(canonical)
        canonical[2], canonical[3] = canonical[3], canonical[2]
        with self.assertRaises(ValueError): a.ordered_hex(canonical)


if __name__ == '__main__': unittest.main()
