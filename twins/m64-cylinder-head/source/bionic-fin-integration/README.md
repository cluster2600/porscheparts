# Integration of the bionic fins into the four-valve cylinder head

The request of October 12, 2026 is carried out as a **geometric integration
into a working copy of the existing body**. The candidate body contains six
branched ribs, three on each flank. The four valves, four seats and four guides
of the retained module remain distinct and unchanged.
The master scan and the reference BRep are neither overwritten nor replaced.

The reference model comes from the work on the 935 scan; its adaptation to an
M64/993 variant and its absolute scale are not certified. Coordinates remain
scan units assumed to be millimeters. This file delivers no functional part and
no manufacturing authorization.

**Retained deliverable: `native-004/head-bionic.brep`**, editable native CAD,
accompanied by `head-bionic.stl` and the views in `native-004-views/`.
The BRep, saved then read back, and its mesh pass the geometric checks.
The STEP is kept as an **unqualified** study export: its standard read-back
passes, but the exact check fails on 57 faces. It does not replace the
retained BRep.

## Placement in the real body

[contract.json](contract.json) independently fixes the two peripheral zones of
the prototype: `X ∈ [-61,-48]` or `[48,61]`, `Y ∈ [-35,35]`,
`Z ∈ [12,48]`. This is not a thickness or strength mask accepted by an
engineer. The outer material of these zones is reshaped: this work is not
limited to adding decorative ribs to the body.

The roots are placed at `|X| = 47.2` and at heights `Z = 16, 30, 44`.
They geometrically overlap the retained body before the mask is cut.
The profile comes from the already tested [fin candidate](../bionic-fins/candidate.json):
thick root, two tapered branches, same thicknesses and branch offsets.
Its radial reach is **compressed from 28 to 11.8 units**, up to `|X| = 59`,
and its depth goes from 60 to 70. It is therefore not the original thermal
cell placed unmodified in the cylinder head.

[Program.cs](Program.cs) actually builds the sheets with PicoGK and
ShapeKernel (`BaseBox`, `LocalFrame`, `LineModulation`), merges them, removes
body material only inside the mask, and joins the retained body with the new
sheets. The scale and frame of the body remain those of the private inputs,
with a common grid phase canceled at export.

The voxelization trials of the complete body are rejected for their small
parasitic fragments. [build_native.py](build_native.py) then keeps the body in
OpenCASCADE CAD, cuts only the two zones and merges into them the **analytical
counterpart of the same PicoGK profile**. The base BRep does not go through a
voxelization. This counterpart is not a STEP exported from a PicoGK mesh. Its
fin volume differs by **0.0988%** from that of the fine PicoGK calculation,
which checks the representation of the profile, not its thermal effectiveness.

The valves, seats and guides lie outside the mask and its check halo. The
engine interfaces, studs, cam carriers, flanges, spark plugs and real
tolerances are not certified by this separation of meshes.
Heat must pass from the body to the roots, then to the branches and the air;
combustion, clamping and valvetrain loads require a thermomechanical check
specific to the reshaped body.

## Private deliverables and inspection

The calculations are kept under `work/m64-bionic-integration-20261012/` in this
task's worktree. The `coarse-001/` and `fine-001/` folders contain:

| File | Interpretation |
| --- | --- |
| `head-bionic.stl` | Candidate cylinder-head body with integrated fins |
| `baseline.stl` | Baseline voxelized at the same step and phase |
| `fins.stl` | Six new ribs, separate diagnostic |
| `added.stl` / `removed.stl` | Raw material differences with the baseline |
| `integration.json` | Inputs, digests, connections and producer checks |

`native-004/` additionally contains the retained BRep and the unqualified STEP
export. `native-004-views/` contains the views `assembled.png`, `opposite.png`
and the section `section.png`. [render.py](render.py) uses **all the real
triangles**, without smoothing, decimation or image synthesis. The other
components stay in their recorded position. Orange marks the reshaped zones,
gray the retained body; the colors assign no material property.

These STL files and views derive from a private scan: they are not added to
Git. Only the sources, contracts, tests and non-geometric summaries are
published. The summary of this iteration is in [verification.json](verification.json).

[audit.py](audit.py) reads back the raw files and their digests. It checks edge
incidences, orientation, components, zero-area triangles and non-finite
normals, without repair or removal. Connectivity by sparse graph is checked
against the existing inspector on analytical, open and disjoint witnesses.
Files are bounded to twenty million triangles each. Vertex links and geometric
intersections are not certified by this audit.

The following checks are distinct:

- each root positively overlaps the retained body before the mask clip;
- the difference fields produce no surface outside the `0.6 unit` halo of the
  two zones, at the computed steps;
- all vertices of the exported differences must stay within that same halo;
- the twelve valve/seat/guide references stay separated from the halo by
  their geometric boxes, and their content stays bound to the input digests;
- a closed one-component body is required by the complete surface check.

The baseline and the candidate at step **0.30** each contain the same tiny
fragment of **12 triangles** outside the mask, near `X ≈ 36.44`.
Their one-component check fails. This result is kept as a rejection; the
fragment is neither removed nor repaired. At step **0.15**, baseline and
candidate contain four components and are also rejected. The native model
reuses none of these body meshes.

On the retained native deliverable, baseline and candidate have one closed
component, consistent incidences and orientations, zero zero-area triangles
and finite normals. The BRep has one valid solid and shell, checked
independently after read-back. The material differences stay inside the mask,
with no solid volume added or removed outside it. The relative volume balance
is `1.69e-12`, with an adaptive quadrature requested at `1e-10`. The initial
check with an absolute threshold of `1e-6 unit³` was unsuited to this relative
precision; its rejections remain in the local logs.

The maximum envelope in X goes from `59.145` to `59.348` units on the native
mesh, about **+0.203 unit**. This local overshoot of the inclined tips is to be
checked in the installed engine; no packaging compatibility or hot margin is
inferred from the rendering.

The 8–15% thermal gain calculated on the synthetic cell is **not transferred**
to this body. The radial compression, the connection, the obstacles, the
convection and the pressure losses have changed. No CHT simulation of this
cylinder head, no strength/fatigue analysis and no hardware test has been run.
The air passages, the strength of the roots and the installed envelope remain
to be qualified; voxelized boxes and fields do not prove an engine installation.

## Reproduction and software validation

Use the PicoGK DLL and ShapeKernel checkout locked for
[the initial study](../bionic-fins/README.md#reproduction). The contract binds
the private inputs to the retained body and module; no substitute input is
accepted implicitly. Output folders must be new.

```sh
dotnet build Integration.csproj -c Release \
  -p:PicoGKPath=/runtime/PicoGK.dll \
  -p:ShapeKernelRoot=/upstream/LEAP71_ShapeKernel -o /private/integration-bin
```

From the repository root, with the existing machine PicoGK lock:

```python
import runpy, subprocess
lock = runpy.run_path('parts/picogk-catalog/tools/run_part.py')
lock['acquire']()
try:
    for step in ('0.3', '0.15'):
        subprocess.run([
            'dotnet', '/private/integration-bin/Integration.dll', '/private/inputs',
            'twins/m64-cylinder-head/source/bionic-fin-integration/contract.json',
            'twins/m64-cylinder-head/source/bionic-fins/candidate.json',
            f'/private/head-bionic-{step}', step
        ], check=True)
finally:
    lock['LOCK'].unlink(missing_ok=True)
```

With a working NumPy and SciPy for the audit, and VTK and Matplotlib for the
views:

```sh
python audit.py --inputs /private/inputs --directory /private/head-bionic-0.15 \
  --output /private/fine-inspection.json
python render.py --inputs /private/inputs --directory /private/head-bionic-0.15 \
  --output /private/head-views
```

To produce the retained native model, with OCP 7.9.3.1 and the private BRep
whose digest is imposed by the contract:

```sh
python build_native.py --head /private/candidate-private.brep --inputs /private/inputs \
  --picogk /private/head-bionic-0.15 --output /private/native-head-bionic
python audit.py --inputs /private/inputs --directory /private/native-head-bionic \
  --output /private/native-inspection.json
python render.py --inputs /private/inputs --directory /private/native-head-bionic \
  --output /private/native-head-views
```

The native audit also reads back the two CAD exports: only the BRep passes the
exact check in this iteration. The overall status remains
`native_geometry_screen_passed_step_export_unqualified`, without a
manufacturing decision.

The targeted tests run from the root:

```sh
python -m unittest discover -s tests -p 'test_m64_bionic_fin*.py' -v
```

Twelve targeted tests pass in the existing virtualenv. Invocations with
`NaN`, a modified profile or an existing output are refused without
overwriting. Compilation passes with 37 deprecation warnings from the upstream
ShapeKernel sources. `make check` was run: 3,638 tests, two failures,
23 errors and 205 skipped tests, in the existing Python/SciPy checks and the
fan's floating-point comparisons. This global check does not pass and no merge
is proposed.
