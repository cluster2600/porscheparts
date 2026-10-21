"""Draw the complete two actual STL surfaces and a shared visual detail; no repair."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import signal
import struct
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def quality(vertices, faces):
    import numpy as np
    triangles = vertices[faces]
    twice = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    longest_squared = np.max(np.sum((triangles - np.roll(triangles, -1, axis=1)) ** 2, axis=2), axis=1)
    if np.any(longest_squared == 0):
        raise ValueError('Zero-length triangle refused by this figure')
    return twice / longest_squared


def render(output):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    import vispy
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Surface figure budget')))
    signal.alarm(110)
    resource.setrlimit(resource.RLIMIT_CPU, (100, 105))
    manifest = json.loads((HERE / 'inputs.json').read_text())
    pins = manifest['files_sha256']
    before = {name: sha(HERE / name) for name in pins}
    if before != pins:
        raise ValueError('Actual figure source or input differs')
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Fresh figure output required')
    meshes = [read_binary(HERE / name) for name in ('inputs/native.stl', 'inputs/remeshed.stl')]
    ratios = [quality(*mesh) for mesh in meshes]
    counts = [int((q < .001).sum()) for q in ratios]
    old = json.loads((HERE / 'inputs/native-topology.json').read_text())
    for name, array in zip(('vertices', 'faces'), meshes[0]):
        identity = old['array_identities'][name]
        if list(array.shape) != identity['shape'] or array.dtype.str != identity['dtype'] or hashlib.sha256(array.tobytes()).hexdigest() != identity['sha256']:
            raise ValueError('The complete canonical old mesh differs from the actual libigl audit')
    if counts[0] != old['topology']['needle_triangles'] or counts[0] != 463:
        raise ValueError('Old exact needle mask differs from the actual audit')
    generation = json.loads((HERE / 'inputs/generation.json').read_text())
    if len(meshes[1][1]) != generation['triangles'] or generation['candidate_STL_sha256'] != sha(HERE / 'inputs/remeshed.stl'):
        raise ValueError('Actual complete new surface generation differs')
    spec = importlib.util.spec_from_file_location('_unchanged_carrier_surface_raster', HERE / 'raster_unlit.py')
    raster = importlib.util.module_from_spec(spec); spec.loader.exec_module(raster)
    common_bounds = np.array([np.minimum(meshes[0][0].min(0), meshes[1][0].min(0)), np.maximum(meshes[0][0].max(0), meshes[1][0].max(0))])
    pictures = []
    for (vertices, faces), q in zip(meshes, ratios):
        normals = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]])
        light = np.array([.25, -.5, .8]); light /= np.linalg.norm(light)
        intensity = .35 + .65 * np.maximum(0., normals @ light / np.linalg.norm(normals, axis=1))
        colors = np.tile(matplotlib.colors.to_rgba('#5e91af'), (len(faces), 1))
        colors[:, :3] *= intensity[:, None]
        colors[q < .001] = matplotlib.colors.to_rgba('#d65325')
        pictures.append(raster.raster(vertices, faces, colors, 30., 0., bounds=common_bounds))
    worst = int(np.argmin(ratios[0]))
    triangle = meshes[0][0][meshes[0][1][worst]]
    normal = np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])
    hidden_axis = int(np.argmax(np.abs(normal)))
    axes = [a for a in range(3) if a != hidden_axis]
    centre = triangle.mean(0)
    span = max(2., float(np.ptp(triangle[:, axes], axis=0).max()) * 3)
    sign = 1 if normal[hidden_axis] >= 0 else -1
    matplotlib.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none', 'svg.hashsalt': 'carrier-surface-triangles-20261017', 'pdf.fonttype': 42, 'font.size': 11})
    fig = plt.figure(figsize=(15, 10.8), facecolor='#f5f7f9')
    fig.text(.05, .955, 'SUPPORT 993 · RETRIANGULATION DE LA SURFACE', fontsize=22, weight='bold', color='#163247')
    fig.text(.05, .919, 'Deux STL réels du même maître BREP C1 · coordonnées conservées dans leur repère', fontsize=12, color='#435e6f')
    titles = ['Avant · export natif', 'Après · surface Gmsh dédiée']
    for i, ((vertices, faces), q, picture) in enumerate(zip(meshes, ratios, pictures)):
        x = .05 + .48 * i
        ax = fig.add_axes([x, .59, .43, .265]); ax.imshow(picture); ax.axis('off')
        ax.set_title(titles[i], loc='left', fontsize=15, weight='bold', color='#163247', pad=8)
        fig.text(x, .565, f'{len(faces):,} triangles · {counts[i]:,} aiguilles'.replace(',', ' '), fontsize=14, weight='bold', color='#ba4824' if counts[i] else '#216e52')
        ax = fig.add_axes([x + .055, .18, .32, .32])
        triangles = vertices[faces]
        projected = triangles[:, :, axes]
        low, high = centre[axes] - span / 2, centre[axes] + span / 2
        selected = ((triangles.max(1) >= centre - span / 2) & (triangles.min(1) <= centre + span / 2)).all(1)
        order = np.argsort(sign * triangles[selected, :, hidden_axis].mean(1), kind='stable')
        colors = np.tile(matplotlib.colors.to_rgba('#dce8ef'), (int(selected.sum()), 1))
        colors[q[selected] < .001] = matplotlib.colors.to_rgba('#eb835b')
        ax.add_collection(PolyCollection(projected[selected][order], facecolors=colors[order], edgecolors='#425f72', linewidths=.25, rasterized=True))
        flagged = selected & (q < .001)
        ax.add_collection(PolyCollection(projected[flagged], facecolors='none', edgecolors='#d65325', linewidths=.9, rasterized=True))
        ax.set_xlim(low[0], high[0]); ax.set_ylim(low[1], high[1]); ax.set_aspect('equal')
        ax.set_xlabel('XYZ'[axes[0]] + ' [mm]'); ax.set_ylabel('XYZ'[axes[1]] + ' [mm]')
        ax.set_title('Même zone locale · projection des triangles réels', fontsize=10.5, pad=9)
        ax.set_facecolor('white')
    fig.text(.05, .12, 'Orange : aire double / plus grande arête² < 0,001 · critère historique inchangé', fontsize=11.5, color='#9d4829')
    fig.text(.05, .087, ('Zoom : cube visuel de %.3f mm centré sur la pire aiguille ; contours orange = triangles signalés.' % span).replace('.', ','), fontsize=10, color='#435e6f')
    fig.text(.05, .056, 'Ces images et le compte d’aiguilles ne remplacent pas les contrôles distincts de fermeture, intersections et distance au BREP.', fontsize=10, color='#435e6f')
    output.mkdir(); exports = {}
    for suffix in ('png', 'svg', 'pdf'):
        metadata = {'Creator': 'Carrier actual surface evidence'}
        if suffix == 'svg': metadata['Date'] = None
        if suffix == 'pdf': metadata.update(CreationDate=None, ModDate=None)
        path = output / ('carrier-surface-before-after.' + suffix)
        fig.savefig(path, dpi=180, facecolor=fig.get_facecolor(), metadata=metadata)
        exports[path.name] = sha(path)
    plt.close(fig)
    if {name: sha(HERE / name) for name in pins} != before:
        raise ValueError('A figure input changed')
    receipt = dict(status='actual_complete_STL_comparison_rendered_no_admission', input_sha256=before, exports_sha256=exports,
        needle_counts=counts, complete_triangle_counts=[len(f) for v, f in meshes], old_mask_checked_against_actual_libigl_audit=True,
        worst_old_triangle_index=worst, worst_old_quality=float(ratios[0][worst]), zoom_centre_mm=centre.tolist(), zoom_span_mm=span,
        zoom_projected_axes=axes, zoom_depth_axis=hidden_axis, zoom_is_display_only=True, zoom_local_3D_bbox_intersection_only=True, flagged_edges_overlaid=True, flat_lighting_for_visual_readability=True, all_faces_retained_in_global_views=True, geometry_modified=False,
        new_topology_or_fidelity_admission=False, runtime=dict(numpy=np.__version__,matplotlib=matplotlib.__version__,vispy=vispy.__version__), seconds=time.monotonic()-started)
    with (output / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False); stream.write('\n')
    signal.alarm(0)
    print(json.dumps({key:receipt[key] for key in ('status','needle_counts','complete_triangle_counts','seconds')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    render(parser.parse_args().output)
