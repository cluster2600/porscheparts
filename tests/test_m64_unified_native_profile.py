"""Témoins synthétiques du profil 86 faces, pas des résultats de CAO ou de CFD."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/mesh_gas_domain.py'
spec=importlib.util.spec_from_file_location('unified_mesh_tests',PATH)
mesh=importlib.util.module_from_spec(spec);spec.loader.exec_module(mesh)
p=mesh.profiles


def fixture():
    rows=[]
    for i in range(1,87):
        role='inlet' if i==48 else 'receiver_outlet' if i==17 else 'walls_port'
        source=mesh.UNIFIED_GUIDE_STEM_SOURCES.get(i)
        if source:role='walls_guide' if 'guide' in source else 'walls_valve'
        if 63<=i<=68:
            role='walls_valve';source='intake_%d_valve_face_6'%(1 if i%2 else 2)
        rows.append({'id':i,'role':role,'sha256':p.UNIFIED_FACE_SHAS.get(i,format(i,'064x')),
                     'area':1.,'center':[0.,0.,float(i)],'surface_type':'GeomAbs_Cylinder',
                     'source_match':[{'source':source}] if source else []})
    clean={'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]}
    return {'schema':'m64-intake-gas-domain/v1','exports':{'domain_brep':{'sha256':p.UNIFIED_DOMAIN_SHA256}},
        'gates':{**dict.fromkeys(p.NATIVE_ONLY_GATES,True),'step_roundtrip_valid':None},
        'native_BOP':clean,'native_roundtrip_BOP':deepcopy(clean),'STEP_BOP_qualified':False,
        'manufacturing_authorized':False,'inputs_unchanged':True,'boundary_faces':rows,
        'boundary_role_transfer':{'synthetic_only':True}}


def registration(value):
    stack=ExitStack()
    stack.enter_context(patch.object(p,'UNIFIED_MANIFEST_SHA','f'*64))
    stack.enter_context(patch.object(p,'UNIFIED_MANIFEST_CONTENT_SHA',p.content_sha(value)))
    return stack


class UnifiedProfileTests(unittest.TestCase):
    def test_unified_request_cannot_skip_actual_guide_gates(self):
        mesh.validate_unified_guide_request(SimpleNamespace(unified_native_only=True,
            guide_size=.2,guide_chord_reference=Path('synthetic-reference.json')))
        for size,reference in ((None,None),(None,Path('reference.json')),(.2,None)):
            with self.subTest(size=size,reference=reference),self.assertRaisesRegex(ValueError,'requires_guide'):
                mesh.validate_unified_guide_request(SimpleNamespace(unified_native_only=True,
                    guide_size=size,guide_chord_reference=reference))
        mesh.validate_unified_guide_request(SimpleNamespace(unified_native_only=False))

    def test_exact_new_profile_does_not_modify_or_qualify_input(self):
        value=fixture();before=deepcopy(value)
        with registration(value):
            result=p.registered_unified_manifest(value,'f'*64)
            contract=mesh.validated_boundary_contract(value,unified_native_only=True)
        self.assertEqual(value,before)
        self.assertEqual(contract['groups']['inlet'],[48])
        self.assertEqual(result['domain_sha256'],p.UNIFIED_DOMAIN_SHA256)
        self.assertFalse(result['STEP_used']);self.assertFalse(result['CFD_qualified'])
        self.assertFalse(result['manufacturing_authorized'])

    def test_absent_or_stale_registration_is_rejected(self):
        value=fixture()
        with registration(value):
            for h in ('0'*64,p.SEGMENTED_MANIFEST_SHA):
                with self.assertRaises(ValueError):p.registered_unified_manifest(value,h)
            with patch.object(p,'UNIFIED_MANIFEST_SHA',None),self.assertRaises(ValueError):
                p.registered_unified_manifest(value,for_meshing=False)
            changed=deepcopy(value);changed['boundary_faces'][0]['area']=2.
            with self.assertRaises(ValueError):p.registered_unified_manifest(changed)

    def test_registered_flags_cannot_waive_native_failure_or_grant_STEP(self):
        for gate in p.NATIVE_ONLY_GATES:
            value=fixture();value['gates'][gate]=False
            with self.subTest(gate=gate),registration(value),self.assertRaises(ValueError):
                p.registered_unified_manifest(value)
        for path,replacement in ((('gates','step_roundtrip_valid'),True),
                (('native_BOP','faults'),['BOPAlgo_GeomAbs_C0']),
                (('inputs_unchanged',),False),(('manufacturing_authorized',),True)):
            value=fixture();obj=value
            for k in path[:-1]:obj=obj[k]
            obj[path[-1]]=replacement
            with self.subTest(path=path),registration(value),self.assertRaises(ValueError):
                p.registered_unified_manifest(value)

    def test_all_faces_and_new_guide_pins_are_required(self):
        for change in ('missing','old_hash','duplicate'):
            value=fixture()
            if change=='missing':value['boundary_faces'].pop()
            elif change=='old_hash':value['boundary_faces'][52]['sha256']=p.SEGMENTED_FACE_SHAS[55]
            else:value['boundary_faces'][1]['id']=1
            with self.subTest(change=change),registration(value),self.assertRaises(ValueError):
                p.registered_unified_manifest(value)

    def test_modes_cannot_mix_and_obsolete_face38_is_rejected(self):
        value=fixture();binding={'descriptor_bijection_verified':True,'matches_private':[]}
        with registration(value):
            for flags in ({},{'segmented_native_only':True},
                    {'c0_diagnostic':True,'unified_native_only':True},
                    {'segmented_native_only':True,'unified_native_only':True}):
                with self.subTest(flags=flags),self.assertRaises(ValueError):
                    mesh.validated_boundary_contract(value,**flags)
            self.assertIsNone(mesh.face38_size_assignment(value,binding,None))
            for algorithm in (1,5):
                with self.assertRaisesRegex(ValueError,'obsolete_face38'):
                    mesh.face38_algorithm_assignment(value,binding,algorithm)
            with self.assertRaisesRegex(ValueError,'obsolete_face38'):
                mesh.face38_size_assignment(value,binding,.15)

    def test_guide_sizing_uses_new_faces_and_all_fourteen_fragments(self):
        value=fixture()
        rows=[r for r in value['boundary_faces'] if r['source_match']]
        frames={'native_inventory':{'cylinders_private':[
            {'face_id':r['id'],'face_sha256':r['sha256'],'role':r['role'],
             'source_names':[s['source'] for s in r['source_match']]} for r in rows]},
            'coverage':{'selected_face_ids':list(p.UNIFIED_GUIDE_FACE_IDS),
                        'excluded_cylinders':[{'face_id':i} for i in range(63,69)]}}
        binding={'descriptor_bijection_verified':True,'matches_private':[
            {'source_face_index':i,'gmsh_face_tag':900+i} for i in p.UNIFIED_GUIDE_FACE_IDS]}
        with registration(value):
            result=mesh.guide_size_assignment(value,binding,.2,frames)
            self.assertEqual([r['source_face_id'] for r in result['faces']],list(p.UNIFIED_GUIDE_FACE_IDS))
            self.assertEqual([r['gmsh_face_tag'] for r in result['faces']],[900+i for i in p.UNIFIED_GUIDE_FACE_IDS])
            self.assertEqual(len(result['source_fragments_examined']),14)
            self.assertEqual(result['native_axially_excluded_stem_fragments'],list(range(63,69)))
            stale=deepcopy(frames);stale['coverage']['selected_face_ids']=list(p.GUIDE_FACE_IDS)
            with self.assertRaises(ValueError):mesh.guide_size_assignment(value,binding,.2,stale)

    def test_new_inventory_requires_exact_producer_and_no_mesh_result(self):
        value=fixture()
        frames={'schema':'m64-native-guide-cylinder-frames/v2','domain_sha256':p.UNIFIED_DOMAIN_SHA256,
                'classified_manifest_sha256':'f'*64,'coverage':{'selected_face_ids':list(p.UNIFIED_GUIDE_FACE_IDS)}}
        receipt={'schema':'m64-native-guide-frame-inventory/v1','mode':'native_inventory_only',
            'all_inputs_unchanged':True,'CAD_modified':False,'mesh_accepted':False,'CFD_executed':False,
            'manufacturing_authorized':False,'inputs_sha256':{'domain':p.UNIFIED_DOMAIN_SHA256,
                'boundary_report':'f'*64,'source':'a'*64,'profile_source':'b'*64},
            'result':{'frames_private':frames,'whole_facet_chord_gate':None}}
        with registration(value),patch.object(mesh,'UNIFIED_GUIDE_FRAME_RECEIPT_SHA','c'*64),\
                patch.object(mesh,'UNIFIED_GUIDE_PRODUCER_SOURCE_SHA','a'*64),\
                patch.object(mesh,'UNIFIED_GUIDE_PRODUCER_PROFILE_SHA','b'*64):
            self.assertIs(mesh.validated_guide_frames(receipt,'c'*64,value),frames)
            for path,replacement in ((('inputs_sha256','domain'),p.SEGMENTED_DOMAIN_SHA),
                    (('inputs_sha256','source'),'0'*64),(('inputs_sha256','profile_source'),'0'*64),
                    (('result','frames_private','coverage','selected_face_ids'),list(p.GUIDE_FACE_IDS)),
                    (('result','whole_facet_chord_gate'),{'passed':True})):
                changed=deepcopy(receipt);obj=changed
                for k in path[:-1]:obj=obj[k]
                obj[path[-1]]=replacement
                with self.subTest(path=path),self.assertRaises(ValueError):
                    mesh.validated_guide_frames(changed,'c'*64,value)
            with self.assertRaises(ValueError):
                mesh.validated_guide_frames(receipt,mesh.SEGMENTED_GUIDE_FRAME_RECEIPT_SHA,value)


if __name__=='__main__':unittest.main()
