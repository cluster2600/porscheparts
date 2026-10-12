import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/935-horizontal-cooling-system-f0/source'
sys.path.insert(0, str(SOURCE))
from assess_candidate_cfd import assess, sha256


class CandidateCFDAssessmentTests(unittest.TestCase):
    def prepare(self, root, pressure=None, outflow=.6):
        for name in ('system/controlDict', 'system/fvSolution', 'system/fvSchemes', 'constant/MRFProperties',
                     'constant/triSurface/rotor.stl', '0/U', '0/p', '0/k', '0/omega', '0/nut'):
            target=root/name;target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('endTime 200;\n' if name.endswith('controlDict') else 'fixture\n')
        metadata={'classification':'conditional_square_duct_not_935_installation', 'rotor_sha256':'a'*64,
                  'rotor_rpm':6000, 'density_kg_m3':1.15, 'specified_volume_flow_m3_s':.6,
                  'prepared_input_sha256':{str(p.relative_to(root)):sha256(p) for p in root.rglob('*') if p.is_file()}}
        (root/'case-metadata.json').write_text(json.dumps(metadata))
        (root/'simpleFoam.log').write_text('End\n');(root/'solver.exit').write_text('0\n')
        (root/'checkMesh.log').write_text('Mesh OK.\n')
        for name in ('inletFlow','outletFlow','inletPressure','outletPressure','forces'):
            target=root/'postProcessing'/name/'0'/('moment.dat' if name=='forces' else 'surfaceFieldValue.dat')
            target.parent.mkdir(parents=True)
            rows=[]
            for time in range(10,201,10):
                values={'inletFlow':[-.6], 'outletFlow':[outflow],
                        'inletPressure':[-100 if pressure is None else pressure(time),10],
                        'outletPressure':[0,100], 'forces':[0,0,-2,0,0,-2,0,0,0]}[name]
                rows.append(' '.join(map(str,[time,*values])))
            target.write_text('# fixture\n'+'\n'.join(rows)+'\n')

    def test_known_pressure_units_signs_and_steady_histories(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.prepare(root);report=assess(root)
            self.assertAlmostEqual(report['metrics']['total_pressure_rise_Pa']['final_window_mean'],166.75)
            self.assertEqual(report['metrics']['resisting_torque_z_Nm']['final_window_mean'],2)
            self.assertTrue(report['single_mesh_pilot_pass'])
            self.assertFalse(report['accepted_for_935_fan_curve'])
            self.assertFalse(report['manufacturing_authorized'])

    def test_oscillation_drift_and_mass_leak_prevent_acceptance(self):
        for pressure,outflow in ((lambda t:-100+10*(-1)**(t//10),.6),
                                 (lambda t:-100 if t<=100 else -110,.6), (None,.59)):
            with self.subTest(outflow=outflow), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);self.prepare(root,pressure,outflow)
                self.assertFalse(assess(root)['single_mesh_pilot_pass'])

    def test_changed_inputs_and_incomplete_or_nonfinite_histories_rejected(self):
        for mutation in ('input','missing_sample','short','nan','solver'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);self.prepare(root)
                target=root/'postProcessing/outletFlow/0/surfaceFieldValue.dat'
                if mutation=='input':(root/'0/U').write_text('changed')
                elif mutation=='solver':(root/'simpleFoam.log').write_text('interrupted')
                elif mutation=='nan':target.write_text(target.read_text().replace('200 0.6','200 nan'))
                else:
                    lines=target.read_text().splitlines()
                    target.write_text('\n'.join(lines[:-1] if mutation=='short' else lines[:3]+lines[4:])+'\n')
                with self.assertRaises(ValueError):assess(root)

    def test_input_symlink_cannot_escape_case_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'case';root.mkdir();self.prepare(root)
            outside=Path(folder)/'outside';outside.write_bytes((root/'0/U').read_bytes())
            (root/'0/U').unlink();(root/'0/U').symlink_to(outside)
            with self.assertRaisesRegex(ValueError,'inputs changed'):assess(root)


if __name__=='__main__':
    unittest.main()
