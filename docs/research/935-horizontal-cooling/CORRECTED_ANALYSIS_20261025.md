# 935 corrected rotor: bounded analysis surface and fresh fluid-case input

This continuation uses the guarded PicoGK root correction reported in the
[preceding checkpoint](ROOT_MESH_RESUME_20261025.md). It concerns the **horizontal
935 rotor**. The shroud, drive, engine interfaces and complete cooling system
still require their own measured assembly and solver evidence.

The first, 0.6-source-unit root-closing STL is
`ee8f91167f6147edd125b2b4db9da65a5704aac95879a82f2aab6bada779f9ed`.
The independently indexed mesh is
`9128da15ba5ac3ea55373c792006478deb5dd77713d52d38a9eac7c4b70d0c8e`.
Both remain private. The [OFF preparation source](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_surface.py)
checks both hashes and reads back every coordinate and triangle. Its output
contains 660,003 vertices and 1,320,006 triangles, with SHA-256
`5cdd1b993029a80921f995636a3a980027a66af7c87fc33ba935f7bf3a6458cf`.

## Bounded simplification

The existing [CGAL simplifier](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/quality_preserving_simplify.cpp)
was built on macOS with the already documented
[input-facet protection patch](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/protected-input-patches-20261022.patch).
This preserves three rings around inherited thin facets rather than silently
removing them. The source and patch are unchanged. The local toolchain was
CGAL 6.2.1, Boost 1.92.0, Apple Clang 21.0.0 with `-O2 -std=c++17
-frounding-math`; Python 3.12.11, NumPy 2.3.5 and Trimesh 5.1.0 handled
independent readback.

| Check | Result |
|---|---:|
| Simplified surface | 438,652 vertices; 877,304 triangles |
| Simplified OFF SHA-256 | `c8aef379ac3a66188518ecc247fb1970ffe80fa33cea1b49b0b87db098959ac9` |
| Connected components / boundary or nonmanifold edges | 1 / 0 |
| Euler characteristic / genus | 0 / 1 |
| Original thin facets below quality 0.05 retained with identical coordinates and connectivity | 121 / 121 |
| Source-to-candidate and candidate-to-source complete envelope | Pass / pass |
| Envelope bound / reserved numerical margin | 0.0225 / 0.0025 source units |
| Candidate volume / relative difference from corrected rotor | 431,014.075493 source units³ / +0.00011006% |

The [independent continuous-envelope checker](../../../twins/935-horizontal-cooling-system-f0/source/analysis-envelope/tiled_envelope.cpp)
tested all 1,320,006 source triangles and all 877,304 candidate triangles.
Its self-test includes a counterexample in which vertex-only proximity would
incorrectly pass. Closed topology, valid triangle mesh and complete
self-intersection checks passed. The candidate retains the source's 121 very
thin faces; simplification has not claimed to repair those observed facets.
The bound is relative to the corrected *reconstruction*, not the raw scans or
an authenticated manufacturing tolerance.

## Fresh OpenFOAM input

The [case preparation source](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_fluid_case.py)
accepts only these exact source and candidate hashes and the passing
bidirectional certificate. It reuses the earlier Foundation 13 pilot's
unchanged system dictionaries, including mesh-quality SHA-256
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`,
and replaces the old rotor OBJ with the corrected candidate. The existing
export helper reads back every SI OBJ vertex and face. The new private case is
`work/935-corrected-analysis-20261025/fluid-case-001/`; its rotor OBJ is
`4ea77849439ac1b525d000386d8fa8e564a7f311552117262e4b55e29cb42528`.
One uncalibrated source unit is provisionally mapped to 0.001 m, as in the
earlier pilot; this is **not** a verified physical scale.

The [reduced machine-readable receipt](corrected-analysis-20261025.json)
identifies the source, candidate, case and private checkpoint. The private
[release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
holds the OFFs, source copy, compiled controls, geometry receipts and case
without publishing scan-derived geometry in this repository. Its 20 archived
files were read back and hash-checked locally.

## Volume-mesh trials on the corrected surface

The private candidate OFF was also passed to Gmsh 4.15.2 on the Mac with its
877,304 triangles preserved as a discrete boundary. The Frontal algorithm
generated 1,462,151 raw and 1,387,601 optimized tetrahedra. Independent
readback found an exact coordinate-and-triangle bijection with the input
boundary, one connected tetrahedral region, no negative-volume cells and no
nonmanifold faces in either volume. **Both volumes contain 12 tetrahedra with
exactly zero volume, so both are refused for FEA.** All four vertices of each
zero-volume tetrahedron lie on the boundary, in two localized patches around
radial positions 84.87–88.87 uncalibrated source units. Altering those nodes
would change the certified surface and requires a new geometry assessment.

HXT generated a volume but volume elements referenced node tag 438653, absent
from both the exported node table and Gmsh's individual `getNode` lookup. Its
volume is refused. The Delaunay trial exceeded its 300-second controller limit
before writing a volume. No trial produced an admitted mechanical mesh.

The six attempts, independent audits, controller logs and a diagnostic plot
(`gmsh-trial-001/zero-cells-map-002.png`) are in the same private release as
`gmsh-volume-001.tar.gz`: SHA-256
`207986ede430ee98dc5db5f37c6615f186ac4c5f674d493ac0c79648ccf78be7`.
All 44 archive members were read back and hash-checked; GitHub's asset digest
matches the local archive. These trials are numerical evidence about this
particular analysis surface and mesher settings, not a strength calculation.

## Second hypothesis and inspection assembly

### Second root-closing hypothesis: 0.7 source unit

A fresh PicoGK reconstruction changed only the root-closing radius from 0.6
to 0.7 uncalibrated source unit. This parameter is a repair hypothesis, not a
measured historical dimension. Its private STL SHA-256 is
`5522ec1af957a4523244bc2b2f05ff902b52eb882e1cb3b2ef88b093ffb598eb`.
The surface audit found one closed genus-one component, with the original
outer and bore triangles preserved. The protected CGAL analysis surface has
878,730 triangles and SHA-256
`5d900f6da900b4bffac2fdacfd6e0a346f8c0259a19299725621d4fd1e48c12a`.
Complete bidirectional surface-envelope checks passed at a 0.0225-source-unit
bound relative to this reconstruction. The 0.7 native and analysis volumes
differ by +0.00015718%.

Gmsh 4.15.2 Frontal produced 1,464,371 raw and 1,393,021 optimized
tetrahedra. Independent exact-arithmetic readback found **zero zero-volume or
negative-volume tetrahedra** in both, an identical boundary, one connected
volume, and the expected analysis-surface volume. This clears the basic
geometric volume screen that the 0.6 candidate failed. It does **not** clear
mechanical mesh quality: the optimized mean-ratio minimum is
`1.77149e-05`, with 3,255 tetrahedra below 0.01. Netgen optimization did
not produce an output within 300 seconds; three TetGen attempts failed during
internal facet repair. No FEA result is accepted.

The private machine-readable numerical receipt has SHA-256
`c70dcfcd721f019c4e159dc378f6392d1376e135598de08a3946282ed2536859`.
The private `root-radius-0p7-001.tar.gz` has SHA-256
`ea2a611dd512d9e6ef50b0dc1539e0d93bc1f6509c568daa7eef3cf22cf11a0a`;
all 42 members and the GitHub asset digest were checked.

### PicoGK inspection assembly with the 0.7 rotor

The existing PicoGK assembly program was rebuilt without changing its source.
It placed this rotor with the observed 935 drive/support scan, a **provisional**
shroud, and a **917 engine scan used solely as comparative context**. The four
components contain 7,262,969 triangles. Independent export readback preserved
their transforms and triangle identities in GLB and SI-unit USD. At the
assumed, unverified scale, the rotor/shroud radial separation is 6.258 mm;
the conservative swept-annulus screens found zero candidate drive triangles.
These are surface screens at a hypothetical pose, not confirmed interfaces,
occupied-body interference checks, thermal clearances or a 935 engine fit.
The inspection render still shows incomplete blade sectors.

The native assembly, GLB, USD, four-view PNG and receipts are saved in the
same private release as `assembly-root-0p7-001.tar.zst`, SHA-256
`fb9b033ec360790395a92c2e3044e98e6728a5012b4a100965371b48ebe31c0d`.
Its 19 source members and GitHub asset digest were checked. The six
non-finite STL normals in the 917 context scan were zeroed in a display-only
copy; all triangle coordinates and the PicoGK source files were unchanged.

### Active six-cylinder 935 packaging study

The separate, already documented [935-only assembly](COMPLETE_SYSTEM_20261022.md)
was also refreshed with the 0.7 rotor. It combines the observed 935
drive/support, this corrected rotor, a provisional distribution shroud and a
**hypothetical two-bank, six-cylinder engine envelope**. No 917 geometry is
used in this active study; an actual 935 crankcase scan is still absent. The
PicoGK output has 12,599,570 triangles. Independent review found exact
coordinate and triangle-order preservation in the combined mesh and in the
SI-unit USD/GLB exports. Its four-view inspection image shows the assembly
and the remaining incomplete blade sectors.

The provisional rotor/shroud radial separation is 6.258 mm at the assumed
scale. The swept rotor-annulus screen found zero candidate support triangles,
but the support/shroud screen found **1,190,558 candidate triangles**. That
conservative count does not prove a collision; it motivated the full surface
contact study below. The duct cutout and support interface still need measured
mounting datums.
The engine envelope does not supply historical mounting datums, thermal
clearances or airflow resistance.

The complete active-scene evidence is saved privately as
`assembly-935-six-root-0p7-001.tar.zst`, SHA-256
`2ff700d4d4fc359cfd450a4d9bc25ae06b80c8d402cffb59713937ee065e1f16`.
Its 17 source files were extracted and individually hash-checked; the GitHub
asset digest matches. It includes
the native PicoGK scene, USD, GLB, PNG and receipts; no geometry is committed
to the public repository.

### Retained-pose contacts and one rigid revolution

The existing [FCL surface reviewer](../../../twins/935-horizontal-cooling-system-f0/source/review_surface_contacts.py)
was rerun against the 0.7 six-cylinder scene. It tested all six original
surface pairs without decimation. The conservative support/shroud candidate
count above is **not a collision**: the FCL surface distance is 6.83367
uncalibrated source units. The support/rotor distance is 3.83430 and the
rotor/shroud distance is 6.25830 at the retained pose. The observed support
does cross the **hypothetical** engine envelope near source coordinates
`(95, -8, -210)`; this same crossing existed in the earlier scene. It cannot
be interpreted as a clash with an actual 935 crankcase.

The new [rigid-sweep reviewer](../../../twins/935-horizontal-cooling-system-f0/source/review_rotor_sweep.py)
checks 240 equally spaced rotor phases about the assumed Z axis. The maximum
rotor radius is 143.74075 source units, so any intermediate point moves at
most `2R sin(pi/(2×240)) = 1.88155` units from its nearest sampled phase.
Subtracting that motion and a 0.0001-unit numerical reserve from the lowest
sampled FCL distance gives conservative lower bounds of **1.95136 source
units** to the support and **4.37637 source units** to the provisional shroud
through a rigid revolution. Analytic static and moving FCL controls passed;
the independent exploratory and final runs had identical phase results.

These bounds concern **surface separation under an assumed axis, fixed pose
and rigid, cold geometry**. They establish neither the missing torque-carrying
hub/shaft connection nor solid containment, thermal growth, elastic motion,
historical engine fit, operational speed or physical safety. Full reports,
logs and source hashes are in the private release as
`contact-and-sweep-0p7-002.tar.gz`, SHA-256
`1d05c5940698bb1806cd5b4114ba43ee7b668de67ab37954ee522f43227e033a`;
its 11 files and GitHub asset digest were checked. The earlier archive is
retained as an exploratory attempt. The private `rotor-sweep-0p7.png` plot has
SHA-256 `dadc6a2f38a043c0f30cf45a33704ea700f8a3d2a7861dc4826d4b270ade4447`.

## Remaining gates

No new OpenFOAM meshing or CFD solve has run on either corrected candidate.
The prior snapped case used the old rotor and failed the full native `checkMesh` with
316,996 concave cells and two duplicate-face warnings. Its numerical results
cannot validate the new input. Kali1's Thunderbolt bridge dropped during this
run, then recovered; SSH access and the previously known host key were
verified. The `lolman` account cannot access its Docker daemon, and the Mac
Docker daemon did not answer an eight-second read-only probe. Neither service
was changed. No new Vast rental was created.

The next computational gates are a quality-converged conforming volume for
mechanics and a fresh fluid mesh on the chosen rotor, with complete native
quality checks, boundary-layer evidence, resolved concavity and duplicate
faces, and a three-grid study. Airflow, pressure, torque, mechanical strength,
full 935 fitment and manufacturing remain unqualified until their
corresponding calculations, measurements and review exist.
