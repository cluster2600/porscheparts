"""Independent analytic/native-receipt checks for the impeller iteration."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
FAN=ROOT/'twins/993-engine-cooling-fan-system-f0'
sys.path.insert(0,str(FAN/'source'))
from check_material_process_import import check as check_materials

try:
    import numpy as np
    from prepare_engineering_sensitivities import parse_mesh
    from summarize_engineering_sensitivities import displacement_blocks,stress_blocks
    from localize_mesh_failures import analyze,read_set
    from prepare_hex_mesh_pilot import prepare as prepare_hex
except ImportError:
    np=None

try:
    from audit_hex_surface import extract_rotor
except ImportError:
    extract_rotor=None


class ImpellerEngineeringTests(unittest.TestCase):
    @unittest.skipIf(extract_rotor is None,'Trimesh unavailable')
    def test_native_rotor_extraction_preserves_vertex_ids_and_rejects_invalid_references(self):
        with tempfile.TemporaryDirectory() as temp:
            obj=Path(temp)/'surface.obj'
            text='v 0 0 0\nv .001 0 0\nv 0 .001 0\nv 0 0 .001\nv 2 2 2\ng inlet\nf 1 2 5\ng rotor\nf 1 3 2\nf 1 2 4\nf 2 3 4\nf 3 1 4\n'
            obj.write_text(text);mesh=extract_rotor(obj)
            self.assertEqual(len(mesh.vertices),4);self.assertEqual(len(mesh.faces),4)
            self.assertTrue(mesh.is_watertight);self.assertAlmostEqual(mesh.volume,1e-9/6)
            obj.write_text(text.replace('f 3 1 4','f 3 1 9'))
            with self.assertRaisesRegex(ValueError,'vertex IDs'):extract_rotor(obj)

    @unittest.skipIf(np is None,'NumPy unavailable')
    def test_native_cell_localization_keeps_dimension_specific_physical_tags(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);sets=root/'sets';vtk=root/'vtk';sets.mkdir();vtk.mkdir()
            mesh=root/'mesh.msh';mesh.write_text('$PhysicalNames\n2\n2 1 "rotor"\n3 1 "fluid"\n$EndPhysicalNames\n$Nodes\n4\n1 0 0 0\n2 .001 0 0\n3 0 .001 0\n4 0 0 .001\n$EndNodes\n$Elements\n2\n7 2 2 1 1 1 2 3\n42 4 2 1 1 1 2 3 4\n$EndElements\n')
            for name in ['underdeterminedCells','twoInternalFacesCells','skewFaces','lowWeightFaces','lowVolRatioFaces']:
                (sets/name).write_text('FoamFile {}\n1\n(\n0\n)\n')
            for name in ['skewFaces','lowWeightFaces','lowVolRatioFaces']:
                (vtk/f'{name}.vtk').write_text('# vtk DataFile Version 2.0\nfixture\nASCII\nDATASET POLYDATA\nPOINTS 3 float\n0 0 0 .001 0 0 0 .001 0\nPOLYGONS 1 4\n3 0 1 2\n')
            result=analyze(mesh,sets,vtk,root/'out')
            self.assertEqual(result['patch_contact_histogram']['rotor'],1)
            self.assertEqual(result['underdetermined_cell_bounds_mm'],[[.25,.25,.25]]*2)
            with (root/'out/underdetermined-cell-centres.csv').open() as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(rows[0]['gmsh_element_id'],'42')
            (sets/'underdeterminedCells').write_text('FoamFile {}\n2\n(\n0 0\n)\n')
            with self.assertRaisesRegex(ValueError,'coverage'):read_set(sets/'underdeterminedCells')

    @unittest.skipIf(np is None,'NumPy unavailable')
    def test_hex_preparation_rejects_unverified_source_or_scan_before_creating_case(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);surface=root/'rotor.stl';surface.write_bytes(b'original fixture')
            receipt=root/'receipt.json';native=root/'log.surface';native.write_text('Surface is closed.\nSurface is not self-intersecting\n')
            base={'metres_sha256':hashlib.sha256(surface.read_bytes()).hexdigest(),'private_scan_used':False,'status':'regularized_requires_independent_surface_and_mesh_checks'}
            for invalid in [{**base,'private_scan_used':True},{**base,'status':'rejected'},{**base,'metres_sha256':'invalid'}]:
                receipt.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):prepare_hex(surface,receipt,native,root/'out')
                self.assertFalse((root/'out').exists())
            receipt.write_text(json.dumps(base));native.write_text('Surface is closed.\n')
            with self.assertRaisesRegex(ValueError,'intersection'):prepare_hex(surface,receipt,native,root/'out')

    def test_material_records_keep_alloy_scenario_identity_and_open_gates(self):
        result=check_materials()
        self.assertEqual(result['shared_scenario_names']['EOS_M290_30_AB'],['AlF357','AlSi10Mg'])
        self.assertFalse(result['release_admissible'])

    def test_json_csv_disagreement_is_detected_even_if_transfer_hash_is_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'import';shutil.copytree(FAN/'program/research/materials-20261003',root)
            file=root/'material_evidence.csv'
            file.write_text(file.read_text().replace('M001,AlSi10Mg','M001,AlF357',1))
            path=root/'import-manifest.json';manifest=json.loads(path.read_text());item=next(r for r in manifest['files'] if r['path']==file.name)
            item.update({'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()});path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'CSV/JSON value differs'):check_materials(root)

    @unittest.skipIf(np is None,'NumPy unavailable')
    def test_native_uniform_eigenstrain_release_matches_analytic_displacement_and_zero_stress(self):
        case=FAN/'results/engineering-iteration-20261003/lpbf'
        nodes,_=parse_mesh((case/'unit-eigenstrain.inp').read_text())
        fields=displacement_blocks(case/'unit-eigenstrain.frd')
        tensors=stress_blocks(case/'unit-eigenstrain.dat')
        self.assertEqual(len(fields),2);self.assertEqual(len(tensors),2)
        self.assertEqual(set(fields[-1]),set(nodes))
        self.assertLess(max(np.linalg.norm(fields[-1][i]+.001*x) for i,x in nodes.items()),1e-8)
        self.assertLess(max(abs(t).max() for t in tensors[-1].values()),1e-7)
        self.assertGreater(max(abs(t).max() for t in tensors[0].values()),1.)

    @unittest.skipIf(np is None,'NumPy unavailable')
    def test_reduced_integration_or_incomplete_connectivity_is_not_silently_admitted(self):
        text=(FAN/'results/engineering-iteration-20261003/lpbf/unit-eigenstrain.inp').read_text()
        with self.assertRaisesRegex(ValueError,'full-integration'):parse_mesh(text.replace('TYPE=C3D10','TYPE=C3D10R'))
        with self.assertRaises(ValueError):parse_mesh(text.replace('*NODE','*IGNORED',1))


if __name__=='__main__':unittest.main()
