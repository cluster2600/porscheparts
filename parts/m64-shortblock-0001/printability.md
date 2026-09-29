# Printability study — M64-SHORTBLOCK-0001 (concept stage)

Scope: material/process selection per part for additive candidates, fin
minimum-thickness versus process capability, and per-part print-candidate
selection. This is a **selection study for a concept geometry**; no part here
is released for printing. All geometry values referenced are
provenance-classed in `provenance.json` — most are ASSUMPTION parameters.

## Candidate process: LPBF (laser powder bed fusion)

Reference window for structurally relevant LPBF (AlSi10Mg, ~30 µm layer,
~200 W class machines; values are process-capability ranges from the public
LPBF literature, not qualified on our machine):

- Stable free-standing walls: ≥ ~0.8–1.0 mm (down-skin and tall thin walls
  need more; 0.8 mm is the survival floor, not a robust design value).
- Recommended design minimum for qualified production: ≥ 2 mm.
- Vertical overhangs < 45° need supports or are problematic; horizontal
  cylindrical shells (fins as discs on a barrel) print vertically-friendly
  only with the barrel axis vertical in the build.
- LPBF AlSi10Mg T6 typical: UTS ~350–450 MPa, YS ~160–250 MPa, elongation
  6–12 %; fatigue scatter is large and anisotropic — no fatigue credit
  without coupons.

## Per-part assessment

### Piston — NOT a print candidate (F1)

- Duty: combustion pressure, sliding side load, ~200–300 °C crown. LPBF
  AlSi10Mg loses strength approaching 250 °C sustained; the piston is the
  worst thermal candidate in the lane and a fatigue/thermal-fatigue part.
- 2618-T61 (or 2618 forged) remains the reference material for a real
  piston; nothing in LPBF changes that at this stage.
- Geometry is a bare envelope anyway (crown/pin unknown). Verdict:
  **print only as a fitment/display dummy** (photopolymer or AlSi10Mg,
  no duty), never as a functional piston.

### ConnectingRod — NOT a print candidate

- Heavily loaded, fatigue-critical (P0 safety class in the repo rules:
  highly loaded engine parts need documented professional review).
- Sourced datum is a **forged 4340 steel** aftermarket rod; an LPBF AlSi10Mg
  rod is a different part, not a substitute. LPBF steel (17-4PH / 300M
  routes) exists but is out of lane scope and unqualified here.
- Envelope contour is hypothesis-class; a print now would bake a guess.
- Verdict: **no print**; retain as machined/forged reference.

### FinnedCylinder — PRIMARY print candidate (with a fin gate)

- Duty: heat rejection, low structural load at the fin; moderate temperature
  (< ~200 °C on the barrel under normal flow) — inside AlSi10Mg comfort zone.
  LPBF's high thermal conductivity path (no contact resistance at fin roots)
  is exactly the reason to print deep fins integrally.
- **Fin min-thickness vs process**: baseline `FinThicknessMm = 1.5 mm` is
  above the ~0.8–1.0 mm survival floor but below the 2 mm qualified-design
  recommendation. Rules adopted in `ShortBlockParams` / run report:
  - `FinMinLPBFThicknessMm = 0.8 mm`: hard study gate — fins below this are
    assumed unprintable (aliasing + down-skin instability).
  - Run warning whenever `FinThicknessMm < 2 × voxel size`: at the default
    1.5 mm voxel, a 1.5 mm fin is one voxel thick and **aliases**; print-
    study builds must use voxel ≤ 0.75 mm so a fin is ≥ 2 voxels.
  - Fin height here is deep: (380 − 110)/2 ≈ 135 mm cantilever at 1.5 mm
    thick is far beyond demonstrated LPBF fin slenderness for a
    support-free vertical wall; real prints need either thicker roots
    (filleted root, ≥ 0.6 mm effective via a tapered profile) or an
    in-build support strategy. The F1 geometry has no root fillet
    (`FilletMm` reserved), so the as-authored fin is optimistic.
- Build orientation: cylinder axis vertical (fins stack along Z, no
  down-facing fin underside except roots); barrel bore needs support/removal
  for the closed top face; note the 15 mm closed head-side face traps
  powder → add a draw/evacuation port before any real build.
- Verdict: **print candidate, one specimen**, AlSi10Mg LPBF, at 0.5 mm
  voxel geometry, fins re-proportioned to ≥ 1.2 mm with filleted roots;
  print is for form/flow-fit demonstration, not thermal certification.

### CrankcaseSkeleton — SECONDARY print candidate (segmented)

- Duty: structural layout master; loads in the real engine go through main
  bearing webs — the skeleton is a stiffened box, low duty for a display/
  fitment build.
- Size: 640 × 480+ × ~250 mm envelope exceeds typical ~250–400 mm LPBF
  builds; candidate is a **segmented print + joined halves** at the split
  plane, or scale-model print, or switch to binder-jet/SandPrint-type
  sand-printing for full-size sand-cast analogues.
- 6 mm nominal wall is comfortable for LPBF at 0.8 mm floor; the closed
  crank cavity and galleries need powder evacuation ports and trapped-
  powder strategy (galleries at Ø12 mm are printable horizontal bores only
  with support or post-removal access).
- Verdict: **print candidate as halves** for fitment check against the
  printed cylinder and piston envelope; AlSi10Mg. No bearing-load credit:
  the main bearing bosses are assumption-class and would need inserts.

## Per-material note: why not 2618 by LPBF here

2618 is the conventional wrought choice (pistons, high-strength cylinders
skirts) and prints reasonably in LPBF (public results ~400 MPa UTS T6), but
it is a niche powder with no qualified track record for engine parts in our
window; the repo keeps 2618 as the *wrought reference* and LPBF AlSi10Mg as
the *additive demonstrator*. Rod stays 4340 forged reference; cylinder and
crankcase demonstrator parts run AlSi10Mg.

## Gate list for print release (none currently met)

1. Voxel ≤ 0.75 mm geometry re-run with fin/root fixes.
2. Powder-evacuation/port features on closed volumes.
3. Coupon set on the same build plate (tensile + fin pull) — no coupon,
   no property claim.
4. Metrology of printed fins vs nominal 1.5 mm (deviation feeds
   ACQ-driven updates, not silent geometry edits).
