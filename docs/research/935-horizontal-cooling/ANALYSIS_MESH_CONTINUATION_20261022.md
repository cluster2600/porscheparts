# 935 analysis-mesh correction — October 22, 2026

The root README's order remains retained observations → PicoGK design master →
independent geometry checks → calculation meshes → reference solvers and numerical
acceptance. This correction concerns the calculation mesh of the horizontal 935
rotor. The design master, historical interfaces and material cards are retained.
The preceding [native GPU study](NATIVE_GPU_CONTINUATION_20261022.md) is merged
through [PR #275](https://github.com/cluster2600/porscheparts/pull/275). Its rental
was destroyed after verified backups. This follow-up uses the Mac and Kali1 over
Thunderbolt, without another rental.

The [aggregate native receipt](analysis-mesh-20261022.json) binds the public
sources to the [private evidence release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/analysis-mesh-935-20261022).

## Diagnosis

The previous 861,404-triangle approximation passes the complete 0.0225-unit
surface-envelope check, including closure and self-intersections. Independent
whole-surface diagnostics nevertheless find **23,407 triangles below 0.1°**,
against **16** in the original PicoGK export. Approximation error and element
shape need separate checks. Its passing distance certificate remains valid;
mechanical mesh admission remains false.

GDB first reproduces TetGen's help exception `0`, then reads rotor exception
**2**, with a backtrace through `repair_badqual_tets` and `improve_mesh`.
Upstream identifies code 2 as an internal error, distinct from memory,
self-intersection and small-feature codes. [TetGen error codes](https://wias-berlin.de/software/tetgen/1.5/doc/manual/manual009.html).

Removing quiet output changes no numerical parameter. The rejected `-O0` trial
still enters mesh improvement: upstream 1.6 calls that phase for PLC input
independently of the flip level. Its earlier `mesh_improvement_disabled` flag
expresses the intended setting; a separate preserved interpretation corrects it.

The unchanged upstream TetGen 1.5.1 release is built locally with assertions and
passes the analytic tetrahedron control. The old-surface rotor job reaches its
900-second limit. Rootless Gmsh 4.12.1 passes raw and optimized tetrahedron
controls; its old-surface Delaunay job reaches 900 seconds and HXT exits 139 after
272.96 seconds. These trials supply no accepted rotor volume.

MeshLab diagonal-change proposals are also preserved. A synthetic control rejects
the default smoothing because it moves vertices. With smoothing disabled, planar
flips reduce the count below 0.1° to 11,583 while retaining every vertex coordinate.
Adding T-vertex edge flips reduces it to 187, but the complete CGAL
validity/self-intersection gate rejects that proposal. The passing Trimesh closure
and winding checks do not establish the missing geometric acceptance.

## Corrected analysis surface

The new [quality-preserving simplifier](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/)
starts again from the complete **original PicoGK export**, with the previous
0.25° sharp-edge constraint and Lindstrom–Turk cost/placement. It rejects a collapse
when any surviving affected triangle would have
`4*sqrt(3)*area/sum(edge_length_squared) < 0.05`, then applies the normal-change
filter. This is a numerical proposal rule. Inherited bad triangles can remain.

The generator uses CGAL **6.2.1**, Boost **1.90.0** and GCC **15.3.0**, with
`-O2 -frounding-math` and assertions retained. Earlier isolated CGAL 5.5.1
proposal-build failures against modern compilers are preserved. The accepted
build uses no compiler diagnostic suppression or library-source patch.
The independent **CGAL 5.5.1** envelope checker remains byte-identical to the
previous qualified binary, with its original controls and bound.

Native CMake/CTest passes five analytic triangle controls and positive, needle
and empty-placement edge-profile controls. A separate closed-cube fixture reduces
768 triangles to 180 while retaining unit volume and every triangle on an original
cube plane. Existing output files and dangling output symlinks are refused intact.

The corrected rotor contains **435,529 vertices and 871,078 triangles**. The actual
float32 export passes the complete bidirectional check against all **1,322,970**
original triangles, including topology and self-intersections, at **0.0225
uncalibrated scan units**. The original 0.0025-unit reserve remains. The published
generator reproduces the accepted double OFF bytes and every quantized coordinate
and triangle exactly; this identity permits explicit reuse of the complete
geometric certificate.

Independent Mac diagnostics retain one closed body, consistent winding and Euler
characteristic −10. The corrected surface retains the original **16** triangles
below 0.1° and **99** below 1°. It has 28,052 below 5°, against 588 originally;
the new rule does not make every triangle well shaped. Relative volume difference
is **7.65411e-7**; relative inertia-matrix difference is **1.19944e-6**.

## Volume and mechanical acceptance

The unchanged preparer verifies every indexed triangle against the new binary
STL and writes a fresh explicit analysis case. TetGen 1.6 still aborts after
17.48 seconds; GDB again identifies exception 2 in bad-tet repair. Surface-quality
improvement alone has therefore not resolved that mesher failure.

Gmsh's documented initial-volume mode completes, saves a raw checkpoint, and
optimizes it explicitly. The raw mesh contains **1,451,658 tetrahedra**, the
optimized proposal **1,381,778**, with 441,241 nodes and 871,080 stored boundary
triangles. The native job completes in 186.98 seconds. The boundary triangulation
changes. The independent audit refuses **both volumes**: each contains **ten
exactly zero-volume cells**, with no inverted cells. Exact integer predicates
confirm this is not merely a floating-point quality-display artefact. Connectivity
has one component, matching stored boundary incidence and no nonmanifold faces;
the total volume agrees to 2.22e-16 relatively. Those passing checks do not
override singular cells. No cell is discarded to obtain acceptance and no
CalculiX job is launched on these proposals.
[Gmsh algorithm options](https://gmsh.info/doc/texinfo/gmsh.html#Mesh-options).

The ten flat cells involve sixteen vertices in two local regions; their complete
incident star contains 180 cells. Some affected vertices are on the boundary.
This localization is preserved for a targeted follow-up; no coordinate is moved
and no cell deleted by the diagnostic. A further ordinary Delaunay run on the
corrected surface reaches its 900-second limit.

Netgen is not compiled into the rootless Linux Gmsh package. An isolated Mac
ARM64 Gmsh 4.15.2 wheel is installed by its PyPI SHA-256, with the loaded library
and Python-module hashes recorded. Its synthetic resume control returns the same
tetrahedron twice, changing exact total volume from 1/6 to 1/3. The unchanged
control criterion refuses it and the rotor is not run through that path.

Native CMake/CTest and the thirteen existing conforming-volume unit tests pass.
The first broad Linux snapshot run exposes group-writable archive modes and a
missing Git index; restoring checkout metadata and `umask 022` resolves the guard
test failures without changing their checks. The next full run has one remaining
environment failure: the installed .NET 6 SDK cannot build a .NET 9 witness.
The final GitHub Linux `make check` run is retained separately from these local
environment attempts.

The previous conditional P1 fields and material/speed projections remain an
unconverged study. This surface correction establishes no new stress, fatigue
life, usable speed, fan curve or manufacturing release. Scale, seventeen
interfaces, transmission internals, process data, structural convergence,
accepted 935 CFD and the physical bench remain open. PhysicsNeMo still has no
accepted rotor reference dataset to learn from.
