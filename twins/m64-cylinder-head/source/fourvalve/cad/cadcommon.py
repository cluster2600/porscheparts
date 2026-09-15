"""Aides CadQuery communes aux jumeaux de composants (repère du plan d'étanchéité)."""
import math

import cadquery as cq
import numpy as np

import kinematics as kin
from layout import (PLUGS, VALVES, axis_up, cam_axis_point, cylinders, head_centre, valve_length)

V = cq.Vector


def _v(a):
    return V(float(a[0]), float(a[1]), float(a[2]))


def _cyl(p0, q0, r):
    p0, q0 = np.asarray(p0, float), np.asarray(q0, float)
    axis = q0 - p0
    length = float(np.linalg.norm(axis))
    return cq.Solid.makeCylinder(float(r), length, _v(p0), _v(axis / length))


def _tube(p0, direction, length, r_in, r_out):
    d = _v(direction)
    outer = cq.Solid.makeCylinder(float(r_out), float(length), _v(p0), d)
    return outer.cut(cq.Solid.makeCylinder(float(r_in), float(length), _v(p0), d)) if r_in > 0 else outer


def _halfspace(normal_angle_deg, height):
    box = cq.Solid.makeBox(800, 800, 800, V(-400, -400, -800))
    return box.rotate(V(0, 0, 0), V(0, 1, 0), normal_angle_deg).translate(V(0, 0, height))
