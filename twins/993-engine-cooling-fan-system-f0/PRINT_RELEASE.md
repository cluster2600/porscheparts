# Turbo fan — metal prototype print release dossier

Date: 28 September 2026. **Release status: HOLD — no print authorization.**
Scope: a first metal prototype of the 993 Turbo M64.60 rotor, targeting the
PMB / Classic Retrofit 240 A alternator. An authorization to manufacture a
controlled test article is separate from permission to spin it or install it.

This dossier replaces the old generic rotor as the design baseline. It does
not transfer old airflow, stress or thermal results to the reconstructed rotor.
The [reference register](reference-research.json) records the identified parts
and conflicting hub fitment statements. The [editable parameters](source/picogk-reference/reference.json)
label unmeasured dimensions explicitly.

## Design and manufacturing decisions

- Preserve a separately identified rotor, bearing hub, housing, alternator,
  rear cone, auxiliary impeller and drive. Confirm the actual Turbo hub before
  defining its interfaces; do not print a surrogate bearing or bearing race.
- Use AlSi10Mg as the current LPBF candidate, not an established optimum.
  Its qualification must cover the selected machine, powder lot/reuse, build
  orientation, heat treatment, surface condition and temperature-dependent
  fatigue data. Generic tensile strength is insufficient for rotating blades.
- Keep machining stock on critical interfaces only after their datums,
  tolerances and finishing route are approved. No arbitrary fits or balancing
  correction pockets are added to the visual model.
- Candidate machine: **ZRapid iSLM420DN**, dual 500 W, nominal
  420 × 420 × 450 mm. The manufacturer's precision layer range is 0.02–0.05 mm;
  this geometric screen uses **0.05 mm**, not a qualified laser recipe.
  Source: [manufacturer specification](https://www.zero-tek.com/cn/slm420dn.html),
  checked 28 September 2026. No supplier has accepted this build.

## Measurements that must close the geometry

Establish proposed datum A on the actual rotor locating face, datum B on the
measured axis and datum C on the drive/bolt clocking feature. The metrologist
must confirm these datums are functional. Record units, instrument, calibration,
uncertainty, part revision and repeatability. Do not derive mating tolerances
from photographs or commercial shipping dimensions.

| Item | Required evidence | Design consequence |
|---|---|---|
| Rotor 96410601522 | Traceable scan plus CMM measurements of tip envelope, axial extent, cup, root fillets and blade sections at several radii | Establish baseline pitch, twist, chord, thickness and clearance |
| Turbo housing 99310666750 | Inner profile, runout, mounting faces, stationary vanes and exit area | Define cold/hot tip clearance and actual CFD flow path |
| Bearing hub 96410605131 | Exact Turbo applicability, locating diameters, bearing designation, shoulder positions, bolt pattern, threads and fits | Resolve supplier contradiction before assembly |
| PMB 240 A | Manufacturer drawing for exact delivered revision: shaft, shoulders, threads, key/spline, body, mounts, vents and rear connections | Replace the missing alternator geometry; establish interference and cooling passages |
| Drive | Exact serpentine kit, pitch diameters, ratio, tensioner travel, belt load and pulley planes | Determine fan speed, torque and bearing loads; no guessed stock ratio |
| Axial stack | All spacers, bearing seats, washers, fasteners and pulley shoulders measured as assembled | Tolerance stack, clamp load, axial clearance and belt alignment |
| Rear cone / auxiliary impeller | Confirm 93060304101 / 92860304501 applicability and dimensions with PMB installation | Close outlet routing and alternator cooling model |

Internet research establishes part identity and nominal envelopes, but the
linked sources do not provide these complete interfaces and tolerances.

## Validation sequence and release gates

| Gate | Evidence required to close | Current state |
|---|---|---|
| Configuration freeze | Exact parts, PMB revision, hub compatibility and drive BOM signed off | OPEN |
| Metrology and fit | Dimensioned interface drawing, uncertainty and tolerance stack; full assembly interference check | OPEN |
| Aerodynamic baseline | Measured or traceably reproduced fan curve and system resistance; correct speed/direction, density and temperature | OPEN |
| CFD comparison | Same boundary conditions for baseline and candidates; pressure/flow/torque, conservation, mesh sensitivity and convergence; include housing and alternator blockage | OPEN |
| Blade choice | Quantified improvement at operating point without unacceptable torque, noise or stress penalties | OPEN |
| Mechanical design | Verified speed envelope including overspeed, belt and thermal loads; centrifugal/contact FEA, mesh sensitivity, modes/Campbell assessment and fatigue with LPBF defect/surface knockdowns | OPEN |
| Manufacturing plan | Reviewed orientation/supports, removal access, powder escape, machining stock, heat treatment sequence and distortion/recoater assessment | OPEN |
| Process qualification | Supplier's calibrated AlSi10Mg parameter set, representative coupons, inspection method and acceptance criteria | OPEN |
| Prototype inspection plan | Datum-based CMM/scan, qualified defect detection, surface and balance requirements, traceability and rejection rules | OPEN |
| Professional release | Named engineer approves this revision, remaining risks and test article restrictions; supplier approves build pack | OPEN |

Airflow alone is not the optimization objective: compare volume flow against
pressure rise and absorbed shaft power, while maintaining alternator cooling,
clearance, fatigue margin and balance. PhysicsNeMo can support a surrogate
only after suitable training/validation data exist. Omniverse visualisation
and USD validation do not establish CFD or structural validity.

A functional print release cannot be signed while the locating interfaces and
speed/load envelope remain unknown. No numeric fatigue margin, overspeed
limit, balance grade or defect limit is invented here: these are outputs of
the engineering review and intended test envelope.

## New rotor: completed geometric print screen

[Raw screen and layer metrics](results/print-release/manifest.json) ·
[Inclined report](results/print-release/993-turbo-fan-reference-lpbf-geometry-report.json) ·
[Flat comparison](results/print-release/flat-slicing.json).
Two independent executions produced identical inclined reports.

The reconstructed mesh spans 244.471 × 244.986 × 58.139 mm. These are
**computed model dimensions**, not measurements of a Porsche part.

| Metric | Inclined 45° about Y | Flat, rotor axis along build Z |
|---|---:|---:|
| Build height, bare part | 208.993 mm | 58.139 mm |
| Layers at 0.05 mm | 4,180 | 1,163 |
| Vertical-column support proxy | 1,118.986 cm³ | 306.552 cm³ |
| Layers with unsupported areas | 2,821 | 645 |
| New isolated islands across layers | 98 | 108 |
| Bare part fits nominal envelope | Yes | Yes |

The flat orientation reduces the support-column proxy by approximately 72.6%
and layer count by 72.2%, but has more new islands and a larger maximum
unsupported area per layer (145.902 versus 24.444 mm²). **It is a candidate for
supplier review, not an approved orientation.** A minimum-overhang-area rule
selected the inclined case; the complete slicing comparison exposes its
manufacturing cost. Proxy volume is a geometric column envelope, not actual
support material or a quote. No laser-time or build-price claim is made.

The 2,000-point thickness screen reports a 3.621 mm median, 0.292 mm minimum
and 5.45% of probes below 1.5 mm. This is a warning requiring a location-based
check of leading/trailing edges, cup and fillets on the final master; it is
not a certified minimum wall measurement. The 0.65 mm PicoGK voxel size and
mesh reduction are too coarse to qualify submillimetre features. A 1 mm
voxel screen detects no closed powder pockets, without proving complete
powder removal or absence of smaller traps.

These results advance manufacturing assessment; they do not close metrology,
flow, fatigue, supports or professional release gates.

## Controlled prototype acceptance

The eventual signed pack must identify: CAD/source revision and hashes,
released drawing, machine and material/process revision, orientation and
supports, post-processing traveller, coupon layout, dimensional/defect
acceptance criteria, responsible engineer and manufacturer, date, serial/lot
traceability and disposition of nonconformities. Mark the article as a test
prototype. Contained spin tests and engine installation require their own
approved procedures; a printing authorization alone permits neither.

## Reproduce the geometric screening

Generate `rotor-mm.stl` with the checked-in PicoGK reference project, then run
from the repository root with the existing scientific Python environment:

```sh
python twins/993-engine-cooling-fan-system-f0/source/run_reference_print_screen.py \
  /path/to/reference-geometry /path/to/new-print-analysis
```

This reuses `scripts/run_metal_am_geometry_screen.py`: six candidate
orientations, complete 50 µm layer slicing for the selected orientation,
support-column proxy, sampled thickness and voxel powder-escape screening.
A 50,000-triangle analysis mesh must remain closed, connected and within 0.2%
of the source volume. Source and analysis hashes bind the results. This does
not bound local thin-feature error; manufacturing checks must return to the
final metrology-based master. Plate/support allowances and the selected
orientation require supplier review. It does not simulate melt-pool physics,
residual stress, recoater collisions or actual laser toolpaths.
