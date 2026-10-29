"""Repair finite internal voids; independent distance, transfer and intersection checks remain required."""
from pathlib import Path
import argparse, hashlib, json, signal, importlib.metadata
import numpy as np
from meshlib import mrmeshpy as mr, mrmeshnumpy as mn

def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--envelope-directory', type=Path, required=True)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    a.output.mkdir()
    signal.alarm(180)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert {k: importlib.metadata.version(k) for k in ['meshlib', 'meshlib-core', 'numpy']} == dict(meshlib='3.1.4.297', **{'meshlib-core': '3.1.4.297', 'numpy': '2.2.6'})
    r = json.loads((a.input / 'assessment.json').read_text())
    assert r['status'] == 'dominant_void_network_per_analytic_sign_retained' and (not r['manufacturing_authorized'])
    assert sorted((c['branch'] for c in r['selected'])) == [-1, 1]
    envelopes = json.loads((a.envelope_directory / 'assessment.json').read_text())
    assert sha(a.envelope_directory / 'envelopes.npz') == envelopes['output_sha256']['envelopes.npz']
    core_volume = envelopes['components'][r['rank']]['volume_mm3']
    rows = []
    contract = dict(scope='Evaluation-only SDK; deliberate repair of internal voids; complete external carrier surface untouched', maximum_relative_volume_change=0.01, maximum_geometric_distance_mm=0.01, self_intersection_method='Fixed pre-quality and post-quality passes: CutAndFill, maxExpand=2, relaxIterations=2, touchIsIntersection=True', degeneracy_method='Remesh, maxDeviation=.005 mm, tinyEdgeLength=.0001 mm, criticalTriAspectRatio=100', decimation_method='maxError=.005 mm, stabilizer=1e-6, packMesh=True, native maxTriangleAspectRatio=20', source_sha256=sha(Path(__file__)), input_assessment_sha256=sha(a.input / 'assessment.json'), core_envelopes_sha256=sha(a.envelope_directory / 'envelopes.npz'), manufacturing_authorized=False)
    (a.output / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')
    for selected in r['selected']:
        path = a.input / selected['file']
        assert sha(path) == selected['sha256']
        z = np.load(path)
        v = np.array(z['vertices'])
        f = np.array(z['triangles'], dtype=np.int32)
        mesh = mn.meshFromFacesVerts(f, v)
        loaded = mesh.topology.getValidFaces().count()
        before = mesh.volume()
        pre = mr.SelfIntersections.getFaces(mesh).count()
        s = mr.SelfIntersections.Settings()
        s.method = mr.SelfIntersections.Settings.Method.CutAndFill
        s.maxExpand = 2
        s.relaxIterations = 2
        s.touchIsIntersection = True
        mr.SelfIntersections.fix(mesh, s)
        q = mr.FixMeshDegeneraciesParams()
        q.maxDeviation = 0.005
        q.tinyEdgeLength = 0.0001
        q.criticalTriAspectRatio = 100
        q.mode = mr.FixMeshDegeneraciesParams.Mode.Remesh
        mr.fixMeshDegeneracies(mesh, q)
        d = mr.DecimateSettings()
        d.maxError = 0.005
        d.packMesh = True
        d.stabilizer = 1e-06
        result = mr.decimateMesh(mesh, d)
        before_final_repair = mr.SelfIntersections.getFaces(mesh).count()
        mr.SelfIntersections.fix(mesh, s)
        v = mn.getNumpyVerts(mesh).copy().astype(np.float64)
        f = mn.getNumpyFaces(mesh.topology).copy().astype(np.uint64)
        relative = abs(mesh.volume() - selected['volume_mm3']) / selected['volume_mm3']
        post = mr.SelfIntersections.getFaces(mesh).count()
        holes = len(mesh.topology.findHoleRepresentiveEdges())
        row = dict(branch=selected['branch'], input_triangles=int(len(z['triangles'])), loaded_triangles=loaded, output_triangles=len(f), volume_before_mm3=before, volume_after_mm3=mesh.volume(), relative_volume_change=relative, native_self_intersecting_faces_before=pre, native_self_intersecting_faces_before_final_repair=before_final_repair, native_self_intersecting_faces_after=post, boundary_holes=holes, decimation_cancelled=result.cancelled, float32_input_transport_maximum_l1_mm=float(abs(z['vertices'] - np.array(z['vertices'], dtype=np.float32).astype(float)).sum(1).max()), independent_self_intersection_check_pending=True, independent_distance_check_pending=True)
        (a.output / ('observation-' + selected['file'] + '.json')).write_text(json.dumps(row, indent=2) + '\n')
        assert not result.cancelled and (not holes) and (relative <= 0.01) and (post == 0)
        np.savez_compressed(a.output / selected['file'], vertices=v, triangles=f)
        rows.append(dict(selected, exact_oriented_triangle_roundtrip=False, native_transfer_check_pending=True, sha256=sha(a.output / selected['file']), volume_mm3=mesh.volume(), vertices=len(v), triangles=len(f)))
    r.update(core_volume_mm3=core_volume, status='internal_void_repair_candidate_generated', selected=rows, finite_retained_solid_fraction=1 - sum((x['volume_mm3'] for x in rows)) / core_volume, source_sha256={str(Path(__file__)): sha(Path(__file__))}, retained_void_volume_mm3=sum((x['volume_mm3'] for x in rows)), independent_self_intersection_check_pending=True, independent_distance_check_pending=True)
    (a.output / 'assessment.json').write_text(json.dumps(r, indent=2) + '\n')
    signal.alarm(0)
if __name__ == '__main__':
    main()
