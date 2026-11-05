# 935 assembly in PicoGK and Qwen trial — 12 October 2026

The active geometric chain targets exclusively the horizontal system of the
historical 935. It builds the rotor from **nine individually observed
blades**, keeps the scan of the drive and adds an intake
with a distribution envelope towards two banks of three cylinders.
The C# sources and the private JSON parameters are editable.

The complete 935 engine is not scanned in the recovered data. Its case,
its six finned cylinders and its six cylinder heads are therefore **13 hypothetical
positioning envelopes**, with no interfaces or reconstructed material.
The count of six cylinders is documented for the 935 K3 by
[Porsche](https://www.porsche.com/stories/culture/8-porsche-race-cars-that-made-le-mans-history/).
It fixes neither the variant of our specimen nor its dimensions. No 917
engine scan or 993 adaptation programme feeds this scene.

## Geometry actually produced

| Element | Construction | Status |
|---|---|---|
| Nine blades | Contours from the scan, vertex registration between sections, `PicoGK.Mesh` lofts, then native voxels | Profiles fitted to the acquisitions; each blade keeps its own contours |
| Missing roots and tips | Constant extrapolation of the nearest available contour | Surfaces designed under hypothesis |
| Hub, back and bore | Implicit fields and PicoGK Boolean operations | Radii fitted on observed sectors; thicknesses, bearing length and closure not qualified |
| Drive | `PicoGK.Mesh` import and rigid transformation of the open scan | All observed triangles kept; hidden components and datums unresolved |
| Engine envelopes | `PicoGK.Lattice` and implicit fields | Six-cylinder architecture; hypothetical dimensions and pose |
| Intake and plenum | Open implicit shell, distribution towards both banks and passage for the drive | Provisional geometry; historical outlets, sealing and fasteners unknown |

[prepare_native_sections.py](../../../twins/935-horizontal-cooling-system-f0/source/prepare_native_sections.py)
reuses the existing contour registration, separately for each of the nine
blades. The private register keeps, section by section, the fitted acquired
profiles, the interpolations and the extrapolations. Python prepares the numerical
data; no FreeCAD/build123d CAD operation is called in
this chain. The
[existing C# loft](../../../twins/935-horizontal-cooling-system-f0/source/picogk-section-loft/Program.cs)
and the new
[C# assembler](../../../twins/935-horizontal-cooling-system-f0/source/picogk-935-assembly/Program.cs)
create all the reconstructed surfaces and solids in PicoGK.

The kernel produces 8, 14 and 30 triangles of exactly zero area at rotor
resolutions of 1.2, 0.6 and 0.3 assumed mm units. The assembler removes them with the native
Mesh API, keeps the unfiltered outputs and explicitly bounds this
removal. An independent check compares all retained triangles:
coordinates and order unchanged. No triangle of positive area is removed.
The final rotor and shroud are each one closed component, consistently
oriented and without zero-area triangles. This closure proves
neither the absence of any self-intersection nor conformity with the specimen.

The first periodic variants and the failed attempts remain
archived. The 917 engine of the
[previous scene](INSPECTION_ASSEMBLY.md) remains an old comparative context
excluded from the active reconstruction of the 935.

## Numerical measurements and observed limits

Three successive rotor grids, **1.2 → 0.6 → 0.3**, are computed with the
same analytical loft as input. Independent integration of the triangles
gives, between the two fine grids, **0.073 %** variation in volume and
**0.116 %** in the inertia tensor about the axis origin. The fine volume
is **434,062 source units³**, conditionally 434,062 mm³ under H-SCALE.
These figures characterise this reconstruction and its hypothetical closures.
They do not provide a physical mass without calibration and a qualified density.

The bidirectional comparison uses points uniformly distributed by
area and their distance to the triangles. It is limited to the acquired radial
intervals of each blade, defined by projection onto its radial axis, with a
guard of two units at the cuts. All
samples and extreme values are kept. The extrapolated roots, tips and
hub are excluded from this comparison of acquired zones.
The scan → candidate RMS values range from **0.038 to 0.715 source units**; the 95th
percentiles range from **0.080 to 0.186**. In the reverse direction, the RMS values range from **0.038 to
0.081**. A few atypical scan points on blade 05 raise its RMS and
remain to be classified. The first cut used the global distance to the
axis and thus included extrapolated roots in the acquired zones; it
is kept as a rejected analysis, with its large reverse deviations.
The corrected cut follows the section planes and their provenance, without
eliminating points by their distance. These checks do not yet qualify
an exact replica.
The results are not converted into machining tolerances or manufacturing
accuracy. No filtering of large deviations changes the verdict.

The inspection assembly uses a 0.8 grid to contain the cost of the
engine envelopes; the fine 0.3 rotor is delivered separately. The GLB and USD
keep all the triangles of their four groups, with controlled
conversion from the assumed mm unit to metres. They attribute no undocumented
physical joint, density or fastener.

The initial shroud intersected the observed drive. A PicoGK cut
removes these surface contacts at the studied pose. This passage remains open:
its seal, its air losses and its historical conformity remain to be defined.
The drive also crosses the top of the hypothetical engine-case
envelope. This overlap is kept and flagged: the real geometry
of the 935 is needed to resolve this assembly. The checks cover observed
surfaces and envelopes; the unknown interior volumes, expansion,
deformation and the dynamics of the mechanism are not validated.

## Qwen actually tested

[test_qwen_935.py](../../../twins/935-horizontal-cooling-system-f0/source/test_qwen_935.py)
runs locally **Qwen2.5-Coder-1.5B-Instruct 4-bit**, revision
`b3252a2f97102b1fb1571fec2c9b27219a8536be`, with MLX-LM 0.31.3. It compares
the base model and the existing adapter `coding-003/checkpoint-600`.
The weights are verified before and after; a lock avoids disturbing an
active training run. No training or replacement of the default model
is performed.

The five cases are declared before inference: 935/917 architecture, scan
unit, partially observed interface, unknown material and six prescribed
hypothetical positions. Temperature 0, seed 42, limit of 512 tokens.
The score requires exact JSON, including types and the absence of duplicate keys.

| Model | Compliant raw responses | Decisive failures |
|---|---:|---|
| Base | 0/5 | JSON wrapped in Markdown; architecture proposed with one bank of six |
| With adapter | 3/5 | Wrong architecture; duplicated coordinates and Python prefix |

One response from the base model contains the six correct prescribed
coordinates. A **separate import step** removes only its complete Markdown JSON
fence; the
[validator](../../../twins/935-horizontal-cooling-system-f0/source/accept_935_centres.py)
then requires equality with the independent definition. The C# checks the
six positions again. This proposal feeds only the hypothetical engine
envelopes; it infers no historical dimension.
The raw score remains 0/5 and the original report is not rewritten.

The small model tested cannot decide the architecture, a mechanical
interface or a material qualification. Its output remains a proposal
to be checked. This conclusion does not measure the performance of other
sizes or versions of Qwen. No code generated by the model is executed.

## Reproduction and retention

Reuse .NET 9, PicoGK 2.3/Core 26.2.0 and the numerical runtimes already
installed. No additional software or Vast machine was bought.
The executed cases, sections, parameters, reversible matrices and digests
are in the [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/native-six-20261012).
The [public receipt](native-six-20261012.json) keeps only the results
and references compatible with the public repository.

```sh
python twins/935-horizontal-cooling-system-f0/source/prepare_native_sections.py \
  work/PRIVATE/prepare-individual-case.json work/PRIVATE/new-sections
dotnet /PRIVATE/SectionLoft.dll \
  work/PRIVATE/new-sections/sections.json SECTIONS_SHA256 1 0.8 work/PRIVATE/new-lofts
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-935-assembly/Assembly935.csproj \
  -c Release -p:PicoGKAssembly=/PRIVATE/PicoGK.dll
# Make the official native library reachable by the system loader.
dotnet twins/935-horizontal-cooling-system-f0/source/picogk-935-assembly/bin/Release/net9.0/Assembly935.dll \
  work/PRIVATE/individual-assembly.json CASE_SHA256 work/PRIVATE/new-assembly
python twins/935-horizontal-cooling-system-f0/source/export_inspection_assembly.py \
  work/PRIVATE/new-assembly work/PRIVATE/new-exports
python twins/935-horizontal-cooling-system-f0/source/render_935_native.py \
  work/PRIVATE/new-assembly work/PRIVATE/new-exports work/PRIVATE/new-review
python twins/935-horizontal-cooling-system-f0/source/test_qwen_935.py \
  /PRIVATE/existing-m64-qwen-runtime work/PRIVATE/new-qwen-test
python twins/935-horizontal-cooling-system-f0/source/accept_935_centres.py \
  work/PRIVATE/new-qwen-test/responses.json work/PRIVATE/new-validated-centres.json
python -m unittest discover -s tests -p test_935_native_qwen.py -v
make check
```

The assembly case imposes `target: 935`, six cylinders, `scale_verified: false`,
explicit hypotheses, the digests of the native blades and of the checked
position proposal, a single drive import and a rigid pose.
The preparation case reuses the existing schema with `profile_stride: 1`.
The `rotor_only` mode serves the three grids; the `assembly` mode remains bounded
to a grid of 0.8 or more. The outputs must be new under the ignored
`work/`. Altered cases are refused before geometry is created.

The next corrections concern the atypical points of blade 05
and the still hypothetical roots, tips and hub surfaces,
the identification of the 935 case and its fasteners, the independent calibration
of the two scans and the definition of the historical guide. The old
CFD/FEA results remain attached to their old geometries: they do not qualify
this new rotor. The dynamics, the aerodynamics of this shroud and physical
tests remain open. No manufacturing authorisation is given.

The [continuation on the Mac](MAC_PICOGK_20261012.md) adds bounded root
blends, thickness checks and VDB fields. Five centrifugal calculations
and a CFD pilot now concern this individual rotor; the convergence
criteria remain insufficient and their rejections are kept.
