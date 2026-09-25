# 0001 — Open local toolchain

Date: 2026-08-28

## Decision

Use FreeCAD as the main parametric CAD, complemented by OpenSCAD, Blender,
MeshLab, CloudCompare, Gmsh, CalculiX, ParaView and open-source slicers.

## Reasons

- Master formats accessible without a subscription
- Work possible on macOS, Linux and Windows
- Automation and reproducibility
- Less vendor lock-in
- Consistency with a public, editable catalogue

## Accepted limitation

LPBF machine preparation will generally remain proprietary at the manufacturer.
The project controls the inputs, requirements and evidence, without claiming to
control the manufacturer's in-house production software.
