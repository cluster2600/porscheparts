"""Bounded adaptive mesh-7 discrete refinement campaign; NEVER armed by pending-plan.json."""
from collections import defaultdict
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def protected_facets(original_boundary, boundary_parent_faces, groups):
    """Refuse subdivision of ANY exterior face with three old group corners."""
    group_sets = {name: set(tags) for name, tags in groups.items()}
    protected = {face: [name for name, tags in group_sets.items() if set(face) <= tags]
                 for face in original_boundary}
    protected = {face: names for face, names in protected.items() if names}
    children = defaultdict(list)
    for child, parent in boundary_parent_faces.items(): children[parent].append(child)
    changed = {face: children.get(face, []) for face in protected if children.get(face) != [face]}
    require(not changed, 'Protected BC/load facet subdivided or missing: ' + repr(changed))
    return {','.join(map(str, face)): names for face, names in protected.items()}


def node_lines(path):
    active = False; rows = {}
    with Path(path).open('r', encoding='ascii', newline='') as stream:
        for line in stream:
            if line.startswith('*'):
                active = line.strip().upper() == '*NODE'; continue
            if active and line.strip():
                tag = int(line.split(',')[0]); require(tag not in rows, 'Duplicate original NODE line')
                rows[tag] = line
    return rows




def copy_parent_inputs(sources, output, expected):
    """Reproduce the original four-file CAD parent layout, without mutation."""
    names = {'carrier.step', 'study.json', 'geometry.json', 'protected-interfaces.json'}
    require(set(sources) == set(expected) == names, 'Incomplete parent CAD layout')
    result = {}
    for name, source in sources.items():
        require(Path(source).name == name, 'Parent CAD basename differs')
        with Path(source).open('rb') as src, (output / name).open('xb') as dst:
            shutil.copyfileobj(src, dst, 1024 * 1024)
            dst.flush(); os.fsync(dst.fileno())
        result[name] = sha(output / name)
        require(result[name] == expected[name], 'Copied parent CAD input differs')
    return result


def ordered_tags(old_tags, new_node_tags):
    """The old prefix follows from sorted old IDs and append-only new IDs."""
    require(old_tags and all(type(t) is int and t > 0 for t in old_tags)
            and all(a < b for a, b in zip(old_tags, old_tags[1:])), 'Old tags not strictly sorted')
    new = list(new_node_tags)
    require(all(type(t) is int and t > 0 for t in new) and len(set(new)) == len(new), 'Invalid new tag set')
    require(set(old_tags) <= set(new), 'Old node ID missing')
    require(all(t > old_tags[-1] for t in set(new) - set(old_tags)), 'New IDs are not appended above all old IDs')
    result = sorted(new)
    require(result[:len(old_tags)] == old_tags, 'Old tag prefix changed')
    return result


def mesh_metadata(reference, quality, nodes, elements, volume, cad_volume, bore_counts,
                  gmsh_version, parent_path, parent_sha256, STEP_sha256):
    """Current measurements first; old Gmsh sizing metadata stays historical."""
    return dict(nodes=nodes, C3D10_elements=elements,
                minimum_sampled_Jacobian=quality['minimum_Jacobian'],
                bore_node_counts=dict(bore_counts), element_order=2, straight_midsides=True,
                mesh_volume_mm3=volume, volume_relative_error=volume / cad_volume - 1,
                STEP_sha256=STEP_sha256,
                meshing_backend='scikit-fem12.0.2 MeshTet1.refined plus lineage-preserving T10 lift',
                quality_evaluator=dict(name='Gmsh', version=gmsh_version, discrete_model_only=True,
                                       methods=['minDetJac', 'volume'], remeshing=False),
                parent_mesh=dict(path=parent_path, mesh_json_sha256=parent_sha256),
                historical_reference_mesh_metadata=dict(reference))


def retain_npz_xyz(old_tags, old_xyz, new_tags, physical_nodes, np):
    """Preserve the original NPZ block independently of old INP lexemes."""
    require(new_tags[:len(old_tags)].tobytes() == old_tags.tobytes(), 'Old NPZ node tags changed')
    xyz = np.asarray([physical_nodes[int(t)] for t in new_tags], dtype=np.float64)
    xyz[:len(old_tags)] = old_xyz
    require(xyz[:len(old_tags)].tobytes() == old_xyz.tobytes(), 'Old NPZ XYZ changed')
    return xyz



def adaptive_refine(bridge, api, nodes, elements, groups, regions, output, maximum_nodes, maximum_elements):
    """One bounded campaign; each pass is certified relative to its input mesh."""
    np = api.np; records = []; current_nodes = nodes; current_elements = elements
    initial_marked = None; initial_by_region = None; lifted = None; protected = None
    with (output / 'passes.jsonl').open('x') as journal:
        def event(value):
            journal.write(json.dumps(value, allow_nan=False) + '\n'); journal.flush(); os.fsync(journal.fileno())
        while True:
            require(len(current_nodes) <= maximum_nodes and len(current_elements) <= maximum_elements, 'Explicit input-size refusal')
            compact = bridge.compact_t10(current_nodes, current_elements, groups)
            marked, by_region = bridge.mark_t4(compact, regions)
            if initial_marked is None: initial_marked, initial_by_region = marked, by_region
            if not marked:
                require(lifted is not None, 'Reference already meets targets; no adaptive proposal')
                event(dict(event='targets_reached', completed_passes=len(records), marked=0,
                           nodes=len(current_nodes), elements=len(current_elements)))
                return lifted, records, initial_marked, initial_by_region, protected
            number = len(records) + 1
            event(dict(event='pass_start', pass_number=number, marked_count=len(marked),
                       nodes=len(current_nodes), elements=len(current_elements)))
            p = np.asarray(compact['points'], dtype=np.float64); t = np.asarray(compact['cells'], dtype=np.int32)
            new_p, new_t, ledger = bridge.refine_with_ledger(p, t, np.asarray(marked, dtype=np.int32), api)
            require(len(new_t) > len(t), 'Adaptive pass made no progress')
            proposal = bridge.lift_t10(compact, new_p, new_t, ledger)
            protected = protected_facets(bridge.boundary(current_elements), proposal['boundary_parent_faces'], groups)
            require(len(proposal['nodes']) <= maximum_nodes and len(proposal['elements']) <= maximum_elements, 'Explicit output-size refusal')
            proof = dict(pass_number=number, input_is='original_mesh7' if number == 1 else 'previous_pass_output',
                         previous_pass_proof_sha256=None if not records else records[-1]['proof_sha256'],
                         input_nodes=len(current_nodes), input_elements=len(current_elements),
                         output_nodes=len(proposal['nodes']), output_elements=len(proposal['elements']),
                         marked=marked, marked_by_region=by_region, ledger=ledger,
                         parent_elements=proposal['parent_elements'], parent_element_scope='Immediately preceding mesh only',
                         closure_parent_elements=proposal['closure_parent_elements'],
                         boundary_parent_faces=[dict(child=list(k), parent=list(v)) for k, v in proposal['boundary_parent_faces'].items()],
                         protected_facets=protected, protected_facets_unchanged=True,
                         all_input_nodes_used_and_IDs_XYZ_unchanged=True,
                         native_midpoint_differences=proposal['native_to_retained_midpoint_differences'],
                         exact_Q_geometry_conservation_claimed=False)
            name = 'pass-' + str(number).zfill(4) + '.json'
            with (output / name).open('x') as stream:
                json.dump(proof, stream, indent=2, allow_nan=False); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
            record = dict(pass_number=number, proof=name, proof_sha256=sha(output / name),
                          input_nodes=len(current_nodes), input_elements=len(current_elements),
                          output_nodes=len(proposal['nodes']), output_elements=len(proposal['elements']))
            records.append(record); current_nodes, current_elements = proposal['nodes'], proposal['elements']; lifted = proposal
            event(dict(event='pass_finish', **record))


def main(plan_path, expected_plan_sha256):
    started = time.monotonic(); cpu = time.process_time()
    plan_path = Path(plan_path); require(sha(plan_path) == expected_plan_sha256, 'Plan drift')
    plan = json.loads(plan_path.read_text())
    # This guard precedes all real mesh access and all scientific imports.
    require(plan['launch_ready'] is True and plan['root_GO_sha256'] is not None, 'Real caller remains unarmed')
    require(sha(ROOT / plan['root_GO']) == plan['root_GO_sha256'], 'Root GO differs')
    require(plan['reference_mesh'] == 'work/part-workflow/run-001/cad/mesh-7', 'Wrong reference mesh')
    require(plan['threads'] == 1 and plan['workers'] == 0 and plan['outer_seconds'] == 1200, 'Resource drift')
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('1150s discrete single pass')))
    signal.setitimer(signal.ITIMER_REAL, 1150); resource.setrlimit(resource.RLIMIT_CPU, (1100, 1101))
    output = ROOT / plan['output_directory']
    require(not output.exists() and not output.is_symlink(), 'Output must be fresh')
    require(all(not p.is_symlink() for p in output.parents), 'Output symlink ancestor')
    require(output.is_relative_to(ROOT / 'work'), 'Output must be local work-only')
    pins = plan['files_sha256']; before = {p: sha(ROOT / p) for p in pins}
    require(before == pins, 'Source, runtime, evidence or original mesh drift')
    bridge = load('discrete_bridge_frozen', ROOT / plan['bridge'])
    api = load('discrete_package_original', ROOT / plan['package_helper']); np = api.np
    energy = load('discrete_energy_original', ROOT / plan['energy_source'])
    measure = load('discrete_measure_original', ROOT / plan['measure_source'])
    ordering = load('discrete_Gmsh_order_original', ROOT / plan['type11_helper'])
    catalogue = json.loads((ROOT / plan['catalogue_record']).read_text())
    require(catalogue['part_id'] == '993-ENG-CARRIER-0001', 'Wrong catalogue authority')
    sys.path.insert(0, str(ROOT / plan['gmsh_site_packages']))
    import gmsh
    require(gmsh.__version__ == '4.15.2', 'Wrong Gmsh read-only quality runtime')
    mesh = ROOT / plan['reference_mesh']; inp = mesh / 'mesh.inp'
    tags, xyz_inp, old_eids, indices = energy.read_mesh(inp)
    physical_nodes = {int(t): tuple(map(float, xyz)) for t, xyz in zip(tags, xyz_inp)}
    old_elements = {int(e): tuple(map(int, tags[row])) for e, row in zip(old_eids, indices)}
    with np.load(mesh / 'mesh.npz', allow_pickle=False) as raw:
        require(set(raw.files) == {'tags', 'xyz', 'faces', *bridge.GROUPS}, 'Unexpected original NPZ fields')
        old_npz = {k: raw[k].copy() for k in raw.files}
    require(np.array_equal(old_npz['tags'], tags), 'Original INP/NPZ tags differ')
    require(old_npz['xyz'].dtype == np.float64 and old_npz['xyz'].shape == xyz_inp.shape
            and np.isfinite(old_npz['xyz']).all(), 'Invalid original NPZ coordinates')
    require(np.max(np.abs(old_npz['xyz'] - xyz_inp)) <= 1e-10, 'Original NPZ/INP serialization guard failed')
    groups = {g: old_npz[g].tolist() for g in bridge.GROUPS}
    require(min(map(len, groups.values())) >= 12, 'Original group roster too small')
    require(len(set(t for g in groups.values() for t in g)) == sum(map(len, groups.values())), 'Original group overlap')
    reference = json.loads((mesh / 'mesh.json').read_text())
    require(reference['STEP_sha256'] == pins[plan['STEP']], 'Original mesh STEP binding')
    geometry = json.loads((ROOT / plan['geometry']).read_text())
    inspection = json.loads((ROOT / plan['inspection']).read_text())
    require(geometry['CAD_valid'] and geometry['solid_count'] == 1 and geometry['dense_reference_mass_kg'] <= 1.30, 'Original CAD guards')
    require(geometry['STEP_readback_volume_match'] is True
            and abs(inspection['STEP_volume_mm3'] / geometry['volume_mm3'] - 1) <= 1e-8, 'Original volume readback guard')
    require(inspection['inputs_sha256']['carrier.step'] == pins[plan['STEP']], 'Inspection STEP binding')
    spec = json.loads((ROOT / plan['specification']).read_text()); regions = spec['regions']
    original_boundary = bridge.boundary(old_elements)
    require(set(original_boundary) == {tuple(sorted(map(int, f))) for f in old_npz['faces']}, 'Original NPZ exterior mismatch')
    output.mkdir(); new_mesh = output / 'mesh'; new_mesh.mkdir()
    parent_inputs = copy_parent_inputs({n: ROOT / p for n, p in plan['CAD_inputs'].items()}, output,
                                      {n: pins[p] for n, p in plan['CAD_inputs'].items()})
    report = dict(status='incomplete_no_FEA', reference_mesh=plan['reference_mesh'],
                  original_nodes=len(tags), original_elements=len(old_eids),
                  original_NPZ_XYZ_block_preserved=False, original_INP_NODE_lexemes_preserved=False,
                  parent_CAD_inputs_sha256=parent_inputs, catalogue_sha256=pins[plan['catalogue_record']],
                  adaptive_campaign=True, termination='mark_t4 returns no marked cells, or explicit refusal/resource limit',
                  h2_qualified=False, FEA_started=False)
    error = None
    try:
        lifted, passes, marked, by_region, protected = adaptive_refine(
            bridge, api, physical_nodes, old_elements, groups, regions, output,
            plan['maximum_nodes'], plan['maximum_elements'])
        report.update(adaptive_passes=passes, initial_marked=marked, initial_marked_by_region=by_region,
                      new_nodes=len(lifted['nodes']), new_elements=len(lifted['elements']),
                      protected_facets=protected, protected_facets_unchanged_at_every_pass=True,
                      all_original_nodes_IDs_XYZ_unchanged_and_used=True,
                      parent_scope='Per-pass proofs refer to the immediately preceding mesh, not directly to original mesh7')
        bridge.write_inp(new_mesh / 'mesh.inp', node_lines(inp), physical_nodes, lifted)
        tag_order = ordered_tags(old_npz['tags'].tolist(), lifted['nodes'])
        ntags = np.array(tag_order, dtype=old_npz['tags'].dtype)
        require(ntags.tolist() == tag_order, 'Node ID overflow during NPZ cast')
        nxyz = retain_npz_xyz(old_npz['tags'], old_npz['xyz'], ntags, lifted['nodes'], np)
        faces = np.array(lifted['boundary_faces'], dtype=old_npz['faces'].dtype)
        np.savez_compressed(new_mesh / 'mesh.npz', tags=ntags, xyz=nxyz, faces=faces, **{g: old_npz[g] for g in bridge.GROUPS})
        with np.load(new_mesh / 'mesh.npz', allow_pickle=False) as check:
            require(check['tags'].tobytes() == ntags.tobytes() and check['xyz'].tobytes() == nxyz.tobytes()
                    and check['faces'].tobytes() == faces.tobytes(), 'NPZ roundtrip changed arrays')
            require(all(check[g].dtype == old_npz[g].dtype and check[g].tobytes() == old_npz[g].tobytes()
                        for g in bridge.GROUPS), 'Discrete group roster changed')
        report.update(original_NPZ_XYZ_block_preserved=True, original_INP_NODE_lexemes_preserved=True)
        rt, rx, re, ri = energy.read_mesh(new_mesh / 'mesh.inp')
        require(np.array_equal(rt, ntags) and np.max(np.abs(nxyz - rx)) <= 1e-10, 'New NPZ/INP serialization guard')
        require(all(bridge.bits(tuple(rx[i])) == bridge.bits(physical_nodes[int(tag)]) for i, tag in enumerate(tags)), 'Old solver-coordinate change')
        require(np.max(np.abs(rx[ri][:, 4:] - (rx[ri][:, energy.EDGE_PAIRS[:, 0]] + rx[ri][:, energy.EDGE_PAIRS[:, 1]]) / 2)) <= 1e-10, 'New straight-midside guard')
        gmsh.initialize()
        try:
            gmsh.option.setNumber('General.Terminal', 0); gmsh.option.setNumber('General.NumThreads', 1)
            permutation = ordering.type11_permutation(gmsh.model.mesh.getElementProperties(11))
            inverse = [permutation.index(i) for i in range(10)]
            report['CCX_positions_for_native_type11'] = permutation
            entity = gmsh.model.addDiscreteEntity(3)
            gmsh.model.mesh.addNodes(3, entity, rt.tolist(), rx.ravel().tolist())
            gmsh.model.mesh.addElementsByType(entity, 11, re.tolist(), rt[ri[:, permutation]].ravel().tolist())
            kinds, eid, conn = gmsh.model.mesh.getElements(3)
            require(list(kinds) == [11] and len(eid[0]) == len(re), 'Gmsh import topology mismatch')
            order = np.argsort(eid[0]); require(np.array_equal(eid[0][order], re)
                and np.array_equal(np.asarray(conn[0]).reshape(-1, 10)[:, inverse][order], rt[ri]), 'Gmsh imported connectivity changed')
            gt, gx, _ = gmsh.model.mesh.getNodes(); order = np.argsort(gt)
            require(np.array_equal(gt[order], rt) and np.array_equal(np.asarray(gx).reshape(-1, 3)[order], rx), 'Gmsh imported coordinates changed')
            jac = gmsh.model.mesh.getElementQualities(eid[0], 'minDetJac')
            volumes = gmsh.model.mesh.getElementQualities(eid[0], 'volume')
            require(np.isfinite(jac).all() and min(jac) > 0 and np.isfinite(volumes).all() and min(volumes) > 0, 'Original Gmsh Jacobian/volume guard')
            volume = float(volumes.sum())
            quality = dict(minimum_Jacobian=float(min(jac)), nonpositive_elements=int(np.count_nonzero(jac <= 0)), finite=True, elements=len(jac))
        finally: gmsh.finalize()
        meta = mesh_metadata(reference, quality, len(rt), len(re), volume, geometry['volume_mm3'],
                             {g: len(old_npz[g]) for g in bridge.GROUPS}, gmsh.__version__,
                             plan['reference_mesh'], pins[plan['reference_mesh'] + '/mesh.json'], pins[plan['STEP']])
        (new_mesh / 'quality.json').write_text(json.dumps(quality, indent=2)+'\n')
        (new_mesh / 'mesh.json').write_text(json.dumps(meta, indent=2)+'\n')
        report.update(quality=quality, mesh=meta, volume_error_non_regression=abs(meta['volume_relative_error']) <= abs(reference['volume_relative_error']))
        require(report['volume_error_non_regression'], 'Original volume non-regression gate failed')
        measured = [measure.region_edges({int(i): list(xyz) for i, xyz in zip(rt, rx)},
                                        [(int(e), rt[row].tolist()) for e, row in zip(re, ri)], region) for region in regions]
        report['measurements'] = measured
        require(all(r['target_attained'] for r in measured), 'Actual half-h target failed')
        report.update(status='local_adaptive_discrete_h2_mesh_checked_no_FEA', h2_qualified=True)
    except BaseException as exc:
        error = exc; report['error'] = dict(type=type(exc).__name__, message=str(exc))
    after = {p: sha(ROOT / p) for p in pins}
    report.update(source_sha256_before=before, source_sha256_after=after, pins_unchanged=before == after,
                  plan_unchanged=sha(plan_path) == expected_plan_sha256, wall_seconds=time.monotonic()-started,
                  CPU_seconds=time.process_time()-cpu, maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  exact_Q_geometry_conservation_claimed=False, automatic_budget_retry=False)
    report['pass_proof_artifacts_sha256'] = {p.name: sha(p) for p in sorted(output.glob('pass-*.json'))}
    report['completed_pass_authority'] = 'Only pass_finish newline records in passes.jsonl; a proof artifact alone is not a completed pass'
    if (output / 'passes.jsonl').exists(): report['passes_journal_sha256'] = sha(output / 'passes.jsonl')
    (output / 'assessment.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    require(before == after and report['plan_unchanged'], 'Integrity changed after real proposal')
    if error is not None: raise error
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(status=report['status'], assessment_sha256=sha(output / 'assessment.json'))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('plan'); parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args(); main(args.plan, args.plan_sha256)
