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

### Output hub interface: geometric gap, unresolved coupling

An FCL nearest-point query puts the 3.83430-source-unit rotor/drive gap at
the reconstructed rotor bore, not at a blade. The nearest bore and observed
drive points lie at the same Z level, `-4.50417` source units, with radial
positions 11.45477 and 7.62052 respectively. Four separate five-unit
axial bands of the observed output patch give partial-arc circle-fit radii
6.93574–7.07082 source units. Their radial RMS residuals are 0.09877–0.13443,
and each band leaves a 176.8–183.9-degree angular gap in the acquisition.
An earlier bounded fit to the **original rotor scan** (SHA-256
`244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba`)
gave its observed hub patch a cylinder radius of 11.46191 source units,
0.19103-source-unit RMS on held-out sectors of the same scan, and a maximum
unobserved angular gap of 17.65°. The reconstructed bore is a full ring of
fitted radius 11.45601 source units. Its small fit residual describes the
**generated model**, not scanner accuracy; agreement with the original-scan
fit is not independent dimensional calibration or a tolerance claim.

The separate acquired 22-lobe shaft patch previously reported in the drive
study maps roughly 357 source units from the rotor axis and points 55.35°
away from the assumed rotor Z axis. It therefore cannot define the output
hub coupling. A spacer or keyed adapter may be required, but these partial
surfaces do not specify its fit, torque path, axial retention or historical
form. No functional adapter has been designed or released.

The private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains the script, nearest-point receipt, four-band fits, plot and prior
input-side profile as `hub-output-metrology-001.tar.gz`, SHA-256
`741e4af6c3666b0ccb7d9e50c60a3ef8b20dee0f2f78596053d229da55778e58`.
All eight archive members and the GitHub asset digest were checked.
The earlier original-scan hub fit and plot are also archived privately as
`rotor-original-hub-fit-002.tar.gz`, SHA-256
`dec7c80b3acf07c51e9d70e925d5a025d129290fcee40ddbaff15f2cc97a5b41`;
the source OBJ hash, both archive members and GitHub asset digest were verified.

The fitted axis of the original rotor hub patch differs by **0.75106°** from
the reconstruction frame's Z axis. A follow-up geometric bound uses
the maximum rotor vertex distance from the assembly origin (146.46243 source
units): a rigid pose tilt of that angle can move any rotor point by at most
1.91989 source units. Subtracting this from the previously certified full-turn
surface bounds leaves **0.03147** source units to the observed drive and
2.45648 to the provisional shroud. The drive bound reaches zero at a tilt of
0.76337°, only 0.01231° beyond the fitted angle. This narrow positive bound
applies solely to a rigid tilt about the assumed origin with fixed cold
surfaces. The scan fit is not an independently verified bearing or shaft axis;
translation, metrology error, running deflection and thermal growth are absent.
It is **not an operating clearance or manufacturing tolerance**. The pinned
calculation and its self-check are in the private release as
`axis-pose-sensitivity-001.tar.gz`, SHA-256
`e79aa64e02f8f040d629cd1400a390a622736019cf5fc7c02712e61a4482543c`;
both members and the GitHub asset digest were checked.

A direct 240-phase FCL sweep at that one scan-derived tilt orientation found
no sampled surface crossings. Its continuous rigid-sweep lower bounds were
**1.96219** source units to the observed drive and **4.02328** to the
provisional shroud. This sharper result does not cover other tilt azimuths,
axis translations or dynamic deflection; the conservative all-direction
pose bound above remains the applicable bound for an arbitrary tilt of up to
0.75106° about the assumed origin. The private `tilted-sweep-001.tar.gz`,
SHA-256 `9bbb5e0aa375c4babae3f12d2c6991761f3f3e0529cf0897d605b2719cf3a83e`,
contains the script, all phases and log. Its three members and GitHub asset
digest were checked.

### Blade-tip coverage: the nine blades are present, the tips are not measured equally

The original rotor scan has nine segmented blade regions. Their phase pitches
range from 39.040° to 40.879° around a 40° mean. Original triangle-face
centroids beyond radius 139 source units occur only in `blade-05` (374 faces);
its maximum is 143.595. The other eight regions have acquired maxima of
135.519–137.313 and none beyond 139 under the stated sector and axial filter.
The PicoGK loft input already marks **every** section at radius 140 as
`constant_profile_root_or_tip_design`; the last `registered_acquired_reference_section`
varies by blade from radius 122 to 136. Even `blade-05` is registered only
through radius 126 because its outer observations were not accepted as a
reference profile. The exceptional outer patch therefore cannot establish a
common historical tip radius or justify copying one tip onto all nine blades.
These are source-coordinate coverage observations, not calibrated dimensions.
The private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `blade-tip-coverage-002.tar.gz`, SHA-256
`704b4b209b0d71fe1873efaad564bdb9cb64b47f81e3d2a3bd455983fe14eb6f`,
with the script, numerical receipt, plot and both pinned derived section
inputs. All five members and the GitHub asset digest were checked.

### PicoGK tip-radius sensitivity: an explicitly shorter design hypothesis

The existing nine-blade loft was rebuilt on Apple Silicon with PicoGK Core
26.2.0 at the same nominal 0.8-source-unit voxel size. The radius-140 control
reproduced the earlier blade-loft STL **byte for byte** (SHA-256
`5e9183026be266e03944a4fb4db47f06c99fabd1af73898b8edc414688e7e114`).
A second input removed only the radius-138 and radius-140 design sections;
every registered acquired reference section was retained. The shorter input
ends at radius 136. This is a controlled **design sensitivity**, not a claim
that the historical 935 blade ends there.

PicoGK blade-loft volume changed from 203,280.62 to 193,813.80 nominal cubic
source units (−4.657%). With the same hub and rotor construction, the full
rotor's independent, welded, watertight STL volume changed from 433,422.66 to
421,987.97 nominal cubic source units (−2.638%). Its polar second moment at
unit density changed from 3.63510×10⁹ to 3.41670×10⁹ nominal fifth-power
units (−6.008%). These ratios describe geometry at the same assumed scale;
they do not establish a material mass, strength, safe speed or airflow gain.
The independent STL volumes agree with the corresponding PicoGK volume
receipts within 0.11%. The three nonrotor full-assembly component STLs
(provisional engine context, observed drive and provisional shroud) have
identical hashes in both cases.

At the unchanged provisional pose, a 240-phase FCL surface sweep found zero
sampled crossings for either rotor. The shortest sampled separation from the
observed drive was 3.82486 source units in both cases. Separation from the
provisional shroud increased from 6.25805 to 13.99869 source units; the
respective rigid continuous-sweep lower bounds increased from 4.37640 to
12.21837. These are conditional *surface* distances in uncalibrated source
coordinates. They do not include the missing output coupling, a verified 935
engine interface, running deflection or thermal growth.

The 21 derived inputs, code, receipts, comparison plot and sweep reports are
archived in the private [release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
as `tip-variant-r136-package-001.tar.gz`, SHA-256
`d3ad0d1b097564dce58dee658e67b3b7344fcc1edf6b85e1eecd1d440c72f5dd`.
Every archive member, its manifest and the GitHub asset digest were checked.

### Mechanical volume-mesh diagnosis and rejected surface-remesh trials

The protected 0.7-root surface produces 1,393,021 optimized Gmsh tetrahedra.
Of the 3,255 cells below mean ratio 0.01, **3,040 have all four vertices on
the boundary** and another 189 have three. The defects concentrate along the
blade/root annulus and outer blade regions. This locates the quality problem
at the triangulated surface rather than in a broad interior-volume pocket.

Gmsh 4.15.2's standard STL classification and reparametrization trial failed
after creating 253 discrete surfaces: `Wrong topology of boundary mesh for
parametrization`. A separate CGAL 6.2.1 isotropic remesh of the closed analysis
surface produced a 520,378-face unconstrained surface at target edge length
1.0 source unit. A second trial retained edges classified as sharp at 40°
and targeted 0.7 source unit, producing 1,035,442 faces. Both remained closed,
genus one and free of self-intersections under the independent checker.

On the unconstrained 1.0 trial, the optimized Gmsh mesh had 779,177 positive
tetrahedra, median mean ratio 0.23707 and 16 cells below 0.01. On the
feature-constrained 0.7 trial it had 1,555,572 positive tetrahedra, median
mean ratio 0.15388 and 46 cells below 0.01. The original median was 0.11501.
The feature-constrained surface changed enclosed volume by −0.01513% relative
to the protected surface. Yet the **complete bidirectional 0.0225-source-unit
surface-envelope test failed**. A fixed 20,000-point sample in each direction
found a maximum distance of 0.12268 source unit from protected surface to
candidate and 0.09130 in reverse. Those sample maxima are lower evidence
about the true global maxima, not guaranteed bounds. Neither remesh qualifies
as the reference geometry or an FEA input.

The next geometry step is a **local, constrained repair of the affected
boundary facets**, with the complete bidirectional envelope and topology
rechecked before volume meshing. Merely accepting the better tetrahedral
statistics would conceal a changed rotor shape. The private
[release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `remesh-quality-private-package-001.tar.gz`, SHA-256
`a041687336295c93b7befff10ffa90f704fdc375f93d009017a7ebc5e40177c4`,
with code, surfaces, volume meshes, failed and accepted trial receipts, exact
envelope result, machine-readable comparison and defect map. All 24 archive
members were read back against its manifest; GitHub reports the same asset
SHA-256.

### Targeted facet repair also rejected

Selecting faces within 1.5 source units of the 3,255 low-quality tetrahedron
centroids isolates **33,017 of 878,730** input faces (3.757%). CGAL then
remeshed only that patch with its boundary edges preserved, a 0.5-source-unit
edge target and sharp edges constrained at 40°. The output remained one closed
genus-one surface without self-intersections. Its enclosed volume changed by
only −0.000156%, but the **complete 0.0225-source-unit envelope still failed**.
In a fixed 20,000-point sample per direction, the largest surface distances
were 0.02755 and 0.04785 source unit; the sample is not a global bound.
In the companion unconstrained local 0.5 trial, projecting its 51,133 changed
vertices back onto the original surface moved them by at most 7.1×10⁻¹³
source unit. For that trial, the deviation comes from new triangle
connectivity across curved detail rather than off-surface vertices.

The new raw Gmsh volume had 1,603,495 tetrahedra, including **27 exactly
zero-volume and 8 inverted cells**; 12,514 had mean ratio below 0.01.
Optimization reported worst quality zero and had effectively plateaued after
184 seconds, so it was terminated. No optimized volume or FEA result is
accepted. The private archive `local-remesh-rejected-package-001.tar.zst`,
SHA-256 `582ac4629d2fef81628de46311dc0e5aad6af8821b5ab83f4b8277310ac36a53`,
contains the three local surface attempts, patch selector, source, raw volume,
exact-envelope result and defect map. All 21 archive members passed local
readback; GitHub reports the same asset SHA-256.

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
