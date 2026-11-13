"""Unchanged analytical cube and polygonal-bore fixture definition."""
import math

def fixtures():
    import numpy as np
    import trimesh
    vertices = np.array([[-5, -5, -5], [5, -5, -5], [5, 5, -5], [-5, 5, -5],
                         [-5, -5, 5], [5, -5, 5], [5, 5, 5], [-5, 5, 5]], dtype=np.float64)
    faces = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7]]
    for i in range(4):
        j = (i + 1) % 4
        faces.extend([[i, j, j + 4], [i, j + 4, i + 4]])
    cube = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces, dtype=np.int64),
                           process=False, validate=False)
    n, outer, inner, height = 64, 5.0, 2.0, 4.0
    theta = np.arange(n, dtype=np.float64) * (2 * np.pi / n)
    vertices = np.array([[radius * np.cos(a), radius * np.sin(a), z]
                         for z in (-height / 2, height / 2)
                         for radius in (outer, inner) for a in theta], dtype=np.float64)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        oi, oj, ii, ij = i, j, n + i, n + j
        ti, tj, ui, uj = 2 * n + i, 2 * n + j, 3 * n + i, 3 * n + j
        faces.extend([[oi, oj, tj], [oi, tj, ti], [ii, ui, uj], [ii, uj, ij],
                      [ti, tj, uj], [ti, uj, ui], [oi, ij, oj], [oi, ii, ij]])
    annulus = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces, dtype=np.int64),
                              process=False, validate=False)
    area = n * math.sin(2 * math.pi / n) * (outer ** 2 - inner ** 2) / 2
    return [
        ('cube', cube, 100.0, 0, 1000.0, {'edge_mm': 10.0}),
        ('annular_polygon_prism', annulus, area, 1, area * height,
         {'sides': n, 'outer_radius_mm': outer, 'inner_radius_mm': inner,
          'height_mm': height, 'ideal_circle_area_mm2': math.pi * (outer ** 2 - inner ** 2),
          'expected_area_formula': 'n*sin(2*pi/n)*(R**2-r**2)/2; exact regular polygon, not ideal circle'}),
    ]
