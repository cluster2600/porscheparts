"""Prepared, unrun stdlib checks of actual byte extraction functions."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('cap_extract', Path(__file__).with_name('extract.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class CapExtraction(unittest.TestCase):
    def test_exact_subset_reindex_and_identity_map(self):
        # Two disconnected triangles are only a byte-codec fixture, not a cap-domain proof.
        points = [(99., 99., 99.), (0., 0., -0.), (1.0000000000000002, 0., 0.), (0., 1., 0.),
                  (2., 0., 0.), (3., 0., 0.), (2., 1., 0.)]
        rows = [(0, 1, 2), (3, 2, 1), (6, 5, 4)]
        raw = M.MAGIC + struct.pack('<QQ', len(points), len(rows))
        raw += b''.join(struct.pack('<ddd', *v) for v in points)
        raw += b''.join(struct.pack('<QQQ', *v) for v in rows)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.bin'; source.write_bytes(raw)
            data, meta = M.payloads(source, [1, 2], [[1, 2, 3], [4, 5, 6]],
                [{'members': [1], 'selected_keeper': 1}], [2])
            self.assertEqual(data['local-to-global-vertices.u64'], struct.pack('<6Q', 1, 2, 3, 4, 5, 6))
            self.assertEqual(data['local-to-global-faces.u64'], struct.pack('<2Q', 1, 2))
            self.assertEqual(data['old-to-keeper.u64'], struct.pack('<2Q', 0, 0))
            self.assertEqual(data['fixed-face-ids.u64'], struct.pack('<Q', 1))
            self.assertEqual(data['cap.bin'][24:48], struct.pack('<ddd', *points[1]))
            self.assertEqual(data['cap.bin'][24 + 6*24:], struct.pack('<6Q', 2, 1, 0, 5, 4, 3))
            output = Path(folder) / 'out'; output.mkdir()
            for name, bits in data.items(): (output / name).write_bytes(bits)
            self.assertTrue(M.readback(output, source, data, meta))
            damaged = bytearray(data['cap.bin']); damaged[24] ^= 1
            (output / 'cap.bin').write_bytes(damaged)
            with self.assertRaisesRegex(ValueError, 'byte readback'):
                M.readback(output, source, data, meta)
            self.assertEqual(source.read_bytes(), raw)

    def test_fixed_face_map_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.bin'
            points = [(0.,0.,0.), (1.,0.,0.), (0.,1.,0.), (2.,0.,0.), (3.,0.,0.), (2.,1.,0.)]
            source.write_bytes(M.MAGIC + struct.pack('<QQ', 6, 2) +
                b''.join(struct.pack('<ddd', *v) for v in points) + struct.pack('<6Q', 2,1,0,5,4,3))
            with self.assertRaisesRegex(ValueError, 'Fixed cap vertex'):
                M.payloads(source, [0,1], [[0,1,2],[3,4,5]], [{'members':[0,1], 'selected_keeper':0}], [0])


if __name__ == '__main__': unittest.main()
