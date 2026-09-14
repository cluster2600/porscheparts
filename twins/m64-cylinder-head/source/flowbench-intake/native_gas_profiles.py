"""Additional exact native-only profile; never replace the historical gas05 pins.

Registration is deliberately fail-closed until the independently reviewed private
package is available. Hashes refer to representation/provenance, not manufacture.
"""
import hashlib
import json

SEGMENTED_DOMAIN_SHA = '7fc114c1a8229665047c734fd22129783df420deb5e01e809995c6b3efdc5de8'
# Prepared package authorizes native inventory only, never meshing.
PREPARED_MANIFEST_SHA = '78a53bdb394bb357f4c3ee277d432d76ca048440cfd4d63c3a9d9fd21131b5fa'
PREPARED_MANIFEST_CONTENT_SHA = '97742f896edba760a9a18a9e9ce46703db0066f8f0a5acfaffea34c85b92eeb3'
SEGMENTED_MANIFEST_SHA = '92576714217042c0f152c1da7d8a8fa0da8f1757e5ec06c9c6f4eee3c66ccc58'
SEGMENTED_MANIFEST_CONTENT_SHA = '4b0dea5d24cb2429df2e3ecf1430030407a2c5d8f8bd221ce2eccb89014d51e3'
SEGMENTED_FACE_SHAS = {
    38:'39b2290ec7176675498e9b9c8e83b147f23438ab8d12ced8f3836fa8e31a6561',
    55:'2976073b2920e1db6502e7c821b3e379eb7823a26e9493ec0da07c96fcc63f8d',
    56:'fd6c4663c9b402ac45391f1e2ceaa79272d3b126844d7bffeb8bd7bc981aa3d8',
    57:'1c886d70246d7908c6bd69c6002a28670e425b213ca2922b66a62776381bca0f',
    58:'79ff20cbe4543716fd54bb065db217d7bc78a7c888320ff4618bdacf2615747e',
    61:'7844332996b465cd7ab831f3e4aad45dc2487ecef69aa8231ac6633bc40fcb69',
    62:'0fd082f1f9063fd261bb950c3cf3c11ddda677a3b76c6586146bde7c5b0fb959',
    63:'429db01186a8b2640eff216376f4a31303dc06e6898b231d57b562ada71785b2',
    64:'6f76beb9a840dbb5f19d7ebea8d1ba7c8e636049e87f65da731a4de2e577b747',
}
GUIDE_FACE_IDS = (55,56,57,58,61,62,63,64)
# Exact three-face partition merge, independently compared with its explicit
# serialization control. This is a new packet, not a renaming of the 88-face one.
UNIFIED_DOMAIN_SHA256 = 'fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
UNIFIED_MANIFEST_SHA = '58b8be5aa0faeac678e6801cad29cfc5520cbf1590076276dbf5ad5157776aa1'
UNIFIED_MANIFEST_CONTENT_SHA = '1112d2dcfef906d57b4c75d24be0f8c524040de61e36e95974eed46603f6d5fd'
UNIFIED_GUIDE_FACE_IDS = (53,54,55,56,59,60,61,62)
UNIFIED_FACE_SHAS = {
    37:'654f0da248f3bb62c51be1c30e512abd6c2140db8493719ae495b53a2776cb88',
    53:'4d7b6a7e38c0ce98f9fe76938fadfc0bd0da5cfc141f706ba57a49dbf607943d',
    54:'4099b5d6c03d06b3af6cb3e60fb8e21ad8815de01fd5e9b1f0397e198f147ed6',
    55:'4bb47ab84f0a4f1cbab834a69c36899e70f9d5d97faa50c8d2b0a52d108fe00f',
    56:'70c8276646fd1b0866366327d0785492d1b7876ddd31e7f8983401c043c36f45',
    59:'99a890ee2816981e69e7571e3f1f11fc2565f34cf8d85a7f92342f19453e201b',
    60:'49e8af6a1e6a9397dbe3baf5a4dcd881aa099e05e7c511b2f99b1175419e40ea',
    61:'38918d22a72948c8e01fb16be5261a014c68caa3430ecca0e322962da7f4ef44',
    62:'66a710bbd6523c87f6aeca5ee21ad322b319357016fbfdf879ccdada700fd6ac',
}
UNIFIED_CONTROL_REVIEW_SHA = '7bd9c92d5ac4bafc0146cb77e55f8e95c45d041972ad235f2dce0ab84a21b897'
NATIVE_ONLY_GATES = ('single_solid','brep_valid','bop_no_faults','native_roundtrip_valid',
                     'boundary_assignment_complete','positive_intake_curtain',
                     'guide_extensions_communicate')


def content_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
                                    allow_nan=False).encode()).hexdigest()


def registered_segmented_manifest(manifest,manifest_sha=None,*,for_meshing=True):
    """Require the reviewed complete package, not caller-provided success flags."""
    pins={SEGMENTED_MANIFEST_SHA:SEGMENTED_MANIFEST_CONTENT_SHA} if for_meshing else {
        PREPARED_MANIFEST_SHA:PREPARED_MANIFEST_CONTENT_SHA,
        SEGMENTED_MANIFEST_SHA:SEGMENTED_MANIFEST_CONTENT_SHA}
    pins={key:value for key,value in pins.items() if key and value}
    if not pins:
        raise ValueError('segmented_native_profile_not_registered')
    digest=content_sha(manifest)
    matched=[key for key,value in pins.items() if digest==value and (manifest_sha is None or key==manifest_sha)]
    if (len(matched)!=1 or
            manifest.get('schema')!='m64-intake-gas-domain/v1' or
            manifest.get('exports',{}).get('domain_brep',{}).get('sha256')!=SEGMENTED_DOMAIN_SHA):
        raise ValueError('exact_reviewed_segmented_native_package_required')
    if (set(manifest['exports'])!={'domain_brep'} or
            manifest.get('gates',{}).get('step_roundtrip_valid') is not None or
            manifest.get('STEP_BOP_qualified') is not False or
            manifest.get('manufacturing_authorized') is not False):
        raise ValueError('native_only_profile_cannot_inherit_STEP_or_manufacturing_approval')
    faces=manifest.get('boundary_faces',[])
    if (len(faces)!=88 or {r['id'] for r in faces}!=set(range(1,89)) or
            {r['id']:r['sha256'] for r in faces if r['id'] in SEGMENTED_FACE_SHAS}!=SEGMENTED_FACE_SHAS or
            not isinstance(manifest.get('boundary_role_transfer'),dict)):
        raise ValueError('complete_hash_bound_segmented_face_role_transfer_required')
    if for_meshing:
        if any(manifest.get('gates',{}).get(k) is not True for k in NATIVE_ONLY_GATES):
            raise ValueError('segmented_native_gates_not_all_accepted')
        clean={'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]}
        if manifest.get('native_BOP')!=clean or manifest.get('native_roundtrip_BOP')!=clean:
            raise ValueError('segmented_native_requires_actual_clean_BOP_not_C0_waiver')
        if manifest.get('inputs_unchanged') is not True:
            raise ValueError('segmented_native_provenance_changed')
    return {'name':'gas05_C0_segmented_native_only','domain_sha256':SEGMENTED_DOMAIN_SHA,
            'manifest_sha256':matched[0],'STEP_used':False,
            'STEP_status':'not_tested_for_this_candidate','CFD_qualified':False,
            'manufacturing_authorized':False}


def segmented_face_sha(manifest,face_id):
    registered_segmented_manifest(manifest,for_meshing=False)
    return SEGMENTED_FACE_SHAS[face_id]


def registered_unified_manifest(manifest,manifest_sha=None,*,for_meshing=True):
    """Accept only the new 86-face packet; old receipts cannot approve this body."""
    if not UNIFIED_MANIFEST_SHA or not UNIFIED_MANIFEST_CONTENT_SHA:
        raise ValueError('unified_native_profile_not_registered')
    if (content_sha(manifest)!=UNIFIED_MANIFEST_CONTENT_SHA or
            (manifest_sha is not None and manifest_sha!=UNIFIED_MANIFEST_SHA) or
            manifest.get('schema')!='m64-intake-gas-domain/v1' or
            manifest.get('exports',{}).get('domain_brep',{}).get('sha256')!=UNIFIED_DOMAIN_SHA256):
        raise ValueError('exact_reviewed_unified_native_package_required')
    if (set(manifest['exports'])!={'domain_brep'} or
            manifest.get('gates',{}).get('step_roundtrip_valid') is not None or
            manifest.get('STEP_BOP_qualified') is not False or
            manifest.get('manufacturing_authorized') is not False):
        raise ValueError('native_only_profile_cannot_inherit_STEP_or_manufacturing_approval')
    faces=manifest.get('boundary_faces',[])
    if (len(faces)!=86 or {r['id'] for r in faces}!=set(range(1,87)) or
            {r['id']:r['sha256'] for r in faces if r['id'] in UNIFIED_FACE_SHAS}!=UNIFIED_FACE_SHAS or
            not set(UNIFIED_GUIDE_FACE_IDS).issubset(UNIFIED_FACE_SHAS) or
            not isinstance(manifest.get('boundary_role_transfer'),dict)):
        raise ValueError('complete_hash_bound_unified_face_role_transfer_required')
    if for_meshing:
        if any(manifest.get('gates',{}).get(k) is not True for k in NATIVE_ONLY_GATES):
            raise ValueError('unified_native_gates_not_all_accepted')
        clean={'has_faulty':False,'has_errors':False,'has_warnings':False,'faults':[]}
        if manifest.get('native_BOP')!=clean or manifest.get('native_roundtrip_BOP')!=clean:
            raise ValueError('unified_native_requires_actual_clean_BOP')
        if manifest.get('inputs_unchanged') is not True:
            raise ValueError('unified_native_provenance_changed')
    return {'name':'gas05_unified_partition_native_only','domain_sha256':UNIFIED_DOMAIN_SHA256,
            'manifest_sha256':UNIFIED_MANIFEST_SHA,'control_review_sha256':UNIFIED_CONTROL_REVIEW_SHA,
            'STEP_used':False,'STEP_status':'not_tested_for_this_candidate',
            'CFD_qualified':False,'manufacturing_authorized':False}


def guide_face_ids(domain_sha):
    if domain_sha==SEGMENTED_DOMAIN_SHA:return GUIDE_FACE_IDS
    if domain_sha==UNIFIED_DOMAIN_SHA256:return UNIFIED_GUIDE_FACE_IDS
    raise ValueError('registered_native_guide_profile_required')


def guide_face_hashes(domain_sha,frames=None):
    if domain_sha==UNIFIED_DOMAIN_SHA256:
        if (not UNIFIED_MANIFEST_SHA or not set(UNIFIED_GUIDE_FACE_IDS).issubset(UNIFIED_FACE_SHAS) or
                (frames is not None and frames.get('classified_manifest_sha256')!=UNIFIED_MANIFEST_SHA)):
            raise ValueError('unified_guide_frames_must_bind_new_manifest')
        return {i:UNIFIED_FACE_SHAS[i] for i in UNIFIED_GUIDE_FACE_IDS}
    if domain_sha!=SEGMENTED_DOMAIN_SHA:
        raise ValueError('registered_segmented_guide_profile_required')
    if frames is not None and frames.get('classified_manifest_sha256') not in {
            h for h in (PREPARED_MANIFEST_SHA,SEGMENTED_MANIFEST_SHA) if h}:
        raise ValueError('segmented_guide_frames_must_bind_current_manifest')
    return {i:SEGMENTED_FACE_SHAS[i] for i in GUIDE_FACE_IDS}
