import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1]/'twins/reference-917-engine/source/additive_energy_diagnostic_f58.py'
spec = importlib.util.spec_from_file_location('f58', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EnergyDiagnosticTests(unittest.TestCase):
    def log(self, folder, rows):
        path = Path(folder)/'energy-run.log'
        path.write_text('\n'.join('F58_BALANCE '+' '.join(map(str, row)) for row in rows))
        return path

    def test_energy_storage_and_latent_are_both_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = [(i*1e-7, 1e-7, 1000, 60, 30, -10, 100, 0, 0, 0) for i in range(1, 1201)]
            result = module.evaluate(self.log(folder, rows), 1e-7)
            self.assertTrue(result['time_series_complete'])
            self.assertIsNone(result['solver_exit_code'])
            self.assertFalse(result['solver_exit_status_verified'])
            self.assertAlmostEqual(result['integrated_terms']['latent_storage_j'], .0036)
            self.assertAlmostEqual(result['integrated_terms']['laser_in_j'], .012)
            self.assertFalse(result['manufacturing_authorized'])
            self.assertEqual(result['relative_absolute_energy_residual'], 0)

    def test_missing_or_nonfinite_samples_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for values in ([], [(1e-7,1e-7,float('nan'),1,1,1,1,1,1,1)],
                           [(2e-7,1e-7,300,0,0,0,0,0,0,0)]):
                with self.assertRaises(ValueError):
                    module.evaluate(self.log(folder, values), 1e-7)

    def test_capped_result_is_never_manufacturing_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            result = module.evaluate(self.log(folder, [(1e-7,1e-7,3300,1,2,-1,5,0,1,0)]), 1e-7)
            self.assertTrue(result['temperature_cap_hit'])
            self.assertFalse(result['time_series_complete'])
            self.assertFalse(result['manufacturing_authorized'])

    def test_absolute_residual_does_not_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = [(1e-7,1e-7,300,12,0,0,10,0,0,2),
                    (2e-7,1e-7,300,8,0,0,10,0,0,-2)]
            result = module.evaluate(self.log(folder, rows), 1e-7)
            self.assertAlmostEqual(result['integrated_terms']['equation_residual_j'], 0)
            self.assertAlmostEqual(result['relative_absolute_energy_residual'], .2)

    def test_inconsistent_reported_residual_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            row = (1e-7,1e-7,300,60,30,-10,100,0,0,1e-6)
            with self.assertRaisesRegex(ValueError, 'inconsistent with component'):
                module.evaluate(self.log(folder, [row]), 1e-7)

    def test_rounding_tolerance_does_not_feed_reported_residual_into_integral(self):
        with tempfile.TemporaryDirectory() as folder:
            row = (1e-7,1e-7,300,60,30,-10,100,0,0,5e-13)
            result = module.evaluate(self.log(folder, [row]), 1e-7)
            self.assertEqual(result['integrated_terms']['equation_residual_j'], 0)
            self.assertEqual(result['absolute_residual_energy_j'], 0)
            self.assertEqual(result['residual_verification']['max_logged_recomputed_difference_w'], 5e-13)

    def test_fixed_dt_contract_and_exact_instrumentation(self):
        self.assertIn('fvc::laplacian(kappa, T)', module.BEFORE)
        self.assertIn('sources.qDot()', module.BEFORE)
        self.assertIn('alpha1.primitiveField()-f58Abefore', module.AFTER)
        self.assertIn('rDeltaT*A*(T-Tmax)', module.LIMITER)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                module.evaluate(self.log(folder, [(1e-7,1e-7,300,0,0,0,0,0,0,0)]), 5e-8)

    def test_pair_preserves_every_physical_file_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, solver, output = root/'case', root/'solver', root/'out'
            files = {
                'system/fvSolution': 'explicitSolve true; nOuterCorrectors 0; Tmax 3300.0;',
                'system/controlDict': 'deltaT 1e-7;\nadjustTimeStep yes;\nendTime 0.00012;\nrunTimeModifiable yes;\n',
                'constant/heatSourceDict': 'absorption { model Kelly; eta0 0.28; etaMin 0.35; }',
                'constant/transportProperties': '#include "AlSi10Mg.cfg"',
                'constant/polyMesh/points': 'mesh fixture', '0/T': '293.15',
            }
            for name, content in files.items():
                p = source/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            for name, content in {
                'additiveFoam.C': '        #include "thermo/TEqn.H"',
                'thermo/TEqn.H': '        T.correctBoundaryConditions();',
                'thermo/thermoScheme.H': 'fixture Euler terms',
                'thermo/thermoSource.H': 'fixture dFdT and T0 only',
                'updateProperties.H': 'fixture Cp updated before TEqn',
                'Make/files': 'EXE = $(FOAM_USER_APPBIN)/additiveFoam',
            }.items():
                p = solver/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
            pinned = {name: module.digest(solver/name) for name in module.PINNED}
            before = module.hashes(source)
            with patch.object(module, 'PINNED', pinned):
                result = module.prepare(source, solver, output)
                with self.assertRaises(FileExistsError):
                    module.prepare(source, solver, output)
            self.assertEqual(before, module.hashes(source))
            self.assertFalse(result['physics_changed_between_pair'])
            self.assertFalse(result['manufacturing_authorized'])
            left, right = module.hashes(output/'dt'), module.hashes(output/'dt_half')
            self.assertEqual([key for key in left if left[key] != right[key]], ['system/controlDict'])
            for name in files:
                if name != 'system/controlDict':
                    self.assertEqual(before[name], left[name])
            self.assertIn('deltaT 5e-08;', (output/'dt_half/system/controlDict').read_text())


if __name__ == '__main__':
    unittest.main()
