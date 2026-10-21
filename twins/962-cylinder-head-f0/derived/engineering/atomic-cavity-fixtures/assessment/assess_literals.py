"""Pure retained-output checks for the three frozen atomic literal references."""
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT/'work/962-engineering/atomic-cavity-fixtures-prep-001'
PINS = {'prepare.py':'89a2af8ee73d0fc6ca78253dac6f72cc70251462e3e032d3bd88c25167a33d38',
        'expectations.json':'2a6993b704a007da882fa8d48bbe9aa6c04a42831b520e77d7e3dd26246baa1e',
        'fixture-freeze.json':'9584ca30708a08f738ce909bd479d3fdc52fb6581d4e3afbb630477ecbbd4ca2'}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_arithmetic():
    assert all(sha(PREP/n)==h for n,h in PINS.items())
    spec=importlib.util.spec_from_file_location('immutable_atomic_literal_arithmetic',PREP/'prepare.py')
    module=importlib.util.module_from_spec(spec)
    old=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:spec.loader.exec_module(module)
    finally:sys.dont_write_bytecode=old
    return module


def read(path):
    raw=path.read_bytes();assert raw[:8]==b'962SURF1'
    nv,nf=struct.unpack_from('<QQ',raw,8);assert 0<nv<=12 and 0<nf<=20 and len(raw)==24+24*(nv+nf)
    points=[list(v) for v in struct.iter_unpack('<ddd',raw[24:24+24*nv])]
    faces=[list(v) for v in struct.iter_unpack('<QQQ',raw[24+24*nv:])]
    assert all(math.isfinite(x) for p in points for x in p)
    return raw[24:24+24*nv],points,faces


def canonical(t):
    t=tuple(t);return min(t,t[1:]+t[:1],t[2:]+t[:2])


def boundary(faces):
    result=Counter()
    for t in faces:
        for a,b in zip(t,t[1:]+t[:1]):result[tuple(sorted((a,b)))]+=1 if a<b else -1
    return {e:n for e,n in result.items() if n}


def assess_case(name, directory):
    """Read completed files only; the caller separately audits actual execution/closure."""
    arithmetic=load_arithmetic();case=next(x for x in json.loads((PREP/'expectations.json').read_text())['cases'] if x['name']==name)
    directory=Path(directory);assert directory.is_dir() and not directory.is_symlink()
    report_path=directory/'report.json';report=json.loads(report_path.read_text(),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
    assert report['head_or_solver_admitted'] is report['manufacturing_authorized'] is False
    assert report['historical_SMS_veto_identified'] is False and report['independent_distance_intersection_features_pending'] is True
    if name=='all-fixed':
        assert {p.name for p in directory.iterdir()}=={'report.json'}
        assert report['status']=='rejected_no_candidate' and report['stage']=='input_association'
        assert report['reason']=='Mapped component touches original fixed vertex'
        assert report['candidate_built'] is False and report['quality_checked'] is False and report['minimum_quality'] is None
        assert report['exported'] is False and report['candidate_file'] is report['origins_file'] is None
        assert report['input_vertices']==10 and report['input_faces']==16 and report['fixed_source_vertices']==10 and report['original_reference_faces']==12
        assert report['groups']==1 and report['guards']['inputs'] is False
        return {'case':name,'expected_native_returncode':3,'report_sha256':sha(report_path),'report_only_refusal':True,'candidate_credited':False}
    assert {p.name for p in directory.iterdir()}=={'report.json','candidate.bin','vertex-coordinate-origins.u64'}
    assert report['status']=='local_candidate_only' and report['stage']=='complete'
    assert report['candidate_built'] is report['quality_checked'] is report['exported'] is True
    assert all(type(x) is bool and x is True for x in report['guards'].values()) and len(report['guards'])==9
    raw_points,points,faces=read(directory/'candidate.bin')
    assert raw_points==b''.join(struct.pack('<ddd',*p) for p in case['expected_points'])
    assert [canonical(t) for t in faces]==[canonical(t) for t in case['expected_oriented_faces']]
    origins_raw=(directory/'vertex-coordinate-origins.u64').read_bytes()
    assert origins_raw==b''.join(struct.pack('<Q',v) for v in case['expected_origins'])
    origins=list(case['expected_origins']);geometry=arithmetic.geometry(points,faces);topology=arithmetic.topology(points,faces,True)
    assert geometry==case['expected_after'] and topology==case['expected_after_topology']
    assert report['bad_faces']==geometry['poor_faces']==0 and report['minimum_quality']==geometry['minimum_triangle_SICN']
    assert report['candidate_vertices']==len(points) and report['candidate_faces']==len(faces)
    assert report['dropped_faces']==case['expected_removed_faces'] and report['affected_survivors']==4
    assert report['fixed_source_vertices']==report['fixed_retained']==8 and report['original_reference_faces']==len(case['actual_source_policy_mask']['original_patch_face_rows'])
    assert report['before_components']==report['after_components']==1 and report['before_Euler']==report['after_Euler']==2
    assert report['final_affected_neighbor_pairs']==8 and all(report[k]==0 for k in ['normal_failures','duplicates','envelope_failures','area_ratio_failures','dihedral_failures'])
    original=case['input_points'];original_faces=case['input_oriented_faces'];mask=case['actual_source_policy_mask'];candidate_orig_faces=[[origins[v] for v in t] for t in faces]
    lookup={origin:i for i,origin in enumerate(origins)}
    for origin in mask['fixed_original_IDs']:
        assert struct.pack('<ddd',*points[lookup[origin]])==struct.pack('<ddd',*original[origin])
    exterior=[t for i,t in enumerate(original_faces) if i not in mask['original_patch_face_rows']]
    keys=Counter(canonical(t) for t in candidate_orig_faces)
    assert all(keys[canonical(t)]==1 for t in exterior)
    group=set(case['group_current_IDs']);before=[t for t in original_faces if group.intersection(t)]
    after=[t for t in candidate_orig_faces if 8 in t]
    assert boundary(before)==boundary(after)
    assert all(sha(PREP/n)==h for n,h in PINS.items())
    return {'case':name,'expected_native_returncode':0,'report_sha256':sha(report_path),'candidate_sha256':sha(directory/'candidate.bin'),'origins_sha256':sha(directory/'vertex-coordinate-origins.u64'),'all_coordinate_bytes_and_ordered_oriented_faces_match':True,'all_origin_bytes_match':True,'full_quality_exact_reference_match':True,'minimum_triangle_SICN':geometry['minimum_triangle_SICN'],'exact_signed_volume_mm3':geometry['signed_volume_mm3'],'topology':topology,'fixed_exterior_affected_boundary_exact':True,'native_final_affected_neighbor_pairs':8,'candidate_local_scope_only':True,'head_or_solver_admission':False}
