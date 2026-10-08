# 964/993 monocoque — architecture concept and layup strategy

Status: **concept**. No geometry, no part dimension, no executable layup.
`prohibited_pending_engineering` class unchanged.

This document contains the design work that **depends on no unknown in the
datum network** — topology, load paths, ply orientation — and which could
therefore be done before the jig bench survey. The interfaces, for their part,
are declared as parameters in `twins/964-chassis/source/monocoque_interface.py`.

## 1. What the monocoque must do, according to our own measurements

`twins/964-chassis/fea/README.md` establishes three things that drive the form.

**Stiffness follows thickness linearly, not its cube** (1.251 for 1.250).
That rules out plate bending, but NOT thin-walled beam bending: see section
3bis, where the measurement shows that the floor pan alone works in bending and
not in shear, contrary to what the dossier claimed.

**What pays is closing the rings, not the material.** From the bare floor pan to
the closed cell, K x 3.7. But the windshield frame, 1.1 kg, returns 172 to 191
times more per kilogram than the roof, 10.5 kg; and the B-pillars added alone,
with nothing to close the front, return zero for 7.5 kg.

**Carbon is the weak lever.** x 1.25 at equal mass, against x 1.51 for closing
the box section.

Design conclusion: **a monocoque is not a carbon body shell, it is a body shell
whose rings are closed by construction.** The material comes after. That is
also what makes the concept defensible against ZESAD without access to their
product: the argument is structural, not commercial.

## 2. The rings, in order of return

The architecture is defined as a set of closed rings connected by longitudinal
beams. Order established by `ring_study.py` and `body_study.py`:

| ring / element | function | measured return |
|---|---|---|
| windshield frame | closes the cell at the top front | **the highest in the whole model** |
| center tunnel or equivalent longitudinal beam | connects the two end rings | +71 % on its own |
| wheel arches | extend the side rail upward at the ends | high |
| front bulkhead and rear bulkhead | close the box section at the ends | medium |
| B-pillars and sills | only worth anything if a ring closes | zero in isolation |
| roof | fills a surface already carried | near zero |

Two consequences that run against the "monocoque = shell" intuition:

- **the roof is not a structural part** at this load level. It can be thin,
  removable, or glazed, without notable loss of torsional stiffness. That is a
  design freedom, and it is free;
- **the B-pillars are not sized in isolation.** They only serve as the upright
  of a closed ring. A massive B-pillar without a windshield frame is dead mass,
  measured as such.

**Caveat.** The model that produces this ranking has no bonded glazing, no
doors, and no panel openings. All three absences flatter the closed ring. The
ranking is robust — verified at three mesh densities — but the ratios are less
so than the order.

## 3. The layup: result corrected after verification

**A first version of this section announced a x 1.75 gain for a +/-45 layup.
That number is wrong and it is withdrawn.** It held as an analytical prediction
— a +/-45 stack does give 1.75 times the shear modulus of a quasi-isotropic one
— but the assumption that carried it to the body shell, "this structure works
in shear", turned out to be false. See section 3bis.

Finite element calculation is now possible: `run_fea_laminate.py` solves a real
multilayer laminate (`*SHELL SECTION, COMPOSITE`, one `*ORIENTATION` per ply and
per panel family). The chain is validated on an analytical case — uniaxial
tension on a UD ply, `verify_laminate_shear.py` and the uniaxial check — which
gives back E1 at 0 degrees, E2 at 90 and the off-axis value at 45, to within
3 %.

Same mass, eight 0.4 mm plies, same boundary conditions:

| stack | floor pan alone (open) | closed cell |
|---|---|---|
| quasi-isotropic | 1586 | 6311 |
| **+/-45** | 696 (**0.44x**) | **6849 (1.09x)** |
| 0/90 | 1910 (1.20x) | 4043 (0.64x) |

**The ranking reverses between the open architecture and the closed
architecture.** On the floor pan alone, +/-45 loses more than half the
stiffness. On the closed cell it gains, but by 9 % — not by 75 %.

What this means for the layup:

- **there is no universally good stack** for this body shell. A ply is only good
  relative to the load path of the panel that carries it;
- **+/-45 dominant only in panels genuinely in shear** — side-rail webs of a
  closed section, bulkhead webs — and only once the rings are closed;
- **0/90 where the load is axial**: side-rail flanges, edges, bending paths,
  surroundings of hard points;
- **quasi-isotropic remains a reasonable default compromise**, which is a result
  in itself: it is not the bad setting this section used to claim.

Zoned layup remains the real process lever, but its gain is counted in tens of
percent, not in factors, and it requires knowing the load path panel by panel —
which the current model does not resolve.

## 3bis. This body shell does not work in shear, except once closed

The dossier claimed "box section in membrane shear, the criterion is `G/rho`
and not `E/rho`". That claim rested on two observations, neither of which
demonstrates it:

- stiffness follows thickness linearly and not its cube. That rules out
  **plate** bending, but not bending of a **thin-walled beam**, whose second
  moment of area also varies linearly with thickness;
- the iso-stiffness prediction when changing material landed at 6.9 %. But all
  the materials compared were isotropic, hence `G` proportional to `E`: that
  check cannot, by construction, distinguish one from the other.

`dominance_study.py` settles it by varying `E` and `G` **separately**, with a
fictitious orthotropic material in which the two are decoupled:

| architecture | double E | double G | mechanism |
|---|---|---|---|
| floor pan, side rails, crossmembers | **+93.8 %** | +2.1 % | bending, near pure |
| closed cell | +37.7 % | **+56.9 %** | shear dominant, but mixed |

**The floor pan alone does not work in shear at all.** In torsion, its two side
rails bend in opposite directions: they are two cantilevers, and the criterion
there is `E`. Shear only appears once the rings are closed, and it never becomes
exclusive.

It is the same discovery as ring closure, seen from the other end: **closing a
ring does not just add stiffness, it changes the mechanism that carries it.**
And that explains exactly the reversal in the layup table above.

Consequence for the material conclusions: for the floor pan alone, the
criterion is `E/rho`, not `G/rho`. The carbon > aramid ranking is not affected,
since carbon dominates on both criteria.

## 4. The question of the steel windshield frame

ZESAD sells a "monocoque with steel windshield frame" configuration. Our own
ranking puts the windshield frame first in return. Three possible readings, not
mutually exclusive, none confirmed:

1. **structural**: it is the most loaded ring, and a laminate handles
   concentrated loads and glass bonding poorly there;
2. **process**: the aperture requires a shape accuracy that large-format
   composite holds with difficulty without re-machining;
3. **vehicle identity**: retaining an original element can serve the
   homologation route, see `MONOCOQUE_964_993_PROGRAMME.md` section 7.

This question must be settled early: it changes the nature of the product, its
tooling and probably its regulatory dossier. It is settled by reading 3 first,
which is legal and cheap.

## 5. What remains undetermined, and what unblocks it

| undetermined | unblocked by |
|---|---|
| suspension and engine interface positions | jig bench survey (M1) |
| P5 -> P12 spacing, front axle crossmember support -> gearbox crossmember support (not the wheelbase) | jig bench survey (M1) |
| absolute stiffness target | torsion test on a donor body shell (M2) |
| load path panel by panel, to zone the layup | model with real sections, not available |
| load introduction at hard points | vehicle load model, not started |
| crashworthiness | physical tests, not substitutable |

## 6. What this document is not

- It is not a design: no dimension, no thickness, no stacking sequence.
- The x 1.75 announced in the first version was wrong: see section 3.
- The ring ranking comes from a model with `ASSUMED` sections that is not
  mesh-converged. Only the order and the orders of magnitude are usable.
- Nothing here concerns crashworthiness, strength, delamination, buckling,
  fatigue or fire.
