# 964 monocoque shell, from plate 50-05a

A 911-shaped body shell for the
[carbon monocoque programme](../../../docs/MONOCOQUE_964_993_PROGRAMME.md).
Until now the programme's only whole-body model was the box cell of
[`../fea/`](../fea/): good at relative questions, nothing like a 911. This
shell takes its outline from Porsche's own drawing.

## Numerical and stress-demand audit — 2026-10-12

The preceding interface work was ported and merged in [PR #140](https://github.com/cluster2600/porscheparts/pull/140).
The current baseline also includes the bulkhead correction (#152), the tube
studies (#154/#155) and bending (#156). Do not merge the obsolete interface
branch over the corrected datum chain.

[`source/strength_audit.py`](source/strength_audit.py) reuses the **F0 skin-box
model**, not the old truss or a new geometry: 43,719 nodes, 89,608 S3 elements,
420 sections and assumed equivalent-isotropic carbon. It retains every input,
solver log, nodal result and integration-point stress. The machine-readable
[receipt](derived/strength-audit-20261012.json) includes their SHA-256 digests,
the source digests, all six runs and all 16 numerical checks.

| Serial run | Applied load | Response | Stiffness |
|---|---|---|---|
| torsion | 1,142.561 N·m | 0.032220° | 35,461.55 N·m/deg |
| torsion, doubled | 2,285.122 N·m | 0.064439° | 35,461.55 N·m/deg |
| bending | 2,000 N | 0.144698 mm | 13,821.88 N/mm |
| bending, doubled | 4,000 N | 0.289396 mm | 13,821.88 N/mm |

Reversing each load reverses its displacement and stress fields exactly at
the precision printed. The largest relative scaling discrepancy is 3.19e-7;
the external-force balance error is at most 1.86e-7 of the applied absolute
load. Prescribed translations are zero to numerical precision. These checks
reproduce the published finest-mesh stiffnesses; they do **not** establish
stress convergence, correct physical boundary conditions or vehicle safety.

### Parallel run rejected, not averaged away

On the same local ARM64 CalculiX 2.21 image, four-thread SPOOLES first returned
44,630.11 and 46,411.28 N·m/deg for opposite loads, then crashed on the doubled
load with `fatal error in SubMtx_denseInfo`. That is a failed numerical run,
not an alternative design result. Its physical input blocks are byte-identical
to the corresponding serial runs; only output requests changed. The serial
run reproduces main's 35,462 N·m/deg and passes the sign/scaling checks.

`torsion.run()` now defaults to **one thread**, retaining an explicit
`OMP_NUM_THREADS` override. The historical agreeing-pair selection remains for
compatibility, but is not a correctness proof. This observation does not
identify the precise upstream defect or qualify other solvers/platforms.
The rejected input and log hashes are in the
[execution record](derived/strength-audit-execution-20261012.json).

### Strength: stress demand is now available, no pass claimed

The old `OUTPUT=2D` stress images average through the shell thickness and
remove bending stresses. The new `*EL PRINT, GLOBAL=YES` output records all
179,216 integration points, including both thickness points of each S3.
This distinction follows the [CalculiX manual, sections 7.51–7.52](https://www.dhondt.de/ccx_2.22.pdf).
An independent cantilever test checks the through-thickness axial stress
against beam theory away from its clamp and load, with a 15% discretization
tolerance. It also confirms that the averaged plot omits most of this bending
stress (but retains transverse shear).

| Unit case | Largest principal tension | Largest principal compression | Maximum von Mises display scalar |
|---|---|---|---|
| torsion, 1,142.561 N·m | 21.655 MPa | −18.367 MPa | 16.771 MPa |
| bending, 2,000 N | 16.083 MPa | −34.490 MPa | 25.841 MPa |

These are integration-point peaks of the **equivalent isotropic model**,
not ply stresses, surface extrapolations or material allowables. Von Mises is
not a CFRP failure criterion. The two display peaks lie near
`X=-1725, Y=715, Z=871 mm`; local mesh/section details need investigation
before using a peak for design. No reserve factor is invented: allowable,
reserve factor and strength pass are explicitly `null`.

The requested 1,200 kg vehicle corresponds to 11,767.98 N of weight, but this
weight is **not** silently applied as the 2 kN bending load. Axle loads, mass
locations, suspension forces, inertial/aero cases and measured interfaces are
still required. Next: qualified ply/core/bond data and layup/orientation;
converged local and layered models; then buckling, fatigue, joints, physical
correlation and professional review. No crash, manufacturing or TÜV approval
is supplied by this audit. Status remains `prohibited_pending_engineering`.

Reproduce where the existing numerical dependencies and `ccx` are installed:

```sh
OMP_NUM_THREADS=1 python3 twins/964-chassis/monocoque/source/strength_audit.py \
  --output work/964-strength-new-run
python3 -m unittest discover -s tests -p test_964_strength_audit.py -v
```

The output directory must not exist. The solver witness skips unless `ccx`
is on PATH; it was **executed**, not skipped, for this audit. Generation ran
on the Mac and solving in a bounded local ARM64 Docker container, without
network or paid compute. Kali's previously recorded SSH addresses timed out.
Full raw results remain locally under `work/964-strength-serial-20261012/`;
they are not embedded in Git. Historical reports and figures are unchanged.

![The shell from four sides](evidence/shell-views.png)

*Four views of `derived/monocoque-shell.ply`. Outline from the workshop
manual; sections, thickness and openings modelled. Not a part, not a ZESAD
geometry, nothing to manufacture.*

## Where the shape comes from

Plate 50-05a of volume V ("Dimensions for assembly - from Model 91 onward")
draws the body-in-white from the side and from above, to scale, with the front
wings, doors and lids off: the outline of a monocoque. Both views were
calibrated on the markers whose fore-aft positions are published
([datum chain](../README.md#the-longitudinal-chain-closed-from-plate-50-05a)),
1.1253 and 1.1287 mm per pixel at 400 dpi, and traced
(`source/trace_plate_50_05a.py`):

| traced | used for |
|---|---|
| side view, upper profile | front lid, windscreen, roof, rear deck |
| side view, lower profile | front apron, floor, rear structure |
| plan view, half width | body width along the car |
| door aperture, quarter window, rear wheel house | openings |

The plate is not in the repository. Its trace, one point every 13.5 mm, is
`data/profiles-50-05a.json`; heights are anchored on the published 964 height
of 1310 mm.

## What is modelled, not traced

`source/build_shell.py` builds one closed section every 11 mm and stitches
them:

- a rounded lower body with a barrel side, more swollen over the rear
  quarters, up to an **880 mm beltline** (the quarter-window bottom on the
  plate);
- above it a superellipse greenhouse to the roof, which gives the 911
  tumblehome; where the profile drops under the belt, a crowned lid;
- openings cut along continuous fields, so their edges stay smooth: doors and
  quarter windows from the plate, windscreen and rear window between the
  pillars, front-lid and engine-lid openings, open engine bay underside, both
  wheel arches;
- a front bulkhead under the scuttle, a rear bulkhead behind the seats, four
  cylindrical wheel houses.

Section shapes, beltline, glass and lid extents, wheel-house radii and
bulkhead heights are **modelling hypotheses**. No sheet thickness,
reinforcement or sill box section is drawn.

## A first whole-body calculation

`source/torsion.py` runs the box model's torsion load case on the structural
shell (shell and bulkheads, without the wheel houses, which are not connected
node to node): rear suspension area clamped, ±1000 N at the front wheel-house
tops, linear S3 shells, uniform 0.8 mm steel.

![von Mises stress under torsion](evidence/torsion-von-mises.png)

**K = 3,209 N·m/deg.** It is the stiffness of this surface model under this
load, not of a 964 body shell: the door and window apertures are open, there
is no glass, no boxed sill, no wheel house in the load path, and the mesh is
not converged. What holds is where the load goes: around the windscreen
frame, into the A-pillars and the corners of the door apertures, and across
the C-pillars, with the floor and the roof lightly loaded. The hot spots
around the front wheel-house tops are local: that is where the load is
applied. That is the open shell a monocoque has to close. (Until
2026-10-11 this read 2,261: the bulkheads were missing, see
[Corrections](#corrections-2026-10-11).)

## The monocoque inside it, in PicoGK

[`picogk/`](picogk/README.md) builds a ZESAD-type carbon monocoque in voxels
inside this shell, with the pinned PicoGK kernel. It has an outer skin, a
closed section around every aperture, boxed sills, a tunnel and rails,
sandwich floor and bulkheads, and wheel tubs. That closes the rings this open
shell leaves open. It is a design envelope, not a part.

![The PicoGK monocoque](evidence/zesad-monocoque-views.png)

## An independent closed-ring study, in PicoGK

[`picogk-rings/`](picogk-rings/README.md) is a second, independent PicoGK
study on the same shell: tubes tangent to the skin for the rings the torsion
case loads (windscreen frame and A-pillars, B-hoop, C-pillars, wheel arches),
boxed sills, a central tunnel with a C4-tube clearance check, solid sandwich
floor and bulkheads, drain holes, a thin-wall mass breakdown and an
independent mesh QA (one body, no sealed void). Study geometry only, same
`prohibited_pending_engineering` status.

![PicoGK closed-ring study](evidence/picogk-monocoque.png)

## Torsion of the monocoque architecture

`source/torsion_monocoque.py` puts the members of [`picogk/`](picogk/README.md)
on the open shell's own mesh, as shells, and reruns its load case. The two
answers therefore differ by the architecture alone. Each closed section is
built from three parts:

- **outer wall:** a band of skin;
- **inner wall:** a copy of the band, offset inward by the section depth;
- **sides:** a wall along every free edge of the band, including a flange
  on the aperture edge.

Sizes come from the PicoGK report. There are four cases, solved at three
shell densities (210, 300 and 420 sections):

| case | mass | K, 210 / 300 / 420 sections |
|---|---|---|
| open shell, 0.8 mm steel | 69 kg | 7,123 / 4,792 / 3,209 N·m/deg |
| open shell, CFRP | 43 kg | 5,681 / 3,624 / 2,418 |
| **monocoque, 0.8 mm steel** | 135 kg | **41,578 / 47,750 / 47,267** |
| **monocoque, CFRP** | 84 kg | **30,786 / 34,834 / 35,462** |

![Open shell and monocoque in torsion](evidence/torsion-monocoque.png)

*Top: von Mises stress on one colour scale, same steel, same load. Bottom:
rotation of each cross-section along the car under the 1.14 kN·m torque.*

What holds, and what does not:

- **The monocoque's K is stable on the two finer meshes.** They agree
  within 2%; the coarsest is 12-13% lower, its bands being too coarse. The
  open shell's K is not stable at all: it keeps falling. With its apertures
  open, it is close to a mechanism. **The ratio between the two (×5.4 to
  ×15 depending on the mesh) is therefore not a result.** What remains is
  that the closed architecture is more than five times stiffer than the
  open shell at any density tried.
- **The load path changes.** On the open shell, the stress collects at the
  windscreen frame, the A-pillars and the door corners. On the monocoque it
  spreads at a low level, and the twist builds up evenly from the clamp to
  the front instead of in steps at each aperture.
- **Carbon versus steel**, same architecture: 0.73 to 0.75 of the stiffness
  for 0.62 of the mass. That is ×1.17 to ×1.20 in specific stiffness, close
  to the ×1.25 found earlier on the box cell ([`../fea/`](../fea/README.md)).
  The architecture remains the lever, not the material.

Limits that come on top of the shell's own:

- Doors, glass, joints and inserts are absent, and every member size is
  assumed. K is a value of this model, not of a car.
- The offset folds at the tightest curvatures. There the depth is cut back
  locally: 709 of 15,493 section vertices, to 0.63 of nominal on average.
- The sills are 140 mm deep, not 210. The rear rails and wheel tubs are
  left out.
- The sandwich panels count by their faces only, which is on the soft side.
- Two other convergence checks were tried and rejected: S6 elements (the
  slivers of the aperture clip collapse the open shell), and splitting
  every triangle of the monocoque in four (more than 12 GB for the direct
  solver).
- CalculiX now and then returns a K that is too high for the same input
  (+2% to +60%, never too low), while a correct solve repeats to the unit.
  Every value is therefore the one two solves agree on, and all the solves
  are kept in the JSON.

## Two architectures, one load case

The repository holds a second PicoGK study on the same shell,
[`picogk-rings/`](picogk-rings/README.md). It closes the body with discrete
tubes, Ø50 to 70 mm, tangent to the skin from inside (windscreen frame and
A-pillars, B-hoop, C-pillars, roof rails, wheel arches), plus boxed sills
and a tunnel. `source/torsion_rings.py` runs it through the same mesh, the
same clamp and the same load:

- **sills and tunnel** are built as skin bands, as above;
- **each tube** is a beam carrying the tube's area, bending and torsion
  stiffness, tied by short stiff links to every skin node within 20 mm of
  its tangent point: a bonded strip about 40 mm wide (ASSUMED);
- **all members and paths** come from the study's own parameters and
  `prepare.py`.

Checked on a cantilever plate with a tube, the method is 12% stiffer than
composite beam theory.

| CFRP layup | mass | K, 210 / 300 / 420 sections | K per kg, 210 / 300 / 420 |
|---|---|---|---|
| open shell | 43 kg | 5,681 / 3,624 / 2,418 | 134 / 85 / 57 |
| `picogk-rings/` without its tubes | 58 kg | 7,137 / 5,038 / 4,600 | 124 / 87 / 80 |
| **`picogk-rings/`, tubes, 40 mm bond** | 73 kg | **42,504 / 38,640 / 38,630** | **585 / 532 / 532** |
| **`picogk/`, skin boxes** | 84 kg | **30,786 / 34,834 / 35,462** | **365 / 413 / 420** |

![Two architectures in torsion](evidence/torsion-architectures.png)

**The tube result hinges on the bond.** Tied to the skin at a single node,
as first done, a tube sinks into the skin as the mesh is refined, and K
lost 15% per refinement. Tied over a strip, it converges: 38,640 then
38,630. But K then follows the strip width assumed
(`torsion_rings.py --bond-sensitivity`):

| bonded strip | K, 300 / 420 sections | against the skin boxes, per kg |
|---|---|---|
| a single node | 27,705 / 23,665 (not converged) | ×0.78 |
| 20 mm | 28,833 / 25,155 (not converged) | ×0.82 |
| **40 mm** | **38,640 / 38,630** | **×1.27** |
| 60 mm | 56,278 / 57,508 | ×1.89 |

A beam element has a rigid cross-section. Tying a skin strip rigidly to
it assumes that the tube never ovalizes and passes all the shear: the
wider the strip, the more stiffness the model invents. That makes the
strip ties an upper bound, while the point tie, which sinks, is a lower
bound. **The skin boxes, at 35,462, sit inside that bracket.**

**Tubes meshed as shells.** `source/torsion_shell_tubes.py` gives every
tube its own wall:

- S3 shells, refined with the skin;
- bonded along the line of tangency to the skin triangle beneath
  (translation ties);
- tied to each other where they meet.

On a cantilever plate carrying a tube, this bond converges to 9% softer
than composite beam theory. That is physical: the shell can ovalize. Tying
more lines around the tube was tried and rejected, because it came out
stiffer than the theory, which is impossible.

| CFRP layup | K, 210 / 300 / 420 sections | against the skin boxes, per kg |
|---|---|---|
| `picogk-rings/`, shell tubes, line bond | 35,198 / 29,607 / 25,895 | ×0.75 / ×1.01 / ×1.18 |
| `picogk-rings/` without its tubes | 7,137 / 5,038 / 4,600 | |
| `picogk/`, skin boxes | 30,786 / 34,834 / 35,462 | 1 |

What holds:

- **The tube model still does not converge** (−16%, then −13%). This time
  the bond is not the cause: the tubes are refined with the skin. The
  cause is the skin between the tubes. Bonded to the tubes along a line
  only, it stays an open skin, and its flexibility keeps growing as the
  mesh is refined, as the open shell's does. The beam tubes on strips
  seemed to converge only because their rigid strips stiffened that skin.
- **In the skin-box architecture the same skin is one wall of the closed
  sections,** and that model is stable. On the finest mesh the boxes lead
  by ×1.18 per kilogram, and the gap grows with each refinement.
- **This is the design result:** a closed section formed with the skin
  puts the skin to work. Tubes added to the skin leave it open, unless
  their joint is a wide, stiff flange, which is then the part to design.
  The ranking now leans to the skin boxes with a physical bond. It is not
  a converged number: the tube model's absolute K is not known.
- **The tubes do work:** 5 to 6 times the model without them, for 15 kg.

Neither model is a design. The `picogk/` boxes are larger and heavier: its
members include rings around the lids and arches and a full B-ring, while
`picogk-rings/` frames the doors with Ø50-60 tubes only. Both stay
`prohibited_pending_engineering`.

## What each member is worth

`source/member_study.py` removes each member of `picogk/` in turn from the
CFRP shell model and measures what it costs. It reports two measures:

- **K at the load points**, as everywhere in this folder;
- **the cabin's own K**: the torque over the rotation difference between
  d = 400 and d = 1950 mm. It leaves out the load introduction at the front
  wheel houses and the clamped rear.

The study runs on two meshes (300 and 420 sections).

![Members in torsion](evidence/torsion-members.png)

| member | mass | K lost | cabin K lost | reading |
|---|---|---|---|---|
| door rings | 4.4 kg | 19-20% | 27-31% | carries the cabin |
| windscreen frame | 2.1 kg | 18-22% | 24-27% | carries the cabin |
| quarter-window rings | 1.1 kg | 23% | 17-20% | best return: 7,200 N·m/deg per kg |
| sills | 3.3-3.8 kg | 5-7% | 8-11% | carries the cabin |
| rear arches | 1.4-1.6 kg | 5% | 5% | small |
| B-ring | 2.8-3.0 kg | 3% | 4-5% | small alone |
| tunnel, rear window, front rails | 0.9-4.2 kg each | 0-4% | 0-4% | small |
| front lid, front arches | 1.8-3.5 kg each | 10-23% | -2 to 2% | the load introduction, not the cabin |
| engine-lid ring | 1.6 kg | 0-0.1% | 0-0.1% | worth nothing in torsion |

*Ranges cover the two meshes. The architecture as a whole returns 420 to
435 N·m/deg per kg.*

**Removed together, the weak members cost more than one by one.** Without
the B-ring, the rear-window ring, the tunnel, the front rails and the
engine-lid ring, the model loses 10 to 13% of its K and 14 to 16% of the
cabin K, for 11 to 15 kg. One at a time, the same five sum to 7 to 11% and
9 to 12%: the B-ring and the rear-window ring close the back of the cabin
together. Leave-one-out alone does not license pruning.

What it means for the design:

- **The cabin is carried by the door rings, the windscreen frame, the
  quarter-window rings and the sills.** These closed sections deserve the
  effort: depth, wall, joints.
- **The front lid ring and the front arches stiffen the load introduction,
  not the cabin.** With the bulkheads in place, the cabin measure no longer
  sees them.
- **The engine-lid ring can go:** 1.6 kg for nothing measurable in torsion.
- **The other weak members are a trade, not a free gain.** Pruning them
  gains 5 to 6% in K per kg but loses 14 to 16% of the cabin's stiffness.
  And torsion is one load case: the B-ring is the roll-over and
  side-impact hoop, and the tunnel houses the C4 driveline. Neither is
  judged here.

## Where the carbon pays

`source/layup_study.py` keeps the members and moves the plies. Each family
of walls gets 0.5 mm more CFRP in turn, and the gain is measured per
kilogram added:

![Where the carbon pays](evidence/torsion-layup.png)

| family | area | F0 | cabin K per kg added |
|---|---|---|---|
| box outer walls (skin forming a closed section) | 3.0-3.2 m² | 2.0 mm | 1,690-1,720 |
| free skin | 3.7-3.9 m² | 2.0 mm | 990-1,390 |
| box inner and side walls | 9.4-10.5 m² | 2.5 mm | 1,140-1,170 |
| floor (sandwich faces) | 2.2 m² | 2.4 mm | 450 |
| bulkheads (sandwich faces) | 1.9 m² | 2.4 mm | 240-270 |

**F1, at the mass of F0** (fixed rule, see the script):

1. remove the engine-lid ring;
2. thin the bulkhead faces from 2.4 to 1.9 mm;
3. give the freed mass to the families in order of return: the skin that
   forms the boxes goes from 2.0 to 2.5 mm, the remainder to the inner
   walls (2.54-2.56 mm).

The result is **+5.6 to +5.7% in K and +5.7 to +5.9% in cabin K, for the
same mass**, on both meshes.

What it says:

- **The plies pay where the skin is part of a closed section**: four to
  seven times more than in the floor or the bulkheads.
- The bulkheads and the floor matter for closing the body (see
  [Corrections](#corrections-2026-10-11)), but extra thickness in them
  returns little.

Limits:

- Torsion only, linear, S3. No strength, buckling, impact, joint or
  manufacturing check.
- A thicker skin than +0.5 mm inverts S3 elements on the clipped aperture
  edges, so F1 caps each family at +0.5 mm. That is a limit of the mesh,
  not of the design.

## Bending: the same members, other weights

`source/bending.py` asks whether the members that carry torsion also carry
the other global load case: the body as a beam between its axles. It uses
the same shell models, materials and meshes, with a different load:

- **supports:** the suspension patches of the torsion case, cut down to a
  strip of ±40 mm around each axle and held vertically (rollers at the
  front, pins at the rear, no clamp moment);
- **load:** 2 kN downward, spread over the skin of both sills within
  ±100 mm of mid-wheelbase. The load goes on the sills, not the floor,
  because the floor is modelled by its sandwich faces only;
- **two measures:** K, the force over the mean deflection of the loaded
  skin (N/mm), and the cabin's own sag, the mid-wheelbase deflection
  below the chord between d = 400 and 1950 mm. Deflections are read on
  the sill line, not on whole sections, which also distort.

![Bending](evidence/bending.png)

| case | mass | K, three meshes | cabin K, three meshes |
|---|---|---|---|
| open shell, 0.8 mm steel | 69 kg | 5,086 / 5,190 / 4,481 | 9,237 / 9,509 / 8,527 |
| open shell, CFRP | 42 kg | 3,534 / 3,597 / 3,131 | 6,297 / 6,403 / 5,767 |
| `picogk/` boxes, 0.8 mm steel | 124-135 kg | 18,331 / 20,752 / 18,914 | 36,014 / 35,446 / 32,170 |
| `picogk/` boxes, CFRP | 78-84 kg | 13,425 / 15,021 / 13,822 | 26,482 / 26,725 / 23,505 |

*N/mm. The values move by up to 12% between meshes and not in one
direction: the support strips hold 27, 70 and 107 nodes. The ratios hold.*

**The boxes multiply the bending stiffness by about four:** ×3.6 to ×4.4
in K and ×3.7 to ×4.2 in cabin K, on every mesh. In torsion the same boxes
gain ×5 to ×15 and more as the mesh is refined. The open shell already
carries bending through its sides, roof and floor; it cannot carry torsion
without closed sections.

**Members** (`bending.py --members`, CFRP, 300 and 420 sections, same
leave-one-out as `member_study.py`):

| member | mass | bending: K lost | bending: cabin K lost | torsion: cabin K lost |
|---|---|---|---|---|
| sills | 3.3-3.8 kg | 22-28% | 28-37% | 8-11% |
| door rings | 4.4 kg | 24% | 20-21% | 27-31% |
| windscreen frame | 2.1 kg | 9-11% | 5% | 24-27% |
| quarter-window rings | 1.1 kg | 6% | 3% | 17-20% |
| front arches | 2.4-3.5 kg | 14% | -1 to -0.7% | -2 to 0% |
| rear arches | 1.4-1.6 kg | 4-5% | 1-3% | 5% |
| front lid ring | 1.8-1.9 kg | 2-3% | 0-0.1% | 2% |
| B-ring, engine lid, front rails, rear window, tunnel | 0.9-4.2 kg each | 0-1% | 0-1% | 0-5% |

The five weak members removed together cost 0.4 to 1.5% of K and 0.4 to
1.1% of the cabin K in bending, for 11 to 15 kg. In torsion the same
pruning costs 14 to 16% of the cabin K.

What it says:

- **No new member is needed for bending.** The cabin members are the same,
  with other weights: the sills lead in bending (28-37%), the door rings
  follow. The windscreen frame and the quarter windows, decisive in
  torsion, count for little here.
- **Torsion decides the architecture and the pruning.** The pruning trade
  of [What each member is worth](#what-each-member-is-worth) costs about
  1% in bending, so its price is the torsion one.
- **The sills are where bending and the carbon meet.** Their outer wall is
  part of the "box outer walls" family, the one with the best return in
  [Where the carbon pays](#where-the-carbon-pays).
- **The front arches carry the front supports into the body:** 14% of K,
  nothing for the cabin, as in torsion.

Limits:

- One vertical load at mid-wheelbase, idealised supports. No doors, no
  glass, no suspension, no payload distribution, no strength or buckling
  check.
- The floor and bulkheads count by their faces only, so the floor's and
  the tunnel's bending roles are under-estimated.

## Corrections (2026-10-11)

Three faults in this folder's shell model were found and fixed. All the
values above come from the corrected model. The values published from #139
to #147 (2026-10-08 to 2026-10-10) are superseded.

1. **The bulkheads were missing.** `build_shell.bulkhead()` placed them at
   exactly d = 380 and 1975 mm, a few millimetres from the section whose
   ring they used. They did not weld to the shell, and
   `connectivity("largest")` dropped them. Placed on their section, they
   weld. The open shell goes from 2,261 to 3,209 N·m/deg, and every
   torsion result changes.
2. **Needle walls.** Side walls under 0.5 mm wide, on cut-back edges, made
   the model 1-1.5% too stiff, and they inverted when thickened. They are
   now filtered.
3. **Solver outliers.** CalculiX now and then returns a K too high for the
   same input. Each value is now one two solves agree on.

What changed in the conclusions:

- **The comparison of the two architectures** (#144) claimed the skin boxes
  lead per kilogram "at all three meshes". That came from the tubes being
  tied to the skin at single nodes, which sink as the mesh is refined.
  Tied over a bonded strip, the tube model converges, and the ranking then
  depends on the strip width assumed (see above): it is not established.
- **The member ranking** (#147) holds for the members that carry the cabin.
  The front members no longer count on the cabin measure: their earlier
  weight there came from the missing front bulkhead.

## Reproduce

In the `cadsim` image, with shapely from the print-simulation library folder:

    python3 source/trace_plate_50_05a.py page9-009.png   # only with the local plate
    python3 source/build_shell.py      # derived/monocoque-shell.ply and -structural.npz
    python3 source/torsion.py          # derived/torsion-snapshot.npz
    python3 source/torsion_monocoque.py   # derived/torsion-monocoque.json, after ../picogk/
    python3 source/torsion_rings.py       # derived/torsion-rings.json, from picogk-rings/
    python3 source/torsion_rings.py --bond-sensitivity   # other tube-to-skin bond widths
    python3 source/torsion_shell_tubes.py    # tubes meshed as shells, line bond (12 GB)
    python3 source/member_study.py        # derived/torsion-members.json, two to three hours
    python3 source/member_study.py --pruned   # the weak members removed together
    python3 source/layup_study.py         # derived/torsion-layup.json, about two hours
    python3 source/bending.py             # derived/bending.json, vertical bending
    python3 source/bending.py --members   # leave-one-out in bending, about an hour
    python3 source/bending.py --pruned    # the torsion pruning, in bending
    python3 source/figures.py          # evidence/*.png
    python3 ../fea/hero.py             # the home-page banner

## Limits

- The outline is Porsche's to the plate's drawing accuracy (about ±4 mm on
  the calibration markers); everything between outlines is modelled.
- The plate shows a 964 from model year 1991; the 993 shares the floor and
  the datum points, not the outer panels.
- No thickness, material or layup is proposed here. The shell carries the
  programme's `prohibited_pending_engineering` status: it is a design
  envelope, not a part.
