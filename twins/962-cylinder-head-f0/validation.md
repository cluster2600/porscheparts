<a id="vérification-f0--12-octobre-2026"></a>

# F0 verification — October 12, 2026

<a id="vérifications-locales"></a>

## Local checks

- Existing C# project build: successful, zero errors. Two SourceLink warnings
  concern the local PicoGK archive without Git metadata.
- Three native generations with PicoGK 2.3.0 / runtime 26.2, 0.75 mm voxel.
  The final solid measures 160 × 160 × 90 mm and contains approximately
  353.19 cm³. This geometric volume is not a qualified part mass.
- Independent inspection of the three STL files: closed surfaces, consistent
  orientations, one component per volume. Removal limited to exactly
  degenerate triangles, with counts retained in the report.
- 197,322 probes on the water volume, minimum signed distance to dry volumes
  **3.598 mm**. This sampled minimum certifies neither minimum wall thickness
  nor sealing. Six probes check the four guide and two spark-plug reservations.
- Four targeted tests pass in the VTK environment; in system Python, three
  pass and the VTK witness is skipped because the library is unavailable.
- Five invalid inputs rejected without STL: qualified status, dimension
  declared published, fractional export mode, skin too thin and non-finite voxel.
- Strict Markdown links: zero broken links.
- Final preview visually inspected: visible volumes without cutting the frame;
  the chamber reservation below the combustion deck is hidden in the preview.
  Inspection meshes retain the complete dry volume.

The first candidate is rejected for an intersection between the return
manifold and gas passages, with −7.858 mm signed distance.
It remains local under `work/962-head/native/`. The final return is raised
and unnecessary distribution extensions removed. Final STL files are in
`work/962-head/delivery/`; digests and measurements are versioned in
[study-report.json](derived/study-report.json).

The [runtime register](derived/runtime-provenance.json) retains digests of
binaries actually used. The local PicoGK archive has no Git metadata:
its relationship to the commit declared in `sources.lock` was not
independently rechecked during this delivery. The Apache-2.0 license was read.

<a id="vérifications-du-dépôt"></a>

## Repository checks

`make check` ran on the final delivery: **3,764 tests**, **2 failures,
26 errors and 223 skipped**, in 242.6 s. The three F0 tests compatible with
system Python pass; its VTK witness is skipped and passes separately in the
VTK environment. Global problems concern unmodified modules: NumPy/SciPy
incompatibility, Python 3.10 without `hashlib.file_digest` for Qwen, and overly
strict floating-point equalities in the impeller/stator studies on this Mac.
The local log is `work/962-head/make-check-final.log`.
Targets after `test` are not considered executed; overall status remains failed.

[Draft PR 184](https://github.com/cluster2600/porscheparts/pull/184) was created
and the remote branch checked. GitHub validation of commit
`4c76e0efbc3c220bcaddb2ca94189135c6a6fc1f` passed:
[run 664](https://github.com/cluster2600/porscheparts/actions/runs/38283253271).
This evidence belongs to that commit, not the later product additions.

The PR remains a research and geometry draft. These local checks authorize
no merge or deployment.

<a id="extension-au-programme-kit-1-000-ch"></a>

## Extension to the 1,000 metric-horsepower kit program

The [product program](KIT_962_PROGRAMME.md) and its [register](kit-program.json)
add the commercial target and per-variant qualification. They modify neither
the C# generator, geometry parameters nor sources and contracts with recorded
digests. Two additional tests check scoping-calculation units and separation
between power target, compatibility and manufacturing authorization.
The six targeted tests pass with VTK; in system Python, five pass and the
VTK witness remains skipped. Markdown links and the diff are checked.
The global Mac validation above belongs to the previous geometry dossier;
it is not presented as execution of the new product program.
CI for the new revision remains to be observed.

<a id="extension-au-module-thermique"></a>

## Extension to the thermal module

The [thermal study](THERMAL_MODULE.md) adds an algebraic TEC balance and a
visually inspected SVG/PNG functional diagram. The code distinguishes cold
heat load, electrical power at the TECs, hot-side heat, conversion losses,
auxiliaries and bus consumption. Six additional tests check energy conservation,
loss separation, rejection of invalid/non-finite inputs and numerical overflow,
the CLI and links between examples and the calculation source.
The twelve targeted tests pass with VTK; eleven pass in system Python with
one skipped VTK witness. Actual COP, engine load, radiator, vehicle bus,
enclosure, embedded control and automotive benefit are not qualified.
Reference cooling independent of the TECs remains required.

<a id="confirmation-de-la-cible-produit"></a>

## Product-target confirmation

The owner confirms 1,000 metric horsepower at the crankshaft and qualification
on the bench then on the track. The register and its test distinguish this
decision from unknown requirements and authorizations retained at `false`.
The twelve targeted tests pass with VTK; Markdown links and the diff are
checked. No new geometry calculation or physical test is performed.
The global Mac `make check` is not rerun for this clarification.

<a id="fusion-du-programme-et-préparation-g1"></a>

## Program merge and G1 preparation

CI for commit `e033e041f6a3d11e6905f108b2f73c3837a69c32` passed:
[run 672](https://github.com/cluster2600/porscheparts/actions/runs/38286252107),
including Linux `make check`. PR 184 was merged at the owner's request;
the merge commit is `a2f066864a765e9ece59c960c87e60a4d9b93a9d`.
This qualifies no physical part.

The follow-up adds the G1 dossier and material qualification without changing
geometry. A CSV check verifies twenty unique identifiers, coverage of the
eight M64 contract interfaces and entirely blank observation fields.
The existing M64 validator confirms incomplete interfaces and retains
manufacturing at `false`. The twelve 962 tests pass with VTK; no broken
Markdown links in the 878 files examined, and no diff errors.

Mac `make check` is rerun for this stage: 3,794 tests in 232.037 s,
2 failures, 26 errors and 229 skipped, then it stops at the `test` target.
Errors remain in SciPy/NumPy and Python 3.10 without `hashlib.file_digest`;
the two failures are impeller/stator floating-point equalities in unmodified
modules. The log remains local: `work/962-head/make-check-metrology.log`.
Subsequent global targets are not considered executed.
CI for the new G1 revision must be observed separately.

## G1 merge and coolant boundary diagnostic

The G1 CI of commit `1dd4f65e770481cdbc8475606be05b69387158e1` passed:
[run 677](https://github.com/cluster2600/porscheparts/actions/runs/38291189844).
PR 188 was merged at the owner's request in
`d8fed9fa5e7f96d4fe1e0af27b0a51eb9f94177e`.

The follow-up uses the original STL files, with no rerun or modification of the
generator. The [boundary report](derived/boundary-audit.json) keeps
digests, sections and classifications at the four probing distances.
The nineteen targeted tests pass with VTK. Seven new controls check
the classifications on analytic surfaces, open or disconnected
sections, invalid inputs and the refusal of an STL modified before export.
The probing plot is inspected visually. The VTP sections stay
local in `work/962-head/boundary-audit-final2/`.

The coolant/metal gaps remain present in the evidence: no CFD status,
conformal interface, wall strength or physical qualification is granted.
The strict link check passes on 880 Markdown files. The Mac
`make check` ends in failure: 3,803 tests, 2 failures, 26 errors, 232 skipped,
251.837 s. The SciPy/NumPy and `hashlib.file_digest` errors as well as the
two floating-point equalities concern the same unmodified modules; the
nineteen 962 tests are verified separately with VTK. The log stays local
in `work/962-head/make-check-boundaries.log`; the targets after `test`
are not considered executed. The CI of this new revision remains
to be observed.

## Refinement and views of the cylinder head

The CI of the previous diagnostic, commit
`427ec23e67bbed6b2a01483276a4188eb44a5102`, passed:
[run 687](https://github.com/cluster2600/porscheparts/actions/runs/38295662492).
This evidence does not validate the following additions.

Three new PicoGK exports at 0.5 mm are actually calculated with the
verified binaries, under the shared lock; only the resolution of the input
copies changes. The original inspector is reused and the new report
records separately the digests of the actual inputs executed.
The [report](derived/refinement-report.json) keeps all qualification
values at `false`. The coolant/metal gaps near the surfaces remain
observed. Three 1600 × 1200 views are inspected visually and linked to the
report by digest; the published images are identical to the inspected views.
The native exports are not recalculated when inspection/rendering is resumed.

## Envelope added after visual review

The first exterior render showed a frame, with no complete envelope.
The [enclosed-solid.json](source/enclosed-solid.json) variant and the new
generator add a continuous rounded body, then subtract coolant and gas.
These are envelope assumptions, with no measured engine interfaces.
The separate project builds against the verified PicoGK binary libraries,
because the old local source path is no longer available. Build
succeeded with no warning; native export at 0.5 mm actually executed under
the shared lock in 89.8 s. The solid body is not optimized under load.

The [report](derived/enclosed-report.json) keeps binaries and sources,
closure/orientation/connectivity of the solid, seven material probes and six
openings. The three new views are inspected visually. The virtual
cut is closed and verified on an analytic cube. The twenty-five targeted
tests pass with VTK; the Markdown links pass on 882 files.
The initial evidence and the old routing views remain intact.
The coolant/metal interface and all physical qualifications remain open.

## Photographic architecture, Qwen, LatticeLibrary and VDB

The 962 C restoration views were inspected; their license and their
lack of scale are recorded, without publishing their pixels. The
[gallery](GALLERY.md) uses the actual STL files of a new ShapeKernel
architecture, with four inclined guides and two candidate ignition wells.
Two complete invalid Qwen responses were rejected; only one verified elliptical
expression was integrated. The prompts, outputs and digests are
kept. Build of the architecture and rib projects: zero errors,
35 deprecation warnings in ShapeKernel.

The three base domains are closed/oriented and have a single component
after documented removal of degenerate triangles. The ribbed solid is
also a single component; 56 internal cell corners are inside
the base body. The two port lofts pass an independent elliptical
area check at 2%. The minimum sampled coolant/dry separation is
4.401 mm over 805,530 points: no physical thickness is qualified.
The [reports](derived/architecture-report.json) and
[VDB/rib evidence](derived/bionic-report.json) link the sources to the outputs.

LatticeLibrary builds 36 external BCC cells, with no lattice in the coolant.
Five VDB fields are read back by name. Three domains pass native equality;
1,153,186 scalar values and as many vectors pass the exact
bidirectional comparisons. These are geometric fields, with no solver.
The 32 targeted tests pass with VTK; the new images are inspected.
The classifications at the metal/coolant boundaries remain unresolved: at
0.25 mm, 1,609 probes are assigned to neither domain. Smoothing
therefore does not produce a conformal interface ready for CHT.

## Global check after integrating main

`make check` was run on
`1dc719f622811158f81bf1d36f29c0dc39942477`: **3,855 tests** in 251.879 s,
**2 failures, 26 errors, 235 skipped**. The failures concern the
impeller/stator floating-point equalities; the errors concern the numerical imports
SciPy/NumPy and `hashlib.file_digest` under Python 3.10, in modules not
modified by this study. The targets after `test` were not executed.
The full log stays local in `work/962-head/make-check-final-main.log`.
The 32 cylinder head tests pass with VTK; the separate link check passes
on 916 Markdown files. This global Mac result is not announced as green.

## Linux CI result on the translated revision

The GitHub Actions workflow "Validate catalogue",
[run 38578122965](https://github.com/cluster2600/porscheparts/actions/runs/38578122965)
(`pull_request` event, 2026-10-14), passed on
`d4a8ce4dec818ac56da09abe712b9f4b21f7323c`, including the
"Validate repository" step that runs `make check`. This is a Linux CI
software check of the repository; it does not validate the geometry,
the coolant interface or any physical property of the study.

## Flow-sized 4 L study: delivery receipt versus repository copies

The [delivery receipt](derived/flow4l/delivery-report.json) pins the 37
entries of the local archive
`work/962-flow4l/delivery-001/mezger-4l-sp95-head-study.zip`. Its entry
`documentation/FLOW4L_STUDY.md` (SHA-256 `cfbea813…9a43b25`, 6,873 bytes) is
the pre-packaging snapshot from commit `e0c6feac`. The repository copy of
[FLOW4L_STUDY.md](FLOW4L_STUDY.md) was edited afterwards, in the commit that
added the receipt (`615fd71f`), to record the rejected `snappyHexMesh` and
native tetrahedral meshes and the archive itself. It therefore no longer
matches the receipt. The archive copy is the one the receipt attests.

The other repository-resident entries were re-hashed on 2026-10-16 and match
the receipt: `MEZGER_4L_SP95.md`, the 23 source files and the seven derived
reports and views. The three STL files, the VDB and `native-fields-report.json`
exist only in the archive, which is not on this host. Reissuing the receipt
from the current documentation needs a new native packaging run on the
owner's machine; until then, neither the receipt nor its pinned documentation
copies are edited here.

<a id="vérifications-physiques-absentes"></a>

## Physical checks absent

No 962 donor scan/CT, metrology, CFD/CHT, mechanical analysis, qualified material,
depowdering inspection, pressure proof test, seat/guide retention, thermal
fatigue or engine test has been performed.
The [interface-contract.json](interface-contract.json) retains these unknown
inputs and authorizations at `false`. Any manufacturing requires the
professional review and validation plan described in the
[dossier](README.md#feuille-de-route-vers-un-jumeau-exploitable).
