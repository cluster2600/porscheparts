"""Synthetic protocol witnesses, not private geometry or meshing qualification."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/native_gas_profiles.py'
spec=importlib.util.spec_from_file_location('segmented_native_profile',PATH)
profiles=importlib.util.module_from_spec(spec);spec.loader.exec_module(profiles)


def fixture():
    return {'schema':'m64-intake-gas-domain/v1',
        'exports':{'domain_brep':{'sha256':profiles.SEGMENTED_DOMAIN_SHA}},
        'gates':{**dict.fromkeys(profiles.NATIVE_ONLY_GATES,True),'step_roundtrip_valid':None},
        'STEP_BOP_qualified':False,'manufacturing_authorized':False,'inputs_unchanged':True,
        'native_BOP':{'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]},
        'native_roundtrip_BOP':{'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]},
        'boundary_role_transfer':{'synthetic_witness_only':True},
        'boundary_faces':[{'id':i,'sha256':profiles.SEGMENTED_FACE_SHAS.get(i,format(i,'064x'))}
                          for i in range(1,89)]}


def registered(value,prepared=False):
    stack=ExitStack();prefix='PREPARED' if prepared else 'SEGMENTED'
    stack.enter_context(patch.object(profiles,prefix+'_MANIFEST_SHA','f'*64))
    stack.enter_context(patch.object(profiles,prefix+'_MANIFEST_CONTENT_SHA',profiles.content_sha(value)))
    return stack


class SegmentedNativeProfileTests(unittest.TestCase):
    def test_native_only_is_explicit_and_original_data_are_not_changed(self):
        value=fixture();original=deepcopy(value)
        with registered(value):
            result=profiles.registered_segmented_manifest(value,'f'*64)
        self.assertEqual(value,original)
        self.assertFalse(result['STEP_used'])
        self.assertFalse(result['CFD_qualified'])
        self.assertFalse(result['manufacturing_authorized'])

    def test_prepared_inventory_cannot_grant_meshing_even_with_success_flags(self):
        value=fixture()
        with registered(value,prepared=True),patch.object(profiles,'SEGMENTED_MANIFEST_SHA',None):
            profiles.registered_segmented_manifest(value,'f'*64,for_meshing=False)
            with self.assertRaises(ValueError):profiles.registered_segmented_manifest(value,'f'*64)

    def test_old_wrong_or_modified_manifest_is_refused(self):
        value=fixture()
        with registered(value):
            with self.assertRaises(ValueError):profiles.registered_segmented_manifest(value,'0'*64)
            for target,path,replacement in (
                    ('domain',('exports','domain_brep','sha256'),'3'*64),
                    ('face',('boundary_faces',37,'sha256'),'0'*64),
                    ('approval',('gates','step_roundtrip_valid'),True)):
                changed=deepcopy(value);obj=changed
                for key in path[:-1]:obj=obj[key]
                obj[path[-1]]=replacement
                with self.subTest(target=target),self.assertRaises(ValueError):
                    profiles.registered_segmented_manifest(changed,'f'*64)

    def test_failed_native_gates_cannot_be_waived_by_a_registered_package(self):
        for key in profiles.NATIVE_ONLY_GATES:
            value=fixture();value['gates'][key]=None
            with self.subTest(key=key),registered(value),self.assertRaises(ValueError):
                profiles.registered_segmented_manifest(value,'f'*64)
        value=fixture();value['native_BOP']['faults']=['BOPAlgo_GeomAbs_C0']
        with registered(value),self.assertRaises(ValueError):profiles.registered_segmented_manifest(value,'f'*64)

    def test_native_profile_cannot_claim_STEP_or_accept_incomplete_faces(self):
        for key,entry in (('step',True),('manufacturing',True),('missing_face',None)):
            value=fixture()
            if key=='step':value['gates']['step_roundtrip_valid']=entry
            elif key=='manufacturing':value['manufacturing_authorized']=entry
            else:value['boundary_faces'].pop()
            with self.subTest(key=key),registered(value),self.assertRaises(ValueError):
                profiles.registered_segmented_manifest(value,'f'*64)

    def test_guide_frames_require_a_registered_new_manifest_not_old_domain(self):
        with patch.object(profiles,'SEGMENTED_MANIFEST_SHA','f'*64):
            frames={'classified_manifest_sha256':'f'*64}
            self.assertEqual(set(profiles.guide_face_hashes(profiles.SEGMENTED_DOMAIN_SHA,frames)),set(profiles.GUIDE_FACE_IDS))
            frames['classified_manifest_sha256']='0'*64
            with self.assertRaises(ValueError):profiles.guide_face_hashes(profiles.SEGMENTED_DOMAIN_SHA,frames)
            with self.assertRaises(ValueError):profiles.guide_face_hashes('0'*64)


if __name__=='__main__':unittest.main()
