"""Stable scan coordinate frame and provisional interface planes.

The values come from large planar facets in the purchased scan.  OBJ units
look like millimetres, but the scale remains unconfirmed until a physical
dimension is checked.
"""

from __future__ import annotations

import numpy as np

C_AXIS = np.array([0.09216808492652868, -0.8170262691134965, -0.5691863664033568])
B_HINT = np.array([-0.66828442, 0.37015754, -0.64527462])
A_AXIS = np.cross(B_HINT, C_AXIS)
A_AXIS /= np.linalg.norm(A_AXIS)
B_AXIS = np.cross(C_AXIS, A_AXIS)
B_AXIS /= np.linalg.norm(B_AXIS)

FRAME = np.vstack((A_AXIS, B_AXIS, C_AXIS))

COMBUSTION_FACE_C = -88.0
HEAD_BACK_C = -175.0
LOW_PORT_FACE_B = -251.0
HIGH_PORT_FACE_B = -62.0


def scan_to_abc(points: np.ndarray) -> np.ndarray:
    """Project scan XYZ points into the right-handed A/B/C frame."""

    return np.asarray(points) @ FRAME.T

