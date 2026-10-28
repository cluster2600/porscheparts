"""Draw the complete actual 07b STL and a source-datum crop; no native geometry operation."""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import sys
import time


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def fresh(path):
    path = Path(path)
    require(not path.exists() and not any(p.is_symlink() for p in [path, *path.parents]), 'Fresh nonsymlink output required')
    return path


def read_binary(path):
    data = Path(path).read_bytes()
    if len(data) < 84:
        raise ValueError('Truncated binary STL')
    count = struct.unpack('<I', data[80:84])[0]
    if not count or len(data) != 84 + 50 * count:
        raise ValueError('Nonempty exact-length binary STL required')
    import numpy as np
    records = np.frombuffer(data, dtype=np.dtype([('normal', '<f4', 3), ('points', '<f4', (3, 3)), ('attribute', '<u2')]), offset=84)
    points = records['points'].reshape(-1, 3).astype(np.float64)
    if not np.isfinite(points).all():
        raise ValueError('Finite STL coordinates required')
    vertices, inverse = np.unique(points, axis=0, return_inverse=True)
    return vertices, inverse.reshape(-1, 3).astype(np.int64)


def display_box(physical_edges, radius):
    require([e['edge_index_zero_based'] for e in physical_edges] == [431, 293, 292, 291, 290, 289, 161], 'Whole ordered source contour required')
    first = physical_edges[0]
    require([v['vertex_index_zero_based'] for v in first['endpoints']] == [302, 210], 'Original source endpoints differ')
    points = [v['source_point_mm'] for v in first['endpoints']]
    require(radius == 1.0 and all(len(p) == 3 and all(math.isfinite(x) for x in p) for p in points), 'Finite original source datums and actual R1 required')
    return [[min(p[a] for p in points) - radius for a in range(3)], [max(p[a] for p in points) + radius for a in range(3)]]


def select_data(law_root, law_owner, generation_root, generation_owner, mass_root, mass_owner):
    patched = law_owner['variants']['patched']
    require(law_root['owner_terminal_sha256'] == '7a0d05364c8b5786374f58366c1031498fc977a5b07f9e96ca379ef67a0206c0', 'Foreign law owner')
    require(law_root['actual_returncodes'] == [1, 0] and patched['actual_tool_returncode'] == patched['actual_child_returncode'] == 0, 'Closed actual patched law observation required')
    require(generation_owner['actual_outer_returncode'] == generation_owner['actual_child_returncode'] == 0 and generation_owner['fresh_owned_group_absent'] is True, 'Generation did not close')
    require(generation_root['new_STL_sha256'] == generation_owner['STL_sha256'] == '8d0b09b705e17ae2a8a57588ae44879790c97ef31fbd7ec44995536971442a6d', 'Foreign actual candidate STL')
    require(generation_root['new_STL_triangles'] == generation_owner['triangles'] == 637850 and generation_root['new_STL_bytes'] == generation_owner['STL_bytes'] == 31892584, 'Complete STL count/length differs')
    require(patched['raw_BREP_sha256'] == generation_owner['master_BREP_sha256'] == '07b354e3716b4e856010e271f7a36aa7f6fe05a4ee4ce36eb0959af84e92409e', 'Native master identity differs')
    require(mass_owner['actual_tool_and_child_returncode'] == 0 and mass_root['mass_kg'] == mass_owner['mass_kg'] == 1.2623644100871174, 'Closed native mass authority differs')
    require(mass_root['native_candidate_volume_mm3'] == mass_owner['native_candidate_volume_mm3'] == 285602.8077120175, 'Native adaptive volume differs')
    physical = patched['whole_post_Build_physical_source_edges']
    box = display_box(physical, 1.0)
    return dict(schema='actual-functional-law-candidate-image-data-1', BREP_sha256=patched['raw_BREP_sha256'], STL_sha256=generation_owner['STL_sha256'], STL_bytes=generation_owner['STL_bytes'], STL_triangles=generation_owner['triangles'], native_mass_kg=mass_owner['mass_kg'], native_adaptive_volume_mm3=mass_owner['native_candidate_volume_mm3'], whole_source_physical_edges=physical, whole_retained_native_laws=patched['whole_final_native_laws'], whole_retained_exact_function_proof=patched['whole_final_exact_function_proof'], source_edge431_display_box_mm=box, display_radius_expansion_mm=1.0, source_datums_are_not_candidate_boundary_or_stress_measurements=True, engineering_qualification_transferred=False, snapshot_gate_flags_not_current_status=True)


def literal_sources(root, plan):
    prior = (root / plan['loader_original']).read_text()
    current = Path(__file__).read_text()
    def segment(source):
        return ast.get_source_segment(source, next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'read_binary'))
    require(segment(prior) == segment(current), 'Original exact binary loader changed')
    require((root / plan['raster_original']).read_bytes() == (root / plan['raster_copy']).read_bytes(), 'Original raster source changed')


def verify(plan_path, expected, rendering=False, hash_STL=True):
    require(sha(plan_path) == expected, 'Plan hash differs')
    plan = read(plan_path)
    root = Path(plan['source_root'])
    require(plan['schema'] == 'functional-law-candidate-STL-figure-plan-1' and plan['bounds'] == dict(outer=180, inner=150, CPU=[140, 141], threads=1, workers=0), 'Figure scope or budget differs')
    require(plan['native_calls'] == 0 and plan['overview_camera_degrees'] == [30.0, 0.0] and plan['detail_axes'] == [0, 2] and plan['detail_view_from_negative_Y'] is True, 'Display-only operator differs')
    if rendering:
        require(plan['launch_ready'] is True and plan['root_GO'] is not None and sha(root / plan['root_GO']) == plan['root_GO_sha256'], 'NON-ARMED: ROOT render GO required')
    for name, digest in plan['files_sha256'].items():
        path = root / name
        if name == plan['STL'] and not hash_STL:
            require(path.stat().st_size == 31892584, 'Closed STL size differs')
        else:
            require(sha(path) == digest, 'Input/source/runtime hash differs: ' + name)
    require(plan['files_sha256'][str(Path(__file__).relative_to(root))] == sha(__file__) and len(plan['runtime_sha256']) == 5259 and all(plan['files_sha256'].get(n) == h for n, h in plan['runtime_sha256'].items()), 'Current source/runtime map differs')
    literal_sources(root, plan)
    context = plan['closed_context']
    rows = []
    for key in ['law', 'generation', 'mass']:
        spec = context[key]
        review, owner = read(root / spec['root_review']), read(root / spec['owner_terminal'])
        require(review['owner_terminal_sha256'] == sha(root / spec['owner_terminal']), 'ROOT/owner join differs: ' + key)
        rows.extend([review, owner])
    require(rows[3]['addition_ROOT_sha256'] == sha(root / context['mass']['root_review']), 'Generation/native mass ROOT join differs')
    data = read(root / plan['data'])
    require(data == select_data(*rows), 'Whole retained data/provenance differs')
    require(plan['files_sha256'][plan['STL']] == data['STL_sha256'], 'STL content authority differs')
    require(not any(n.split('.')[0] in ['OCP', 'build123d', 'gmsh', 'trimesh'] for n in sys.modules), 'Native geometry or audit module imported')
    require(sha(plan_path) == expected, 'Plan changed')
    return plan, data


def render(plan_path, expected, output):
    started = time.monotonic()
    plan, data = verify(plan_path, expected, rendering=True)
    root = Path(plan['source_root'])
    require(Path(output) == root / plan['output_directory'], 'Declared output differs')
    output = fresh(output)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import vispy
    vertices, faces = read_binary(root / plan['STL'])
    require(len(faces) == data['STL_triangles'], 'Full actual STL triangle roster differs')
    triangles = vertices[faces]
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    light = np.array([.25, -.5, .8]); light /= np.linalg.norm(light)
    illumination = np.divide(normals @ light, lengths, out=np.zeros(len(faces)), where=lengths != 0)
    colors = np.tile(matplotlib.colors.to_rgba('#5e91af'), (len(faces), 1))
    colors[:, :3] *= (.35 + .65 * np.maximum(0., illumination))[:, None]
    spec = importlib.util.spec_from_file_location('_literal_actual_surface_raster', root / plan['raster_copy'])
    raster = importlib.util.module_from_spec(spec); spec.loader.exec_module(raster)
    picture = raster.raster(vertices, faces, colors, 30., 0.)
    box = np.array(data['source_edge431_display_box_mm'])
    selected = ((triangles.max(1) >= box[0]) & (triangles.min(1) <= box[1])).all(1)
    require(selected.any(), 'Source-datum display crop is empty')
    # Negative-Y view: far (+Y) triangles are painted first; no geometry is changed.
    order = np.argsort(-triangles[selected, :, 1].mean(1), kind='stable')
    projected = triangles[selected][:, :, [0, 2]][order]
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none', 'svg.hashsalt': 'carrier-functional-law-candidate-actual-STL-001', 'pdf.fonttype': 42, 'path.simplify': False})
    fig = plt.figure(figsize=(15, 8), facecolor='#f5f7f9')
    fig.text(.045, .946, '993 TURBO CARRIER · COMPLETE FUNCTIONAL-LAW CANDIDATE', fontsize=12, weight='bold', color='#536d7d')
    fig.text(.045, .892, 'The retained geometry, in its original coordinates', fontsize=24, weight='bold', color='#183347')
    fig.text(.045, .85, 'Actual binary STL · no remeshing, decimation, displacement or new native CAD operation', fontsize=11, color='#536d7d')
    ax = fig.add_axes([.025, .43, .63, .34]); ax.imshow(picture); ax.axis('off')
    ax.set_title('A / Complete candidate surface', loc='left', fontsize=14, weight='bold', color='#183347', pad=10)
    ax = fig.add_axes([.71, .285, .25, .46])
    ax.add_collection(PolyCollection(projected, facecolors=colors[selected][order], edgecolors='#425f72', linewidths=.18, rasterized=True))
    ax.set(xlim=box[:, 0], ylim=box[:, 2], xlabel='X (mm)', ylabel='Z (mm)')
    ax.set_aspect('equal'); ax.set_facecolor('white')
    ax.set_title('B / Junction display crop', loc='left', fontsize=14, weight='bold', color='#183347', pad=12)
    for row in data['whole_source_physical_edges'][0]['endpoints']:
        point = row['source_point_mm']; ax.plot(point[0], point[2], marker='o', markersize=4, markerfacecolor='white', markeredgecolor='#ba582d')
        ax.annotate('Source v' + str(row['vertex_index_zero_based']), (point[0], point[2]), xytext=(5, -13 if row['vertex_index_zero_based'] == 302 else 7), textcoords='offset points', fontsize=8, color='#984823')
    fig.text(.045, .335, f"{len(faces):,} actual triangles  |  Native mass {data['native_mass_kg']:.9f} kg", fontsize=14, weight='bold', color='#183347')
    fig.text(.045, .29, 'All complete STL faces are retained in the overview. Camera: 30° elevation, 0° azimuth.', fontsize=9.8, color='#536d7d')
    fig.text(.045, .25, 'Close-up: source edge 431 endpoint region, expanded by the 1 mm radius ceiling.', fontsize=9.5, color='#536d7d')
    fig.text(.045, .216, 'The source markers are original contour datums; they are not new surface or stress measurements.', fontsize=9.5, color='#536d7d')
    fig.text(.045, .145, 'Generation candidate only. This image grants no interface, surface-audit, mechanical or manufacturing qualification.', fontsize=10, color='#984823')
    fig.text(.045, .103, 'BREP 07b354e3716b…  /  STL 8d0b09b705e1…  /  Generation ROOT 1f26c9dd…  /  Native mass ROOT 0fbfbcdd…', fontsize=9, color='#536d7d')
    fig.text(.045, .069, 'Source units: millimetres. Flat face lighting and painter-sorted detail serve visual readability only.', fontsize=9, color='#536d7d')
    verify(plan_path, expected, rendering=True)
    output.mkdir()
    for suffix in ['png', 'svg', 'pdf']:
        metadata = {'Date': None, 'Creator': 'Actual functional-law candidate surface'} if suffix == 'svg' else ({'CreationDate': None, 'ModDate': None, 'Creator': 'Actual functional-law candidate surface'} if suffix == 'pdf' else {'Software': 'Actual functional-law candidate surface'})
        fig.savefig(output / ('carrier-functional-law-candidate.' + suffix), dpi=180, metadata=metadata)
    plt.close(fig)
    verify(plan_path, expected, rendering=True)
    runtime = {str((root / n).resolve()): h for n, h in plan['runtime_sha256'].items()}
    loaded = {str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m, '__file__', None) and Path(m.__file__).is_file() and 'site-packages' in str(Path(m.__file__).resolve())}
    diagnostic = dict(runtime_imported_files=sorted(loaded), outside_runtime_imported_files=sorted(loaded - set(runtime)), declared_runtime_file_count=len(runtime))
    write(output / 'runtime-origin-diagnostic.json', diagnostic)
    require(loaded <= set(runtime), 'Plot package imported outside the retained runtime')
    write(output / 'render-receipt.json', dict(schema='actual-functional-law-candidate-STL-render-1', status='actual_complete_candidate_STL_two_panel_display_only', plan_sha256=expected, source_sha256=sha(__file__), input_sha256=plan['files_sha256'], runtime_imported_files=sorted(loaded), runtime=dict(numpy=np.__version__, matplotlib=matplotlib.__version__, vispy=vispy.__version__), complete_STL_triangles=len(faces), indexed_vertices=len(vertices), all_faces_retained_in_overview=True, local_display_box_mm=box.tolist(), local_selected_triangle_count=int(selected.sum()), local_triangle_selection='closed_triangle_AABB_intersects_source_datum_ROI', local_projected_axes=[0, 2], local_view_from_negative_Y=True, source_physical_edge431=data['whole_source_physical_edges'][0], native_mass_kg=data['native_mass_kg'], geometry_modified=False, engineering_qualification_transferred=False, native_calls=0, cwd=os.getcwd(), wall_seconds=time.monotonic()-started, CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime, maxRSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, exports_sha256={p.name: sha(p) for p in sorted(output.iterdir())}))


if __name__ == '__main__':
    for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
        os.environ[key] = '1'
    mode, plan_path, expected = sys.argv[1:4]
    if mode == 'preflight':
        plan, data = verify(plan_path, expected, hash_STL=False)
        print(json.dumps(dict(status='source_only_no_STL_body_read_no_scientific_import', launch_ready=plan['launch_ready'], actual_triangle_count_from_closed_receipt=data['STL_triangles'], source_runtime_pins=len(plan['files_sha256']), STL_body_hash_deferred_until_GO=True)))
    elif mode == 'render':
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150-second actual-STL figure budget')))
        signal.setitimer(signal.ITIMER_REAL, 150)
        resource.setrlimit(resource.RLIMIT_CPU, (140, 141))
        os.chdir('/')
        render(plan_path, expected, sys.argv[4])
    else:
        raise SystemExit('usage: figure.py preflight PLAN SHA | render ARMED_PLAN SHA FRESH_OUTPUT')
