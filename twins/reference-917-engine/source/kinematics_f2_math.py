#!/usr/bin/env python3
"""Pure four-stroke kinematic helpers shared by F2 and F10 validators."""

from __future__ import annotations

import math


def cylinder_phase_deg(cylinder: int, firing_order: list[int]) -> float:
    """Return the firing phase on the 720-degree four-stroke cycle."""
    return float(firing_order.index(cylinder) * 60)


def cylinder_cycle_deg(cycle_angle_deg: float, cylinder: int, firing_order: list[int]) -> float:
    """Return a cylinder's 720-degree valve cycle without folding 12 phases to six."""
    return (cycle_angle_deg + cylinder_phase_deg(cylinder, firing_order)) % 720.0


def slider_delta_mm(angle_deg: float, crank_radius: float, rod_length: float) -> float:
    angle = math.radians(angle_deg)
    current = crank_radius * math.cos(angle) + math.sqrt(
        rod_length**2 - (crank_radius * math.sin(angle)) ** 2
    )
    return current - (crank_radius + rod_length)


def rod_tilt_deg(angle_deg: float, crank_radius: float, rod_length: float) -> float:
    return math.degrees(math.asin(crank_radius * math.sin(math.radians(angle_deg)) / rod_length))


def periodic_lift_mm(angle_deg: float, center_deg: float, duration_deg: float, maximum_lift: float) -> float:
    delta = (angle_deg - center_deg + 360.0) % 720.0 - 360.0
    half = duration_deg / 2.0
    if abs(delta) >= half:
        return 0.0
    return maximum_lift * 0.5 * (1.0 + math.cos(math.pi * delta / half))
