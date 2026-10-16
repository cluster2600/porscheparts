# Bore95 normal-only USD: actual CPU validation

The original bore95 study now has a normal-bearing USD derivative. Its full
ordered geometry and every other authored property match the original; an
independent checker verifies all **1,804,706 face normals** against predeclared
binary32 error bounds. These are asset and software checks. No material,
collider, rigid body or computed engineering field was added.

The [sealed evidence capsule](derived/engineering/usd-face-normals-bore95/README.md)
contains labelled report projections, complete logical input/artifact maps,
exact small reports and separate root/peer reviews. Original captures remain
unchanged and are bound by SHA-256. The reviews check all 494 captured files
from ten native steps and the byte-copy step. Reassembling this capsule runs
no native engineering solver.

The [verified English review download](derived/engineering/usd-face-normals-bore95-review-delivery/README.md)
contains the original asset, the normal-bearing alias and this sealed evidence.
Its ZIP and two metadata assets are uploaded to the existing draft release;
all 30 earlier assets remain intact.

## Results and scope

| Actual check | Result | Meaning |
| --- | --- | --- |
| Original, derivative and alias preflights | Ready | Each validator binds its own exact source and ready manifest |
| Normal authoring and full independent check | Pass | Geometry bytes and other authored content unchanged; every face normal checked |
| Official minimum validation | 8 checks pass | Stage opens; default prim, axis and unit metadata are available |
| Generic CPU validation | Pass | No reported issues; the pinned legacy validator fallback was used |
| Geometry category | Pass | No reported category issues; this does not establish finite-element quality |
| Physics category | Pass | No reported category issues, with zero authored bodies, colliders or material bindings |
| Prop-Robotics-Neutral 1.0.0 | **Fail** | Six failed feature rows across five requirement IDs, preserved below |

| Formal feature | Failed requirement |
| --- | --- |
| FET000_CORE | NP.006: naming |
| FET001_BASE_NEUTRAL | UN.007: metre-based units |
| FET003_BASE_NEUTRAL | RB.001: rigid-body requirements |
| FET004_BASE_NEUTRAL | RB.001: rigid-body requirements |
| FET005_BASE_NEUTRAL | GSP.001: grasp metadata |
| FET006_BASE_MDL | VM.MAT.001: visual material |

The report also retains the validator's single-component policy exception for
`RB.MB.001`, its ignored issue and its warning. It is not silently deleted.
The profile exits with native code 1 and controller code 2 for recorded
findings; there is no controller error or unreaped worker. All native pinned
inputs remain unchanged. Declared limits were two CPU cores, 4 GiB address
space and 120 seconds per step, except author/check at 6 GiB and 90 seconds.
Actual peak RSS and CPU consumption were not sampled.

The installed SimReady API accepts `.usd` and `.usda` at its pinned source
locator; it skips `.usdc`. The substantive profile therefore uses a separately
verified **byte-identical `.usd` alias**, with its own fresh ready preflight.
The 39,026,927-byte normal-bearing content has SHA-256
`b5cbcc23c6d59762c4a0e876691b2815ef402fc906be53aac069e46935d6850f`.
The original USDC remains
`eb73024ebb1e207ef5f77edec5438f4098e0e12cb73cd1181d6845dcf10cc0d8`.
No API source, wheel, runtime binary or private transport capture is published.

The [FET005 workflow guidance](https://github.com/NVIDIA/simready-foundation/blob/a1e9dd68ee2d107f74dc6cd6da875b54ad3f8fd3/skills/simready-foundation-conform-fet-005-simulate-grasp-physics/SKILL.md)
expects earlier core/unit checks to pass and usually the rigid-body check.
Those findings remain unresolved, so grasp repair is held for a separate
physical-authoring scope. This is workflow sequencing guidance; the actual
FET005 native dependency field is `[]`. Its actual `GSP.001` result remains
**Fail**. No grasp points, metadata stamp or arbitrary physical properties were
authored to obtain a pass.

## Geometry lineage and next engineering gate

This derivative retains the **original 902,145 vertices and 1,804,706 faces**,
including its original 744 triangles below the necessary analysis-quality
screen. It does not use the [separate endpoint003 proposal](derived/engineering/finest-endpoint-003-head/README.md),
which has 901,861 vertices, 1,804,138 faces and 266 deficient triangles and
remains rejected. Neither geometry has become an accepted analysis mesh.
Other bores do not inherit this full bore95 validation checkpoint.

Continue with the original-surface quality investigation and unchanged
distance/volume acceptance gates before head thermal or structural solves.
Material selection, calibrated whole-head LPBF, mapped computed twin fields,
PhysicsNeMo training/evaluation, OEM dimensional fidelity and manufacturing
authorization remain open in the [engineering programme](ENGINEERING_PROGRAM.md).
