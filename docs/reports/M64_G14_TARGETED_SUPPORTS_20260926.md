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
| Central 68 mm + local under-journal links | 166,581 | Passed, 144 poses; 2 mm stiffness target fails |
| Central 68 mm, spine width 40 mm | 203,991 | Passed, 144 poses; 2 mm stiffness target fails |
| Central width 40 mm, root transition 2 mm | 210,893 | Passed, 144 poses; 2 mm stiffness target fails |
| Central root2 + upper journal caps | 214,972 | Passed, 144 poses; 2 mm stiffness screen passes, convergence pending |
| Outer high cheeks, positive side | 204,787 | Passed, 144 poses |
| Outer high cheeks + lower haunches, positive side | 212,906 | Passed, 144 poses |
| Outer high cheeks + haunches extended to z137 | 231,816 | Passed, 144 poses; 2 mm stiffness target fails |
| Outer extended haunches, root transition 2 mm | 239,022 | Passed, 144 poses; 2 mm stiffness target fails |
| Outer root2 + upper caps | 241,503 | Passed, 144 poses; 2 mm stiffness target fails |
| Outer upper caps + lower inner bands | 242,604 | Passed, 144 poses; 2 mm stiffness target fails |
| Outer inner bands + intake inboard web | 247,509 | Passed, 144 poses; FEA pending |

All outer designs were independently constructed and checked on the negative
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

The next pair of hypotheses is a [shorter central root transition](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-central-root-v1.json)
and [outer haunches extended from z108 to z137](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-extended-v1.json).
They add respectively 6,902 mm³ and 18,910 mm³ to their immediate predecessors,
without altering the first millimetre, fixed land, journals or oil paths.
The central transition shortens from 9 to 2 mm; its steeper connection still
requires stress and convergence assessment. No gain is predicted from CAD alone.

The [three candidate support-support intersections](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/combined-candidate-clearance-v1.json)
are zero. Identical individual 144-pose screens cover the unchanged moving
parts; the new check covers the three stationary support pairs. This is not a
minimum-clearance measurement, deformable/hot clearance or assembled FEA.

The next [central upper-cap hypothesis](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-central-caps-v1.json)
adds 4,079 mm³ (1.93%) above the protected journal regions to address the
observed upper-ear/spine displacement difference. Its native test, unchanged
interfaces and 144 sampled poses pass. [Coexistence with the extended outer supports](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/combined-caps-extended-clearance-v1.json)
also passes the three Boolean intersection checks, with before/after hashes.

The next [outer root-transition hypothesis](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-outer-root-v1.json)
shortens the lower haunch ramp to 2 mm and adds 7,205 mm³ (3.11%) per support.
Both independently constructed sides pass their native test and 144 poses,
preserving the first millimetre, fixed land, journals and oil/tool reservations.
These CAD passes do not establish any stiffness gain.
[Coexistence of upper caps and outer root2](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/combined-caps-outer-root-clearance-v1.json)
also passes all three stationary Boolean pairs, without claiming assembled
stiffness or deformed clearance.

## Actual CAD views — isolated supports only

These are native CAD line views, not generated product concepts or stress maps.
The SVG exports are fingerprinted in the CAD receipts; PNGs were rendered with
`rsvg-convert 2.63.0`, white background. They do not show the complete head.

![Central 68 mm support](../assets/m64-g14/central68.png)

![Combined outer support](../assets/m64-g14/outer-combined.png)

![Combined outer support, cut at x=0](../assets/m64-g14/outer-combined-section.png)

![Central support with local under-journal links](../assets/m64-g14/central-local.png)

![Central local-link support, cut at x=0](../assets/m64-g14/central-local-section.png)

![Central support with upper journal caps, isolated CAD view](../assets/m64-g14/central-caps.png)

![Outer support with upper caps, isolated CAD view, coarse stiffness target fails](../assets/m64-g14/outer-upper-caps.png)

![Intake inboard-web candidate, isolated native support, stiffness not yet established](../assets/m64-g14/outer-intake-web.png)

![Intake inboard-web candidate, cut at x=0, not a complete cylinder head](../assets/m64-g14/outer-intake-web-section.png)

The last two PNG fingerprints are respectively `cdc90b63efb8a65b945d1702a77a8d1b2b85cf8fcedc2d7272aefbddea5ffc3a`
and `3ae91ca5ff4e456bb1c6fbaaad31298adabedcb292b0ef633003caf3240787c7`.

## Central 68 mm: completed coarse calculation

The [verified native CPU result](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central68-coarse.json)
uses 128,926 nodes and 84,755 quadratic tetrahedra at 2 mm. Both load cases pass
force/moment equilibrium and the independent FP64 CPU-CG equation check.
Both solvers use the same discretized elasticity problem; this is an algebraic
cross-check, not an independent physical model or experimental correlation.
The maximum force-weighted journal motion is **0.0439716 mm** under +x;
under −z it is 0.0209578 mm. Thus the unchanged **0.040 mm target fails**.
The roughly 7% decrease from G13 central t30 is not sufficient.

CG residuals are 1.012e-10 and 9.697e-11; maximum nodal disagreement divided by
maximum reference displacement is 1.163e-7 and 1.914e-7. The complete run took
483 seconds, and all 37 retained artifact fingerprints were checked. The
corresponding immutable native runner and guard tests are in `native-replay/fea/`.
The existing [G13 native runtime qualification](M64_G13_SUPPORT_REFERENCE_20260926.md)
is reused; no CUDA execution or material qualification is implied.

The combined outer 2 mm run [stopped at the 300-second CG limit](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-combined-cg-timeout.json).
Both direct load cases were executed and equilibrated, but the original run did
not finish its numerical audit. All 36 retained artifact fingerprints match;
the original failure remains immutable.

The [separate 900-second retained-matrix audit](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-combined-cg-retry.json)
has now passed both unchanged numerical checks, without rerunning CCX or
meshing. It confirms **0.0589815 mm** under −z and 0.0456177 mm under +x:
the stiffness target still fails. The two CG solves took 321.6 and 324.2 seconds
(8,880/8,923 iterations), with true residuals 1.11e-10/1.19e-10. All eight new
artifacts and 36 original artifacts were rehashed; the process group is absent.
The 300-second failure is not rewritten as a completed execution.

The [local under-journal links](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-local-coarse.json)
also completed both numerical cross-checks: maximum motion **0.0433335 mm**,
only a 1.45% reduction from central68 for 4.68% added volume. The target still
fails. All 37 artifacts were verified; this run took 493 seconds.
The [width-40 comparator](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central40-coarse.json)
also passes both equation checks, but its **0.0412720 mm** maximum still exceeds
the target by 3.18%. Its 37 artifact fingerprints match; the run took 813 seconds.
No failed coarse candidate is promoted to convergence.

The [2 mm root-transition candidate](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-root2-coarse.json)
is also numerically consistent in both directions, but its maximum is
**0.0410793 mm**: only 0.47% below width40, for 3.38% added volume.
The 164,661-node/110,176-element calculation took 727 seconds; all 40 artifacts
were rehashed. The small gain does not support further root filling as the
next priority. The unchanged target still fails.

The [extended outer haunches](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-extended-coarse.json)
pass both numerical cross-checks. Under +x the largest journal motion falls
to **0.0395699 mm**, but under −z it remains **0.0511259 mm**. The overall target
therefore fails, despite a 13.32% reduction from the shorter haunches for 8.88%
added volume. The 200,339-node/128,555-element run took 1,040 seconds; all
40 artifacts were verified. The −z intake journal vector is
[0.0094700, −0.0423662, −0.0270052] mm: transverse motion still dominates.

These last two candidates used a separately fingerprinted coarse-only CPU recipe:
900 seconds per CG RHS and a 3,600-second process-group deadline. Direct CCX
and matrix-export limits stay at 600 and 900 seconds. Loads, supports,
constitutive parameters, solver algorithm and acceptance tolerances are
unchanged. Four focused recipe tests and both real input checks pass; the
completed calculations above are separate from these preparation checks.

The [central upper caps](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-caps-coarse.json)
complete both numerical cross-checks and reach **0.03822224 mm** at the worst
journal under +x; under −z the maximum is 0.01755186 mm. This is a **coarse
screen pass**, not converged acceptance. The +x global nodal maximum remains
0.05026383 mm: the agreed target is the force-weighted journal norm, not every
node. The caps reduce that journal metric by 6.95% from root2 for 1.93% added
volume. The 169,825-node/112,966-element run took 940 seconds; all 41 artifacts
were rehashed. CG residuals are 1.004e-10/9.966e-11 and direct-field disagreement
is 1.398e-7/2.403e-7. The 1.5→1 mm comparison is still required.

The [outer root2 calculation](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-root2-coarse.json)
also passes both numerical audits, but its maximum remains **0.04682910 mm**
under −z, **17.07% above the target**. Under +x it reaches 0.03883437 mm.
The change reduces the limiting motion by 8.40% from the extended haunches;
it is not promoted to refinement. The 206,787-node/132,568-element run took
1,016 seconds; all 42 artifacts were verified. The independent CG solves took
313.6/313.4 seconds, with residuals 1.072e-10/1.145e-10 and direct-field
disagreement 1.261e-7/1.341e-7. Loads and acceptance gates remain unchanged.

## Energy-guided outer upper-cap hypothesis

Read-only integration of the retained −z fields gives **102.780536 N·mm** for
the [extended haunch](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-extended-minus-z-energy-v2.json)
and **95.939031 N·mm** for [root2](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-root2-minus-z-energy-v1.json).
For each affine C3D10, the four-point stress energy uses the unchanged isotropic
material and actual element volume. Agreement with `0.5 F·U` is 7.02e-10 and
4.79e-9 relative, below the predeclared 1e-4 limit; no renormalization is used.
Three analytic/parser checks and an independent source review pass.

Root2 reduces total energy by 6.66%, almost entirely in the frame. The local
upper region (`y < 45 mm`, `z >= 138 mm`) retains 19.004 N·mm: 19.81% of the
total energy in 3.78% of quadrature-assigned volume. These regions are classified
at Gauss points, not exact clipped-volume integrals. Energy/compliance under −z
does **not** give the exact sensitivity of the limiting journal displacement.

The resulting [single upper-cap CAD hypothesis](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-outer-upper-caps-v1.json)
adds 2,482 mm³ (1.04%) per outer support. The two 6 mm upper caps pass the native
one-solid, void, mirror, first-millimetre, fixed-land, journal, oil and 144-pose
screens. Explicit cam-bore and cap-split masks are unchanged; new material has
zero overlap with declared shaft/lobe/cap-lift and socket reservations.
Conservative reservations already overlap the baseline: these tests establish
**non-aggravation**, not a validated removal sequence or tool fit. The retained
baseline is neither pocketed nor erased to make a test pass.
The [three stationary pairs with the central caps](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/combined-caps-outer-upper-clearance-v1.json)
have zero Boolean intersection, with unchanged source/input fingerprints.

The [completed coarse calculation](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-upper-caps-coarse.json)
now confirms **0.04484792 mm** under −z and 0.03666628 mm under +x. The limiting
motion falls 4.23% from root2, but remains **12.12% above 0.040 mm**. Both
equilibrium and direct/CG checks pass; CG residuals are 1.065e-10/1.125e-10,
field disagreements 1.408e-7/1.368e-7. This 208,904-node/133,901-tetrahedron run
took 1,003 s; all 45 retained artifact fingerprints were checked. The observed
outer process-group peak was 8.697 GiB, not a fine-mesh memory requirement.
This candidate is not promoted to refinement.

The [retained upper-cap energy integration](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-upper-caps-minus-z-energy-v2.json)
gives 88.889582 N·mm, matching `0.5 F·U` within 4.73e-9 relative. Of that energy,
41.35% remains between the top of the 2 mm root transition and z108. The next
[bounded inner-band hypothesis](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-outer-inner-bands-v1.json)
adds 1,100 mm³ (0.456%) per support, keeping the existing bounding box, fixed
land, first millimetre, journals, cam interfaces and named oil/tool reservations.
Both sides pass 144 sampled poses and the [three support-pair checks](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/combined-caps-outer-inner-bands-clearance-v1.json).
The two strips stay outside the nominal spring envelopes. A full connecting
web is not presumed acceptable: the inclined spark-plug removal path would
cross it even though the installed plug itself ends below the support.
These CAD observations do not predict a 0.040 mm pass or qualify hot clearance.

The [completed inner-band coarse calculation](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/outer-inner-bands-coarse.json)
passes both numerical cross-checks but reaches **0.04486064 mm** under −z:
slightly worse than upper caps (0.04484792 mm). The extra strips therefore
provide no demonstrated gain on the limiting metric and are not refined.
All 45 retained artifact fingerprints match; the calculation took 929 s.

The next [single intake inboard-web hypothesis](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/cad-outer-intake-web-v1.json)
adds 4,905 mm³ (2.02%) per support within the same outer bounding box. Its
first millimetre, fixed land, journal/cam masks and oil paths are unchanged;
both sides pass 144 sampled poses, and the [three support-pair intersections](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/combined-caps-outer-intake-web-clearance-v1.json)
are zero. The new native test also rejects a full cross-web that obstructs the
nominal plug withdrawal reservation. No stiffness benefit is inferred from CAD.
The bounded two-load 2 mm CPU calculation is now running. Ten focused runner
tests and its real input check pass; solver algorithms, force magnitudes and
acceptance thresholds are unchanged. Its result remains pending.

The newly checked axial continuation of the nominal Ø22 mm plug socket exposes
an **inherited baseline obstruction of approximately 1,756 mm³** on each side.
The intake web adds zero overlap, but this proves only non-aggravation, not
plug removal or maintenance access. Supplier tooling and the removal sequence
remain unresolved; the baseline has not been silently cut to remove this issue.

Repository checkpoint: `make check` passed (3,113 main-suite tests, 136 optional
skips, plus the separate repository checks); 519 Markdown files have no broken
local links. These are software/provenance checks, not physical validation.

## Refinement resources and algebra benchmark

The unchanged uniform Gmsh mesher has actually generated both finer central
caps meshes, without running an FE solve:

| Mesh | Nodes | C3D10 elements | Kinematic free DOFs | Meshing peak process RSS | Mesh job artifacts |
|---|---:|---:|---:|---:|---:|
| [1.5 mm](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-caps-mesh-1p5.json) | 380,408 | 260,776 | 1,133,403 | 1.135 GiB | 43.4 MB |
| [1 mm](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-caps-mesh-1.json) | 1,204,049 | 853,716 | 3,595,662 | 3.247 GiB | 143.6 MB |

Both retain the 11 mm journal bands and positive four-point Jacobians. These
are **meshing measurements, not direct-solver RAM requirements or convergence
results**. The 2 mm caps direct solves already took approximately 320/316 s;
the former 600 s timeout is not presumed adequate for refinement. New bounded
execution recipes must retain the same decks, material and numerical gates.

### First actual 1.5 mm solve: failed, retained

The [bounded medium attempt](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-caps-medium-failure.json)
failed after 1,684 s before producing any displacement result. Its newly
generated mesh has 380,799 nodes and 261,006 tetrahedra; it is not the mesh-only
preflight above. The +x DAT is empty; −z, matrix export and CG were not executed.
The observed group peak was 16.91 GiB, below its 28 GiB guard, and minimum free
disk was 32.67 GiB. Neither the 1,800 s direct limit nor the resource guard
caused this termination. All 13 retained artifact fingerprints were checked.

A [separate sanitized OS diagnostic](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-caps-medium-crash-diagnostic.json)
records `SIGSEGV` in `I2Ohash_insert`, inside SPOOLES factor post-processing.
The original wrapper omitted the native return code, which remains unknown;
worker/controller exit 2 must not be substituted for it. The raw OS report is
private. This is a software execution failure, not evidence that the support
physically fails. No medium displacement or convergence claim is made.

The subsequent [isolated numerical-library witness](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/spooles-hash-unit-qualification.json)
identifies the exact cause: keys 46,340/46,340 and table size 49,777 produce
46,341², overflowing a signed 32-bit product. The resulting bucket −49,458
matches the crash register; the correct wide-product bucket is 8,947.
The [three-line correction](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/native-replay/spooles-hash-three-line.patch)
widens that multiplication in insertion, lookup and removal; it changes no
FE equation, material, mesh or load. The [small API regression witness](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/native-replay/spooles-hash-reproducer.c)
exposes the original arithmetic failure in all three operations and passes
the corrected round-trips, boundary and collision cases. The first witness's
overstrict ASan-only expectation remains a recorded failure; the separate
qualification explicitly uses the observed arithmetic failure plus the
corrected combined-sanitizer pass. Raw debug reports remain private.
This is a solver-reliability repair, not a cylinder-head result. Rebuilt-solver
reference checks and a separate exact-deck retry are required before any
medium result can be used; the original runtime and failed attempt are retained.

The [rebuilt native reference requalification](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/hashfixed-reference.json)
has since passed both exact G13 load cases. The existing qualified stiffness
matrix is retained and rehashed, with **two fresh FP64 CPU-CG solves**: residuals
1.003e-10/1.041e-10, full-field disagreements 1.723e-7/9.463e-8. Both direct
return codes are zero, force/moment equilibrium passes, all 24 artifacts match,
and runtime fingerprints agree before/after. The requalification took 631 s.
Only `I2Ohash_util.o` changed in the isolated SPOOLES archive; the CCX objects,
ARPACK and six non-system dynamic libraries were retained. The separate cube
witness passed the analytic displacement, reaction and matrix checks.
This establishes the replacement solver reference, not the fine-mesh target.
The separately bounded medium retry reuses the failed attempt's exact mesh and
`x.inp`; only nodal load direction/sign is transformed to create −z. Six focused
tests cover the transformation and execution handling. No remeshing or change
to E, nu, supports, load magnitudes or numerical acceptance limits is allowed.

### Exact 1.5 mm retry: completed numerical checks

The [verified exact-deck retry](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/central-caps-medium-hashfix.json)
now passes both native direct solves, fresh FP64 CG checks and force/moment
equilibrium. Maximum force-weighted journal motion is **0.03837624 mm**;
the +x global nodal maximum is 0.05069639 mm and is not the target observable.
CG true residuals are 1.068e-10 and 9.879e-11; full-field disagreements are
1.386e-7 and 2.416e-7. All 37 retained artifact fingerprints match. The run took
4,285 s, with an observed process-group peak of 24.32 GiB and minimum free disk
26.68 GiB. Native direct return codes are recorded as zero.

| 2 → 1.5 mm comparison | +x | −z |
|---|---:|---:|
| Maximum raw journal-vector relative change | 0.4071% | 0.5336% |
| Integration-point p95 stress relative change | 1.1654% | 2.7214% |

The unchanged comparison formula divides vector differences by the finer
vector norm, without deleting transverse components. These intermediate
changes meet the 1%/5% stability thresholds but **do not substitute for the
required 1.5 → 1 mm comparison**. The original failed medium run is preserved.
No hot material, contact/preload, assembled or manufacturing claim follows.
The measured medium memory peak is not a bound for the 3.60-million-DOF fine
problem; no fine direct solve is silently launched against the Mac's 64 GiB.

A [retained-matrix PyAMG experiment](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/amg-benchmark.json)
compares fixed symmetric V-cycle preconditioning with the existing Jacobi CG
on the same qualified outer-extended stiffness and two RHS, all FP64 CPU.
All four algebra comparisons pass. Jacobi takes 694.78 s for its two setup/solve
phases; AMG takes 445.25 s plus 6.55 s preparation/hierarchy setup: **1.54× for
those phases**, not for complete FEA. Charging all 19.41 s unallocated worker
overhead to AMG gives 1.47×. Concurrent host work limits benchmark generality.
The [controller](../../twins/m64-cylinder-head/evidence/g14-targeted-supports-20260926/amg-benchmark-controller.json)
exits successfully and reaps its group within 1,174 s. No new mesh, CCX solve,
CUDA execution, production-recipe promotion or mechanical acceptance results
from this benchmark. Sources and self-checks are archived under `native-replay/fea/`.

## Remaining gates

G14 overall target stiffness and 1.5→1 mm convergence are not established;
the central upper-cap candidate passes the 2 and 1.5 mm cold isolated screens,
while the outer candidates above still fail the 2 mm stiffness target.
The fixed-land model remains idealized; generic E=70 GPa and nu=0.33 are not a
qualified hot material card. Thermal response, fatigue, contact/preload,
machining allowances, printing qualification and engine correlation remain
separate requirements.

The combined outer introduces no material inside the existing finite tool
reservations. However, the inherited base already intersects the two mount-tool
volumes by approximately 562 and 579 mm³. Those obstructions are explicitly
retained, not declared accessible or silently removed. Full machining and
assembly access therefore remains unresolved, independently of stiffness.
