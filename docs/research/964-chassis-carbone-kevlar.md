# Carbon/Kevlar chassis for the 964: what the computation says about replacing steel

Status: **material study, class `prohibited_pending_engineering`**. No part
geometry and no layup sequence can be released. See `SAFETY.md`: a
self-supporting structure carries occupant restraint, and it is published only
after a formal engineering review.

## Starting point

`SRC-ZESAD-CARBON-MONOCOQUE-964-993` establishes that a replacement carbon
monocoque for the 964 and 993 exists commercially, from EUR 129,990 to 219,990,
in autoclave-cured prepreg. The record publishes **no mass, no torsional
stiffness, no crash test, no homologation, no layup sequence and no core
material**. There is therefore nothing to reproduce or to compare against: the
only thing that can be done here is to ask the question by computation, on the
model we have.

## Method

The test is the existing torsion test of the 964 floor pan (`fea/README.md`):
rear clamped, a 1290 N.m torque at the side rail tips, S3 shells, CalculiX.
**Neither the geometry, nor the loading, nor the boundary conditions change.**
Only the material and the thickness change. The reference is steel at 0.8 mm,
2442 N.m/deg — a value reproduced identically before any modification.

The laminate properties are not asserted, they are **computed** from the
unidirectional ply constants through the lamination invariants
(`fea/laminate.py`). A quasi-isotropic stack has an isotropic membrane stiffness
matrix A, which allows the shell to be kept isotropic in the computation and
reduces the inputs to the ply constants alone. The module checks its own
algebra: the QI stack of an isotropic ply must return that same material.

QI carbon comes out at **E = 52,401 MPa**, the textbook value for a
quasi-isotropic T300/epoxy. The carbon/aramid hybrid is obtained by mixing the
Q matrices in proportion to the plies, which is exact for A.

## Result, at equal torsional stiffness

| material | E (MPa) | G (MPa) | iso-stiffness thickness | plies | computed K | vM p99 | kg/m2 | vs steel |
|---|---|---|---|---|---|---|---|---|
| steel 0.8 mm (reference) | 210,000 | 80,769 | 0.80 mm | — | 2442 | 69.6 | 6.28 | 1.00x |
| QI carbon | 52,401 | 19,992 | 3.23 mm | 16 | 2503 | 17.0 | 5.17 | **0.82x** |
| QI carbon/aramid 50/50 hybrid | 40,669 | 15,447 | 4.18 mm | 20 | 2538 | 13.0 | 6.23 | **0.99x** |
| QI aramid | 28,931 | 10,902 | 5.93 mm | 24 | 2611 | 9.0 | 8.18 | **1.30x** |

Cured ply thickness taken as 0.25 mm, an `ASSUMED` working value; ply count
rounded to the multiple of 4 that a symmetric QI stack requires.

## What to take away

**Kevlar is the wrong material for this function.** At equal torsional
stiffness, a quasi-isotropic aramid laminate is **30 % heavier than steel**.
This is no surprise once the computation is set up: aramid has a mediocre
specific modulus. Its real value is damage tolerance, penetration resistance and
energy-absorption behavior, not stiffness. If it has a place in a chassis, it is
as a local sacrificial skin or an anti-shatter layer, **not in the torsional
load path**.

**The gain from monolithic carbon is modest: 18 %.** That is very far from what
the word "carbon" leads one to expect. The reason is mechanical and already
established by this repository: this box works in **membrane shear**, so the
stiffness follows `G x t` and not `G x t^3`. The criterion that matters is not
the specific modulus `E/rho` but `G/rho`, and the gap there is much smaller than
in bending. The maximum gap between the thickness predicted by this law and the
full computation is 6.9 %, which confirms the scaling law in material as it was
confirmed in thickness.

**A honeycomb core does not recover this result in torsion.** For a closed box,
Bredt's formula gives a stiffness proportional to `G x t`, to the square of the
enclosed area and to the inverse of the perimeter: the shear flow is carried by
the skins, and separating the skins with a core does not increase the available
`G x t` product. A sandwich buys **panel bending** stiffness and **local
buckling** resistance, which are real criteria and sizing elsewhere, but it does
not multiply the torsional stiffness of the box.

**The real lever is not the material, it is the architecture.** The `vM p99`
columns show it: the reference steel tops out at 86 MPa at peak against a yield
strength of at least 200 MPa even for mild steel, and the iso-stiffness
laminates drop to 9-19 MPa. **The floor pan is not sized by torsional stress.**
Its thickness comes from stiffness, stamping, local impact resistance and
corrosion. A material swap at iso-stiffness therefore converts no margin into
mass.

What a ZESAD-type monocoque gains comes from elsewhere: a single closed shell
instead of a spot-welded assembly, a larger enclosed area, the removal of
overlaps and joints, and the freedom to put material where the load path goes
instead of where stamping allows it. **None of this can be demonstrated on a
floor pan alone**: it would take the front bulkhead, the rear bulkhead, the
tunnel, the wheel arches, the B-pillars and the windshield frame, which carry
most of the torsion of a complete body shell and which no source in the dossier
dimensions.

## Architecture versus material: the question is settled

The claim "the lever is architectural" was, in the first version of this
document, an argument. It is now measured. The trick is that it is
**relative**: it therefore requires no published 964 body-shell stiffness, which
is convenient since none exists.

Same torsion test, three increasingly closed architectures, two materials **at
equal mass** — the carbon laminate is set to 3.92 mm so that it weighs exactly
what steel at 0.8 mm weighs. The quantity compared is the specific stiffness
`K/m`.

| architecture | material | area | mass | K (N.m/deg) | K/m |
|---|---|---|---|---|---|
| floor pan alone | steel 0.8 mm | 4.40 m2 | 27.7 kg | 2442 | 88.3 |
| floor pan alone | QI carbon 3.92 mm | 4.40 m2 | 27.7 kg | 3062 | 110.7 |
| + bulkheads | steel 0.8 mm | 5.60 m2 | 35.2 kg | 3147 | 89.4 |
| + bulkheads | QI carbon 3.92 mm | 5.60 m2 | 35.2 kg | 3914 | 111.2 |
| + bulkheads + tunnel | steel 0.8 mm | 6.40 m2 | 40.2 kg | 5371 | 133.6 |
| + bulkheads + tunnel | QI carbon 3.92 mm | 6.40 m2 | 40.2 kg | 6620 | 164.7 |

These masses were corrected on 2026-09-04. A cross member in the model, placed
behind the rear edge of the floor pan by the unanchored datum chain, was
floating there: it counted 1.66 kg without carrying any load, and therefore
understated every specific stiffness. The stiffnesses themselves were correct.
See `twins/964-chassis/fea/README.md`.

The two levers, at equal mass:

| lever | gain in K/m |
|---|---|
| **close the body shell**, at constant steel | **x 1.51** |
| **switch to carbon**, floor pan alone | **x 1.25** |
| both together | x 1.86 |

**Architecture therefore yields about 20 % more than material**, and above all
the two levers **multiply almost exactly**: 1.51 x 1.25 = 1.89 against 1.86
measured. They are separable, which means that neither substitutes for the
other. Choosing carbon does not exempt you from closing the body shell, and
closing the body shell does not make carbon useless.

The detail is instructive: most of the architectural gain comes not from the
bulkheads but from the **center tunnel**, which on its own takes the stiffness
from 3147 to 5371 N.m/deg, i.e. +71 %. A longitudinal beam closed over the full
length is worth more than two bulkheads at the ends.

**Correction of 2026-09-25: this scan cannot conclude that there is no
tunnel.** The earlier `source/tunnel_probe.py` measured the median relief of
surfaces visible from below, then wrongly inferred the absence of a
longitudinal shaft. A fairing or a lower skin can hide the driveline; the scan's
symmetry residual is not an instrument uncertainty. The corrected script keeps
the missing stations and is now limited to a diagnostic of coverage and of
visible relief.

Porsche describes a transaxle shaft running forward on the 964 Carrera 4 and the
change of system on the 993 Carrera 4; the removal of the tube is placed at the
996 generation. See
[the German manufacturer source](https://newsroom.porsche.com/de/historie/porsche-allradantrieb-meilensteine-lohner-porsche-cisitalia-rennwagen-carrera-4-visco-kupplung-porsche-traction-management-ptm-911-turbo-15045.html),
recorded as `SRC-PORSCHE-964-993-ALL-WHEEL-DRIVE-HISTORY`.

The FEA "tunnel" case remains a **hypothetical section**: neither a
reconstruction of an original tunnel nor proof of its absence. The +71 % gain
applies to that model only. Integrating it still requires the real volumes of
the shift linkage, the C4 tube and shaft, the anchorages, the travel envelopes
and the service access; none of these dimensions can be deduced from a flat
underside. The architectural reading stands: **a closed longitudinal beam
yields more than switching to carbon**, +71 % against +25 %, in this model.

Two consistency checks between the two studies. At equal mass, carbon gives
x 1.25; at equal stiffness, it gave 0.82x the mass, i.e. 1/0.82 = 1.22. The two
readings agree. And the "floor pan alone, steel" case returns 2442 N.m/deg, the
original value: the rewrite of the geometry script is faithful.

**Major caveat.** The bulkheads, their 500 mm height and the 180 x 120 mm tunnel
section are `ASSUMED`: none is published. The absolute values in the table are
therefore not 964 stiffnesses. **Only the ratios count**, and they are what
answers the question asked.

The roof, the B-pillars, the wheel arches and the windshield frame were also
missing from this study. They have since been added to the model, and the result
reinforces this page's conclusion rather than qualifying it: from the bare floor
pan to a closed cell, stiffness is multiplied by 3.7, and what carries this gain
is not the amount of material added but the closing of the rings. The
windshield frame, 1.1 kg, yields two orders of magnitude more per kilogram than
the roof, 10.5 kg. See `twins/964-chassis/fea/README.md`.

## Correction of 2026-09-04: the criterion for the floor pan is not `G/rho`

This page concludes several times that "this box works in membrane shear, so the
criterion is `G/rho` and not `E/rho`". **This mechanical reading is wrong and it
is corrected here.**

It rested on two observations, neither of which demonstrates it: stiffness
follows thickness linearly, which rules out plate bending but not the bending of
a thin-walled beam; and the iso-stiffness prediction lands within 6.9 %, but all
the materials compared are isotropic, where `G` is proportional to `E`, so this
check cannot distinguish one from the other.

By varying `E` and `G` separately (`fea/dominance_study.py`), one measures that
doubling `E` yields **+93.8 %** on the floor pan alone while doubling `G` yields
only **+2.1 %**: this particular architecture works in **bending**. Shear only
becomes dominant once the rings are closed, where the full cell gives +37.7 %
and +56.9 %.

**What remains valid in this page:** all the numbers. They concern isotropic
materials, computed at iso-stiffness by a full computation, and the underlying
mechanism does not change their value. The ranking of carbon ahead of aramid is
unchanged, carbon dominating on both criteria.

**What falls:** the `G/rho` justification, and with it the idea that a
shear-oriented layup would be the right default setting. The full laminate
computation, now possible, shows that the ranking of stacks **reverses with the
architecture**. See `docs/MONOCOQUE_964_993_ARCHITECTURE.md`.

## What this study is not

- **These are not 964 body-shell stiffnesses.** The model is a floor pan, two
  side rails and two cross members. 2442 N.m/deg is not a vehicle value and has
  never been compared with a factory value: none is published.
- **Only stiffness is addressed.** Nothing here says anything about laminate
  strength, delamination, bonded joints — which are the real weak point of a
  composite monocoque —, buckling, crash behavior, fire behavior, fatigue or
  aging. A composite failure criterion is not a von Mises stress.
- **The ply constants are textbook-class, evidence level D.** They are certified
  by no supplier. A real fiber volume fraction, a porosity rate and a cure cycle
  would shift them.
- **The geometry remains unanchored.** The longitudinal anchoring of the 964
  twin's datum network is not resolved, and the side rail and cross member
  sections are `ASSUMED`. No composite part can come out of it.
- **No physical check.** In line with the repository charter, nothing was
  weighed or measured on a vehicle.

## Next useful data point

Unchanged, and it is the same lock as for the rest of the twin: **locating a
single published datum point** to better than its tolerance would anchor the
longitudinal chain. Without that, the material study above remains what it is —
a correct comparison on an approximate geometry.

For the composite axis specifically, the missing data point is a **torsional
stiffness of a complete 964 body shell**, measured or published. It would
finally give a denominator: without it, we can compare materials with each
other, but not say what a monocoque would bring to the car.

## Reproduce

    source twins/964-chassis/source/env.sh
    cd twins/964-chassis/fea
    pycad laminate.py                          # QI properties and self-check
    pycad build_shell.py 0.8 1.0
    pycad composite_study.py                   # iso-stiffness table above
    pycad architecture_study.py                # architecture / material ablation
