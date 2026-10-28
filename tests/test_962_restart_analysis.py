import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/962-cylinder-head-f0/source/coolant_flow'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('restart_analysis', SOURCE / 'analyze_restart.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class RestartAnalysisTests(unittest.TestCase):
    def test_first_pressure_solve_cannot_be_replaced_by_small_corrector_residual(self):
        body = '\nTime = 901s\n'
        for field, residual in [('Ux', '1e-6'), ('Uy', '1e-6'), ('Uz', '1e-6'),
                                ('p', '.01'), ('p', '1e-8'), ('omega', '1e-6'), ('k', '1e-6')]:
            body += f'Solving for {field}, Initial residual = {residual}, Final residual = 1e-9, No Iterations 3\n'
        body += 'ExecutionTime = 1 s\nTime = 902s\nSolving for p, Initial residual = 1e-9'
        records = module.iterations(body)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['initial_residuals']['p'], .01)

    def test_incomplete_completed_block_and_duplicate_history_fail(self):
        with self.assertRaises(ValueError): module.iterations('\nTime = 901s\nExecutionTime = 1 s')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root / 'postProcessing/inletFlux/900'; folder.mkdir(parents=True)
            (folder / 'surfaceFieldValue.dat').write_text('# Time flux\n901 -.001\n901 -.001\n')
            with self.assertRaises(ValueError): module.history(root, 'inletFlux')

    def test_complete_audit_converts_kinematic_pressure_and_rejects_false_convergence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); case = root / 'case'; case.mkdir()
            fields = case / '1000'; fields.mkdir()
            poly = case / 'constant/polyMesh'; poly.mkdir(parents=True)
            (poly / 'boundary').write_text('inlet { nFaces 1; } outlet { nFaces 1; }')
            for name, dims, value in (('p', '0 2 -2 0 0 0 0', 10),
                    ('k', '0 2 -2 0 0 0 0', 1), ('omega', '0 0 -1 0 0 0 0', 1),
                    ('nut', '0 2 -1 0 0 0 0', 0)):
                (fields / name).write_text(f'dimensions [{dims}]; internalField nonuniform List<scalar> 1 ({value});')
            (fields / 'U').write_text('dimensions [0 1 -1 0 0 0 0]; internalField nonuniform List<vector> 1 ((2 0 0));')
            (fields / 'phi').write_text('dimensions [0 3 -1 0 0 0 0]; boundaryField { inlet { value uniform -.001; } outlet { value uniform .001; } }')
            for name, value in [('inletFlux', -.001), ('outletFlux', .001), ('inletPressure', 10), ('outletPressure', 0)]:
                folder = case / 'postProcessing' / name / '900'; folder.mkdir(parents=True)
                (folder / 'surfaceFieldValue.dat').write_text(''.join(f'{t} {value}\n' for t in range(901, 1001)))
            (case / 'case-report.json').write_text(json.dumps(dict(case_hashes={}, cells=1,
                flow_m3_s=.001, water_density_kg_m3=1000, residual_target=1e-5)))
            (case / 'mesh-report.json').write_text(json.dumps(dict(source_hashes={}, cells=1,
                status='mesh_numerical_gate_passed_not_physical_validation')))
            (case / 'solver-exit-code.txt').write_text('0\n')
            text = '\nTime = 1000s\n' + ''.join(
                f'Solving for {field}, Initial residual = 1e-6, Final residual = 1e-9, No Iterations 3\n'
                for field in ('Ux', 'Uy', 'Uz', 'p', 'omega', 'k'))
            text += 'ExecutionTime = 1 s\nSIMPLE solution converged in 1000 iterations\nEnd\n'
            (case / 'log.parallelFoam').write_text(text)
            report = module.analyze(case, root / 'audit')
            self.assertTrue(report['numerical_flow_screen_passed'])
            self.assertEqual(report['provisional_pressure_drop_pa'], 10000)
            self.assertEqual(report['provisional_hydraulic_power_w'], 10)
            (case / 'log.parallelFoam').write_text(text.replace('for p, Initial residual = 1e-6', 'for p, Initial residual = .01'))
            rejected = module.analyze(case, root / 'rejected')
            self.assertFalse(rejected['numerical_flow_screen_passed'])


if __name__ == '__main__': unittest.main()
