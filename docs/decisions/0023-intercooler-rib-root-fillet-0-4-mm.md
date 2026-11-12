# ADR 0023 — 750 hp intercooler coupon: 0.4 mm rib-root fillet as a design assumption

## Status

**Proposed** on 2026-11-12 for
[issue #467](https://github.com/cluster2600/porscheparts/issues/467). It
becomes accepted when the owner records acceptance on that issue. Until then
the coupon keeps both assumed radii and nothing below is in force.

## Context

The four-rib hot passage of the
[pressure coupon](../../twins/993-intercooler/750-hp/pressure-coupon/README.md)
has sharp rib roots whose stress does not converge. Two assumed root fillets,
0.2 mm and 0.4 mm, were studied in plane strain, in a hydraulic proxy, in an
exploratory channel CFD and in the PicoGK geometry. Issue #467 asks for a
choice between them "only against a sourced process capability and
predeclared mechanical criterion", before any 3D study.

Three things were done in this order, each in its own commit:

1. The [criterion](../../twins/993-intercooler/750-hp/pressure-coupon/fillet-radius/criterion.json)
   was written and committed before any source was searched. It says what was
   already known at that point (the retained stresses and hydraulic changes,
   and three catalogue process figures), so it is fixed in advance without
   being blind.
2. Eleven source records were added and the
   [process figures](../../twins/993-intercooler/750-hp/pressure-coupon/fillet-radius/process-capability.json)
   tied to them.
3. The criterion was applied by a
   [script](../../twins/993-intercooler/750-hp/pressure-coupon/source/fillet_radius_choice.py)
   that runs no solver. Its
   [report](../../twins/993-intercooler/750-hp/pressure-coupon/derived/fillet-radius-choice/fillet-radius-choice.json)
   is the basis of this record.

### What the sources state

| Quantity | Reference route (EOS M 290, AlSi10Mg, 30 µm) | Other machines or routes (indicative) |
|---|---|---|
| Layer thickness | 0.03 mm | 0.04 to 0.09 mm |
| Powder upper size | sieve 0.09 mm; stated range 25 to 70 µm | d90 0.062 and 0.073 mm; range to 0.063 mm |
| As-built Rz | not published | mean 0.064, maximum 0.120 mm at 30 µm layers; 0.07 to 0.17 mm at 50 µm; 0.03 to 0.04 mm on one service sheet |
| Dimensional accuracy | not published | ±0.1 mm and ±0.2 mm on two service sheets; a 0.05 mm beam-offset correction between two machines |
| Minimum wall | 0.4 mm | 0.3 to 1 mm |
| Minimum detail | not published | 0.4 mm and 0.5 mm |
| Minimum internal radius | not published | none found |
| Measured as-built concave radius | none found | none found |

**No source states the smallest internal fillet radius that LPBF holds in
AlSi10Mg, and none reports a measured as-built concave radius.** ISO/ASTM
52911-1:2019 is the current design standard for metal powder bed fusion; it is
cited by designation and was not read, so whether it gives such a figure is
not known here. The sources therefore do not settle whether 0.2 mm can be
held. They do not settle it for 0.4 mm either.

One design guide gives a rule of thumb of a quarter of the wall thickness,
which is 0.2 mm for the 0.8 mm rib. That is a proportion for stress, not
evidence that a machine holds the radius. One service guideline advises
rounding edges by at least 3 mm against build stresses; that exceeds the
1.5 mm half-height of the passage and is not a resolution limit.

### What the criterion gives

The fillet replaces a sharp corner by an arc that departs from it by at most
(√2 − 1) r: **0.083 mm at 0.2 mm and 0.166 mm at 0.4 mm**. The criterion asks
that this form stand above each sourced surface-noise scale of the route.

| Test | 0.2 mm | 0.4 mm |
|---|---|---|
| M1: converged root peak below the assumed 40 MPa screen | pass, 12.8 MPa | pass, 9.6 MPa |
| H1: hydraulic proxy penalty at most 5 % | pass, +0.33 % | pass, +1.47 % |
| M2: peak if the radius falls short by the route's accuracy | not evaluable | not evaluable |
| P1: no stated minimum radius or detail above the radius | not evaluable | not evaluable |
| P2: form above layer thickness, powder size and Rz | **fail**: 0.083 mm against the 0.09 mm sieve | pass on the two sourced scales |
| P3: a measured as-built concave radius exists | not met | not met |
| Class | not distinguishable | unsettled |

The peaks are upper bounds of the retained plane-strain values under the
assumed 0.375 MPa. M2 and P1 cannot be evaluated because the reference route
publishes neither an accuracy nor a minimum detail.

## Decision

1. **The next geometry of the coupon carries a 0.4 mm rib-root fillet**
   (rule R3 of the criterion).
2. **It is a design assumption for the 3D study only** (rule R5). No machine
   has been shown to hold it. Its class is "unsettled", not "sourced".
3. **0.2 mm is set aside** (rule R6). It returns after an admitted contributed
   measurement of its as-built root, not before.
4. The 3D study follows the
   [predeclared plan](../../twins/993-intercooler/750-hp/pressure-coupon/fillet-radius/3d-study-plan.json).
   The plan is not executed and several of its inputs are null.

In one sentence: 0.4 mm now, as an assumption; 0.2 mm only after a printed
and sectioned coupon has been measured.

### Why 0.4 mm

- Its form of 0.166 mm is 1.8 times the sieve cut and 5.5 layers; the form of
  0.2 mm is below the sieve cut.
- Its converged root peak is 27 % lower (9.31 against 12.81 MPa on the nodal
  extrapolations), a difference the retained mesh study resolves. The 1.1 point difference in hydraulic penalty lies inside the mesh
  spread of the retained channel CFD.
- If the as-built radius came out 0.1 mm short, an asymptotic scaling checked
  on the two retained radii puts the 0.4 mm peak near 11 MPa and the 0.2 mm
  peak near 18 MPa. With a 0.2 mm shortfall the 0.2 mm root would be sharp,
  and a sharp root has no finite stress to quote. These figures are indicative
  extrapolations, not results.

### How narrow the margin is

The owner should know that 0.2 mm fails by 8 %, on one reading of one scale.
The criterion defines the powder scale as "D90 or the sieve cut" and does not
say which governs when both are sourced. EOS publishes both a 0.09 mm sieve
and a 25 to 70 µm range. The evaluation took the larger, because the scale is
defined as the upper size, and did not amend the criterion afterwards.

Counting only 0.07 mm, 0.2 mm would be "unsettled" like 0.4 mm. The proposed
radius would still be 0.4 mm, by the tie rule R4. The only change would be
that 0.2 mm stays in the 3D study as a second arm. The owner may choose that
reading; it should then be recorded as a deviation from the criterion as
applied.

Against the indicative figures the picture is the same: the 0.2 mm form is
below the 95 % maximum Rz of two 30 µm parameter sets on another make
(0.120 and 0.129 mm) and above their means; the 0.4 mm form is above every
figure found except the upper end of one 50 µm range (0.17 mm).

## What would overturn it

- An admitted measurement that changes the class of either radius, in
  particular 0.4 mm roots that come out much smaller than designed, or with
  dross or lack of fusion at the root.
- A mesh-converged 3D result in which the 0.4 mm arm fails the mechanical
  rules of the plan.
- A resolved conjugate result in which 0.4 mm costs more than 5 % of heat duty
  or of hot-side pressure loss against the sharp passage.
- A stated minimum radius or detail above 0.4 mm for the machine finally
  selected. Two indicative sources already put the smallest reproduced detail
  at 0.5 mm. A larger radius has no retained result and would need its own
  convergence study first.

## What this decision does not claim

- **No pressure strength.** The 0.375 MPa pressure, the 50 GPa hot modulus and
  the 40 MPa screen are assumptions of the coupon study. No hot allowable for
  LPBF AlSi10Mg is sourced. Fatigue, thermal stress, the 3D ends and the
  as-built surface notches at the root are not covered.
- **No print authorisation and no pressure-test authorisation.**
- **No LPBF qualification.** No machine is selected, no build orientation is
  chosen, and depowdering and sealing are open gates.
- **Not an optimum.** Only 0.2 mm and 0.4 mm were compared.
- Nothing about the gyroid core or its headers.

## Consequences

- The pressure-coupon README, the intercooler README and the twins index say
  that a radius is proposed and that the 3D study is planned, not run.
- Issue #467 stays open: its second half, the 3D mechanical and conjugate
  comparison, has not started and is blocked by null inputs (closure, fitting,
  fixture, fitting loads, per-passage flows).
- **Contributor request** (decision
  [0019](0019-accept-contributed-measurements.md)): the plan lists one
  measurement that an outside contributor with access to an LPBF AlSi10Mg
  build could send in: the as-built root radius of a short four-rib section
  designed sharp, at 0.2 mm and at 0.4 mm, through the capture protocol. The
  project prints and measures nothing, and nobody is paid or commissioned.
