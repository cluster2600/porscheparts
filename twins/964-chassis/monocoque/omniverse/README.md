# 964 monocoque: OpenUSD review and Omniverse handoff

The complete retained architecture is now a portable OpenUSD review bundle.
It contains **422,816 triangles in four separately selectable groups**: outer
skin, closed sections, sandwich panels and wheel tubs. The existing closed
sections include the central tunnel, sills, opening frames and B-pillar ring.
This is the existing PicoGK design envelope, not a newly measured body shell.

**Status on 28 October 2026:** local USD validation and local previews executed;
Omniverse RTX execution and application screenshots pending. The project goal
remains open. Manufacturing, strength and 964/993 fitment are not validated.

![Local OpenUSD preview of the complete architecture](media/local-001/front.png)

These images are computed views, not photographs of a manufactured part.
The [rear view](media/local-001/rear.png), [tunnel/interior close-up](media/local-001/interior.png)
and [five-second, 120-frame turntable](media/local-001/turntable.mp4) were rendered
by VTK **from the reopened USD**. They are explicitly labelled as local previews.
The [capture receipt](media/local-001/capture.json) records source and media hashes.

## Bundle and traceability

Open [monocoque.usda](bundle-001/monocoque.usda) for the complete body, or
[interior.usda](bundle-001/interior.usda) to hide the outer skin. Keep the entire
`bundle-001` directory together. Its dependencies are relative and self-contained.

| Layer | Content | Authority |
|---|---|---|
| `geometry.usdc` | Four retained display meshes, unchanged triangle coordinates | `derived/zesad-monocoque.vtp`; already decimated, not an analysis or manufacturing mesh |
| `display.usda` | Group colours and surface appearance | Display only; no mechanical material assignment |
| `results.usda` | Historical torsion/bending stiffness sequences, loads and report hashes | Original S6 study reports, with explicit incomplete validation |
| `presentation.usda` | Three inspection cameras, 120 orbit samples, lights and render products | Review presentation |
| `monocoque.usda` | Composition, millimetres, Z-up, unreleased status | Review assembly |

Coordinates retain the source convention: X forward (`X = -d`), Y left and Z up,
with millimetres. They must not be silently equated with a different scan or
vehicle frame. No suspension, drivetrain, seat, belt or crash attachment has
been invented. In particular, the visible tunnel does not prove C4 shaft or
gearbox-linkage clearance. Exact vehicle year, transmission and C2/C4 identity
are still unconfirmed; 993 compatibility requires separate interface evidence.

The [validation receipt](bundle-001/validation.json) records a fresh relocated
copy, strict Apple `usdchecker` 0.25.11 validation and component counts. Six
native tests also verify every triangle coordinate against its original group,
reject corrupt arrays, changed units and release flags, and reject overwriting
an existing bundle. Two additional tests exercise RTX input hash admission.

The Python `usd-core` 25.11 wheel lacks the shader resources needed by its
Python compliance checker. That attempt failed; the builder now invokes the
complete installed `usdchecker --strict`. No shader check was disabled.

## Interpretation of the calculations

The carbon S6 torsion sequence is **12,647 / 18,143 / 19,900 N.m/deg** for the
three retained mesh densities. The last increment is about 9.7% relative to
the preceding result; convergence has not been established. The finest
monocoque case has not yet been replayed from the committed S6 runner. The
historical bending `cases` block likewise needs replay; see the existing
[reproducibility table](../README.md#reproduce).

These are results of assumed equivalent-isotropic materials and synthetic
support/load patches. The 1,200 kg vehicle target has not been applied as a
complete vehicle load case. The visual and analysis geometries differ in sill
depth, front rails, rear rails and wheel tubs. Therefore this bundle attaches
the original reports and scalar sequences, **without mapping stress fields onto
the visual shell**. No new structural solve was executed for this handoff.

## Steps to the requested twin

| Step | State | Required evidence / next action |
|---|---|---|
| Preserve inputs and current study | Executed | Existing sources and reports retained; bundle and media hashes recorded |
| Portable whole-body OpenUSD | Executed | Four groups, coordinate equality, relocated strict validation |
| Local review media | Executed | Three PNG views and a 120-frame MP4 from the reopened stage |
| Omniverse RTX review | Prepared | Fresh compatible GPU/driver check, bounded rental approval, actual OVRTX captures and runtime receipts |
| Omniverse/application screenshots | Pending | Capture the actual review application after it loads the verified bundle; never substitute a local preview |
| Source-reproducible structural model | Incomplete | Replay finest S6 torsion/bending with sufficient RAM; retain inputs, reactions and convergence results |
| Exact 964/993 interfaces | Blocked by missing measurements | Validated XYZ datums, variant identity and drivetrain travel/clearance envelopes |
| Composite strength and manufacturing | Incomplete | Measured laminate/process data, bonded joints/inserts, delamination/buckling/fatigue and mould/process studies |
| Physical correlation and road/circuit acceptance | Incomplete | Donor torsion test, coupons, component tests and professional review under the programme gates |

The [programme](../../../../docs/MONOCOQUE_964_993_PROGRAMME.md) phases M0–M7
remain applicable. The visual review can proceed with known gaps; it does not
close the physical metrology, test or approval phases. The current geometry is
not sufficient to release moulds or manufacture a self-supporting vehicle body.

## Reproduce locally

Use an isolated Python 3.12 environment with NumPy 2.2.6, VTK 9.5.2, PyVista
0.46.4 and `usd-core` 25.11, plus the complete `usdchecker` and FFmpeg tools.
From the repository root:

```sh
python twins/964-chassis/monocoque/omniverse/build_twin.py work/964-review-new
python -m unittest discover -s tests -p test_964_omniverse_bundle.py -v
python -m unittest discover -s tests -p test_964_rtx_capture_inputs.py -v
python twins/964-chassis/monocoque/omniverse/preview.py work/964-review-new work/964-preview-new
```

Use new output directories. Existing outputs are never overwritten. The build
script, capture adapter and tests are new; the historical PicoGK generator,
solver sources, evidence files and container recipes remain byte-identical.

## Bounded RTX session, not launched

The [rental proposal](rental-proposal.json) specifies the existing qualified
image by digest, one RTX Pro 6000 and a **proposed USD 5 budget / 90-minute
deadline**, including startup and cleanup. The observed compatible offer costs
USD 2.24444/hour including allocated storage; the conservative calculation
with 40 GB download, 15 GB upload and USD 1 cleanup reserve is USD 4.53.
Availability and price must be reread immediately before launch. The public
image digest and its 34.62 GB compressed download were verified anonymously.
No Qwen weights need to be downloaded for rendering this prepared scene.

Use the existing OpenBao wrapper, `engine-twin-v1` compute profile and external
deadline guard. After budget approval, create a fresh private manifest with the
proposed bounds, arm its guard, verify a supported driver, and run the upstream
minimal example before the prepared capture job. The adapter targets OVRTX
0.3.0, matching the retained image and the inspected upstream
[v0.3.0 example](https://github.com/NVIDIA-Omniverse/ovrtx/blob/v0.3.0/examples/python/minimal/main.py)
at `556ceb6a41e4bf6f4ff7b4526943a9366386543c`; it does not mix in the newer
OVStage API. Check the current
[NVIDIA driver requirements](https://github.com/NVIDIA-Omniverse/ovrtx/blob/main/docs/driver_requirements.rst).

```sh
/opt/ovrtx-runtime/bin/python capture_rtx.py /workspace/bundle /workspace/rtx-output-new
```

Collect the actual PNGs, MP4, logs, GPU/driver identity and capture receipt;
compare their hashes on the Mac; destroy the exact rented instance and verify
its absence. A failed job, incompatible driver or failed collection must not
extend the rental beyond its approved deadline. `capture_rtx.py` is prepared
and its input admission is tested, but its GPU execution remains unverified.
