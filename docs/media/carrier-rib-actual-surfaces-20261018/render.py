"""Display both closed surfaces with the existing complete-triangle raster helper."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

H = Path(__file__).resolve().parent
R = H.parents[1]
OLD = R/'work/carrier-first-window-stock-comparison-figure-preparation-001'
JOINT = R/'work/carrier-process-20261017/bounded-webs-stock-rib-libigl-preparation-001'
BODY = JOINT.with_name('bounded-webs-stock-rib-body-inspection-preparation-001')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_bytes())

def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('150 s surface drawing limit')))
    signal.alarm(150)
    resource.setrlimit(resource.RLIMIT_CPU, (140, 141))
    assert os.getpriority(os.PRIO_PROCESS, 0) == 10
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
        os.environ[name] = '1'
    original = load(OLD/'figure.py', '_closed_surface_display')
    plan, previous = original.verify(OLD/'plan.json', sha(OLD/'plan.json'))
    assert sha(JOINT/'root-terminal-review-001.json') == '0ecc25347820b768a7305c3031be803fdc3bceb04b25e74a1ac6dffe3ed26f20'
    joint, owner = read(JOINT/'root-terminal-review-001.json'), read(JOINT/'terminal-collection-001.json')
    assert joint['owner_terminal_sha256'] == sha(JOINT/'terminal-collection-001.json')
    assert joint['all_joint_gates_passed'] and joint['actual_STL_sha256'] == owner['STL_sha256']
    body = read(BODY/'root-terminal-review-001.json')
    assert sha(BODY/'root-terminal-review-001.json') == '3f5313d65f0206aa0141a7334ac5c9c901de296d9d63186856a4fdaf85d7bb0c'
    assert body['candidate_BREP_sha256'] == joint['actual_BREP_sha256']
    paths = [R/plan['STLs'][1], Path(read(JOINT/'plan.json')['STL'])]
    expected = [previous['cases'][1]['STL_sha256'], joint['actual_STL_sha256']]
    assert [sha(p) for p in paths] == expected
    masses = [previous['cases'][1]['native_mass_kg'], body['measured_mass_kg']]
    pins = {str(p): sha(p) for p in [Path(__file__), OLD/'plan.json', OLD/'figure.py', JOINT/'root-terminal-review-001.json', JOINT/'terminal-collection-001.json', BODY/'root-terminal-review-001.json', *paths]}
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    raster = load(R/plan['raster_copy'], '_closed_complete_triangle_raster')
    meshes = [original.read_binary(p) for p in paths]
    assert [len(f) for v, f in meshes] == [582946, 597720]
    framing = np.concatenate([v for v, f in meshes])
    box = np.array([framing.min(0), framing.max(0)])
    pictures, details = [], []
    for i, (vertices, faces) in enumerate(meshes):
        tri = vertices[faces]
        normal = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
        norm = np.linalg.norm(normal, axis=1)
        light = np.array([.25, -.5, .8]); light /= np.linalg.norm(light)
        shade = np.divide(normal@light, norm, out=np.zeros(len(faces)), where=norm != 0)
        colors = np.tile(matplotlib.colors.to_rgba('#5e91af'), (len(faces), 1))
        colors[:, :3] *= (.35+.65*np.maximum(0., shade))[:, None]
        pictures.append(raster.raster(np.concatenate([vertices, meshes[1-i][0]]), faces, colors, 30., 0., bounds=box))
        # shortcut: this common XY crop illustrates one of four mirrored transitions.
        selected = ((tri[:, :, :2].max(1) >= [20, 3]) & (tri[:, :, :2].min(1) <= [38, 21])).all(1)
        assert selected.any()
        order = np.argsort(tri[selected, :, 2].mean(1), kind='stable')
        top = (tri[:, :, 2] == 30.).all(1)
        detail_colors = np.tile(matplotlib.colors.to_rgba('#d4dce1'), (len(faces), 1))
        detail_colors[top] = matplotlib.colors.to_rgba('#3385ab')
        details.append((tri[selected, :, :2][order], detail_colors[selected][order], int(selected.sum())))
    assert pictures[0].shape == pictures[1].shape
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none', 'path.simplify': False})
    fig = plt.figure(figsize=(14, 9), facecolor='#f5f7f9')
    fig.text(.055, .95, '993 TURBO CARRIER | ACTUAL SURFACE COMPARISON', size=12, weight='bold', color='#536d7d')
    fig.text(.055, .9, 'A targeted reinforcement for 6.96 grams', size=24, weight='bold', color='#183347')
    fig.text(.055, .855, 'Complete STL surfaces, same camera and scale. Detail: one of four mirrored rib transitions.', color='#536d7d')
    for i, label in enumerate(['Previous stock design', 'Outward C2 rib reinforcement']):
        left = .055+i*.49
        ax = fig.add_axes([left, .6, .42, .18]); ax.imshow(pictures[i]); ax.axis('off')
        ax.set_title(label+' | '+f'{masses[i]:.6f} kg', loc='left', size=12, weight='bold', pad=10)
        xy, colors, count = details[i]
        ax = fig.add_axes([left+.07, .18, .29, .34])
        ax.add_collection(PolyCollection(xy, facecolors=colors, edgecolors='#425f72', linewidths=.08, rasterized=True))
        ax.set(xlim=(20, 38), ylim=(3, 21), xlabel='X (mm)', ylabel='Y (mm)', aspect='equal')
        ax.set_title('Upper rib at Z=30 mm in blue; lower surfaces gray', size=10)
    fig.text(.055, .09, '1.30 kg cap | New mass: 1.274798 kg | Remaining allowance: 25.20 g', size=12, weight='bold', color='#183347')
    fig.text(.055, .045, 'New surface: 597,720 triangles; topology and intersection checks passed. Mechanical recalculation is separate.', size=10, color='#536d7d')
    out = H/'output-001'; out.mkdir()
    for suffix in ['png', 'svg']:
        fig.savefig(out/('carrier-rib-actual-surfaces.'+suffix), dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    runtime = {str((R/n).resolve()): d for n, d in plan['runtime_sha256'].items()}
    loaded = {str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m, '__file__', None) and Path(m.__file__).is_file() and 'site-packages' in str(Path(m.__file__).resolve())}
    assert loaded <= set(runtime)
    assert all(sha(p) == d for p, d in runtime.items()) and all(sha(p) == d for p, d in pins.items())
    receipt = dict(schema='actual-stock-and-C2-rib-STL-display-1', language='English', inputs_sha256=pins, runtime_sha256=runtime, loaded_runtime_files=sorted(loaded), whole_triangle_counts=[582946, 597720], common_camera=[30., 0.], common_bounds_mm=box.tolist(), display_crop_XY_mm=[[20, 3], [38, 21]], selected_detail_triangle_counts=[v[2] for v in details], native_masses_kg=masses, geometry_or_FEA_modified=False, engineering_qualification=False, wall_seconds=time.monotonic()-started, outputs={p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in out.iterdir()})
    with (out/'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status='complete_actual_surface_display', outputs=receipt['outputs'])))

if __name__ == '__main__':
    main()
