import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/935-horizontal-cooling-system-f0/source'
def load(name):
    spec=importlib.util.spec_from_file_location(name,SOURCE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
witness=load('bending_witness');formulation=load('prepare_formulation_comparison')


class FormulationWitnessTests(unittest.TestCase):
    def test_end_traction_has_zero_force_and_unit_moment_on_every_mesh(self):
        for divisions in ((4,1,1),(8,2,1),(16,4,2)):
            text,case,xyz,fixed=witness.beam(*divisions,'C3D8')
            loads=text.split('*CLOAD\n')[1].split('*NODE PRINT')[0].strip().splitlines()
            total=sum(float(row.split(',')[2]) for row in loads)
            moment=sum(xyz[int(row.split(',')[0])][2]*float(row.split(',')[2]) for row in loads)
            self.assertAlmostEqual(total,0.,places=12);self.assertAlmostEqual(moment,1.,places=12)
            self.assertTrue(all(xyz[node][0]==0 for node in fixed))
            self.assertAlmostEqual(case['exact_tip_uz_mm'],-3/700.,places=12)

    def test_witness_formulations_share_mesh_loads_and_boundary(self):
        a,*_=witness.beam(8,2,1,'C3D8');b,*_=witness.beam(8,2,1,'C3D8I')
        self.assertEqual(a,b.replace('TYPE=C3D8I,','TYPE=C3D8,'))
        for bad in (0,True,65,float('nan')):
            with self.assertRaises(ValueError):witness.beam(bad,2,1,'C3D8')

    def test_rotor_adapter_changes_only_element_header(self):
        source='*NODE\n1,0,0,0\n*ELEMENT,TYPE=C3D8,ELSET=ROTOR\n1,1,2,3,4,5,6,7,8\n*BOUNDARY\nBORE,1,3,0\n*STATIC\nROTOR,CENTRIF,1,0,0,0,0,0,1\n'
        result=formulation.replace_formulation(source)
        self.assertEqual(result.replace('TYPE=C3D8I,','TYPE=C3D8,'),source)
        for bad in (source.replace('C3D8,','C3D8R,'),source+source,source.replace('BORE,1,3,0','BORE,1,2,0')):
            with self.assertRaises(ValueError):formulation.replace_formulation(bad)
