import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEAD = ROOT / 'twins/962-cylinder-head-f0'
spec = importlib.util.spec_from_file_location('head_workflow', HEAD / 'source/workflow_plan.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(module.CONTRACT.read_text())

    def test_repository_instructions_and_required_software_cover_the_chain(self):
        stages = module.validate_contract(self.contract)
        tools = set().union(*(set(s['software']) for s in stages))
        self.assertTrue({'PicoGK', 'ShapeKernel', 'LatticeLibrary', 'Fasteners',
                         'Gmsh', 'MMG', 'CalculiX', 'MOOSE', 'Adamantine',
                         'AdditiveFOAM 2.0.0', 'OpenFOAM 13', 'OpenFOAM 14',
                         'OpenVDB', 'OpenUSD', 'Content Agents', 'OVRTX',
                         'PhysicsNeMo', 'Qwen'} <= tools)
        self.assertIn('twins/962-cylinder-head-f0/WORKFLOW.md', (ROOT / 'AGENTS.md').read_text())
        self.assertIn('workflow-contract.json', (HEAD / 'AGENTS.md').read_text())

    def test_missing_lpbf_phase_and_cyclic_dependency_are_rejected(self):
        for mutation in ('remove', 'cycle', 'path'):
            contract = copy.deepcopy(self.contract)
            if mutation == 'remove':
                contract['phases'] = [s for s in contract['phases'] if s['id'] != 'lpbf_build']
            elif mutation == 'cycle':
                contract['phases'][0]['depends_on'] = ['delivery']
            else:
                contract['phases'][0]['references'] = ['../outside-recipe']
            with self.assertRaises(ValueError):
                module.validate_contract(contract)

    def test_materialization_is_complete_blocked_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'plan'
            plan = module.materialize(out, self.contract)
            result = module.validate_plan(plan, out, self.contract)
            self.assertEqual(result['phases'], 19)
            self.assertFalse(result['all_phases_accepted'])
            self.assertEqual(set(result['states'].values()), {'blocked'})
            with self.assertRaises(ValueError):
                module.materialize(out, self.contract)

    def test_templates_missing_proofs_and_changed_evidence_cannot_promote_a_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'plan'
            plan = module.materialize(out, self.contract)
            job = plan['jobs'][0]
            job['state'] = 'prepared'
            with self.assertRaises(ValueError):
                module.validate_plan(plan, out, self.contract)
            job['input_bindings'] = {name: 'documented-study-input' for name in job['input_bindings']}
            job['commands'] = [['python3', 'bound-study.py']]
            runtime = out / 'runtime.json'
            runtime.write_text(json.dumps(dict(kind='runtime_qualification', phase='provenance', passed=True)))
            job['runtime_receipt'] = dict(path=runtime.name, sha256=module.sha(runtime))
            self.assertEqual(module.validate_plan(plan, out, self.contract)['states']['provenance'], 'prepared')
            job['state'] = 'accepted'
            with self.assertRaises(ValueError):
                module.validate_plan(plan, out, self.contract)
            job['state'] = 'prepared'
            runtime.write_text('{}')
            with self.assertRaises(ValueError):
                module.validate_plan(plan, out, self.contract)

    def test_core_phase_cannot_be_omitted_or_manufacturing_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'plan'
            plan = module.materialize(out, self.contract)
            invalid = copy.deepcopy(plan)
            invalid['jobs'][9]['state'] = 'not_applicable'
            invalid['jobs'][9]['reason'] = 'skip to save time'
            with self.assertRaises(ValueError):
                module.validate_plan(invalid, out, self.contract)
            invalid = copy.deepcopy(plan)
            invalid['manufacturing_authorized'] = True
            with self.assertRaises(ValueError):
                module.validate_plan(invalid, out, self.contract)
            invalid = copy.deepcopy(plan)
            invalid['source_hashes'].pop(next(iter(invalid['source_hashes'])))
            with self.assertRaises(ValueError):
                module.validate_plan(invalid, out, self.contract)


if __name__ == '__main__':
    unittest.main()
