#!/usr/bin/env python3
"""Render a neutral preview of a generated PLY through headless Blender."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy
from mathutils import Vector


def look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> int:
    if "--" not in sys.argv:
        raise SystemExit("expected: -- INPUT_PLY OUTPUT_PNG")
    values = sys.argv[sys.argv.index("--") + 1 :]
    if len(values) != 2:
        raise SystemExit("expected: -- INPUT_PLY OUTPUT_PNG")
    source, output = Path(values[0]).resolve(), Path(values[1]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.ply_import(filepath=str(source))
    engine = bpy.context.active_object
    engine.data = engine.data.copy()
    engine.color = (0.26, 0.28, 0.31, 1.0)
    corners = [engine.matrix_world @ Vector(corner) for corner in engine.bound_box]
    lower = Vector(tuple(min(point[index] for point in corners) for index in range(3)))
    upper = Vector(tuple(max(point[index] for point in corners) for index in range(3)))
    centre = (lower + upper) / 2.0
    size = max(upper - lower)

    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = centre + Vector((1.35, -1.75, 1.05)).normalized() * size * 2.0
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = size * 1.35
    look_at(camera, centre)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = True
    scene.display.shading.background_type = "THEME"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    scene.render.film_transparent = False
    bpy.ops.render.render(write_still=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
