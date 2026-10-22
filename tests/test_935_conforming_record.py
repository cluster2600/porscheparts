import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ConformingRecordTests(unittest.TestCase):
    def test_runtime_continuation_keeps_witness_and_part_qualification_separate(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/local-runtime-20261022.json').read_text())
        for name,value in record['scope'].items():self.assertIs(value,False,name)
        self.assertFalse(record['quadratic_48GiB_attempt']['accepted'])
        self.assertFalse(record['quadratic_48GiB_attempt']['solver_finished'])
        witness=record['openfoam_witness']
        self.assertEqual(witness['completed_solver_cases'],len(witness['meshes'])*witness['repetitions'])
        self.assertTrue(witness['numerical_reference_criteria_passed']);self.assertTrue(witness['canonical_metrics_identical'])
        self.assertFalse(witness['Porsche_case_executed']);self.assertFalse(witness['exact_original_Docker_confinement_reproduced'])
        for name,expected in witness['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)
        for ci in record['ci']:
            self.assertEqual(ci['headSha'],record['parent_commit']);self.assertEqual(ci['conclusion'],'success')

    def test_source_pins_and_study_boundaries(self):
        record=json.loads((ROOT/'docs/research/935-horizontal-cooling/conforming-rotor-20261022.json').read_text())
        for name,expected in record['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)
        for name,value in record['scope'].items():self.assertIs(value,False,name)
        volume=record['volume']
        self.assertTrue(volume['exact_boundary_coordinate_triangle_bijection'])
        self.assertEqual(volume['tetrahedra'],volume['exact_orientation']['cells'])
        self.assertEqual(volume['exact_orientation']['negative'],0);self.assertEqual(volume['exact_orientation']['zero'],0)
        self.assertFalse(record['quality']['mechanical_mesh_admitted'])
        for result in record['linear_solves'].values():
            self.assertTrue(result['equilibrium_pass'])
            self.assertEqual(result['elements'],volume['tetrahedra'])
            self.assertFalse(result['mesh_convergence_established']);self.assertFalse(result['manufacturing_authorized'])
        self.assertFalse(record['quadratic_32GiB_attempt']['accepted'])
        self.assertTrue(record['quadratic_32GiB_attempt']['stopped_by_physical_footprint'])
        self.assertFalse(record['rejected_iterative_controls']['accepted'])
        self.assertGreater(record['rejected_iterative_controls']['equilibrium_failures'],0)
