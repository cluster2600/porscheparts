"""One native regression witness, supplementary to the recorded 144-pose audit."""
import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('g14_private',Path(__file__).with_name('g14_cad_private.py'))
g14=importlib.util.module_from_spec(spec);spec.loader.exec_module(g14)
import rocker_train


class NativeWitness(unittest.TestCase):
    def test_known_collision_and_unchanged_interfaces(self):
        self.assertEqual(g14.g11.sha256(Path(g14.__file__)),'612c412f2875d4302d2b88d533dd46abe1183ebffd74c30472ae011dc76c4f0f')
        folder=Path(__file__).parent/'cad-v1'
        proof=json.loads((folder/'interface-proof.json').read_text())
        p=proof['values']
        basepath=g14.REPO/'work/m64-g11/cad-v2/centre_w11/central_diaphragm.step'
        expected=next(r for r in proof['variants'] if r['id']=='centre_spine68_t30')['baseline_step_sha256']
        self.assertEqual(g14.g11.sha256(basepath),expected)
        base=g14.cq.importers.importStep(str(basepath)).val()
        rocker=rocker_train.moving_parts(p,'exhaust',1,0)['rocker']
        seventy=g14.central(p,base,70,False)
        self.assertAlmostEqual(g14.audit.overlap(seventy,rocker),3.606217933939723,places=7)
        slab=g14.cq.Solid.makeBox(400,200,1,g14.cq.Vector(-200,-100,p['carrier_face_height']))
        for span,shoulder in ((68,False),(70,True)):
            with self.subTest(span=span,shoulder=shoulder):
                shape=g14.central(p,base,span,shoulder)
                self.assertLessEqual(g14.audit.overlap(shape,rocker),g14.g11.TOL)
                self.assertTrue(g14.assembly.brep_valid(shape))
                self.assertEqual(len(shape.Solids()),1)
                delta=g14.g13.difference(shape.intersect(slab),base.intersect(slab))
                self.assertTrue(all(v<=g14.g11.TOL for v in delta.values()))
                self.assertTrue(all(v<=g14.g11.TOL for row in g14.journal_masks(shape,base,p).values() for v in row.values()))


if __name__=='__main__':unittest.main()
