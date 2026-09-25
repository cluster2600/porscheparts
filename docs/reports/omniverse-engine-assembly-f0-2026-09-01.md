# Omniverse engine report F0 — 2026-09-01

## Result

Three OpenUSD scenes were generated without publishing the source scans:

- `917-engine-assembly-f0.usda`: exterior reference of the 917 engine;
- `993-935-valvetrain-test-rig-f0.usda`: comparison 935 cylinder head and three
  parametric 993 valves;
- `engine-research-overview-f0.usda`: side-by-side view of the two research lines,
  without claiming that they form the same engine.

The composition contract passed with a unit of 0.001 m, a vertical Z axis
and no rigid body added without review. The rig contains four loaded
meshes, three of which are valve prototypes; the overview contains five.
The valves expose lifts of 0, 2, 5 and 10 mm. The intake selects
the Ti-6Al-4V study by default and the two exhausts the INCONEL 751 study.

This result is an F0 research composition, not SimReady conformance,
proof of fit, nor a validated mechanical or thermal model.

## OVRTX rendering evidence

Rendering was executed on an NVIDIA L40S with the image:

`ghcr.io/cluster2600/3dprinting993-simready@sha256:3947ea34d5101065c97103cc2176f395cb9753cb1d7807acb3cfd095796a4e1a`

The first run revealed that Pillow was missing from the validation
environment: the black PNG was therefore not detected. A second run with
pixel inspection and diagnostic lights proved that the USD references
were not embedded in the renderer package. The source scenes
remained composed; only their temporary render copies were flattened.

The final renders passed `--fail-on-uniform`:

| Local evidence outside Git | Size | Triangles inspected | Reduced colors | SHA-256 |
|---|---:|---:|---:|---|
| `valvetrain-rig-final.png` | 1024 × 1024 | 2,466,032 | 117 | `9960952fa086a88a381fc86948324f93560c4016b2cec9b0eb37b9395485539c` |
| `engine-overview-final.png` | 1280 × 720 | 4,931,909 | 64 | `a0b629f75815c7a4bf1e002a0a6eb31f7dd35aeab06f96665b89fc2dc812c4ef` |

The images, derived USD files and scans remain under `work/`, outside Git. The reports,
digests, configurations and scripts make it possible to replay and audit the
work without redistributing third-party assets.

## Validation and limits

- The minimal OpenUSD validation passed on all three scenes.
- The repository's composition validator passed on variants, instances,
  units, axes, meshes and absence of rigid bodies.
- The generic NVIDIA `asset` and `geometry` validators exceeded 120 s under
  amd64 emulation on macOS; this timeout is not declared as a success.
- Material Agent and Physics Agent were not used: no physical
  assignment is justified at this stage and the gated NIM access had refused
  authentication.
- PhysicsNeMo was not launched. It first requires a clean segmentation,
  measured interfaces, temperature-dependent material laws and
  verifiable load cases.

## Infrastructure

Vast.ai instance `49498499` was destroyed after the evidence was retrieved and
checked; the instance list was empty. The container fix adds
Pillow to the validation environment and makes its import mandatory in the
smoke test, so that a future uniform render blocks the chain. The fixed image
was built on a GitHub x86_64 runner, published, downloaded again and
validated by the smoke test under the immutable digest
`sha256:0562c69276c0d3065990cb9b1b8641dcd29355d0dccb9082dcf266fa2d22e90a`.
