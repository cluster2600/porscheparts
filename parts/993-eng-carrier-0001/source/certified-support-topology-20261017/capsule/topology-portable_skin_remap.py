"""Portable private callback: reproduce 92f5 first, then certified SKIN rows only.

No audit predicate is changed. The original loader still compares every XYZ
triangle with np.array_equal. This hook is not a support or exposure admission.
"""
from copy import deepcopy
from fractions import Fraction as Q
import hashlib
import inspect
import json
from pathlib import Path
import struct

ORIGINAL_REMAP_SHA='92f5dbf81fa868e29d13769094e66ae234a4ce09103fb8d2d234ad9c898fb5d7'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def rows_sha(rows):
    if any(len(row)!=3 or any(type(i) is not int or i<0 for i in row) for row in rows):
        raise ValueError('Local remap faces require three nonnegative integer IDs')
    return hashlib.sha256(b''.join(struct.pack('<qqq',*row) for row in rows)).hexdigest()


def patch_rows(rows,entry):
    """Pure local topology patch; full old/new int64 array identities are gates."""
    if len(rows)!=entry['faces'] or rows_sha(rows)!=entry['original_local_faces_sha256']:
        raise ValueError('The original remap face array is not the retained source array')
    result=deepcopy(rows);seen=set()
    for change in entry['changes']:
        i=change['local_face_id']
        if type(i) is not int or i in seen or not 0<=i<len(result) or result[i]!=change['original_local_triangle']:
            raise ValueError('A native SKIN row does not bind its exact original face')
        row=change['native_local_triangle']
        if len(row)!=3 or len(set(row))!=3 or any(type(v) is not int or not 0<=v<entry['vertices'] for v in row):
            raise ValueError('A selected native local triangle is invalid')
        result[i]=row[:];seen.add(i)
    actual=[i for i,(a,b) in enumerate(zip(rows,result)) if a!=b]
    if sorted(seen)!=entry['changed_local_face_ids'] or actual!=entry['changed_local_face_ids']:
        raise ValueError('Changed local SKIN rows differ from the certified list')
    if rows_sha(result)!=entry['candidate_local_faces_sha256']:
        raise ValueError('The whole remapped topology differs from the certified candidate')
    return result


def read_index(root,index_path,expected_sha256):
    """Only flat content-pinned local files are executable dependencies."""
    root=Path(root).absolute();index_path=Path(index_path).absolute()
    if index_path.parent!=root or any(p.is_symlink()for p in [index_path,*index_path.parents])or sha(index_path)!=expected_sha256:
        raise ValueError('The pinned portable remap index differs')
    index=json.loads(index_path.read_text())
    if (index.get('schema')!='portable-certified-SKIN-remap-index-1'or index.get('hook_source_sha256')!=sha(__file__)or
            index.get('global_admission')is not False):
        raise ValueError('The portable remap authority differs')
    def file(name):
        if not isinstance(name,str)or Path(name).name!=name or not name.startswith('topology-')or '\\'in name:
            raise ValueError('Only flat topology-* remap inputs are allowed')
        if name not in index['inputs_sha256']:raise ValueError('A portable remap input is not bound')
        return root/name
    def verify():
        if sha(index_path)!=expected_sha256 or any(p.is_symlink()for p in [root,*root.parents]):
            raise ValueError('The portable remap index or directory changed')
        for name,digest in index['inputs_sha256'].items():
            p=file(name)
            if p.is_symlink()or not p.is_file()or sha(p)!=digest:raise ValueError('A portable remap input changed')
    verify();cases=[];sources=set()
    for descriptor in index['cases']:
        case=json.loads(file(descriptor['bundle']).read_text());source=case['source_index']
        if type(source)is not int or source not in (3,9,10)or source in sources or index['inputs_sha256'][descriptor['bundle']]!=descriptor['sha256']:
            raise ValueError('Duplicate or foreign portable remap source')
        if (case.get('schema')!='portable-certified-SKIN-remap-case-1'or case.get('hook_source_sha256')!=sha(__file__)or
                case.get('global_admission')is not False):
            raise ValueError('Unknown portable remap case authority')
        for role in ('original_npz','candidate_npz','candidate_receipt','trace_npz','trace_receipt','parent_checkpoint','trace_producer'):
            file(case[role])
        if any(index['inputs_sha256'].get(name)!=digest for name,digest in case['inputs_sha256'].items()):
            raise ValueError('Case-local remap identities differ from the index')
        sources.add(source);cases.append(case)
    if sources!={3,9,10}:raise ValueError('Exactly the three real certified sources are required')
    return index,cases,file,verify


def make_remap(root,index_path,original_remap,*,expected_sha256):
    """Apply no operation until the authentic original arrays/receipt reproduce."""
    index,cases,file,verify_files=read_index(root,index_path,expected_sha256)
    def verify_inputs():
        verify_files();source=Path(inspect.getsourcefile(original_remap))
        if source.name!='peripheral_skins.py'or sha(source)!=ORIGINAL_REMAP_SHA:
            raise ValueError('The callback is not the original pinned 92f5 remap')
    verify_inputs()
    import numpy as np
    import trimesh
    def array_identity(array):
        array=np.ascontiguousarray(array)
        return dict(dtype=array.dtype.str,shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest())
    def arrays(name):
        with np.load(file(name),allow_pickle=False)as data:return {n:data[n].copy()for n in data.files}
    entries={}
    for case in cases:
        trace=json.loads(file(case['trace_receipt']).read_text());candidate=json.loads(file(case['candidate_receipt']).read_text())
        parent=json.loads(file(case['parent_checkpoint']).read_text())
        if (candidate.get('status')!='certified_local_flip_candidate_no_global_admission'or candidate.get('global_admission')is not False or
                candidate.get('inputs_unchanged')is not True or
                candidate['output_npz_sha256']!=case['candidate_npz_sha256']or
                sha(file(case['candidate_receipt']))!=case['candidate_receipt_sha256']or
                type(case['initial_collapsed_cuts'])is not int or case['initial_collapsed_cuts']<=0 or
                candidate['proof']['initial_collapsed_cuts']!=case['initial_collapsed_cuts']or candidate['proof']['final_collapsed_cuts']!=0 or
                candidate['inputs_sha256_before']!=candidate['inputs_sha256_after']or
                parent.get('status')!='region_geometry_completed_no_global_admission'or parent.get('runtime_unchanged')is not True or
                parent['runtime_before']!=parent['runtime_after']or
                parent['source_index']!=case['source_index']or parent['files_sha256']['support.npz']!=sha(file(case['original_npz']))or
                trace.get('status')!='original_skin_parameter_trace_verified_no_repair'or
                trace['source_sha256']!=sha(file(case['trace_producer']))or
                trace['source_index']!=case['source_index']or trace['original_surface_sha256']!=sha(file(case['original_npz']))or
                trace['base_surface_sha256']!=case['trace_base_surface_sha256']or
                trace['base_surface_sha256']not in trace['files_sha256_before'].values()or
                trace['base_surface_sha256']not in candidate['inputs_sha256_before'].values()or
                trace['metadata_sha256']!=parent['files_sha256']['geometry-assessment.json']or
                trace['trace_npz_sha256']!=sha(file(case['trace_npz']))or trace['files_sha256_before']!=trace['files_sha256_after']or
                trace['runtime_before_sha256']!=canonical(parent['runtime_before'])or trace['runtime_after_sha256']!=canonical(parent['runtime_after'])or
                candidate['runtime_before_sha256']!=trace['runtime_before_sha256']or candidate['runtime_after_sha256']!=trace['runtime_after_sha256']):
            raise ValueError('A real original, trace or candidate binding differs')
        rows={r['owner']:r for r in trace['rows']}
        if len(rows)!=len(trace['rows'])or {e['owner']for e in case['entries']}!=set(rows)or len(case['entries'])!=len(rows):
            raise ValueError('Every actual traced SKIN chart must have one unique remap entry')
        original,selected=arrays(case['original_npz']),arrays(case['candidate_npz'])
        if set(original)!=set(selected)or set(original)!={'vertices','faces','order','type'}:raise ValueError('Unexpected original/candidate arrays')
        for name in original:
            if (array_identity(original[name])!=candidate['original_arrays'][name]or array_identity(selected[name])!=candidate['candidate_arrays'][name]or
                    name!='faces'and array_identity(original[name])!=array_identity(selected[name])):
                raise ValueError('The bound actual candidate arrays differ')
        for entry in case['entries']:
            row=rows[entry['owner']]
            if (row['whole_material_sha256']!=entry['whole_material_wkb_sha256']or hashlib.sha256(bytes.fromhex(row['whole_material_wkb_hex'])).hexdigest()!=entry['whole_material_wkb_sha256']or
                    array_identity(np.asarray(row['mapping_t_xy_mm'],dtype=np.float64))!=entry['mapping_identity']or
                    canonical(row['remapping_receipt'])!=entry['original_remapping_receipt_sha256']or
                    row['global_face_range']!=entry['global_face_range']or row['global_vertex_offset']!=entry['global_vertex_offset']):
                raise ValueError('The actual whole material, mapping or historical remap differs')
            lo,hi=row['global_face_range'];offset=row['global_vertex_offset'];n=row['trace_proof']['vertices']
            source_vertices=original['vertices'][offset:offset+n];source_faces=original['faces'][lo:hi]-offset;target_faces=selected['faces'][lo:hi]-offset
            if (array_identity(source_vertices)!=entry['original_vertices_identity']or array_identity(source_faces)!=entry['original_local_faces_identity']or
                    array_identity(target_faces)!=entry['candidate_local_faces_identity']or source_faces.shape!=target_faces.shape or
                    entry['vertices']!=n or entry['faces']!=hi-lo or
                    not np.array_equal(np.asarray(patch_rows(source_faces.tolist(),entry),dtype=source_faces.dtype),target_faces)):
                raise ValueError('A local patch does not derive from the actual original/candidate arrays')
            key=(entry['whole_material_wkb_sha256'],entry['mapping_identity']['sha256'])
            if key in entries:raise ValueError('Ambiguous cross-case material/mapping remap target')
            entries[key]=(entry,row,case)
    calls=[]
    def remap(material,mapping):
        verify_inputs();material_sha=hashlib.sha256(material.wkb).hexdigest();mapping_id=array_identity(mapping)
        target=entries.get((material_sha,mapping_id['sha256']))
        if target is None:return original_remap(material,mapping)
        entry,row,case=target
        if mapping_id!=entry['mapping_identity']:raise ValueError('The exact target mapping shape/type differs')
        mesh,historical=original_remap(material,mapping)
        if historical!=row['remapping_receipt']or array_identity(mesh.vertices)!=entry['original_vertices_identity']or array_identity(mesh.faces)!=entry['original_local_faces_identity']:
            raise ValueError('Original remap did not reproduce the actual arrays and receipt')
        faces=patch_rows(mesh.faces.tolist(),entry)
        rebuilt=trimesh.Trimesh(mesh.vertices.copy(),np.asarray(faces,dtype=mesh.faces.dtype),process=False)
        if array_identity(rebuilt.vertices)!=entry['original_vertices_identity']or array_identity(rebuilt.faces)!=entry['candidate_local_faces_identity']:
            raise ValueError('The remap result differs from the exact certified arrays')
        bound=Q(row['trace_proof']['maximum_exact_mapping_error_squared_mm2'])
        if bound<0 or row['trace_proof']['every_actual_error_within_unchanged_original_gamma8_bound']is not True:
            raise ValueError('The unchanged original gamma8 bound is not certified')
        supplement=dict(schema='portable-certified-SKIN-native-topology-remap-1',source_index=case['source_index'],owner=entry['owner'],
            hook_source_sha256=sha(__file__),index_sha256=expected_sha256,candidate_npz_sha256=case['candidate_npz_sha256'],
            candidate_receipt_sha256=case['candidate_receipt_sha256'],historical_remapping_receipt_sha256=canonical(historical),historical_measurements_retained=True,
            current_original_surface_area_mm2=float(mesh.area),current_candidate_surface_area_mm2=float(rebuilt.area),areas_are_float_diagnostics_only=True,
            original_local_faces_identity=array_identity(mesh.faces),candidate_local_faces_identity=array_identity(rebuilt.faces),vertices_byte_identical=True,
            changed_local_face_ids=entry['changed_local_face_ids'],only_native_SKIN_rows_changed=True,same_closed_TZ_point_set=True,
            same_closed_3D_point_set_claimed=False,maximum_original_vertex_error_squared_fraction_mm2=str(bound),
            old_new_Euclidean_squared_upper_fraction_mm2=str(4*bound),graph_or_exposure_or_global_admission=False)
        receipt=deepcopy(historical);receipt['certified_topology_supplement']=supplement
        verify_inputs();calls.append(deepcopy(supplement));return rebuilt,receipt
    remap.supplement_receipts=calls;remap.bundle_sha256=expected_sha256
    return remap


