# M64 G14 — targeted support stiffening

The unchanged target is **0.040 mm force-weighted journal displacement** for
the isolated, generic cold-load screen. It is not a dimensional tolerance or
an authorization to print, assemble or start an engine.

## Why change the G13 design

The [verified G13 coarse calculations](M64_G13_SUPPORT_REFERENCE_20260926.md)
gave 0.047238 mm for the central support and 0.076510 mm for the outer support.
Both passed the direct/CPU-CG equation and equilibrium checks, but neither
passed the mechanical target. They were not refined or relabelled successful.

Node-band observations of the retained fields guide these hypotheses:

- Central: displacement grows through the height and near the terminal journal
  connections. Extend the inner spine towards these connections.
- Outer, +x: the upper rib moves substantially more than the adjacent frame.
  Add high cheeks between them, leaving the shaft neighbourhood clear.
- Outer, −z: much of the transverse y displacement is shared by the frame.
  Add lower haunches as well, rather than presuming the high cheeks solve it.

These are observations of nodal displacement, not an energy decomposition or
proof of a unique cause. Only subsequent FE calculations can establish gains.

```mermaid
flowchart TD
  A[G13: numerical checks pass, mechanical screen fails] --> B[Inspect both +x and -z fields]
  B --> C[Central spine revised]
  B --> D[Outer high cheeks plus lower haunches]
  C --> E[CAD, interfaces, oil paths and 144 sampled poses]
  D --> E
  E --> F[Native CPU two-load coarse FEA and independent algebra check]
  F --> G{Motion below 0.040 mm?}
  G -->|No| H[Retain failure and reconsider geometry]
  G -->|Yes| I[Require 1.5 to 1 mm convergence before scoped acceptance]
```

## Native geometry evidence

| Candidate | Volume, mm³ | Geometric screen |
|---|---:|---|
| Central 70 mm full height | 161,640 | Rejected: four rocker-boss collisions |
| Central 68 mm full height | 159,133 | Passed, 144 poses |
| Central 70 mm with upper shoulder | 158,518 | Passed, 144 poses |
| Central 68 mm + local under-journal links | 166,581 | Passed, 144 poses; FEA pending |
| Central 68 mm, spine width 40 mm | 203,991 | Passed, 144 poses; FEA pending |
| Outer high cheeks, positive side | 204,787 | Passed, 144 poses |
| Outer high cheeks + lower haunches, positive side | 212,906 | Passed, 144 poses |

Both outer designs were independently constructed and checked on the negative
side too. Their whole-body reflected Boolean differences are zero at the
model's OCCT tolerance. This is not physical metrology.

The full-height 70 mm spine intersects the actual exhaust rocker boss by
3.606218 mm³ and the intake boss by 0.817849 mm³ per side. The failure is kept;
moving-component envelopes were not subtracted to disguise it. A separate
native regression check reproduces the collision and the accepted central
variants' unchanged first millimetre and journal neighbourhoods.

The complete first millimetre above the base, the fixed footprint, Ø12.58 mm
bores and 11/8 mm central/outer journal bands are preserved. Oil-tool paths and
the enclosed-void screens pass. All accepted shapes remain one native BRep
solid within the existing assembly envelope. The 144 rigid poses do not prove
continuous, deformable or hot running clearance.

Exact receipts: [initial CAD](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-v1.json),
[independent interface replay](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/interface-v1.json),
[combined outer CAD](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-lower-v1.json).
The [two subsequent central hypotheses](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-central-v2.json)
add respectively 7,448 mm³ (4.68%) and 44,858 mm³ (28.19%) to the 68 mm spine.
Both preserve the full first millimetre, journal neighbourhoods and oil paths.
The two existing central-mount pilot tools have zero intersection with either
the baseline or the new material; complete tool approach remains unqualified.
Source and native test snapshots accompany them under `native-replay/`.
Restore these snapshots to `work/m64-g14/` to use their original relative paths;
the fingerprinted private inputs are still required. This is not a standalone
public reproduction package, and raw STEP/scan files are not published.

## Actual CAD views — isolated supports only

These are native CAD line views, not generated product concepts or stress maps.
The SVG exports are fingerprinted in the CAD receipts; PNGs were rendered with
`rsvg-convert 2.63.0`, white background. They do not show the complete head.

![Central 68 mm support](../assets/m64-g14/central68.png)

![Combined outer support](../assets/m64-g14/outer-combined.png)

![Combined outer support, cut at x=0](../assets/m64-g14/outer-combined-section.png)

![Central support with local under-journal links](../assets/m64-g14/central-local.png)

![Central local-link support, cut at x=0](../assets/m64-g14/central-local-section.png)

## Central 68 mm: completed coarse calculation

The [verified native CPU result](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central68-coarse.json)
uses 128,926 nodes and 84,755 quadratic tetrahedra at 2 mm. Both load cases pass
force/moment equilibrium and the independent FP64 CPU-CG equation check.
The maximum force-weighted journal motion is **0.0439716 mm** under +x;
under −z it is 0.0209578 mm. Thus the unchanged **0.040 mm target fails**.
The roughly 7% decrease from G13 central t30 is not sufficient.

CG residuals are 1.012e-10 and 9.697e-11; maximum nodal disagreement divided by
maximum reference displacement is 1.163e-7 and 1.914e-7. The complete run took
483 seconds, and all 37 retained artifact fingerprints were checked. The
corresponding immutable native runner and guard tests are in `native-replay/fea/`.
The existing [G13 native runtime qualification](M64_G13_SUPPORT_REFERENCE_20260926.md)
is reused; no CUDA execution or material qualification is implied.

The combined outer 2 mm calculation is separate. Local central connections
and a wider-spine comparator remain hypotheses until their own CAD and FE
checks complete. No failed coarse candidate is promoted to convergence.

## Remaining gates

G14 target stiffness and 1.5→1 mm convergence are not established.
The fixed-land model remains idealized; generic E=70 GPa and nu=0.33 are not a
qualified hot material card. Thermal response, fatigue, contact/preload,
machining allowances, printing qualification and engine correlation remain
separate requirements.

The combined outer introduces no material inside the existing finite tool
reservations. However, the inherited base already intersects the two mount-tool
volumes by approximately 562 and 579 mm³. Those obstructions are explicitly
retained, not declared accessible or silently removed. Full machining and
assembly access therefore remains unresolved, independently of stiffness.
