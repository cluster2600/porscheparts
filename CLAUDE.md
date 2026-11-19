# CAD & Scan-to-Digital-Twin Rules
- **Python Environment:** Always execute CAD and point-cloud scripts using `~/cad-env/bin/python`.
- **Scan-to-CAD Workflow:** Follow `~/.claude/skills/cad-skill/SKILL.md`. Use `open3d` and `trimesh` to clean, align, and slice raw 3D scans (`outline_from_scan.py`) before generating parametric CAD geometry. Never dump raw `.ply`/`.obj`/`.stl` vertex coordinates into chat context.
- **CAD & Export Standards:** Use `build123d` or `cadquery` for parametric parts (in millimeters, Z-up). Always export `.step` for engineering CAD and `.stl`/`.glb` for 3D printing and digital twin pipelines.
- **Mandatory Visual Inspection:** Before finishing any 3D modeling or scan-reconstruction task, render multi-view PNGs using `xvfb-run -a ~/cad-env/bin/python ~/.claude/skills/cad-skill/scripts/preview.py` (or PyVista/Trimesh) and inspect the rendered PNG images using your Read tool to verify watertightness and accuracy.
