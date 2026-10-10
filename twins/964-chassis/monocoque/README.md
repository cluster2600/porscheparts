# 964 monocoque shell, from plate 50-05a

A 911-shaped body shell for the
[carbon monocoque programme](../../../docs/MONOCOQUE_964_993_PROGRAMME.md).
Until now the programme's only whole-body model was the box cell of
[`../fea/`](../fea/): good at relative questions, nothing like a 911. This
shell takes its outline from Porsche's own drawing.

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
  stiffness, tied to the skin along its tangent line;
- **all members and paths** come from the study's own parameters and
  `prepare.py`.

Checked on a cantilever plate with a tube, the method is 12% stiffer than
composite beam theory.

| CFRP layup | mass | K, 210 / 300 / 420 sections | K per kg, 210 / 300 / 420 |
|---|---|---|---|
| open shell | 43 kg | 5,681 / 3,624 / 2,418 | 134 / 85 / 57 |
| `picogk-rings/` without its tubes | 58 kg | 7,137 / 5,038 / 4,600 | 124 / 87 / 80 |
| **`picogk-rings/`, tubes** | 73 kg | **32,586 / 27,705 / 23,665** | **449 / 382 / 326** |
| **`picogk/`, skin boxes** | 84 kg | **30,786 / 34,834 / 35,462** | **365 / 413 / 420** |

![Two architectures in torsion](evidence/torsion-architectures.png)

What holds, and what does not:

- **The ranking depends on the mesh.** Per kilogram, the skin boxes lead on
  the two finer meshes (×1.08, then ×1.29). The tubes lead on the coarsest
  (×1.23). The tube model loses 15% at each refinement and is far from
  converged, while the boxes are stable. The trend favours the boxes: a box
  that uses the skin as one wall encloses more area than a tube bonded
  along a line. But it is a trend, not an established result.
- **The tubes do work.** They multiply the model without them by 4.6 to
  5.5, for 15 kg.

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
  lead per kilogram "at all three meshes". With the bulkheads, the tubes
  lead on the coarsest mesh. The advantage of the boxes holds only on the
  finer meshes and is not established.
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
    python3 source/member_study.py        # derived/torsion-members.json, two to three hours
    python3 source/member_study.py --pruned   # the weak members removed together
    python3 source/layup_study.py         # derived/torsion-layup.json, about two hours
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
