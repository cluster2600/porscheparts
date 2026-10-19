"""Read retained arrays/receipts only; no geometry construction or admission replay."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
SKINS = ROOT/'parts/993-eng-carrier-0001/source/process-skins-20261016'
AUDIT = SKINS.parent/'process-scanpath-audit-20261016'
DESIGN = SKINS.parent/'design-20261016'
STORE = ROOT/'work/carrier-process-20261016/sealed-envelopes-v2-001'
STORE_SHA = '63391aa2b74094887155346841db493f57c0eb0a0b8d8998c4c748c95bf13ec4'
CHECKPOINTS = {3:'f968a52e955fd621bc457d0c615d6d9039bb5dcc43cb242342308a5a4713cb74',
              9:'c8cb26890e206dbdba7950c5ddc4ab98eadb5c1cc99baa9c01d87b178a4c5464',
              10:'de3b6bf7be05e5caebd97cf4b82c14be242f888b272368f0e9cf60ae3439f4d1'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(a):
    a = np.ascontiguousarray(a)
    return dict(dtype=a.dtype.str, shape=list(a.shape), sha256=hashlib.sha256(a.tobytes()).hexdigest())


def pointer(value, name):
    for key in name.strip('/').split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def source_path(name):
    for base in [SKINS, AUDIT, DESIGN]:
        path = base/name
        if path.is_file():
            return path
    raise FileNotFoundError(name)


frozen = {Path(__file__):sha(__file__), STORE/'envelopes.json':STORE_SHA}
assert sha(STORE/'envelopes.json') == STORE_SHA
store = json.loads((STORE/'envelopes.json').read_text())
assert store['status'] == 'passed' and store['input_sha256'] == '443b5ae20f7f1b2fd19a210aa5347890086523bc66749dfc95fa3560b85e9a6e'
frozen.update({STORE/name:h for name,h in store['files_sha256'].items()})
assert all(sha(path)==h for path,h in frozen.items())
sys.path.insert(0, str(SKINS))
from region_checkpoints import runtime_identity
runtime_before = runtime_identity()
rows = []
parameters = calendar = None
for index, expected in CHECKPOINTS.items():
    directory = ROOT/f'work/carrier-process-20261016/real-support-v5-regions-001/source-{index:03d}'
    cp = directory/'region-checkpoint.json'
    assert sha(cp) == expected
    checkpoint = json.loads(cp.read_text())
    assert checkpoint['schema'] == 'support-region-checkpoint-1'
    assert checkpoint['status'] == 'region_geometry_completed_no_global_admission' and checkpoint['source_index'] == index
    assert checkpoint['runtime_unchanged'] and checkpoint['runtime_before'] == checkpoint['runtime_after'] == runtime_before
    frozen[cp] = expected
    assert set(checkpoint['files_sha256']) == {'support.npz','geometry-assessment.json','material-connections.json'}
    frozen.update({directory/name:h for name,h in checkpoint['files_sha256'].items()})
    for name,h in {**checkpoint['source_sha256'], **checkpoint['additional_source_sha256']}.items():
        frozen[source_path(name)] = h
    assert all(sha(path)==h for path,h in frozen.items())
    terminal_path = directory/'assessment.json'
    frozen[terminal_path] = sha(terminal_path)
    terminal = json.loads(terminal_path.read_text())
    metadata = json.loads((directory/'geometry-assessment.json').read_text())
    graph = json.loads((directory/'material-connections.json').read_text())
    for key in metadata:
        assert terminal[key] == metadata[key], (index, key)
    assert terminal['source_index'] == index and terminal['runtime_unchanged']
    assert terminal['runtime_before'] == terminal['runtime_after'] == runtime_before
    assert terminal['sources_and_inputs_unchanged'] and terminal['original_source_files_unchanged']
    assert terminal['region_checkpoint']['receipt_sha256'] == expected
    assert terminal['region_checkpoint']['status'] == checkpoint['status']
    assert terminal['material_connections']['status'] == graph['status'] == 'passed'
    assert terminal['material_connections']['receipt_sha256'] == checkpoint['files_sha256']['material-connections.json']
    for key in ['source_sha256','input_sha256','frozen_snapshot_sha256']:
        frozen.update({Path(path):h for path,h in terminal[key].items()})
    assert metadata['surface_sha256'] == checkpoint['files_sha256']['support.npz']
    with np.load(directory/'support.npz', allow_pickle=False) as data:
        assert set(data.files) == {'vertices','faces','order','type'}
        vertices, faces, orders, types = [data[name] for name in ['vertices','faces','order','type']]
    assert vertices.dtype == np.float64 and faces.dtype == np.int64
    assert vertices.shape == (metadata['vertices'],3) and faces.shape == (metadata['faces'],3)
    assert np.isfinite(vertices).all() and faces.min() >= 0 and faces.max() < len(vertices)
    # CORE preserves the producer's float64 face attributes. Check their exact
    # integral values without changing their stored dtype or any coordinate.
    assert orders.shape == types.shape == (len(faces),)
    assert orders.dtype == types.dtype == np.float64
    assert all(np.isfinite(a).all() and np.array_equal(a, np.floor(a)) for a in [orders, types])
    material_sha = hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest()
    assert graph['input_geometry_sha256'] == material_sha and graph['faces'] == len(faces)
    groups = metadata['peripheral_skin']['support_surface_face_groups']
    ids = [g['id'] for g in groups]
    assert len(ids) == len(set(ids)) == graph['groups']
    end = 0
    for g in groups:
        first,last = g['face_range']
        assert first == end and first < last <= len(faces)
        assert np.all(orders[first:last] == g['order']) and np.all(types[first:last] == g['type'])
        end = last
        contact = pointer(metadata, g['contact_reference'])
        assert contact['kind'] == 'generated_material_component'
        for key in ['component_geometry_sha256','component_geometry_wkb_hex','free_domain_geometry_sha256',
                    'free_domain_geometry_wkb_hex','contact_clip_scope','upper_contact_traces_2d_mm',
                    'lower_contact_traces_2d_mm','upper_interface_traces_2d_mm','lower_interface_traces_2d_mm']:
            assert contact[key] == g[key], (index,g['id'],key)
        for stem in ['component_geometry','free_domain_geometry']:
            assert hashlib.sha256(bytes.fromhex(g[stem+'_wkb_hex'])).hexdigest() == g[stem+'_sha256']
    assert end == len(faces)
    assert sorted(g for c in graph['components'] for g in c['group_ids']) == sorted(ids)
    assert all(c['passed'] and c['upper_contact_group_ids'] and c['lower_contact_group_ids'] for c in graph['components'])
    assert sorted(c['group_id'] for c in graph['internal_connectivity']) == sorted(ids)
    assert all(c['passed'] and c['remaining_components'] == 1 for c in graph['internal_connectivity'])
    block = checkpoint['block_identity']
    row = next(r for r in store['regions'] if r['source_index'] == index)
    for key,name in [('part','input-part.npz'),('envelope',row['envelope']),('overhang',f'input-source-{index:03d}-roofs.npz')]:
        with np.load(STORE/name, allow_pickle=False) as arrays:
            assert block[key] == {k:identity(arrays[k]) for k in ['vertices','faces']}, (index,key)
    assert block['parameters']['generateTrussGrid'] is False and block['parameters']['continuousFragmentedInterfaces'] is True
    if parameters is None:
        parameters,calendar = block['parameters'],block['calendar']
    assert block['parameters'] == parameters and block['calendar'] == calendar
    heights = np.array([(i+.5)*store['parameters']['layer_height_mm'] for i in range(1034)])
    assert block['calendar'] == identity(heights)
    attestation = block['interface_attestation']
    assert attestation['final_face_classification_sha256'] == block['interface_kind']['sha256']
    assert sum(attestation[k] for k in ['upper_faces','lower_faces','unanchored_side_faces']) == block['envelope']['faces']['shape'][0]
    assert attestation['source_meshes']['part']['sha256'] == store['files_sha256']['input-part.npz']
    assert attestation['source_meshes']['chain']['sha256'] == row['chain_sha256']
    rows.append(dict(source_index=index,directory=str(directory.relative_to(ROOT)),
        checkpoint_sha256=expected,support_npz_sha256=checkpoint['files_sha256']['support.npz'],local_checkpoint_pass=True,
        checkpoint_status=checkpoint['status'],terminal_status=terminal['status'],geometry_status=metadata['status'],
        terminal_assessment_sha256=frozen[terminal_path],geometry_assessment_sha256=checkpoint['files_sha256']['geometry-assessment.json'],
        material_connections_sha256=checkpoint['files_sha256']['material-connections.json'],
        vertices=len(vertices),faces=len(faces),bounds_mm=[vertices.min(0).tolist(),vertices.max(0).tolist()],
        surface_arrays_sha256=material_sha,graph_status=graph['status'],graph_components=len(graph['components']),
        face_groups=len(groups),all_graph_components_upper_lower_anchored=True,all_groups_internally_connected=True,
        face_ranges_partition_and_type_order_pass=True,metadata_terminal_identical=True,
        part_envelope_overhang_arrays_match_store=True,parameters_calendar_match_other_completed_regions=True,
        current_runtime_identical=True,recorded_seconds=terminal['seconds'],
        interface_attestation_bound=True,interface_classification_not_recomputed=True))
    del terminal, metadata
assert runtime_identity() == runtime_before
assert all(sha(path)==h for path,h in frozen.items())
report = dict(status='three_region_checkpoint_identity_review_passed_no_global_admission',global_admission=False,
    scope='Stored file/array identities, metadata contracts, existing graph bindings and current source/runtime only; no geometry reconstruction, exact replay or full exposure audit',
    source_sha256=sha(__file__),sealed_store_sha256=STORE_SHA,source_STL_sha256=store['input_sha256'],
    rows=rows,runtime_identity_before_after_equal=True,
    runtime_identity_sha256=hashlib.sha256(json.dumps(runtime_before,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    inputs_sha256={str(path.relative_to(ROOT)):h for path,h in frozen.items()},inputs_and_sources_unchanged=True,
    terminal_diagnostic_labels_preserved=True,true_process_returncodes_not_inferred=True,
    geometry_reconstructed=False,global_admission_replayed=False,full_support_exposure_audit_executed=False)
(HERE/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:report[k] for k in ['status','global_admission','runtime_identity_before_after_equal','source_sha256']}))
