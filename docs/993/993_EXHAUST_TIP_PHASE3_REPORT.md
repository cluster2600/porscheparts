# Oval exhaust tip: Phase 3 digital report (conditional F3)

Part: `993-EXH-OVAL-TIP-TI-F1-0001`
([record](../../catalog/parts/993-exh-oval-tip-ti-f1-0001.json)),
status `concept`, safety class `functional`. Issue
[#433](https://github.com/cluster2600/porscheparts/issues/433), 2026-11-09.

> **Not a manufacturing release, not a fitment claim, not a strength claim.**
> This report gathers what the repository's digital evidence establishes for
> the five headings of the ROADMAP Phase 3 exit criterion, and names what
> blocks each of them. It adds no new measurement and no new calculation:
> every number below is quoted from the file it links. Where an input is
> missing, the heading says so instead of assuming a value.

## Candidate and decision

The owner accepted [decision 0014](../decisions/0014-exhaust-tip-route-matrix-conditional-titanium.md)
on 2026-11-09 (issue #5): this tip is the first titanium candidate, behind a
conditional go/no-go that is **no-go today** because no sourced service
temperature exists. Route: LPBF Ti-6Al-4V Grade 5, EOS M 290, 30 µm layers
([process card](../../catalog/manufacturing/processes/eos-m290-ti64-30um.json)).

## Summary

| Heading | State | Basis |
|---|---|---|
| Material | screening values only; no hot allowables | EOS Ti64 M 290 data |
| Mass | **established** for the drawn geometry | CAD volume × sourced density |
| Stiffness | first-mode screen only; static and cross-material comparisons blocked | strip model; interface undefined; moduli unsourced |
| Fatigue | **blocked** | no load case, cycle count or S-N data for the route |
| Manufacturability | geometric screen complete; process and print release blocked | LPBF geometry audit, route cards |

## 1. Material

From the [Ti64 engineering screen](../../parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json),
EOS Titanium Ti64 on M 290 at 30 µm, heat-treated coupons: density
4.41 g/cm³, elastic modulus 110,000 MPa, comparison yield strength 945 MPa,
thermal expansion 8.6 × 10⁻⁶ /K, conductivity 7.0 W/m·K, specific heat
560 J/kg·K. The screen itself labels these "ambient and wrought references
[...] screening inputs, not hot LPBF design allowables".

**Missing:** temperature-dependent properties for this exact route (yield,
modulus, creep and fatigue at service temperature), and the decision on HIP.
The creep-limited service ceiling used by the go/no-go is 350–400 °C
([decision 0014](../decisions/0014-exhaust-tip-route-matrix-conditional-titanium.md)),
which 0014 still asks to check against a primary creep source.

## 2. Mass

From the [route matrix](../../catalog/manufacturing/exhaust-tip-route-matrix.json):
**212.34 g** for LPBF Ti-6Al-4V on the drawn double-wall geometry
(CAD volume 48,149 mm³ × 4.41 g/cm³). On the same geometry it is 42.7 to
44.9 % lighter than the equal-geometry stainless baseline and 47.7 % lighter
than LPBF IN625. Mass is titanium's only measurable benefit for this part
(0014). The geometry itself is an F0 hypothesis: only the 120 × 85 mm outlet
is published, and the 0.8 mm wall and 120 mm length are assumptions.

## 3. Stiffness

- **First mode:** 44.8 Hz from an equivalent cantilever-strip screen
  (`cantilever_strip_first_mode_hz` in the Ti64 screen). The record calls it a
  screen, not a correlated mode.
- **Steel / aluminium / titanium at equal geometry:** not computed. A beam mode
  scales with √(E/ρ), but the repository holds a sourced modulus only for the
  Ti64 route; no `catalog/sources` record gives the modulus of the stainless
  baseline or of an aluminium alloy. Adding those sources is the prerequisite;
  the ROADMAP item "numerically compare the steel, aluminium and Ti-6Al-4V
  variants" stays open until then.
- **Static and clamp stiffness:** blocked. They depend on the slip-fit inlet
  interface and its clamp, which are not defined (issue
  [#530](https://github.com/cluster2600/porscheparts/issues/530)).

## 4. Fatigue

Blocked. The record's
[`titanium.fatigue_assumptions`](../../catalog/parts/993-exh-oval-tip-ti-f1-0001.json)
states that no fatigue load case, cycle count, S-N curve or allowable exists
for this part. The expected cyclic loads (thermal cycling, engine and road
vibration through the clamp, exhaust pulsation) have no spectrum or duty
cycle. EOS publishes no fatigue data for this route, and as-built roughness,
porosity, orientation and the undecided HIP would govern life.

The thermal screen sets a design constraint rather than a life: free thermal
growth is 0.42 mm, and the fully constrained elastic thermal stress is
385 MPa. The record reads this as a warning that the part needs a sliding
interface, not as a predicted stress.

## 5. Manufacturability

From the [LPBF geometry audit](../../twins/993-exhaust-tip-ti-f0/evidence/lpbf-f1/993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json)
(verdict `geometric_print_simulation_completed_process_and_print_release_blocked`):

| Gate | Result |
|---|---|
| Fits the EOS M 290 envelope (orientation `roll_y_25`, 148 mm build height) | yes |
| Full layer-by-layer slicing | completed |
| Single watertight surface mesh; master STEP hash verified | yes |
| Local wall thickness (screen, not a certified wall map) | median 0.79 mm, 5th percentile 0.68 mm, minimum 0.46 mm |
| Trapped powder at 1 mm screen resolution | none detected; CT and endoscopy still required |
| Recoater clearance, supports, machine file, coupons, process physics | not validated |
| Metal print authorized | no |

Process simulation (AdditiveFOAM) was not run: no temperature-dependent,
machine-calibrated material card exists for this route. Route cards and draft
supplier requests exist for
[Ti-6Al-4V](../../twins/993-exhaust-tip-ti-f0/evidence/route-ti64/) and
[Ti-6242](../../twins/993-exhaust-tip-ti-f0/evidence/route-ti6242/); the
[manufacturing request](993-exh-oval-tip-ti-f1-0001-manufacturing-request.md)
must not be sent while its prerequisites are open. No supplier has reviewed
manufacturability.

### Route comparison (decision 0014)

| Route | Verdict |
|---|---|
| LPBF Ti-6Al-4V | best mass of the metal routes; the only one combining titanium and the one-piece double wall; blocked by temperature |
| LPBF Ti-6242 | not a supply route for a first titanium part |
| LPBF IN625 | most likely temperature headroom, unquantified; heavier than stainless here |
| CNC billet | excluded for the drawn geometry; machining stays the finishing step at the slip fit |
| Fabricated stainless (sheet) | the reference: passes temperature with margin, commodity; 75–81 % heavier than LPBF Ti64 at equal geometry |
| Ti-6Al-4V investment casting | excluded: same temperature block, tooling for a small series, thin walls unsupported |
| Aluminium AM | excluded on temperature |
| Polymer AM | excluded; display and fit-check prints only |

## Finite-element analysis: not run, and why

AGENTS.md requires the input to be admissible before a solver is used. Here
the three inputs an FEA would consume are all missing: the inlet interface and
clamp (boundary conditions, #530), a sourced service temperature (thermal
load), and a load spectrum (fatigue). Any FEA run now would sweep assumed
values and record tuning, not engineering. Once those inputs exist, the
studies to run are a thermo-mechanical case with the sliding interface, a
modal case with the measured clamp stiffness, and a fatigue check against
route-specific data.

## Blockers

| Blocker | What clears it | Tracked in |
|---|---|---|
| Sourced service temperature | a published measurement of a 993 tip or outlet temperature, or a contributed measurement under [decision 0019](../decisions/0019-accept-contributed-measurements.md) | #530, decision 0014 |
| Inlet interface and clamp | measured or sourced inlet geometry and clamp definition | #530 |
| Moduli for the stainless and aluminium comparison | `catalog/sources` records for both | this report |
| Hot allowables, HIP decision, fatigue data for the route | supplier or published route data | manufacturing request |
| Galvanic isolation scheme; toleranced drawing | design work after the interface exists | manufacturing request |
| Functional-class release | documented functional testing and professional review (SAFETY.md) | — |

## Phase 3 exit criterion

The ROADMAP asks for "a digital material, mass, stiffness, fatigue and
manufacturability report". This is that report in its conditional form: mass
and the geometric manufacturability screen are established; material,
stiffness and fatigue stop at the blockers above. Supplier review and physical
correlation stay outside the active phase.
