import copy
import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/package_split_gas_domain.py'
spec=importlib.util.spec_from_file_location('split_packet',PATH)
packet=importlib.util.module_from_spec(spec);spec.loader.exec_module(packet)


class SplitGasPacketTests(unittest.TestCase):
    def review(self):
        return {'input_sha256':[packet.OLD,packet.NEW],'inputs_unchanged':True,
            'candidate_exact_valid':True,'all_contours_preserved':True,
            'contours':[{'face_id_private':i,'same_face_orientation':True,
                'same_oriented_edge_multiset_in_each_wire_after_target_expansion':True}
                for i in range(1,89)],
            'summary':{'surfaces':{'count':88,'incompatible_count':0},
                'pcurves':{'incompatible_count':0},'unchanged_edges':{'incompatible_count':0}}}

    def test_complete_correspondence_required_not_count_only(self):
        good=self.review();self.assertTrue(packet.verified_face_transfer(good))
        missing=copy.deepcopy(good);missing['contours'].pop()
        self.assertFalse(packet.verified_face_transfer(missing))
        duplicate=copy.deepcopy(good);duplicate['contours'][-1]['face_id_private']=1
        self.assertFalse(packet.verified_face_transfer(duplicate))
        for key in ('same_face_orientation','same_oriented_edge_multiset_in_each_wire_after_target_expansion'):
            changed=copy.deepcopy(good);changed['contours'][36][key]=False
            self.assertFalse(packet.verified_face_transfer(changed))

    def test_changed_provenance_or_geometry_refused(self):
        good=self.review()
        self.assertFalse(packet.verified_face_transfer({}))
        self.assertFalse(packet.verified_face_transfer({**good,'input_sha256':[packet.NEW,packet.OLD]}))
        for key in ('inputs_unchanged','candidate_exact_valid','all_contours_preserved'):
            self.assertFalse(packet.verified_face_transfer({**good,key:False}))
        for key in good['summary']:
            changed=copy.deepcopy(good);changed['summary'][key]['incompatible_count']=1
            self.assertFalse(packet.verified_face_transfer(changed))


if __name__=='__main__':unittest.main()
