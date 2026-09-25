# 0002 — Script-driven toolchain

Date: August 28, 2026

Partially revises [0001](0001-open-toolchain.md).

## Context

Decision 0001 chose free software, but named each tool by its graphical
interface. Yet almost all of the project's repetitive work — reconstruction,
mesh cleanup, STEP export, FE meshing, analysis, slicing — must be able to run
with no operator in front of the screen, on a machine rented by the hour, and be
rerun identically after a correction.

A tool whose normal use goes through clicks is not reproducible: no script, no
agent and no continuous integration can replay it.

## Decision

For each need, the tool chosen is the one that has a **command-line interface or
a complete Python API**, at equivalent quality and license.

| Need | 0001 | Chosen | Reason for the change |
|---|---|---|---|
| Structure from motion | Meshroom (GUI) | COLMAP + GLOMAP | Complete CLI, inspectable database, GLOMAP sharply reduces pose-estimation time |
| Dense reconstruction | Meshroom | COLMAP dense (CUDA) | Same chain, same format, no second ecosystem |
| Mesh cleanup | MeshLab (GUI) | pymeshlab | Same filters, called from Python; `meshlabserver` no longer exists |
| Point clouds | CloudCompare (GUI) | Open3D | Python API, scriptable registration and downsampling |
| Parametric CAD | FreeCAD (GUI) | build123d and CadQuery | Same OCCT kernel, but geometry written in Python, readable in review and exportable to STEP |
| FE meshing | Gmsh (GUI) | Gmsh Python API | Meshing driven by the script that builds the part |
| Analysis | CalculiX | CalculiX | Already command-line, text input deck |
| CFD | OpenFOAM | OpenFOAM + foamlib | Cases driven from Python rather than by hand-editing dictionaries |
| Slicing | PrusaSlicer | PrusaSlicer CLI | Batch slicing, without opening the interface |

## What does not change

- FreeCAD remains a legitimate tool for human review, STEP inspection and the
  interactive FEM workbench. It only stops being the master source.
- OpenSCAD remains valid: it is already code.
- Blender is still used, in `--background --python` mode, for heavy mesh
  operations and documentation renderings.
- Meshroom remains usable as a second opinion on a difficult reconstruction,
  installed on demand on the rented machine and not in the image.

## Consequences

- A part's master geometry can be a versioned Python file producing a
  reproducible STEP, alongside the `.FCStd` and `.scad` formats.
- Every step becomes replayable: same inputs, same command, same output.
- The container images in `containers/` materialize this chain.
- Cost: authors used to interactive drawing must read CAD code. The trade-off is
  that review by diff becomes possible, which a binary file rules out.
