# Reproduce the 20 October reinforcement surface study

[Results, images and workflow](../../../../../docs/reports/carrier-resume-20261020/README.md)

This recipe reproduces the two certified patch meshes and the one-build-item
3MF assembly from repository inputs. The parent is revision 24af0584. These
are study files; the new volume mesh, mechanics and full print preparation
remain open. Historical scripts and refused input meshes are retained for
traceability. Use **`certified-patch-*.stl`** for the current assembly.

Run from the repository root with a fresh Python environment:

```sh
python3 -m venv work/carrier-resume-env
work/carrier-resume-env/bin/python -m pip install -r parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/requirements-3mf.txt
```

Pinning is intentional: the assembly program rejects other dependency versions.
The installation command is provided for a new machine; this run reused an
already installed runtime. Use a fresh output directory for each execution.

```sh
CARRIER_SOURCE=parts/993-eng-carrier-0001/source/design-20261016/resume-20261020
CARRIER_PYTHON=work/carrier-resume-env/bin/python

$CARRIER_PYTHON "$CARRIER_SOURCE/bounded_patch_tessellation.py" \
  --control-nets "$CARRIER_SOURCE/inputs/nurbs-control-nets.json" \
  --output work/carrier-replay-bounded

$CARRIER_PYTHON "$CARRIER_SOURCE/certified_patch_collapse.py" \
  --meshes work/carrier-replay-bounded/patch-0.stl work/carrier-replay-bounded/patch-1.stl \
  --bounds work/carrier-replay-bounded/assessment.json \
  --output work/carrier-replay-cleaned

$CARRIER_PYTHON "$CARRIER_SOURCE/rebuild_component_3mf.py" \
  --baseline parts/993-eng-carrier-0001/source/design-20261016/corner-slide-candidate-20261018/candidate-surface.stl \
  --patches work/carrier-replay-cleaned/patch-0.stl work/carrier-replay-cleaned/patch-1.stl \
  --manifest "$CARRIER_SOURCE/certified-component-inputs.json" \
  --output work/carrier-replay-assembly
```

The assembly command checks all three source hashes, retains exact coordinate
and triangle bytes in exact-decimal 3MF XML, reopens the file with strict
lib3mf, checks the component graph and transforms, checks positive overlaps
and evaluates the nominal mass bound. `assessment.json` records each result.
Pass the manifest explicitly: the older default bounded-mesh manifest belongs
to the historical pre-contraction trial.

The [full independent audit](../../../../../docs/reports/carrier-resume-20261020/evidence/component-libigl-certified-001/assessment.json)
is a separate executed stage. Its
[exact Docker command](../../../../../docs/reports/carrier-resume-20261020/evidence/component-libigl-certified-001/plan.json)
records the pinned image, ownership, input mounts, read-only filesystem,
resource bounds and time limit. Replace the old absolute host paths with the
new checkout/output paths and use a **fresh** output, container name and CID
file. The worker `audit_component_meshes.py` expects:

| Container path | Read-only input |
| :--- | :--- |
| `/input/study.3mf` | Actual generated archive |
| `/input/source-assessment.json` | Matching assembly `assessment.json` |
| `/source/worker.py` | `audit_component_meshes.py` from this directory |
| `/source/audit.py` | `parts/993-eng-carrier-0001/source/remesh-20261016/audit.py` |
| `/output` | Fresh writable audit directory |

The worker verifies the archive and complete component byte identities before
running all-facet checks. Its process exit means the audit completed; acceptance
requires `status == "all_complete_component_surface_screens_passed"` in the
final report. Refused geometric results are deliberately saved too.

`readback_native_control_nets.py --inputs .../inputs --output FRESH_DIRECTORY`
reopens the two saved native BREP patches with build123d 0.11.1 /
cadquery-ocp-novtk 7.9.3.1.1. It compares every tensor coefficient to the input
control nets; it does not run a new Boolean operation.

`render_resume.py --root . --output FRESH_DIRECTORY` renders every retained
parent triangle and the certified patches with Matplotlib 3.10.8. The saved
figure provenance lists input hashes and plotting versions.

Focused source and evidence tests:

```sh
python3 -m unittest discover -s tests -p 'test_carrier_*20261020.py'
```

Run `make check` for repository integration. It is broader than this recipe
and requires the repository's supported test runtime and retained datasets.

## Reproduce the volume-meshing checkpoint

The separate WildMeshing environment uses NumPy 1.26.4, svgwrite 1.4.3 and
WildMeshing 0.4.1. Its recorded installation used CPython 3.10 / macOS ARM64;
the exact wheel hash and bundled licences are in
[`dependencies/wildmeshing-0.4.1/`](dependencies/wildmeshing-0.4.1/).
Other platforms need their own installation control and numerical checks.

```sh
python3 -m venv work/carrier-volume-env
work/carrier-volume-env/bin/python -m pip install -r parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/requirements-wildmeshing.txt

CARRIER_SOURCE=parts/993-eng-carrier-0001/source/design-20261016/resume-20261020
CARRIER_VOLUME_PYTHON=work/carrier-volume-env/bin/python

python3 "$CARRIER_SOURCE/check_wildmeshing.py" \
  --python "$CARRIER_VOLUME_PYTHON" --output work/carrier-volume-control

gzip -dc "$CARRIER_SOURCE/union-float64.mesh64.gz" > work/carrier-volume-input.mesh64

$CARRIER_VOLUME_PYTHON "$CARRIER_SOURCE/wildmeshing_carrier_checkpoint.py" \
  --mesh work/carrier-volume-input.mesh64 \
  --output work/carrier-volume-checkpoint
```

The checkpoint worker requests nine optimization passes, a 0.06 mm mesher
envelope and a 9 mm ideal edge length. It resolves input paths before running
inside its fresh output directory, so native debug files stay there. For the
0.03 mm fidelity refinement, use `wildmeshing_carrier_tighter_envelope.py` with
the same arguments and another fresh output directory. The final independent
0.06 mm criterion and conservative predicate guard remain unchanged.

The run records `mesh.npz`, `boundary.mesh64`, settings, counts, determinants
and incidence checks. A mesher return does not imply admission: the first
nine-pass checkpoint passed exact orientation and complete boundary checks,
but its conservative global distance guard was refused. The original
unrestricted worker `wildmeshing_carrier.py` is retained as a historical
CPU-limited trial; use the checkpoint worker above for the exported recipe.

The exact orientation/connectivity audit reuses the repository's retained
indexed-tetrahedra checker and additionally evaluates every determinant using
`Fraction`. It needs a separate NumPy/SciPy environment; the recorded audit
used the existing design runtime.

```sh
python "$CARRIER_SOURCE/audit_wildmeshing_volume.py" \
  --mesh work/carrier-volume-checkpoint/mesh.npz \
  --boundary work/carrier-volume-checkpoint/boundary.mesh64 \
  --output work/carrier-volume-exact-audit

python3 "$CARRIER_SOURCE/run_mesh64_audit.py" \
  --mesh work/carrier-volume-checkpoint/boundary.mesh64 \
  --output work/carrier-volume-boundary-audit
```

The second command uses the pinned local Docker libigl image, with an owned
container, read-only inputs, no network, one CPU, 4 GiB and a 230-second worker
bound. The launcher writes its exact command and actual terminal receipt.
Exit 2 means a completed surface refusal; inspect `output/assessment.json`.

`mesh_hausdorff_cgal56.cpp` and `mesh_envelope_predicate_cgal56_seq.cpp` are
separate CGAL 5.6 adapters for the complete global-distance checks. The former
computes a symmetric maximum with a 0.001 mm additive API error; the latter
checks a conservative 0.059 mm guard within the unchanged 0.06 mm limit.
Their [builds, analytic controls and actual execution commands](../../../../../docs/reports/carrier-resume-20261020/README.md#exported-volume-mesh-checkpoint)
are retained in the report. The native build uses the recorded local image;
this stage has not yet been packaged as a standalone portable runtime.


## Single closed union and preserved-boundary TetGen checkpoint

`carrier-union-bounded.mesh64.gz` is the complete audited single surface,
SHA-256 (decompressed) `23a05f9836ae1a99391440e6b795636c3f829aaf91dbab5e0b1e581e39acb223`.
The exact-master-to-surface complete L1 bound is 0.023852782 mm. The new
`tetgen-volume-outward.npz` contains the completed 927,734-cell mesh, with its
boundary winding normalized against this exact input. Original raw outputs
and negative-skin-volume refusal remain in the report evidence.

```sh
CARRIER_SOURCE=parts/993-eng-carrier-0001/source/design-20261016/resume-20261020
gzip -dc "$CARRIER_SOURCE/carrier-union-bounded.mesh64.gz" > work/carrier-bounded.mesh64
python3 "$CARRIER_SOURCE/run_mesh64_audit.py" \
  --mesh work/carrier-bounded.mesh64 --output work/carrier-bounded-audit
python3 "$CARRIER_SOURCE/run_tetgen_preserved.py" \
  --mesh work/carrier-bounded.mesh64 --output work/carrier-tetgen-raw
# Use a NumPy environment for the following commands:
python "$CARRIER_SOURCE/orient_tetgen_boundary.py" \
  --volume work/carrier-tetgen-raw/output/volume.npz \
  --reference work/carrier-bounded.mesh64 --output work/carrier-tetgen-outward
python "$CARRIER_SOURCE/audit_wildmeshing_volume.py" \
  --mesh work/carrier-tetgen-outward/volume.npz \
  --boundary work/carrier-tetgen-outward/boundary.mesh64 \
  --output work/carrier-tetgen-exact-audit
python "$CARRIER_SOURCE/tetra_quality_diagnostics.py" \
  --mesh work/carrier-tetgen-outward/volume.npz --output work/carrier-tetgen-quality
```

The Docker launcher requires the already installed pinned libigl image;
`--pull=never` prevents a silently substituted image. It records its command,
input hashes and terminal receipt, with network disabled, 1 CPU, 6 GiB and a
300-second worker limit. Each output directory must be fresh. The worker's
analytic control and full-mesh triangle bijection run on every attempt.
`run_tetgen_quality.py` is the separate `pYMQq2` interior-refinement experiment. It completed with 351,600 nodes and 1,163,760 exact-positive cells; use the same winding normalization and audits on its fresh output. `tetgen-volume-refined-outward.npz` preserves that completed result without altering the first checkpoint.

The WildMeshing tetrahedron control passed initially, but an isolated repeat
stalled in native Delaunay point location. The supervised control above bounds
and reaps that case; its repeat reached the 60-second bound. The cause remains
unresolved. Both exported WildMeshing carrier boundaries failed the independent
fidelity screen; lowering the requested mesher envelope to 0.03 mm did not fix
window-tip loss. The preserved-boundary TetGen route avoids that surface edit.

## Actual mechanical screening and rejected reinforcement study

The English report now includes complete new gravity/combined CCX results and
a same-recipe baseline comparison. The added-patch combined-load elastic peak
is 32,284 MPa, versus 5,178 MPa on the baseline. These are unconverged numerical
hotspots; the small patches are not adopted as a final mechanical design.

`prepare_tetgen_mechanics_ccx.py` is the corrected preparation recipe for the
published refined volume. It uses the unchanged retained six-component bore
load distributor, nominal bore groups and dense elastic reference. Numeric
fields fit CCX's 20-character input fields; its exact coordinate-transport
bound is recorded. `prepare_tetgen_mechanics.py` remains the historical first
preparation whose long CLOAD field was refused.

```sh
python "$CARRIER_SOURCE/prepare_tetgen_mechanics_ccx.py" \
  --mesh "$CARRIER_SOURCE/tetgen-volume-refined-outward.npz" \
  --output work/carrier-ccx-prepared
python3 "$CARRIER_SOURCE/run_owned_ccx.py" \
  --deck work/carrier-ccx-prepared/gravity.inp \
  --mesh work/carrier-ccx-prepared/mesh.inp \
  --output work/carrier-ccx-gravity --seconds 300
python "$CARRIER_SOURCE/assess_tetgen_mechanics.py" \
  --execution work/carrier-ccx-gravity --preparation work/carrier-ccx-prepared \
  --output work/carrier-ccx-gravity-assessment
```

Use `combined.inp` and another fresh output for the second case. The owned
launcher verifies the recorded CCX binary hash inside its pinned image, runs
with network disabled, one CPU and 6 GiB, records actual termination and removes
only its own container. `assess_ccx_affine_control.py` rechecks the retained
unit-cube input/output against unchanged analytic tolerances before using this
solver configuration. The original helper's container-wide `pkill` is never
called by this launcher.

`round_hollow_root_trial.py` begins a separate native CAD iteration with inner
cavity ends trimmed at |X|=70 mm and end-cap corners rounded to R0.6. Its first
run created and saved the native body, STEP and STL, then failed in the inherited
report's source-dependency path. Do not rerun completed geometry to hide that
failure. `audit_rounded_hollow_native.py` independently reads those exact saved
files, measures mass/radii and attempts strict full-parent retention. The saved-body audits, complete radius certificate and coarse mechanical hotspot are now documented in the main English report. The generator has a report-path-only correction for future runs; the original failed worker is archived, and the corrected generator has not been rerun. `stl_to_mesh64.py` indexes every
triangle without filtering, for the same independent complete-surface audit.

The separate CGAL exact planar-patch experiment reduced 603,152 triangles to
478,598 with zero new vertex coordinates and passed the full surface screen.
Its complete bidirectional exact volume comparison reached the 230-second
bound after the first difference succeeded with zero faces. The second
difference remains unconfirmed; this representation has not replaced the
published 603,152-triangle source or inherited its mechanical results.


## PicoGK closing and MeshLib evaluation

`picogk-closing/` is the actual .NET 9.0.319 project, using the existing PicoGK
runtime through `-p:PicoGKRuntime=/absolute/runtime/path`. It restores without
NuGet packages. Build in that project directory so `global.json` selects the
pinned SDK. Use fresh output/intermediate directories outside the source tree.
`run_owned_picogk_closing.py --help` describes the bounded worker and catalogue
lock. The control must pass before a carrier invocation. The completed carrier
case uses 0.2 mm voxels and 1 mm closing radius on the retained baseline STL.

Install `requirements-meshlib.txt` into a separate Python environment. The
recorded wheel download is under `dependencies/meshlib-3.1.4.297/`.
`meshlib_decimation.py --help` describes the supervisor; run its cube control
before processing the complete closing export. Both 0.02 and 0.04 mm backend
error requests were executed. Backend estimates are not independent geometric
certificates. MeshLib's published licence governs deployment; this was a
numerical evaluation and does not provide a commercial software licence.

Run `run_mesh64_audit.py` on every resulting surface. Then run
`screen_nominal_gauge_volumes.py` using the separate native CAD Python site.
The original 0.02 mm variant passes its full surface audit and six shank tests,
but fails four strict tool-column intersection tests. The failed intersections
are retained. No downstream result may be transferred across changed meshes.
