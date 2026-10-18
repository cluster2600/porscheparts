"""Pure software fixtures; no actual carrier solve or Docker invocation."""
import importlib.util
from pathlib import Path
import unittest

import numpy as np

HERE=Path(__file__).resolve().parent
def load(name):
    s=importlib.util.spec_from_file_location('_wholepart_'+name,HERE/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('prepare');a=load('assess')


class Checks(unittest.TestCase):
    def test_exact_plane_gauges(self):
        nodes={1:(0.,0.,0.),2:(1.,0.,0.),3:(0.,1.,0.),4:(0.,0.,1.)}
        clamp,dofs,proof=p.gauges(nodes)
        self.assertEqual(clamp,[1,2,3]);self.assertEqual(len(dofs),6);self.assertNotEqual(proof['exact_rigid_rotation_determinant'],'0')

    def test_collinear_gauges_refused(self):
        with self.assertRaises(ValueError):p.gauges({1:(0.,0.,0.),2:(0.,1.,0.),3:(0.,2.,0.)})

    def test_uniform_has_analytic_nonzero_gauge(self):
        nodes={1:(0.,0.,0.),2:(1.,1.,0.),3:(0.,1.,0.),4:(0.,0.,1.)}
        clamp,dofs,_=p.gauges(nodes);text=p.deck('uniform',nodes,clamp,dofs)
        self.assertIn('*BOUNDARY,OP=NEW',text);self.assertNotIn('PROVISIONAL_ZMIN,1,3',text)
        self.assertIn('2,2,2,-',text);self.assertNotIn('*CLOAD',text);self.assertNotIn('*SPRING',text)

    def test_release_changes_only_constraints(self):
        nodes={1:(0.,0.,0.),2:(1.,0.,0.),3:(0.,1.,0.),4:(0.,0.,1.)}
        clamp,dofs,_=p.gauges(nodes);text=p.deck('incompatible-release',nodes,clamp,dofs)
        self.assertEqual(text.count('*STEP\n'),2);self.assertEqual(text.count('*BOUNDARY,OP=NEW'),2)
        self.assertEqual(text.count('*INCLUDE,INPUT=quadratic-temperature.inc'),2)
        self.assertEqual(text.count('PROVISIONAL_ZMIN,1,3,0.'),1)

    def test_projected_circle(self):
        points=[[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]]
        r=a.circle(points,2);self.assertAlmostEqual(r['projected_diameter_mm'],2.)
        self.assertLess(r['radial_residual_max_mm'],1e-12)

    def fixture(self):
        xyz=[(0,0,0),(1,0,0),(0,1,0),(0,0,1),(.5,0,0),(.5,.5,0),(0,.5,0),(0,0,.5),(.5,0,.5),(0,.5,.5)]
        nodes={i+1:tuple(map(float,v))for i,v in enumerate(xyz)};groups={}
        for n in ('bolt0','bolt1','bolt2','bolt3','end0','end1'):
            axis=2 if n.startswith('bolt')else 1;ids=[]
            for x,y in [(1.,0.),(0.,1.),(-1.,0.),(0.,-1.)]:
                v=[x,y,2.]if axis==2 else[x,2.,y];i=len(nodes)+1;nodes[i]=tuple(v);ids.append(i)
            groups[n]=ids
        return nodes,{1:tuple(range(1,11))},groups

    def test_uniform_dimensions_volume_and_mass(self):
        nodes,cells,groups=self.fixture();e=-1e-4;u={i:e*np.array(v)for i,v in nodes.items()};r=a.metrics(nodes,cells,groups,u)
        self.assertAlmostEqual(r['deformed_volume_4Gauss_mm3']/r['reference_volume_mm3'],(1+e)**3,places=12)
        self.assertAlmostEqual(r['bore_projected_metrics']['bolt0']['diameter_change_mm'],2*e,places=12)
        self.assertEqual(r['reference_mass_kg'],r['material_mass_kg'])

    def test_inverted_deformation_refused(self):
        nodes,cells,groups=self.fixture()
        with self.assertRaises(ValueError):a.metrics(nodes,cells,groups,{i:-2*np.array(v)for i,v in nodes.items()})


if __name__=='__main__':unittest.main()
