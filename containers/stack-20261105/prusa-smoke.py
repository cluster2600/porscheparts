"""Slice a synthetic cube; this does not select or qualify a printer."""
import json
from pathlib import Path
import subprocess
import tempfile

vertices = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
            (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10)]
faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
         (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
         (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
with tempfile.TemporaryDirectory() as directory:
    model = Path(directory) / "cube.stl"
    lines = ["solid synthetic_cube"]
    for face in faces:
        lines.extend(["facet normal 0 0 0", "outer loop"])
        lines.extend("vertex " + " ".join(map(str, vertices[index])) for index in face)
        lines.extend(["endloop", "endfacet"])
    lines.append("endsolid synthetic_cube")
    model.write_text("\n".join(lines) + "\n")
    output = Path(directory) / "cube.gcode"
    subprocess.run(["prusa-slicer", "--export-gcode", "--output", str(output), str(model)],
                   check=True, timeout=180)
    text = output.read_text()
    assert "PrusaSlicer 2.9.7" in text
    assert any(line.startswith("G1 ") and " E" in line for line in text.splitlines())
    print(json.dumps({"status": "synthetic_cube_sliced", "bytes": output.stat().st_size,
                      "printer_qualified": False}))
