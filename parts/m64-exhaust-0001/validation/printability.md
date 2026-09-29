# m64-exhaust-0001 — LPBF printability assessment (IN625 exhaust lane)

Date: 2026-09-29. Branch: `wave2/geo-ex-20260929`. Owner: m64-writer.
Status: **assessment of authored, not-yet-run geometry** — every input is
tagged in `../source/picogk/provenance.json`; nothing here is a print
release. Printing of the sibling F0 dossiers is itself still prohibited.

## 1. Manifold runner bank (`ManifoldRunner`) — IN625 LPBF

Primary references:

- `parts/993-eng-exhaust-manifold-in625-f0-0001/` — the project F0 manifold
  part folder (STEP core, evidence, LPBF screen in
  `evidence/lpbf-f0/…-lpbf-geometry-screen.png`).
- `docs/993/993_EXHAUST_MANIFOLD_IN625_F0.md` — the manifold dossier, whose
  LPBF print simulation on the EOS M 290 route sliced the F0 at **40 µm over
  its full 215 mm height: 5,375 layers, 1 layer with an unsupported region,
  support proxy 15,425 mm³, local thickness p01 1.098 mm, trapped powder at
  1.00 mm = 0.00 mm³**, orientation rule `build_z`.
- Vendor anchor: Kline offers a 993 Turbo IN625 manifold at 2.9 kg per side
  (heat exchanger included), publishing **no dimension** — it justifies the
  material route only.

Printability findings carried to the authored SDF fields:

- One-piece 3-into-1 junction is the actual AM benefit (no weld bead in the
  gas path); three inlets + one outlet keep powder evacuation open. The F0
  screen showed zero captive powder at 1.00 mm — the authored
  `ManifoldRunner` keeps the same open-ended topology (open runners, open
  collector), so the no-trapped-powder property transfers structurally, not
  by re-simulation.
- Wall: F0 nominal 1.2 mm, p01 1.098 mm. The authored runner wall is tagged
  `ASSUMPTION`; anything below ~0.8 mm is unprintable on the EOS M 290 route,
  and the 1.2 mm F0 value is already at the thin-wall edge — the mesh study
  (1,696 MPa inadmissible fully-restrained elastic bound) says wall and
  interfaces must be re-derived from measured loads, not from the F0.
- Build envelope: F0 envelope 146.4 × 66.4 × 215.0 mm fits the M 290 plate
  in `build_z`. The authored bank runner adds a collector offset but stays
  order-of-magnitude inside the same envelope (all synthetic).

## 2. Exhaust tip (`ExhaustTip`) — oval-tip study

Reference: `docs/993/993_OVAL_EXHAUST_TIP_IN625_F0.md`. FVD declares only the
**120 × 85 mm outlet**; the authored F0 tip is an independent round-to-oval
transition, inner duct + 0.8 mm outer shell + eight radial ties, air gap open
at both ends → **no captive powder volume**. LPBF screen: 3,702 layers at
40 µm, orientation `roll_y_25`, theoretical 406.38 g IN625. The 0.8 mm shell
is printable but is the thinnest feature in this lane; the eight ties are the
printability-critical members (bridging between inner duct and outer shell —
each tie is a small unsupported span that the screen counted in the support
proxy). The authored `ExhaustTip` keeps the open-gap topology, so the
no-trapped-powder result transfers.

## 3. Heat shield (`HeatShield`) — polymer vs metal service temperature

The authored shield mirrors the FVD declared envelope 105 × 160 × 110 mm,
0.23 kg (BOM line M64B-TR-004, OEM protective-cover reference
`993 123 113 51`, declared envelope only per
`../source/picogk/provenance.json`). Its 1.5 mm wall and 12 mm corner
radii are `ASSUMPTION`.

Material question, stated at screening level (no local source publishes a
temperature map for this location — flagged ASSUMPTION throughout):

| route | continuous service capability (general engineering knowledge) | fit at a 993 Turbo turbine outlet |
|---|---|---|
| IN625 / stainless metal | hundreds of °C above glow: IN625 oxidation resistance well beyond 1,000 °C; the manifold dossier screens gas at 900 K | safe margin against radiant + convective exhaust; the only route consistent with the manifold dossier |
| high-temp polymer (PEEK-class, ~250 °C continuous; PA-class far lower) | degrades/creeps well below turbine-outlet radiant fields; polymer shields exist on insulated or far-field locations, not adjacent to an unshielded turbine | **plausible only with measurement** proving local skin temperature; nothing measured here |

The FVD part's 0.23 kg over a 105×160×110 mm box is consistent with a thin
metal pressing, which argues against a polymer reading of the vendor part.
Decision: geometry stays material-agnostic; **polymer selection is blocked on
measured service temperature**, metal (IN625/stainless, matching the rest of
the lane) is the working assumption.

## 4. Oil return pipe (`OilReturnPipe`)

Return-side, not gas-path: service temperature is oil-side (well below any
polymer limit only if routed away from the turbine housing — unmeasured).
IN625 kept for lane consistency; bend radius / self-supporting angle are the
printability items (the authored pipe is straight-with-elbows, printable
without internal supports at ≥45°). Wall is `ASSUMPTION`.

## 5. What printability here is not

No slice of the authored voxel geometry has been run yet (no STL export
recorded — see `compile-record.md`). All layer counts, mass and screen values
above are the sibling F0 dossiers' results, cited as prior screens for the
same material route. Powder lot, orientation, heat treatment, witness
coupons, CT/dye-penetrant, leak test: all open, per the F0 dossiers' gate
lists. **Not authorized for manufacture, an engine, or interior heating.**
