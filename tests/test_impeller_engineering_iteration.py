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
except ImportError:
    np=None


class ImpellerEngineeringTests(unittest.TestCase):
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
