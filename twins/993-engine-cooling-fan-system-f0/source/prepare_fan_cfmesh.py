"""Reuse the conforming-mesh surfaces for a bounded cfMesh recovery attempt."""
import argparse
from pathlib import Path
import trimesh

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("surfaces", type=Path, help="Directory of rotor/duct/inlet/outlet STL in mm")
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
(args.output / "system").mkdir()
with (args.output / "boundary.stl").open("w") as stream:
    for name in ("rotor", "duct", "inlet", "outlet"):
        mesh = trimesh.load_mesh(args.surfaces / (name + ".stl"))
        if name == "rotor":
            assert mesh.is_watertight and mesh.body_count == 1
            assert 240 < mesh.extents[0] < 246, "Expected the 245 mm pilot"
            mesh.invert()  # Inner boundary points out of the fluid domain.
        mesh.apply_scale(.001)
        lines = trimesh.exchange.stl.export_stl_ascii(mesh).splitlines()
        lines[0], lines[-1] = "solid " + name, "endsolid " + name
        stream.write("\n".join(lines) + "\n")
(args.output / "system/meshDict").write_text(
    'FoamFile { version 2; format ascii; class dictionary; object meshDict; }\n'
    'surfaceFile "boundary.stl";\nmaxCellSize 0.012;\nboundaryCellSize 0.002;\n'
    'localRefinement { rotor { cellSize 0.0008; refinementThickness 0.003; } }\n')
