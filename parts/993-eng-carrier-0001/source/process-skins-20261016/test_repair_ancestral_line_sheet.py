import hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from repair_ancestral_line_sheet import repair

class ExplicitRepairTests(unittest.TestCase):
    def test_changed_faces_lose_positive_parent_claims(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);v=np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0],[1e-15,0,0]],dtype=np.float64)
            f=np.array([[4,1,2],[0,4,3],[1,3,2]],dtype=np.int64)
            np.savez(p/'raw.npz',vertices=v,faces=f,all_parent_offsets=np.arange(4),all_parent_faces=np.array([8,9,10]))
            np.savez(p/'snap.npz',vertices=v,faces=f,autorefine_input_face=np.arange(3),source_face=np.array([8,9,10]),source=np.zeros(3,dtype=np.int64))
            sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
            plan={'input_sha256':sha(p/'snap.npz'),'original_float_sha256':sha(p/'raw.npz'),'vertex_maps':[{'source':4,'target':0,'source_coordinates':v[4].tolist(),'target_coordinates':v[0].tolist()}],'admission':['independent geometry audit']}
            (p/'plan.json').write_text(json.dumps(plan));r=repair(p/'snap.npz',p/'raw.npz',p/'plan.json',p/'out');a=np.load(p/'out/result.npz')
            self.assertEqual(r['retained_changed_faces'],1)
            np.testing.assert_array_equal(a['source_face'],[-1,10]);np.testing.assert_array_equal(a['all_parent_offsets'],[0,0,1])
            np.testing.assert_array_equal(a['all_parent_faces'],[10]);np.testing.assert_array_equal(a['historical_parent_faces'],[8,10])
            self.assertTrue(r['removed_microtriangles'][0]['was_positive_area']);self.assertFalse(r['positive_area_change_claimed_zero'])

if __name__=='__main__':unittest.main()
