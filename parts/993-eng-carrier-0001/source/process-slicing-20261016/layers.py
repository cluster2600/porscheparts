"""Preserve native slicing and hatching while excluding triangles outside a Z plane."""
import numpy as np
from pyslm import hatching
from pyslm.geometry import HatchGeometry
import trimesh


def face_z_bounds(mesh):
    """Call after the final build pose; do not transform the mesh afterwards."""
    heights = mesh.vertices[mesh.faces, 2]
    return np.column_stack((heights.min(axis=1), heights.max(axis=1)))


def section(mesh, z, bounds):
    if bounds.shape != (len(mesh.faces), 2) or not np.isfinite(z):
        raise ValueError('Invalid slice height or face bounds')
    tolerance = trimesh.constants.tol.merge
    local = np.flatnonzero((bounds[:, 0] <= z + tolerance) &
                           (bounds[:, 1] >= z - tolerance))
    # Same native cases and tolerance as Trimesh.section; no altered vertices.
    return mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1],
                        local_faces=local, cached_dots=mesh.vertices[:, 2] - z)


def layer_geometry(part, z, parameters, bounds):
    polygons = []
    mesh = part.geometry
    if mesh.bounds[0, 2] <= z <= mesh.bounds[1, 2]:
        path = section(mesh, z, bounds)
        if path is not None:
            planar, _ = path.to_planar(np.eye(4, dtype=np.float32))
            if not planar.is_closed:
                raise ValueError('Open planar section; automatic gap filling is forbidden')
            polygons = planar.polygons_full
    paths = [path for polygon in polygons for path in hatching.utils.poly2Paths(polygon)]
    if any(len(path) < 4 or not np.array_equal(path[0], path[-1]) for path in paths):
        raise ValueError('Open or incomplete part contour')
    if any(not polygon.is_valid for polygon in polygons):
        raise ValueError('Invalid section polygon')
    hatch = hatching.Hatcher()
    hatch.hatchAngle = parameters['hatch_angle_degrees']
    hatch.hatchDistance = parameters['hatch_distance_mm']
    hatch.spotCompensation = parameters['spot_compensation_mm']
    hatch.contourOffset = parameters['contour_offset_mm']
    hatch.volumeOffsetHatch = parameters['hatch_volume_offset_mm']
    hatch.numInnerContours = parameters['inner_contours']
    hatch.numOuterContours = parameters['outer_contours']
    layer = hatch.hatch(paths)
    contours, vectors = [], []
    if layer is not None:
        for item in layer.geometry:
            if isinstance(item, HatchGeometry):
                vectors.extend(item.coords.reshape(-1, 2, 2))
            else:
                contours.append(item.coords)
    vectors = np.asarray(vectors).reshape(-1, 2, 2)
    if not np.isfinite(vectors).all():
        raise ValueError('Non-finite hatch coordinates')
    return paths, contours, vectors, sum(polygon.area for polygon in polygons)
