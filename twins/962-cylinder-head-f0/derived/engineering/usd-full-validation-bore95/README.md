# Bore 95: native CPU USD validation

The [receipt](receipt.json) records **ready software dependencies and failed
asset-conformance diagnostics**. This is the first full static validation of
the unchanged source-exact bore-95 solid. No asset repair, stamping, conversion,
material assignment, physics authoring, rendering or head simulation occurred.

This is an assembled whitelist projection of retained private evidence, not
the full native records or a standalone numerical reproduction package.

The source remains the
[previously audited exact solid](../usd-exact-bore95/README.md), SHA-256
`eb73024ebb1e207ef5f77edec5438f4098e0e12cb73cd1181d6845dcf10cc0d8`.
Its geometry, millimetre units, Z-up frame, identity placement and metadata
remain unchanged.

| Diagnostic | Observed result |
| --- | --- |
| Genuine validation preflight | Ready: OpenUSD, Asset Validator, exact locked SimReady runtime and pinned Foundation checkout verified. |
| Generic Asset Validator | Fail: `NormalsExistChecker`, requirement `VG.027@1.0.0`, on `/Head/Solid`. The mesh has no authored normals and uses `subdivisionScheme=none`. |
| Geometry category | Same `VG.027` finding. |
| Physics category | No findings. The asset has no physics schemas or materials; this result supplies no physical validation. |
| `Prop-Robotics-Neutral@1.0.0` | Fail: six normalized feature findings across five requirement IDs, listed below. |

The formal profile findings are:

- `NP.006`: missing standardized SimReady metadata.
- `UN.007`: the profile requires `metersPerUnit=1.0`; this exact source uses `0.001`.
- `RB.001`: missing rigid-body data, reported in two features.
- `GSP.001`: missing grasp data.
- `VM.MAT.001`: missing MDL material.

The installed reference preserves `RB.MB.001` as an ignored finding under its
declared single-component policy. The report contains one mesh and no
`GeomSubset` components. This exception does not remove the other failures.
`GSP.001` repair is classified as outside this validation-only authorization:
earlier minimal/rigid-body gates fail, and robotic handling, gripper constraints
and visually reviewed local-space grasp points have not been established.
No grasp line was authored.

## Native runtime and bounded execution

A fresh owned Linux x86_64 environment uses CPython 3.12.13 and
`usd-exchange=2.3.0`, which supplies **OpenUSD 25.5**. It contains the nine exact
packages from the installed CAD-to-SimReady skill lock:
`omniverse-asset-validator=1.18.0`, `omniverse-usd-profiles=1.10.22`,
`simready-validate=2026.4.8`, `usd-exchange=2.3.0`, `numpy=1.26.4`,
`jinja2=3.1.6`, `markdown-it-py=4.2.0`, `markupsafe=3.0.3` and `mdurl=0.1.2`.
PyYAML 6.0.3 is an additional prerequisite of the unmodified preflight script.

The Foundation checkout is `v2026.04.1`, commit
`a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3`. Sample LFS assets were not downloaded.
The receipt binds public wheel hashes, licence notices, installed module
sources/native binaries, the exact checkout/specifications, reference scripts,
controllers and genuine preflight reports. The four NVIDIA packages and
Foundation declare Apache-2.0; other package notices are recorded separately.
Runtime packages and upstream source copies remain private.

Each validator was restricted to two CPU cores, 4 GiB address space and a
120-second wall deadline. Generic and geometry checks took approximately
7.20 s and 7.01 s; the physics check took 0.28 s. The formal profile run also
completed within its declared bound. No Kit, GPU, Content Agents, paid service
or shared MOOSE runtime was used. Package installation targeted only the new
validation environment.

## Preserved setup and input limitations

The initial bootstrap imported every pinned package successfully, then its
controller failed to parse JSON because Asset Validator printed startup logs
before the JSON line. A separate finalization verified those exact versions.
The first real preflight then reported missing PyYAML. Both failures remain
preserved; PyYAML was added to the new environment before a fresh successful
preflight.

The pinned SimReady library accepts only `.usd` and `.usda` suffixes. The
original `.usdc` invocation therefore evaluated no asset and produced an empty
report. That failure is not credited as a compliance result. A separate
byte-for-byte `.usd` copy, with the **same SHA-256**, received its own genuine
ready preflight and produced the substantive profile report. This copy involved
no OpenUSD serialization or source conversion. Both payload hashes remained
unchanged after validation.

The source and the copy retain `metersPerUnit=0.001`. Simply changing that
metadata to `1.0` would change physical interpretation by a factor of 1000;
no unit normalization was attempted. The earlier exact authoring/minimum
validation evidence remains intact. Full profile passage, solved-field
mapping, physical material calibration, head simulation and manufacturing
authorization remain false.

Primary references:
[NVIDIA standalone Asset Validator](https://docs.omniverse.nvidia.com/kit/docs/asset-validator/latest/source/python/docs/index.html),
[pinned Foundation source](https://github.com/NVIDIA/simready-foundation/tree/a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3),
[pinned profile](https://github.com/NVIDIA/simready-foundation/blob/a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3/nv_core/sr_specs/docs/profiles/profiles.toml).
