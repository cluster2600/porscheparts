"""Strict, read-only native prism case binding; unknown repaired faces stay -1."""
import hashlib,json,math
from fractions import Fraction as Q
from pathlib import Path
import numpy as np

def _sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _need(condition,message):
    if not condition:raise ValueError(message)
def _refs(value):
    if isinstance(value,dict):
        if set(value)=={'path','sha256'}:yield value
        else:
            for item in value.values():yield from _refs(item)
    elif isinstance(value,list):
        for item in value:yield from _refs(item)
def _radical_bound(d2,e2,limit):
    margin=limit*limit-d2-e2
    return d2>=0 and e2>=0 and limit>=0 and margin>=0 and margin*margin>=4*d2*e2
def _csr(data,count,allow_empty=False):
    offsets=data['all_parent_offsets'];parents=data['all_parent_faces']
    _need(np.issubdtype(offsets.dtype,np.integer) and np.issubdtype(parents.dtype,np.integer),'CSR must be integer')
    _need(offsets.shape==(count+1,) and offsets[0]==0 and offsets[-1]==len(parents),'Invalid CSR bounds')
    _need(np.all(offsets>=0) and np.all(offsets<=len(parents)),'CSR out of range')
    _need(np.all(offsets[1:]>=offsets[:-1]) if allow_empty else np.all(offsets[1:]>offsets[:-1]),'Nonmonotone/empty CSR')
    return offsets,parents
def _same_oriented_triangles(a,b):
    _need(a.shape==b.shape,'Triangle comparison shape mismatch')
    same=np.zeros(len(a),dtype=bool)
    for shift in range(3):same|=np.all(np.roll(a,shift,axis=1)==b,axis=(1,2))
    return same
def _evidence_path(value,map_path):
    path=Path(value)
    if not path.is_absolute():
        _need('..' not in path.parts,'Relative evidence path escapes package')
        path=Path(map_path).parent/path
    return path.resolve()

class PrismNativeCase:
    def verify(self):
        public=(self.final_npz,self.original_raw_npz,self.schema_path,self.native_audit_path,self.source_index)
        _need(public==self._public_identity,'Public case identity changed')
        for path,digest in self._identities.items():_need(_sha(path)==digest,'Evidence changed: '+str(path))
        _need(hashlib.sha256(self.final_to_original_raw_face.tobytes()).hexdigest()==self._mapping_sha,'Face map changed')
        _need(json.dumps(self.boolean_audit,sort_keys=True)==self._boolean_text,'Boolean audit object changed')
        return True

def load_case(native_audit_path,evidence_map_path=None):
    """Return paths/boolean_audit/final_to_original_raw_face and verify().

    The map is a positive geometric-parent lookup only: -1 means unknown,
    irrespective of any historical producer/search-hint indices.
    """
    case=PrismNativeCase();audit_path=Path(native_audit_path).resolve();audit=json.loads(audit_path.read_text())
    _need(audit['schema']=='prism-envelope-native-audit-v2' and audit['geometry_pass'] is True,'Unaccepted native case')
    _need(audit['process_anchor_admission'] is False,'Native case cannot authorize anchors')
    map_path=Path(evidence_map_path).resolve() if evidence_map_path else audit_path.parent/'local-evidence-map.json'
    mapping=json.loads(map_path.read_text()) if map_path.exists() else None
    if mapping:_need(mapping['native_audit_sha256']==_sha(audit_path),'Evidence map belongs to another audit')
    identities={audit_path:_sha(audit_path),Path(__file__).resolve():_sha(__file__)}
    if mapping:identities[map_path]=_sha(map_path)
    def resolve(ref):
        if mapping:
            row=mapping['files'].get(ref['path']);_need(row is not None and row['sha256']==ref['sha256'],'Missing/mismatched local reference')
            path=_evidence_path(row['path'],map_path)
        else:path=Path(ref['path']).resolve()
        _need(path.is_file() and not path.is_symlink() and _sha(path)==ref['sha256'],'Reference SHA mismatch: '+str(path))
        identities[path]=ref['sha256'];return path
    for ref in _refs(audit):resolve(ref)
    receipts=audit['receipts'];repair='local_repair_npz' in audit
    def receipt(name):return json.loads(resolve(receipts[name]).read_text())
    prefix='original_native' if repair else 'boolean'
    original=receipt(prefix+'_audit');native=receipt(prefix+'_native');execution=receipt(prefix+'_execution-receipt')
    _need(execution['status']=='executed' and execution['returncode']==0 and execution['identities_unchanged'] and execution['owned_scope_inactive'],'Original execution incomplete')
    _need(original['native_exact_gate_pass'] and original['native']==native,'Original exact native gate failed')
    _need(original['exact_result_sha256']==audit['original_exact_mesh']['sha256'],'Original exact mesh receipt mismatch')
    original_outputs=execution.get('output_files_sha256')
    if original_outputs is not None:
        for name,ref in [('result.npz',audit['original_raw_npz']),('result.mesh64.exact',audit['original_exact_mesh']),('native.json',receipts[prefix+'_native']),('audit.json',receipts[prefix+'_audit'])]:
            _need(original_outputs.get(name)==ref['sha256'],'Original execution output SHA mismatch')
    else:
        _need(execution['unadmitted_checkpoint_complete'],'Missing original exact checkpoint')
        exact_hashes=[v for k,v in execution['unadmitted_geometry_checkpoint_files_sha256'].items() if k.endswith('.exact')]
        _need(exact_hashes==[audit['original_exact_mesh']['sha256']],'Original checkpoint/final exact mesh mismatch')
    _need(native['exact_output_self_intersection_free'] and native['exact_collinear_output_triangles']==0 and native['source_face_lineage_complete'],'Original geometry/parents failed')
    snap_prefix='final_snap' if repair else 'snap';snap=receipt(snap_prefix+'_audit');sn=receipt(snap_prefix+'_native');se=receipt(snap_prefix+'_execution-receipt')
    _need(se['identities_unchanged'] and se['owned_scope_inactive'],'Final execution identity/scope failed')
    _need(se['status']=='executed' or se['status']=='rejected_or_failed' and se['returncode']==2 and snap['drift_gate_pass'] is False,'Unexpected final execution refusal')
    _need(snap['native_gate_pass'] and snap['topology_gate_pass'] and snap['native']==sn,'Final native/topology gate failed')
    _need(sn['native_return'] and sn['post_double_self_intersection_free'] and sn['exact_collinear_output_triangles']==0 and sn['all_output_coordinates_exactly_double'],'Final native defect')
    _need(sn['snap_grid_bits']==51 and sn['iteration_budget']==5,'Changed snap precision/budget')
    topology=snap['output_topology'];_need(topology['pass'] and topology['signed_volume_mm3']>0,'Invalid final volume/topology')
    for key in ['boundary_edges','nonmanifold_edges','nonmanifold_vertices','unused_vertices','inconsistent_orientation_edges']:_need(topology[key]==0,'Final topology defect')
    case.final_npz=resolve(audit['final_npz']);case.original_raw_npz=resolve(audit['original_raw_npz']);case.schema_path=resolve(audit['raw_geometric_parent_CSR']['schema'])
    _need(original['result_sha256']==audit['original_raw_npz']['sha256'] and snap['result_sha256']==audit['final_npz']['sha256'],'Mesh receipt mismatch')
    raw=np.load(case.original_raw_npz,allow_pickle=False);final=np.load(case.final_npz,allow_pickle=False);offsets,parents=_csr(raw,len(raw['faces']))
    counts=original['leaf_face_counts'];_need(original['leaf_role_order']==['positive_roof_prisms','mask','part','clip_bbox'],'Wrong prism roles')
    _need(np.all(parents>=0) and np.all(parents<sum(counts)-12),'Invalid/bbox parent on final boundary')
    lookup=final['autorefine_input_face'];_need(lookup.dtype==np.int64 and lookup.shape==(len(final['faces']),),'Invalid final producer map')
    if repair:
        patch=np.load(resolve(audit['local_repair_npz']),allow_pickle=False);_need(snap['input_sha256']==audit['local_repair_npz']['sha256'],'Wrong repair input')
        _need(lookup.min()>=0 and lookup.max()<len(patch['faces']),'Repair producer index out of range')
        positive_offsets,positive_parents=_csr(patch,len(patch['faces']),allow_empty=True)
        first=np.load(resolve(audit['repair_input_snap_npz']),allow_pickle=False)
        first_audit=receipt('repair_input_snap_audit');first_native=receipt('repair_input_snap_native');first_execution=receipt('repair_input_snap_execution-receipt')
        _need(first_execution['identities_unchanged'] and first_execution['owned_scope_inactive'],'First snap execution changed')
        _need(first_audit['native_gate_pass'] and first_audit['native']==first_native,'First snap native evidence mismatch')
        _need(first_audit['input_sha256']==audit['original_raw_npz']['sha256'] and first_audit['result_sha256']==audit['repair_input_snap_npz']['sha256'],'First snap mesh binding mismatch')
        patch_input=patch['repair_input_face'];first_map=first['autorefine_input_face']
        _need(patch_input.dtype==np.int64 and patch_input.shape==(len(patch['faces']),) and patch_input.min()>=0 and patch_input.max()<len(first['faces']),'Invalid repair-to-first-snap map')
        _need(first_map.dtype==np.int64 and first_map.min()>=0 and first_map.max()<len(raw['faces']),'Invalid first-snap-to-raw map')
        _need(np.array_equal(patch['historical_snap_input_face'],first_map[patch_input]),'Historical pullback mismatch')
        actual_changed=~_same_oriented_triangles(patch['vertices'][patch['faces']],first['vertices'][first['faces'][patch_input]])
        _need(np.array_equal(actual_changed,patch['repair_changed_face']),'Unmarked geometric repair')
        _need(_same_oriented_triangles(final['vertices'][final['faces']],patch['vertices'][patch['faces'][lookup]]).all(),'Final native check changed a repaired triangle')
        raw_map=patch['historical_snap_input_face'][lookup].copy();unknown=patch['repair_changed_face'][lookup]
        _need(unknown.dtype==np.bool_,'Changed-face mask is not boolean')
        _need(np.flatnonzero(unknown).tolist()==audit['modified_final_face_ids'],'Changed-face IDs mismatch')
        _need(int(unknown.sum())==audit['modified_faces_without_positive_parent_proof']==9,'Expected nine unknown repaired faces')
        for key in ['source','source_face']:
            _need(np.array_equal(final[key],patch[key][lookup]),'Final repair attributes changed')
            _need(np.all(final[key][unknown]==-1),'Unknown repaired face promoted to a parent')
        for patch_row,is_unknown in zip(lookup,unknown):
            row=positive_parents[int(positive_offsets[patch_row]):int(positive_offsets[patch_row+1])]
            if is_unknown:_need(len(row)==0,'Changed repaired face has positive CSR parents')
        # Historical rows remain available separately; they never override -1.
        raw_map[unknown]=-1
    else:
        _need(snap['input_sha256']==audit['original_raw_npz']['sha256'],'Wrong original input')
        raw_map=lookup.copy();unknown=np.zeros(len(lookup),dtype=bool)
        _need(audit['modified_faces_without_positive_parent_proof']==0,'Unexpected unknown count')
    snap_input=patch if repair else raw
    maxima=np.max(np.abs(snap_input['vertices']),axis=0)
    expected_steps=[math.ldexp(1.0,math.frexp(float(x))[1]+1-51) if x else 0.0 for x in maxima]
    _need(sn['maximum_absolute_coordinates_mm']==maxima.tolist() and sn['grid_step_mm']==expected_steps,'Native snap grid differs from actual input domain')
    expected_bound=5*math.sqrt(sum(x*x for x in expected_steps))/2
    _need(sn['cumulative_rounding_budget_mm']==expected_bound==audit['frozen_bound_mm'],'Bound differs from actual native5delta')
    frozen_plan=receipt('frozen_repair_plan' if repair else 'frozen_plan')
    plan_bound=frozen_plan['frozen_shape_drift_limit_mm'] if repair else frozen_plan['downstream_frozen']['original_shape_drift_limit_mm']
    _need(plan_bound==expected_bound,'Plan and native5delta differ')
    if repair:_need(first_native['cumulative_rounding_budget_mm']==expected_bound,'Original first-snap bound differs')
    known=~unknown;_need(np.all(raw_map[known]>=0) and np.all(raw_map[known]<len(raw['faces'])),'Raw map out of range')
    for key in ['source','source_face']:_need(np.array_equal(final[key][known],raw[key][raw_map[known]]),'Known raw-parent lookup mismatch')
    distance_prefix='direct_distance' if repair else 'distance';distance=receipt(distance_prefix+'_audit');de=receipt(distance_prefix+'_execution-receipt')
    _need(de['status']=='executed' and de['returncode']==0 and de['identities_unchanged'] and de['owned_scope_inactive'],'Distance execution incomplete')
    _need(distance['pass'] and distance['native_geometry_gate_pass'] and distance['topology_gate_pass'],'Exact distance gate failed')
    _need(distance['input_sha256']==audit['original_raw_npz']['sha256'] and distance['result_sha256']==audit['final_npz']['sha256'],'Distance meshes mismatch')
    for key,name in [('origin_native_sha256','native'),('origin_audit_sha256','audit'),('origin_execution_receipt_sha256','execution-receipt')]:_need(distance[key]==receipts[snap_prefix+'_'+name]['sha256'],'Distance origin mismatch')
    composed=receipt('composed_drift');limit=Q.from_float(audit['frozen_bound_mm']);e2=Q(native['maximum_coordinate_rounding_squared_mm2_exact'])
    _need(composed['pass'] and composed['identities_unchanged'] and composed['original_shape_drift_limit_mm']==audit['frozen_bound_mm']==distance['shape_drift_limit_mm'],'Composed bound mismatch')
    _need(Q(composed['conversion']['maximum_distance_squared_exact'])==e2,'Conversion bound mismatch')
    linked=[audit['original_raw_npz'],audit['original_exact_mesh'],audit['final_npz'],receipts[prefix+'_native'],receipts[prefix+'_audit'],receipts[distance_prefix+'_audit']]
    for ref in linked:_need(composed['inputs_sha256'].get(ref['path'])==ref['sha256'],'Composed receipt is not bound to these inputs')
    for direction,count in [('input_to_output',len(raw['vertices'])+len(raw['faces'])),('output_to_input',len(final['vertices'])+len(final['faces']))]:
        metric=distance['exact_distance'][direction];d2=Q(metric['maximum_distance_squared_exact']);cm=composed['directions'][direction]
        _need(metric['pass'] and metric['samples']==count and cm['finite_samples']==count,'Wrong finite sampling domain')
        _need(Q(cm['distance_witness_upper_bound_squared_exact'])==d2 and Q(cm['conversion_upper_bound_squared_exact'])==e2 and cm['pass'] and _radical_bound(d2,e2,limit),'Composed exact radical inequality failed')
    contact=receipt('contacts');_need(contact['mesh_npz_sha256']==audit['final_npz']['sha256'] and contact['raw_pairs_npz_sha256']==receipts['pairs']['sha256'] and contact['remaining_pair_count']==0,'Unadjudicated final contacts')
    case.boolean_audit=original;case.final_to_original_raw_face=raw_map;raw_map.setflags(write=False)
    case._mapping_sha=hashlib.sha256(raw_map.tobytes()).hexdigest();case._boolean_text=json.dumps(original,sort_keys=True);case._identities=identities
    case.native_audit_path=audit_path;case.source_index=audit['source_index']
    case._public_identity=(case.final_npz,case.original_raw_npz,case.schema_path,case.native_audit_path,case.source_index)
    case.verify();return case
