# 964/993 carbon monocoque programme — definition

Status: **programme definition**. This document contains no geometry and
authorizes none. It states what has to be established, in what order, and what
is blocking today.

Target: a replacement carbon monocoque for 964 and 993 restomods, an
alternative to the `SRC-ZESAD-CARBON-MONOCOQUE-964-993` offering, industrialized
in China.

This target **contradicts the written scope** of `ROADMAP.md`, which classifies
replacing the unibody structure as "initially out of scope". Scope is a
decision of the project owner, not a technical conclusion; it must be changed
explicitly if this programme is adopted, not bypassed silently. The gates in
`SAFETY.md` and `QUALITY_GATES.md`, on the other hand, are not scope choices:
see the "Safety gates" section.

## 1. The axis of differentiation is documentary, not material

The ZESAD record advertises an autoclave-cured prepreg carbon monocoque, in two
configurations, from 129,990 to 219,990 EUR. It **publishes no mass, no
torsional stiffness, no crash test, no homologation, no engineering partner, no
layup sequence and no core material**. Neither does the company's website.

That is the exploitable weakness, and it is structural: for a part that carries
occupant restraint, the absence of published data **is** the product's defect.
A competitor that publishes mass, measured stiffness, protocol, tests and
homologation route differentiates itself on the one axis where the incumbent
offering is bare, and does so without having to be cheaper.

This repository is already equipped for exactly that: sourced records, evidence
levels, quality gates, a documented refusal to claim beyond the evidence. **The
repository's method is the product.** That is a real advantage and it is not
copied quickly.

Design consequence: everything that follows is organized to produce publishable
evidence, not just a part.

## 2. What the repository has already established that bears on the product

Three established results (see `twins/964-chassis/fea/README.md`) drive the
architecture. They are **relative**, and therefore valid despite `ASSUMED`
sections.

**Carbon is the weak lever.** At equal mass, switching to quasi-isotropic carbon
is worth x 1.25 in specific stiffness. Closing the box section is worth x 1.51.
The two multiply. A monocoque does not win because it is carbon: it wins because
it gets the closures **by construction**, in one piece, without the assembly
compromises of a welded sheet-steel body shell.

**Ring closure dominates everything.** From the bare floor pan to a closed cell,
K x 3.7. The ranking does not follow mass: the windshield frame, 1.1 kg,
returns 172 to 191 times more per kilogram than the roof, 10.5 kg. The
B-pillars and sills, added alone with nothing to close the front, return zero
for 7.5 kg. Verified at three mesh densities.

**Product corollary, and a reading of the competing offering.** ZESAD sells a
"monocoque with steel windshield frame" configuration. Our own calculation says
the windshield frame is the most cost-effective element of the whole body
shell. Putting steel precisely there is therefore defensible, and probably not
an aesthetic compromise: it is the most loaded ring, the one where a laminated
composite handles concentrated loads and glass bonding least well.
**Hypothesis, to be verified** — the record does not say why this option
exists.

**The material criterion is `G/rho`, not `E/rho`.** The box section works in
membrane shear. A sandwich core changes nothing there where the skin works in
in-plane shear. This drives the layup: it needs +/-45 degree plies oriented
along the shear paths, not a uniform quasi-isotropic layup chosen for
convenience.

## 3. The lock that drives the programme: the reference frame

**No monocoque geometry can be designed today.** Not on safety principle, but
because it is metrologically impossible.

A monocoque replaces the body shell. It must therefore carry, in a single
reference frame and to better than its tolerance, at minimum:

| interface | required tolerance | state in the repository |
|---|---|---|
| front subframe and suspension points | ~ +/- 1 mm | P3 and P5 placed from published dimensions, +/- 1.9 mm (95 %) |
| rear trailing-arm mounts | ~ +/- 1 mm | P13, P14 scaled off plate 50-05a, +/- 8.6 mm |
| engine and gearbox mounts | ~ +/- 1 mm | P12, P21 from published diagonals (+/- 9 mm); P15 scaled, +/- 8.6 mm |
| seat belt and seat anchorages | regulatory | not established |
| hinges, strikers, windshield aperture | ~ +/- 1 mm | not established |

**Update 2026-10-08: the front and centre of the chain are closed.** Plate
50-05a of volume V dimensions P1, P3 and P5 from a 0 line through the front
strut mounts, and plate 50-02 draws dimension P as longitudinal. Two
independent published paths then place P17 within 1.9 mm of each other, and
the network P20, P3, P5, P17, P18, P19 is fixed to +/- 2 to 4 mm without any
third-party data. Tied to the scan it lands on identified features (P5 bosses
within 2 mm laterally). See "The longitudinal chain, closed from plate
50-05a" and "The rear of the chain" in `twins/964-chassis/README.md`.

**Same day, the rear.** Diagonals O and N, read unbracketed, place P12 and
P21; plates 50-05a and 50-02 agree with that P12 within 3 to 6 mm, and the
scan's engine-mount cradle with P21 within 7 mm. The rear mounts P13, P14 and
P15 are scaled off plate 50-05a (+/- 8.6 mm). The governing span P5 to P12 is
1535.6 mm, both ends published. Every interface of the contract now has a
position; what is missing is tolerance, not existence: +/- 7 to 9 mm where
a tool needs +/- 1 mm.

Before that update, `twins/964-chassis/README.md` established that **the
longitudinal registration of the datum network was not resolved**: P21 landed
at X = -3112 mm inside the rear bumper, and the search for point 17 on the
scan was a solid negative result.

**This lock used to be a documentation task. It becomes the product's critical
path.** As long as it holds, there is no monocoque: there is an object that
looks like a body shell and does not bolt up.

It is not opened by calculation. It is opened by data, and the leads are
already sorted in `docs/research/964-combler-le-gap-de-donnees.md`: a jig bench
survey (Autorobot, Car-O-Data, Celette), the Rennlist 993 point table, a scan
of a production body. **The jig bench survey goes from "desirable" to
"blocking".** It is the first budget to commit.

## 4. The missing denominator is measured, no longer searched for

Lock B — no published 964 torsional stiffness — was treated as a
literature-search problem. Two campaigns, one of them in German, produced
nothing citable.

**It is a measurement problem, not a bibliography problem.** A body-in-white
torsion test is a workshop test: clamping on the rear suspension points, torque
applied at the front strut towers, rotation measured with dial gauges at
several stations. It needs neither a laboratory nor a homologation budget.

Measuring a donor 964 body shell in torsion delivers at once:

- the denominator nobody publishes, ZESAD included;
- validation of the shell model, whose absolute values are all currently
  invalidated by `ASSUMED` sections and non-convergence of the mesh;
- the commercial argument: "x times the original body shell, protocol
  published".

**It is the most cost-effective recommendation in this document.** It is under
our control, depends on no third party, and turns all the existing FEA work
from qualitative into quantitative.

## 5. Target specification — to be filled, method fixed

No value is entered here until section 4 is done. Entering a number now would
be exactly what this repository refuses to do.

| requirement | unit | method of establishment |
|---|---|---|
| bare body-shell torsional stiffness | N.m/deg | multiple of the measured 964; to be set after the test |
| bare body-shell mass | kg | weighing; compare with the measured 964, not with a forum value |
| torsional natural frequency | Hz | modal test, follows from K and inertia |
| interface positions | mm | registered datum network, tolerance +/- 1 mm |
| seat belt anchorages | — | regulatory requirement of the target market |
| crashworthiness | — | see section 7 |
| manufacturing tolerance | mm | capability of the chosen process |

Rule: **every published line carries its protocol and its uncertainty**, or is
not published. That is the product.

## 6. Manufacturing in China — capacity is not the constraint

**Things must be said the right way round: on manufacturing, China does not
merely match ZESAD, it surpasses it.** ZESAD is a German workshop founded in
2013, a developer of competition parts. The aerospace-grade Chinese composites
industry — autoclave infrastructure built around the domestic civil aircraft
programmes, the world's largest carbon fiber capacity — works at a higher
level, on larger parts and under more demanding quality systems.

The question is therefore not "will we manage to do as well". It is "will we
manage to **choose** the right shop", which is a different and easier problem.

**Correction of an analysis error.** A previous version of this document ruled
out the autoclave on the grounds that amortizing it would be brutal at low
volume. That is wrong as soon as the work is **subcontracted**: autoclave time
is rented from someone who already owns one; the vessel is not amortized by us.
ZESAD's exact route — autoclave-cured prepreg — is therefore fully accessible,
and it is in China that it is most accessible. Tooling cost remains, and it is
real, but it bears no comparison with European tooling.

| route | fiber volume fraction | tooling | remark |
|---|---|---|---|
| autoclave prepreg | highest, most consistent | expensive | ZESAD route, accessible through subcontracting; **the reference to aim for** |
| out-of-autoclave (OOA) prepreg, oven | close to autoclave | medium | credible alternative if the autoclave brings nothing measurable |
| vacuum infusion (VARTM) | lower, more scattered | cheapest | to be adopted only if the scatter is proven under control |
| RTM / C-RTM | high, very consistent | very expensive, press | only if volume rises |

The choice is decided on the **measured scatter** of fiber volume fraction and
coupon properties, not on a preference or on the listed price.

**The real trap in Chinese sourcing is not capacity, it is sorting.** The
Chinese automotive carbon industry is huge but overwhelmingly **cosmetic**:
panels, aero, trim, often wet layup, optimized for the look of the twill weave
and not for a structural property. A safety part is not ordered from that pool.
The relevant shops are the aerospace- or motorsport-grade ones, which exist and
are numerous, but which are a distinct population. Confusing the two is the only
real risk in this part of the programme, and it is handled by the requirements
below.

**Fiber.** China produces its own T700/T800-class fiber — candidates to be
verified: Weihai Guangwei, Zhongfu Shenying, Hengshen, Jilin. That is a real
advantage and not only a cost one: high-modulus, high-strength fiber falls
under dual-use export-control regimes, and a domestic supply chain avoids those
import frictions. **To be verified with the datasheet in hand**: advertised
T700/T800 equivalences require coupon qualification, not a catalogue reading.

**What to require from a subcontractor, and what sorts them quickly:**

- quality system: AS9100 is more meaningful than IATF 16949 for structural
  composites; having neither is not disqualifying but requires a control plan
  written by us;
- prepreg batch traceability, with a log of out-of-freezer life;
- cure-cycle recording for each part, with thermocouples in the tool;
- **witness coupons cured with every part**, and mechanical tests on them:
  without that there is no evidence that the delivered part is worth the
  calculated part;
- non-destructive testing: through-transmission or phased-array ultrasound on
  the critical zones, with a written acceptance criterion;
- ownership of the tooling and of the ply book contractually ours.

**The main risk is neither price nor capacity, it is scatter.** A monocoque
whose stiffness varies by 20 % from one unit to the next is not a publishable
product under the method adopted in section 1. The coupon plan is therefore a
design requirement, not a quality clause.

**And what cannot be subcontracted, anywhere.** An excellent shop manufactures
what it is given: it provides neither design authority, nor layup, nor
validation, nor the homologation dossier. That is precisely what ZESAD does not
publish, so precisely where the difference is made. If manufacturing is not the
constraint — and it is not — then **all of the value and all of the risk are
concentrated in sections 3, 4 and 7 of this document**.

## 7. Vehicle identity and homologation

This is the real commercial constraint, and it takes precedence over the
technical side.

The body shell carries the chassis number. Replacing the unibody structure
raises, depending on the market, the question of whether the vehicle remains
the same vehicle or becomes a new one — with, in the second case, a type
approval dossier out of all proportion to a restomod.

This document does not settle that question: it is legal, it depends on the
country of registration, and it must be investigated market by market
**before** any tooling commitment. A hypothesis to be verified: the ZESAD
configuration "with steel windshield frame" could serve to retain an original
element carrying the identity, as much as to meet the structural need
identified in section 2.

**Sequencing point:** the homologation study is cheap and can kill the
programme. It therefore comes before detailed design, not after.

## 8. Safety gates — what stays closed

`SAFETY.md` presumes occupant restraint, suspension, jacking points and primary
fasteners to be critical. A monocoque carries all of them. It is therefore
`prohibited_pending_engineering`: **never published as a released part** in its
current state.

This class prohibits neither studying, nor calculating, nor specifying, nor
measuring. It prohibits **releasing geometry** without a formal engineering
review and an approved validation plan. Nothing in this programme asks to lift
that gate, and sections 3 to 6 are precisely the work that will one day allow
it to be examined seriously.

One non-negotiable point, and it is not a question of scope: the
crashworthiness of a composite structure **cannot be calculated credibly
without physical tests**. A composite failure criterion is not a von Mises
stress; failure happens by delamination, debonding and local buckling,
mechanisms the current shell model does not represent at all. No safety claim
will come out of this repository without tests.

## 9. Phases and exit criteria

| phase | content | exit criterion | dependency |
|---|---|---|---|
| M0 | identity and homologation study, market by market | route identified or programme stopped | lawyer |
| M1 | registration of the datum network: closed from plates 50-02/03/05a (2026-10-08), +/- 2 to 9 mm | 964 at `F2_interface`, interfaces at +/- 1 mm | +/- 1 mm needs a jig-bench table or published rear dimensions |
| M2 | torsion test on a donor 964 body shell | denominator measured, protocol published | donor body shell |
| M3 | recalibration of the shell model against M2 | model/measurement gap known and documented | M1, M2 |
| M4 | target specification filled | section 5 table complete | M2, M3 |
| M5 | architecture concept and layup | rings closed, shear paths defined | M4 |
| M6 | process and subcontractor qualification | coupon plan validated, scatter measured | M5 |
| M7 | engineering review and physical test plan | review signed in the sense of `SAFETY.md` | M6 |

M0, M1 and M2 run in parallel and are the only ones to commit now. **M1 and M2
are the two that drive everything else**, and M2 is the only one entirely under
our control.

## 10. What this document is not

- It is not a design. No dimension, no layup, no geometry.
- It is not an authorization. The `prohibited_pending_engineering` class is
  unchanged.
- It is not a market study, nor a business plan, nor an evaluation of the ZESAD
  product, of which nothing structural is published and therefore nothing can
  be checked against.
- The fiber producers named are candidates to be verified, not qualified
  suppliers. None has been contacted.
- The scope of `ROADMAP.md` is not changed by this document.
