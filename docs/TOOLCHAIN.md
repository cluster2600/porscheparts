# Toolchain

The selection favors free, open-source, cross-platform software and open
formats. A proprietary tool is accepted only when an industrial machine or a
service provider imposes it, and it must not become the project's only editable
source.

At equal quality, the tool chosen is the one that runs without a graphical
interface: see [decisions/0002-scriptable-toolchain.md](decisions/0002-scriptable-toolchain.md).
The tables below therefore give the command or API used, not just the software
name. The corresponding container images are described in
[COMPUTE_ENVIRONMENT.md](COMPUTE_ENVIRONMENT.md).

## Acquisition and reconstruction

| Need | Preferred tool | Driven by | Output format |
|---|---|---|---|
| Camera poses | COLMAP then GLOMAP | CLI | SQLite database, poses |
| Dense reconstruction | COLMAP `patch_match_stereo` | CLI, CUDA required | Dense PLY |
| Mesh cleanup | pymeshlab | Python API | PLY, OBJ, STL |
| Point clouds | Open3D | Python API | PLY, PCD |
| Organic shapes | Blender `--background --python` | Python script | BLEND, OBJ, PLY |
| Photogrammetry second opinion | Meshroom `meshroom_batch` | CLI, installed on demand | OBJ, point cloud |

| Instrument capture | `scripts/capture_caliper.py` | CLI, pyserial | JSON measurement record |
| Driven photo capture | `scripts/capture_photoset.py` | CLI, gphoto2 | Images and manifest |

A commercial scanner may supply the data, but the exports must stay accessible
in a documented format.

A measurement copied by hand is not traceable. When the instrument can transmit
its reading, the record stores the machine timestamp and the instrument used;
otherwise it explicitly carries the `manual_entry` flag.

## CAD

| Need | Preferred tool | Use |
|---|---|---|
| Mechanical parts | build123d or CadQuery | CAD written in Python on the OCCT kernel, STEP export |
| Simple generative geometry | OpenSCAD | Models reproducible as code |
| Organic surfaces | Blender then solid reconstruction | Mesh reference, then parametric solid |
| Human review and interactive FEM | FreeCAD | STEP inspection, visual check |
| Functional assemblies | FreeCAD Assembly | Constraints, motion and interface review |

A part can therefore have as its master source a versioned Python script that
regenerates its STEP. A `.FCStd` file is still accepted; it is simply harder to
read in review.

For the global twin, STEP/FreeCAD remain the dimensional truth. OpenUSD can
serve as a federated scene to load zones, variants and visual trim without
merging every file into a monolithic model. A USD scene never carries a
manufacturing dimension on its own.

Order of master formats: `build123d` script, `.FCStd` or `.scad`, then `.step`.
The `.3mf` and `.stl` formats are manufacturing derivatives.

## Simulation and numerical inspection

| Need | Preferred tool | Driven by |
|---|---|---|
| Finite-element meshing | Gmsh | Python API |
| Mechanical analysis | CalculiX `ccx` | Text input deck |
| Result conversion | `ccx2paraview`, meshio | CLI and Python |
| Post-processing | PyVista, ParaView | Python script |
| Exploratory CFD | OpenFOAM + foamlib | CLI and Python |
| Local LPBF melt pool | ORNL AdditiveFOAM 2.0.0 on OpenFOAM 14 | CLI/MPI, correlated coupons required |
| Physics surrogate | NVIDIA PhysicsNeMo | Python/PyTorch after converged, correlated runs |
| CAD to scene | `usd-convert-cad 0.2.0` | CLI, STEP to binary OpenUSD |
| USD validation | `nvidia_usd_validate 1.21.0` | CLI and JSON report |
| Shared scene state | `ovstage 0.1.1.355824` | Python/C API |
| Rigid bodies | `ovphysx 0.5.11` | Python/C API, CPU or GPU |
| Rendering and sensors | OVRTX | Python/C API, RTX GPU |

These tools allow an initial study. For a critical part, the model, the load
cases, the properties of the printed lot and the results must be reviewed by a
competent person.

CalculiX/OpenFOAM remain the stress, thermal and fluid solvers. `ovphysx`
checks motion, contact and rigid assembly; OVRTX produces the images and
sensors. An Omniverse rendering therefore never replaces an FEA, and PhysicsNeMo
becomes useful only after a reference dataset has been built.

## Polymer printing

- PrusaSlicer on the command line for batch slicing, OrcaSlicer for interactive
  machine tuning
- UVtools for inspecting resin jobs, if needed
- 3MF as the working format whenever possible

## Titanium manufacturing

LPBF build preparation generally depends on the machine's proprietary software.
The project provides the manufacturer with:

- STEP and dimensioned drawing;
- material and standard;
- surfaces to machine;
- treatment and inspection requirements;
- file version and digest.

The manufacturer remains responsible for the final orientation, the supports and
the qualified parameters. The project keeps their reports without publishing the
service provider's trade secrets.

## Project management

- Git and GitHub for versions, issues and reviews
- Markdown and JSON as portable sources
- Python standard library for local checks
- GitHub Actions to run `make check` on the public repository
