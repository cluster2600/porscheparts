"""Exact IEEE-input support sections, encoded by correctly rounded float64.

This is a versioned hook for the immutable CORE4184, never a patch to its file.
Only support sheets are sliced here. The complete part cache is unaffected.
"""
from fractions import Fraction

import numpy as np


def support_section(surface, z, face_z_bounds):
    """Return each nonzero triangle/plane segment; shared edges are evaluated once.

    No near-plane classification, welding, rounding grid or gap filling is used.
    Python Fraction.__float__ rounds an exact rational to nearest/even binary64.
    CORE.unique_segments subsequently removes exact duplicate exposures.
    """
    z = float(z)
    if not np.isfinite(z):
        raise ValueError('Nonfinite support section height')
    vertices = np.asarray(surface.vertices)
    faces = np.asarray(surface.faces)
    bounds = np.asarray(face_z_bounds)
    if (vertices.dtype != np.float64 or vertices.ndim != 2 or vertices.shape[1] != 3
            or not np.isfinite(vertices).all() or bounds.shape != (len(faces), 2)):
        raise ValueError('Invalid support section input')
    # Bounds only select faces; exact Fraction signs decide every intersection.
    selected = np.flatnonzero((bounds[:, 0] <= z) & (bounds[:, 1] >= z))
    height = Fraction(z)
    points = {}

    def vertex(index):
        key = (int(index),)
        if key not in points:
            points[key] = tuple(Fraction(float(c)) for c in vertices[index])
        return points[key]

    def crossing(a, b):
        key = tuple(sorted((int(a), int(b))))
        if key not in points:
            p, q = vertex(key[0]), vertex(key[1])
            fraction = (height-p[2])/(q[2]-p[2])
            points[key] = tuple(p[i]+fraction*(q[i]-p[i]) for i in range(3))
        return points[key]

    segments = []
    for face in faces[selected]:
        distance = vertices[face, 2]-z
        if np.all(distance == 0):
            # A horizontal sheet has area, not a unique exposure centerline.
            raise ValueError('Coplanar support triangle requires a separate exposure rule')
        cut = [vertex(i) for i in face[distance == 0]]
        for a, b in zip(face, np.roll(face, -1)):
            if (vertices[a, 2] < z < vertices[b, 2]) or (vertices[b, 2] < z < vertices[a, 2]):
                cut.append(crossing(a, b))
        cut = list(dict.fromkeys(cut))
        if len(cut) == 2:
            if cut[0][:2] == cut[1][:2]:
                raise ValueError('Support cut has zero projected exposure length')
            encoded = [[float(c) for c in point] for point in cut]
            if encoded[0][:2] == encoded[1][:2]:
                raise ValueError('A nonzero exact support cut collapses in float64')
            segments.append(encoded)
        elif len(cut) > 2:
            raise ValueError('Invalid support triangle cut')
    return np.asarray(segments, dtype=np.float64).reshape(-1, 2, 3)
