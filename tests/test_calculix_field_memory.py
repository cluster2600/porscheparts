"""Memory-backed current fields must preserve values and reject foreign geometry."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


MEMORY = module('field_memory', 'calculix_field_memory.py')
READER = module('strict_fields', 'calculix_c3d4_field_reader.py')


class FieldMemoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.text = (
            'displacements (vx,vy,vz)\n1 1e-3 2e-3 -3e-3\n2 4e-3 -5e-3 6e-3\n'
            'forces (fx,fy,fz)\n1 10 20 -30\n'
            'stresses (sxx,syy,szz,sxy,sxz,syz)\n1 1 11 12 13 14 15 16\n'
            'internal energy density (value)\n1 1 1.25\n')

    def read(self, text, name, memory):
        destination = self.root / name
        destination.mkdir()
        dat = destination / 'input.dat'
        dat.write_text(text)
        fields = MEMORY.Fields(destination)
        if memory:
            with patch.object(np.lib.format, 'open_memmap', fields.create):
                return READER.parse_dat(dat, destination, 2, 1, np.array([0]))
        return READER.parse_dat(dat, destination, 2, 1, np.array([0]))

    def test_all_four_complete_fields_match_disk_bits(self):
        disk, counts = self.read(self.text, 'disk', False)
        memory, other_counts = self.read(self.text, 'memory', True)
        self.assertEqual(counts, other_counts)
        self.assertEqual(counts, {'u': 2, 'rf': 1, 's': 1, 'ener': 1})
        for name in disk:
            np.testing.assert_array_equal(disk[name].view(np.uint64),
                                          memory[name].view(np.uint64))
            self.assertFalse((self.root / 'memory' / (name + '.npy')).exists())

    def test_storage_backend_does_not_hide_corrupt_fields(self):
        damaged = [self.text.replace('2 4e-3', '1 4e-3'),
                   self.text.replace('1 1 11 12 13 14 15 16\n', ''),
                   self.text.replace('1 1 11 12', '1 2 11 12'),
                   self.text.replace('1.25', 'nan'),
                   self.text + 'internal energy density (value)\n1 1 1.25\n']
        for i, text in enumerate(damaged):
            for memory in (False, True):
                with self.subTest(i=i, memory=memory):
                    with self.assertRaises((AssertionError, ValueError)):
                        self.read(text, f'bad-{i}-{memory}', memory)

    def test_allocation_limit_and_foreign_destination_refused(self):
        fields = MEMORY.Fields(self.root, limit=8)
        with self.assertRaises(AssertionError):
            fields.create(self.root / 'u.npy', dtype='<f8', shape=(2, 3))
        with self.assertRaises(AssertionError):
            fields.create(self.root / 'other' / 'u.npy', dtype='<f8', shape=(1,))
        self.assertEqual(fields.allocated, 0)

    def test_cached_geometry_requires_mesh_and_all_array_bytes(self):
        source = self.root / 'source'
        source.mkdir()
        vertices = np.array([[0., 0., 0.], [1., 1., 1.]], dtype='<f8')
        cells = np.array([[0, 1, 0, 1]], dtype='<i8')
        np.save(source / 'vertices.npy', vertices)
        np.save(source / 'cells.npy', cells)
        (source / 'decoding.json').write_text('{}')
        mesh = self.root / 'mesh.inp'
        mesh.write_bytes(b'input identity fixture')
        digest = lambda data: hashlib.sha256(data).hexdigest()
        contract = dict(vertex_count=2, element_count=1,
                        serialized_vertex_bytes_sha256=digest(vertices.tobytes()),
                        connectivity_i8_bytes_sha256=digest(cells.tobytes()))
        deck = dict(mesh_sha256=digest(mesh.read_bytes()))
        actual, connectivity = MEMORY.reuse_decode(
            mesh, self.root / 'valid', contract, deck, source)
        np.testing.assert_array_equal(actual.view(np.uint64), vertices.view(np.uint64))
        np.testing.assert_array_equal(connectivity, cells)
        for key in ('serialized_vertex_bytes_sha256', 'connectivity_i8_bytes_sha256'):
            bad = dict(contract, **{key: '0' * 64})
            with self.assertRaises(AssertionError):
                MEMORY.reuse_decode(mesh, self.root / key, bad, deck, source)
            self.assertFalse((self.root / key).exists())
        with self.assertRaises(AssertionError):
            MEMORY.reuse_decode(mesh, self.root / 'wrong-mesh', contract,
                                dict(mesh_sha256='0' * 64), source)


if __name__ == '__main__':
    unittest.main()
