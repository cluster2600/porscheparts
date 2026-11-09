"""Capture actual native-wall display geometry in a bounded CPU VTK lane.

The hash-bound input is a lossless native transport or a declared visual derivative.
No measured compatibility, composite physics or native Omniverse is inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import pyvista as pv
from vtkmodules.util.numpy_support import vtk_to_numpy


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', type=Path, required=True)
    parser.add_argument('--mesh-sha256', required=True)
    parser.add_argument('--native-sha256', required=True)
    parser.add_argument('--parameters', type=Path, required=True)
    parser.add_argument('--quality-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=120)
    parser.add_argument('--fps', type=int, choices=(12, 24), default=24)
    parser.add_argument('--full-native', action='store_true')
    args = parser.parse_args()
    if args.output.exists() or args.frames not in (0, 60, 120):
        parser.error('Use a fresh output and zero, 60 or 120 animation frames')
    if sha(args.mesh) != args.mesh_sha256:
        parser.error('Display source hash mismatch')
    quality = json.loads(args.quality_receipt.read_text())
    if (quality['native_stl_sha256'] != args.native_sha256 or quality['geometry_admitted']
            or quality['zero_area_triangle_count'] <= 0):
        raise ValueError('Require the actual rejected native-quality receipt for diagnostic capture')
    defect_note = f"Native mesh-quality screen rejected: {quality['zero_area_triangle_count']} collapsed faces retained."
    inputs = {'mesh': args.mesh_sha256, 'quality_rejection': sha(args.quality_receipt), 'parameters': sha(args.parameters),
              'renderer': sha(__file__), 'native_authority': args.native_sha256}
    mesh = pv.read(str(args.mesh))
    limit = 40_000_000 if args.full_native else 2_000_000
    if not mesh.n_cells or mesh.n_cells > limit or not np.isfinite(mesh.points).all():
        raise ValueError('Require a finite, bounded display mesh')
    # Native indexed transport avoids reconstructing STL's duplicated vertices
    # or allocating the legacy four-int face array for tens of millions of faces.
    coordinates = vtk_to_numpy(mesh.GetPoints().GetData())
    connectivity = vtk_to_numpy(mesh.GetPolys().GetConnectivityArray())
    signature = lambda a: hashlib.sha256(memoryview(a).cast('B')).hexdigest()
    original_signatures = [signature(coordinates), signature(connectivity)]
    args.output.mkdir(parents=True)
    frames = args.output/'frames'
    frames.mkdir()
    plotter = pv.Plotter(off_screen=True, window_size=(1600, 1100))
    plotter.set_background('#f5f6f7')
    plotter.add_mesh(mesh, color='#34444b', smooth_shading=False,
                     split_sharp_edges=False, copy_mesh=False,
                     ambient=.30, diffuse=.72, specular=.35, specular_power=28)
    # Lighting changes appearance only; the actual display vertices stay intact.
    plotter.remove_all_lights()
    for position, intensity in [((-1500, -2500, 3500), .9),
                                ((3000, 1700, 2200), .55),
                                ((500, 0, 4000), .35)]:
        plotter.add_light(pv.Light(position=position, focal_point=(1050, 0, 500), intensity=intensity))
    plotter.add_text('F2  |  SCULPTED CARBON CENTRAL CELL', position='upper_left',
                     font_size=16, color='#26343c')
    note = ('Actual full native PicoGK wall surface, losslessly transported.' if args.full_native else
            'Native PicoGK wall surface, explicitly reduced for display.')
    plotter.add_text('Assumed design. '+note+'\n'
                     'CPU VTK capture; fitment, strength and manufacture remain unqualified.\n'+defect_note,
                     position='lower_left', font_size=11, color='#43545d')
    plotter.enable_parallel_projection()
    plotter.enable_anti_aliasing('ssaa')
    target = np.asarray(mesh.center)
    target[2] += 35
    records = {}
    def capture(name, offset, up, scale):
        plotter.camera_position = [(target+np.asarray(offset)).tolist(), target.tolist(), up]
        plotter.camera.parallel_scale = scale
        plotter.reset_camera_clipping_range()
        plotter.render()
        path = args.output/(name+'.png')
        plotter.screenshot(path)
        return {'sha256': sha(path), 'camera': [list(p) for p in plotter.camera_position],
                'parallel_scale_mm': scale, 'display_triangles': mesh.n_cells}
    for name, offset, up, scale in [
            ('isometric', [-2800, -3400, 2100], [0, 0, 1], 1200),
            ('rear', [2800, 3000, 1900], [0, 0, 1], 1200),
            ('side', [0, -4500, 0], [0, 0, 1], 1000),
            ('top', [0, 0, 4500], [1, 0, 0], 1450),
            ('inside', [-800, -1200, 4000], [1, 0, 0], 1550)]:
        records[name] = capture(name, offset, up, scale)
    proxies = []
    parameters = json.loads(args.parameters.read_text())
    package = parameters['assembly_proxy_parameters']
    for axle in package['axles']:
        for side in (-1, 1):
            wheel = pv.Cylinder(center=(axle['x_mm'], side*axle['half_track_mm'], axle['centre_z_mm']),
                                direction=(0, 1, 0), radius=axle['tyre_outer_radius_mm'],
                                height=axle['tyre_width_mm'], resolution=96)
            proxies.append(plotter.add_mesh(wheel, color='#262b2f', ambient=.35, specular=.1))
    for module in package['module_reservations']:
        bounds = [module[key][axis] for axis in range(3) for key in ('min_mm', 'max_mm')]
        proxies.append(plotter.add_mesh(pv.Box(bounds=bounds), color='#a6b7be', opacity=.14,
                                        show_edges=True, edge_color='#70838e'))
    label = plotter.add_text('PACKAGE CONTEXT: nominal wheel cylinders and unattached module reservations',
                             position=(20, 1010), font_size=11, color='#43545d')
    records['assembly'] = capture('assembly', [-3500, -4300, 2600], [0, 0, 1], 2000)
    for actor in proxies+[label]:
        plotter.remove_actor(actor)
    orbit = []
    started = time.monotonic()
    for index in range(args.frames):
        azimuth = 225+360*index/args.frames
        angle = math.radians(azimuth)
        plotter.camera_position = [(target+np.array([3700*math.cos(angle),
                                    3700*math.sin(angle), 2050])).tolist(), target.tolist(), [0, 0, 1]]
        plotter.camera.parallel_scale = 1250
        plotter.reset_camera_clipping_range()
        plotter.render()
        path = frames/f'frame-{index:04d}.png'
        plotter.screenshot(path)
        orbit.append({'index': index, 'azimuth_deg': azimuth, 'sha256': sha(path)})
    capabilities = plotter.ren_win.ReportCapabilities()
    (args.output/'render-capabilities.txt').write_text(capabilities)
    plotter.close()
    sections = {}
    for station in (350, 900, 1050, 1750):
        section = mesh.slice(normal=(1, 0, 0), origin=(station, 0, 0))
        if not section.n_cells:
            raise ValueError('Missing native display section')
        view = pv.Plotter(off_screen=True, window_size=(1500, 1000))
        view.set_background('#f5f6f7')
        view.add_mesh(section, color='#34444b', line_width=2)
        view.add_text(f'F2  |  NATIVE DISPLAY SECTION AT X = {station} mm',
                      position='upper_left', font_size=16, color='#26343c')
        view.add_text('Assumed design station. Literal slice of the native wall surface; no cap added.\n'+defect_note,
                      position='lower_left', font_size=11, color='#43545d')
        view.enable_parallel_projection()
        view.camera_position = [(station-4000, 0, 600), (station, 0, 600), (0, 0, 1)]
        view.camera.parallel_scale = 930
        view.reset_camera_clipping_range()
        path = args.output/f'section_x{station}.png'
        view.screenshot(path)
        sections[str(station)] = {'sha256': sha(path), 'slice_cells': section.n_cells,
                                  'added_cap_or_geometry_repair': False}
        view.close()
    section = mesh.slice(normal=(0, 1, 0), origin=(0, 0, 0))
    if not section.n_cells:
        raise ValueError('Missing literal central longitudinal section')
    view = pv.Plotter(off_screen=True, window_size=(1500, 1000))
    view.set_background('#f5f6f7')
    view.add_mesh(section, color='#34444b', line_width=2)
    view.add_text('F2  |  NATIVE LONGITUDINAL SECTION AT Y = 0 mm',
                  position='upper_left', font_size=16, color='#26343c')
    view.add_text('Literal native wall slice; no cap or geometry repair.\n'+defect_note,
                  position='lower_left', font_size=11, color='#43545d')
    view.enable_parallel_projection()
    view.camera_position = [(1050, -4000, 520), (1050, 0, 520), (0, 0, 1)]
    view.camera.parallel_scale = 1000
    view.reset_camera_clipping_range()
    path = args.output/'longitudinal_y0.png'
    view.screenshot(path)
    sections['Y0'] = {'sha256': sha(path), 'slice_cells': section.n_cells,
                       'plane_origin_mm': [0, 0, 0], 'plane_normal': [0, 1, 0],
                       'camera': [list(p) for p in view.camera_position],
                       'added_cap_or_geometry_repair': False}
    view.close()
    if [signature(coordinates), signature(connectivity)] != original_signatures:
        raise ValueError('Capture modified display geometry')
    if sha(args.mesh) != args.mesh_sha256 or sha(args.parameters) != inputs['parameters']:
        raise ValueError('Source inputs changed during capture')
    result = {'classification': ('full_native_wall_lossless_transport_CPU_capture' if args.full_native else
                                 'authored_native_wall_display_derivative_CPU_capture'),
              'inputs': inputs, 'stills': records, 'sections': sections, 'frames': orbit,
              'fps': args.fps, 'frame_count': len(orbit),
              'full_native_geometry_retained': args.full_native,
              'point_and_connectivity_sha256_before_and_after': original_signatures,
              'orbit_elapsed_seconds': time.monotonic()-started,
              'geometry_unchanged_during_capture': True,
              'runtime': 'CPU VTK EGL; see retained capabilities',
              'native_omniverse': False, 'geometry_quality_admitted': False,
              'collapsed_native_faces_retained': quality['zero_area_triangle_count'], 'physical_validation': False}
    (args.output/'capture.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'stills': len(records), 'frames': len(orbit), 'triangles': mesh.n_cells}))


if __name__ == '__main__':
    main()
