"""Try the retained V5 carrier against the separate, unmeasured F0 bracket."""
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
PART = ROOT / 'parts/993-eng-carrier-0001'
FAMILY = ROOT / 'twins/993-engine-mount-system-f0'


def pattern_screen(carrier, bracket, carrier_radius, bracket_radius, bolt_radius):
    """Necessary spacing condition, allowing every hole assignment and rigid pose."""
    a, b = np.asarray(carrier, dtype=float), np.asarray(bracket, dtype=float)
    for points in (a, b):
        if (points.shape != (4, 2) or not np.isfinite(points).all()
                or len(np.unique(points, axis=0)) != 4
                or np.linalg.matrix_rank(points-points.mean(0)) != 2):
            raise ValueError('Four finite, distinct, noncollinear hole centres are required')
    radii = np.array([carrier_radius, bracket_radius, bolt_radius], dtype=float)
    if not np.isfinite(radii).all() or (radii <= 0).any():
        raise ValueError('Finite positive hole and bolt radii are required')
    da = np.linalg.norm(a[:, None]-a[None, :], axis=2)
    db = np.linalg.norm(b[:, None]-b[None, :], axis=2)
    # Pair distances are rigid invariants; two centre errors can change a pair by at most 2e.
    bound = min(float(np.max(abs(da-db[np.ix_(p, p)])))/2
                for p in itertools.permutations(range(4)))
    clearance = float(carrier_radius+bracket_radius-2*bolt_radius)
    rejected = min(carrier_radius, bracket_radius) < bolt_radius or bound > clearance+1e-8
    return {'minimum_possible_max_axis_error_lower_bound_mm': bound,
            'combined_radial_bolt_clearance_mm': clearance,
            'spacing_rejected': bool(rejected),
            'criterion': 'Necessary condition for straight bolts normal to parallel mating faces; a non-rejection is not fit approval',
            'fitment_validated': False, 'manufacturing_authorized': False}


def run(output):
    import trimesh
    from build123d import Axis, GeomType, Vector, import_step
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    source = PART / 'derived/bionic-flat-20261012/carrier-flat.step'
    flat_path = PART / 'source/bionic-20261011/flat-results.json'
    flat = json.loads(flat_path.read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(source) == flat['geometry']['flat_STEP_sha256']
    bracket_path = FAMILY / 'derived/993-ENG-BRACKET-0001.stl'
    receipt_path = FAMILY / 'derived/study-report.json'
    receipt = json.loads(receipt_path.read_text())
    assert digest(bracket_path) == receipt['artifacts'][bracket_path.name]
    spec_path = FAMILY / 'source/engine-bracket.json'
    assert digest(spec_path) == receipt['inputs'][str(spec_path.relative_to(ROOT))]
    spec = json.loads(spec_path.read_text())['parameters']
    contract_path = FAMILY / 'interface-contract.json'
    contract = json.loads(contract_path.read_text())
    assert contract['manufacturing_authorized'] is False
    assert contract['interfaces']['bracket_to_engine']['measurement_evidence'] is None

    # Undo build placement only; never alter a hole or reshape either source component.
    body = import_step(source).translate(Vector(*(-np.array(flat['orientation']['translation_mm']))))
    body = body.rotate(Axis.Z, -45)
    assert body.is_valid and len(body.solids()) == 1
    assert abs(body.volume/flat['geometry']['flat_readback_volume_mm3']-1) < 1e-8
    holes = []
    for face in body.faces():
        if face.geom_type != GeomType.CYLINDER:
            continue
        cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
        x, y, _ = cylinder.Location().Coord()
        if (abs(x) < 70 and abs(y) < 35 and abs(cylinder.Radius()-5.5) < 1e-7
                and abs(abs(cylinder.Axis().Direction().Z())-1) < 1e-7):
            bounds = face.bounding_box()
            holes.append([x, y, cylinder.Radius(), bounds.min.Z, bounds.max.Z])
    holes = np.unique(np.round(holes, 6), axis=0)
    assert holes.shape == (4, 5) and np.allclose(holes[:, 2:], [5.5, -4, 4])
    centres = holes[:, :2]
    vertices, faces = body.tessellate(0.08, 0.12)
    carrier = trimesh.Trimesh(np.array([tuple(v) for v in vertices]), np.array(faces))
    bracket = trimesh.load_mesh(bracket_path)
    assert bracket.is_watertight and bracket.is_winding_consistent
    assert trimesh.creation.box().contains([[0, 0, 0], [3, 0, 0]]).tolist() == [True, False]

    section = bracket.section(plane_origin=[0, 0, 4], plane_normal=[0, 0, 1])
    circles = []
    for loop in section.discrete:
        xy = loop[:-1, :2]
        if not (9 < np.ptp(xy, axis=0).min() and np.ptp(xy, axis=0).max() < 12):
            continue
        cx, cy, offset = np.linalg.lstsq(np.c_[2*xy, np.ones(len(xy))], (xy*xy).sum(1), rcond=None)[0]
        radius = float(np.sqrt(offset+cx*cx+cy*cy))
        residual = float(np.max(abs(np.linalg.norm(xy-[cx, cy], axis=1)-radius)))
        assert residual < 0.05
        circles.append([cx, cy, radius, residual])
    assert len(circles) == 4
    circles = np.array(sorted(circles, key=lambda c: (round(c[0]), round(c[1]))))
    h = spec['study_hole_half_span_x_mm']['value']
    k = spec['study_hole_half_span_y_mm']['value']
    nominal = np.array(list(itertools.product((-h, h), (-k, k))))
    assert np.allclose(circles[:, :2], nominal, atol=0.05)
    bracket_radius = spec['study_hole_diameter_mm']['value']/2
    assert np.allclose(circles[:, 2], bracket_radius, atol=0.05)
    comparison = pattern_screen(centres, nominal, 5.5, bracket_radius, 5)
    comparison['axis_errors_in_centred_pose_mm'] = np.linalg.norm(centres-nominal, axis=1).tolist()

    pose = np.diag([1., -1., -1., 1.])
    pose[2, 3] = -4
    bracket.apply_transform(pose)
    # shortcut: positive interior samples prove a clash; no finite sample set certifies clearance.
    angles = np.arange(72)*2*np.pi/72
    witnesses = []
    for x, y in centres:
        probes = np.array([[x+r*np.cos(a), y+r*np.sin(a), -8]
                           for r in (0, 2.5, 4.5) for a in angles])
        inside = bracket.contains(probes)
        witnesses.append({'carrier_axis_xy_mm': [x, y], 'samples': len(probes),
                          'samples_inside_bracket': int(inside.sum()),
                          'first_interference_point_mm': probes[inside][0].tolist() if inside.any() else None})

    meshes = {'Carrier_V5': (carrier, '#839aa9'), 'Bracket_F0_unmeasured': (bracket, '#daa34e')}
    for i, (x, y) in enumerate(centres):
        bolt = trimesh.creation.cylinder(radius=5, height=20, sections=48)
        bolt.apply_translation([x, y, -6])  # Under-head plane Z=4; nominal tip Z=-16.
        meshes[f'M10x20_shank_gauge_{i+1}'] = (bolt, '#c94344')
    scene = trimesh.Scene()
    for name, (mesh, colour) in meshes.items():
        item = mesh.copy()
        item.apply_scale(0.001)  # glTF uses metres; CAD and report use millimetres.
        item.visual.face_colors = [int(colour[i:i+2], 16) for i in (1, 3, 5)]+[255]
        scene.add_geometry(item, node_name=name, geom_name=name)
    scene.metadata = {'status': 'incompatible_unmeasured_study_pair', 'manufacturing_authorized': False}
    scene.export(output/'virtual-assembly.glb')
    reread = trimesh.load_scene(output/'virtual-assembly.glb')
    assert len(reread.geometry) == 6 and np.allclose(reread.bounds, scene.bounds, atol=1e-7)
    render(meshes, centres, nominal, output)
    inputs = [source, flat_path, bracket_path, receipt_path, spec_path, contract_path, Path(__file__)]
    result = {
        'status': 'incompatible_unmeasured_study_pair',
        'scope': 'V5 carrier vs separate F0 concept bracket, not the OEM bracket or an engine reconstruction',
        'source_geometry_modified': False,
        'inputs': {str(p.relative_to(ROOT)): digest(p) for p in inputs},
        'carrier_cylindrical_faces_xy_radius_zmin_zmax_mm': holes.tolist(),
        'bracket_mesh_section_z_mm': 4,
        'bracket_fitted_circles_xy_radius_max_residual_mm': circles.tolist(),
        'nominal_pattern_screen': comparison,
        'assumed_bracket_transform': pose.tolist(),
        'bolt_shank_interference_witnesses': witnesses,
        'bolt_stack': {'nominal_under_head_length_mm': 20, 'carrier_CAD_pad_mm': 8,
                       'bracket_study_pad_mm': spec['root_pad_height_mm']['value'],
                       'remaining_length_for_washers_nut_protrusion_mm': 20-8-spec['root_pad_height_mm']['value'],
                       'OEM_joint_stack_mm': None, 'thread_engagement_verified': False},
        'not_checked': ['OEM fit', 'bracket-to-engine interface', 'mount/body/exhaust clearances',
                        'complete part-to-part interference', 'bolt head/nut/tool access and installation path',
                        'thread geometry, runout, preload or strength'],
        'fitment_validated': False, 'manufacturing_authorized': False,
        'previous_V5_structural_rejection_still_applies': True,
        'artifacts': {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()},
        'GLB_readback': {'geometry_count': len(reread.geometry), 'units': 'metres', 'bounds_match': True},
    }
    (output/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'pattern': comparison, 'bolt_witnesses': witnesses, 'output': str(output)}, indent=2))


def render(meshes, centres, bracket_centres, output):
    import pyvista as pv
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    plot = pv.Plotter(off_screen=True, shape=(2, 1), window_size=(1600, 1200))
    for row in (0, 1):
        plot.subplot(row, 0)
        plot.set_background('#f4f5f2')
        for name, (mesh, colour) in meshes.items():
            poly = pv.PolyData(mesh.vertices, np.c_[np.full(len(mesh.faces), 3), mesh.faces])
            plot.add_mesh(poly, color=colour, smooth_shading=True, split_sharp_edges=True,
                          opacity=.65 if name.startswith('M10') else 1)
        plot.camera_position = [(180, -330, -220), (0, 0, -8), (0, 0, -1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = 180 if row == 0 else 62
        plot.add_text('V5 carrier + separate F0 bracket | assumed pose' if row == 0 else
                      'Close-up | red = nominal M10 x 20 shank gauges', font_size=17, color='#203544')
    plot.add_text('The existing CAD pair does not align. Neither part is measured OEM geometry.',
                  position='lower_left', font_size=13, color='#9a3033')
    plot.screenshot(output/'virtual-assembly.png')
    plot.close()
    fig, ax = plt.subplots(figsize=(12, 7), facecolor='#f4f5f2')
    ax.set_facecolor('#f4f5f2')
    for i, (a, b) in enumerate(zip(centres, bracket_centres)):
        ax.add_patch(Circle(a, 5.5, fill=False, edgecolor='#39658b', linewidth=2,
                            label='Carrier: diameter 11 mm' if i == 0 else None))
        ax.add_patch(Circle(b, 5.25, fill=False, edgecolor='#b67619', linewidth=2,
                            label='Bracket: nominal diameter 10.5 mm' if i == 0 else None))
        ax.plot([a[0], b[0]], [a[1], b[1]], color='#ad3539', linewidth=2)
    ax.set(xlim=(-65, 65), ylim=(-38, 42), xlabel='X (mm)', ylabel='Y (mm)', aspect='equal')
    ax.set_title('Virtual bolt alignment: 96 x 46 mm versus 100 x 40 mm\n'
                 'Centred axes differ by 3.606 mm; combined radial clearance is only 0.750 mm', pad=15)
    ax.legend(loc='upper center', fontsize=10)
    ax.grid(alpha=.2)
    fig.text(.5, .02, 'Existing hypothetical CAD pair only. OEM hole positions remain unknown.',
             ha='center', color='#963438')
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(output/'hole-alignment.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    run(sys.argv[1])
