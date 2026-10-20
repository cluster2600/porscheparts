"""Analytic integration checks and regression for a real rejected CCX field."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'
EVIDENCE=ROOT/'docs/reports/carrier-resume-20261020/evidence'


def actual_errors(case):
    folder=EVIDENCE/case;expected=json.loads((folder/'input/analytic.json').read_text());u=[];stress=[];active=None
    for line in (folder/'execution/case/job.dat').read_text().splitlines():
        text=line.strip()
        if text.startswith('displacements ('):active='u'
        if text.startswith('stresses ('):active='s'
        row=text.split()
        if row and row[0].isdigit():
            if active=='u'and len(row)==4:u.append(list(map(float,row[1:])))
            elif active=='s'and len(row)==8:stress.append(list(map(float,row[2:])))
    if len(u)!=8 or len(stress)!=6:raise ValueError('Incomplete analytic result roster')
    uerror=max(abs(x-y)for row,want in zip(u,expected['expected_displacements'])for x,y in zip(row,want))
    serror=max(abs(x-y)for row in stress for x,y in zip(row,expected['expected_stress_MPa']))
    return expected,uerror,serror


class CCXControlTests(unittest.TestCase):
    def test_direct_affine_solution_meets_both_original_limits(self):
        expected,u,s=actual_errors('ccx-affine-direct-control-001')
        self.assertEqual(expected['absolute_displacement_tolerance_mm'],1e-11)
        self.assertEqual(expected['absolute_stress_tolerance_MPa'],1e-6)
        self.assertLessEqual(u,expected['absolute_displacement_tolerance_mm'])
        self.assertLessEqual(s,expected['absolute_stress_tolerance_MPa'])

    def test_default_iterative_result_remains_refused_at_the_same_limits(self):
        expected,u,s=actual_errors('ccx-affine-control-001')
        self.assertGreater(u,expected['absolute_displacement_tolerance_mm'])
        self.assertGreater(s,expected['absolute_stress_tolerance_MPa'])
        direct=json.loads((EVIDENCE/'ccx-affine-direct-control-001/input/analytic.json').read_text())
        self.assertEqual(expected,direct)

    def test_actual_rejected_cload_value_fits_the_CCX_numeric_field(self):
        spec=importlib.util.spec_from_file_location('_ccx_fields',SOURCE/'prepare_tetgen_mechanics_ccx.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        value=1.3843990327051638e-5
        self.assertGreater(len(format(value,'.17g')),20)
        for x in [value,-value,280.12345678901234,1e-300,-1e-300,0.]:
            token=module.ccx_field(x)
            self.assertLessEqual(len(token),20)
            self.assertLessEqual(abs(float(token)-x),max(abs(x)*1e-13,1e-313))
