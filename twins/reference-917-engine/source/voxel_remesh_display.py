#!/usr/bin/env python3
"""Create a closed display-only reconstruction with Blender's voxel remesher.

Run this file through Blender, not the system Python:
``blender --background --python voxel_remesh_display.py -- input.ply output.stl 2.0``.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> tuple[Path, Path, float, float]:
    if "--" not in sys.argv:
        raise SystemExit("expected: -- INPUT_MESH OUTPUT_STL VOXEL_SIZE")
    values = sys.argv[sys.argv.index("--") + 1 :]
    if len(values) not in (3, 4):
        raise SystemExit("expected: -- INPUT_MESH OUTPUT_STL VOXEL_SIZE [SCALE]")
    scale = float(values[3]) if len(values) == 4 else 1.0
    return Path(values[0]).resolve(), Path(values[1]).resolve(), float(values[2]), scale


def export_binary_stl(obj: bpy.types.Object, output: Path) -> None:
    mesh = obj.data
    mesh.calc_loop_triangles()
    matrix = obj.matrix_world
    with output.open("wb") as stream:
        stream.write(b"3dprinting993 display-only 917 engine".ljust(80, b"\0"))
        stream.write(struct.pack("<I", len(mesh.loop_triangles)))
        for triangle in mesh.loop_triangles:
            points = [matrix @ mesh.vertices[index].co for index in triangle.vertices]
            normal = (points[1] - points[0]).cross(points[2] - points[0])
            normal = normal.normalized() if normal.length else Vector((0.0, 0.0, 0.0))
            stream.write(struct.pack("<3f", *normal))
            for point in points:
                stream.write(struct.pack("<3f", *point))
            stream.write(struct.pack("<H", 0))


def main() -> int:
    source, output, voxel_size, scale = arguments()
    if voxel_size <= 0 or scale <= 0:
        raise SystemExit("voxel size and scale must be positive")
    output.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    if source.suffix.lower() == ".ply":
        bpy.ops.wm.ply_import(filepath=str(source))
    elif source.suffix.lower() == ".obj":
        bpy.ops.wm.obj_import(filepath=str(source))
    else:
        raise SystemExit(f"unsupported input format: {source.suffix}")

    objects = [item for item in bpy.context.scene.objects if item.type == "MESH"]
    if not objects:
        raise SystemExit("no mesh imported")
    bpy.ops.object.select_all(action="DESELECT")
    for item in objects:
        item.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    engine = bpy.context.view_layer.objects.active
    engine.name = "Porsche_917_display_only"
    engine.data = engine.data.copy()
    engine.scale = (scale, scale, scale)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    engine.data.remesh_voxel_size = voxel_size
    engine.data.remesh_voxel_adaptivity = 0.0
    engine.data.use_remesh_preserve_volume = True
    bpy.ops.object.voxel_remesh()

    # The voxel-remesh operator can leave a shared mesh datablock in headless
    # Blender.  Make it single-user before applying the derived decimator.
    engine.data = engine.data.copy()
    bpy.ops.object.modifier_add(type="DECIMATE")
    modifier = engine.modifiers[-1]
    modifier.decimate_type = "COLLAPSE"
    modifier.ratio = 0.65
    modifier.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    export_binary_stl(engine, output)

    report = {
        "input": str(source),
        "output": str(output),
        "classification": "display_print_nonfunctional",
        "voxel_size_obj_units": voxel_size,
        "source_to_output_scale": scale,
        "vertices": len(engine.data.vertices),
        "polygons": len(engine.data.polygons),
        "warning": "OBJ units are not confirmed as millimetres; do not manufacture before scale validation.",
    }
    output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
