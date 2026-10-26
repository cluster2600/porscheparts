"""Check the variational envelope against independently solved anisotropic SPD systems."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022/bound_cellular_compliance.py'
spec=importlib.util.spec_from_file_location('cell_bounds',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ComplianceBoundsTests(unittest.TestCase):
    def test_independently_solved_anisotropic_matrices_obey_both_bounds(self):
        rng=np.random.default_rng(993)
        for _ in range(200):
            A=rng.normal(size=(5,5));K0=A.T@A+np.eye(5)
            d,v=np.linalg.eigh(K0);root=(v*np.sqrt(d))@v.T
            Q,_=np.linalg.qr(rng.normal(size=(5,5)));P=(Q*rng.uniform(0,1,5))@Q.T
            core=root@P@root;d,v=np.linalg.eigh(core);core_root=(v*np.sqrt(d))@v.T
            Q,_=np.linalg.qr(rng.normal(size=(5,5)));etas=rng.uniform(.1,.4,5);H=(Q*etas)@Q.T
            Knew=K0-core+core_root@H@core_root;force=rng.normal(size=5)
            u=np.linalg.solve(K0,force);fraction=float(u@core@u/(force@u));actual=float(force@np.linalg.solve(Knew,force)/(force@u))
            lower,upper=m.compliance_bounds(fraction,float(etas.min()),float(etas.max()))
            self.assertLessEqual(lower,actual+1e-12);self.assertLessEqual(actual,upper+1e-12)

    def test_limits_and_invalid_hypotheses(self):
        self.assertEqual(m.compliance_bounds(0,.2,.4),(1.,1.))
        lower,upper=m.compliance_bounds(1,.2,.4);self.assertAlmostEqual(lower,2.5);self.assertAlmostEqual(upper,5.)
        for args in [(-.1,.2,.4),(1.1,.2,.4),(.5,0,.4),(.5,.5,.4),(.5,.2,1.1)]:
            with self.assertRaises(ValueError):m.compliance_bounds(*args)

    def test_cli_refuses_incompatible_baseline_and_invalid_region_before_output(self):
        root=SOURCE.parents[5];base=root/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025'
        for invalid in ['dense_material','density','region_energy']:
            material=json.loads((base/'periodic-gyroid-study-002/n48-floor1e-6/assessment.json').read_text());sweep=json.loads((base/'cellular-skin-sweep-001/assessment.json').read_text())
            if invalid=='dense_material':material['dense_C_MPa'][0][0]*=1.1
            elif invalid=='density':material['solid_fraction']=float('nan')
            else:sweep['rows'][0]['T10_baseline_energy_fraction']=1.1
            with tempfile.TemporaryDirectory()as folder:
                p=Path(folder);(p/'material.json').write_text(json.dumps(material));(p/'sweep.json').write_text(json.dumps(sweep));args=['bounds','--material',str(p/'material.json'),'--skin-sweep',str(p/'sweep.json'),'--output',str(p/'output')]
                with patch('sys.argv',args),self.assertRaises(ValueError):m.main()
                self.assertFalse((p/'output').exists())

    def test_published_N64_envelope_keeps_its_source_image_and_conditional_scope(self):
        root=SOURCE.parents[5];p=root/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025/conditional-compliance-bounds-n64-020/assessment.json';r=json.loads(p.read_text())
        self.assertEqual(r['material_resolution'],64)
        self.assertTrue(r['homogenized_uniform_constitutive_substitution_only'])
        self.assertFalse(r['finite_cell_connections_modelled']);self.assertFalse(r['stress_or_strength_bounded']);self.assertFalse(r['cellular_part_generated'])
        self.assertIn(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),r['source_sha256'].values())
        image=root/'docs/media/carrier-convergence-20261022/conditional-compliance-bounds-n64-020/conditional-compliance-bounds.png'
        self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(),r['figure_sha256'])
