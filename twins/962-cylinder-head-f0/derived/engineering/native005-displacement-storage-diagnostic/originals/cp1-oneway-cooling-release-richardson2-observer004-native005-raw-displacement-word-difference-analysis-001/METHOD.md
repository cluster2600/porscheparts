# Derived displacement-word difference classification

This analysis reads only the1,021,950B derived report7f11a0976f15d90d05f26c388e3d5b5196916dfcc2d401f88a6b8e627fcc0d8a.
It does not reopen the12 original scientific inputs, runtime records or source
programs, and does not replay the diagnostic, solver, strict collector or
mechanical assessor. The report identity was checked before and after analysis.

All1275 saved node/slot rows, component names, unique global indices and saved
comparison flags were reconstructed from the report. X1 and CSV agree in all
1275 raw words. The same192 rows differ in X1/Exodus and CSV/Exodus.
Every difference is finite and numerically unequal; none is a signed-zero or
nonfinite case. All192 complete original rows/raw words remain in analysis.json,
with decoded exact hex values, exact rational differences, source IDs,
components/global indices, shared-group labels and doublet line positions.

| Component | Mismatches | 1 ULP | 2 ULP |
|---|---:|---:|---:|
| disp_x |63|60|3|
| disp_y |67|58|9|
| disp_z |62|55|7|
| Total |192|173|19|

The192 rows affect117 source IDs. Among the report's shared25 IDs,14 rows
across8 nodes differ (10 at1ULP,4 at2ULP). Among its other400 IDs,178 rows
across109 nodes differ (163 at1ULP,15 at2ULP). Shared IDs/positions are taken
from the saved nodal-storage associations; no new geometric classification
or original CSV parsing is performed. Per-node/component/group projections,
all unaffected source IDs and every raw difference are retained.

For a saved little-endian uint64 word u, let magnitude=u&(2^63-1).
The ordered rank is2^63-magnitude for a negative sign and2^63+magnitude
otherwise; distance is the absolute rank difference. This collapses the two
zero encodings, while sign-zero differences are separately classified.
The definition counts ordered finite binary64 steps; it introduces no
tolerance or physical error criterion.

Values are decoded only from the report's raw binary64 hex words. Exact
Fraction.from_float subtraction gives Exodus minus X1; absolute ranges and
all fractions are retained with numerator/denominator and exact dyadic decimal
strings. Approximate decimal fields are display only.

The minimum absolute difference is1/36893488147419103232
(approximately2.710505431213761e-20); the maximum is
1/4611686018427387904 (approximately2.168404344971009e-19).
These are raw decoded displacement-value units only. This scope does not
independently establish SI/metres, engineering significance or an acceptable
tolerance. Exodus is greater in91 differing rows and less in101.

One/two-ULP differences do not establish exporter rounding, conversion, event
ordering, a numerical floor or any other cause. Allthree views share the
solver pipeline. A later separately authorized pinned exporter/event-source
investigation must establish state/timing and serialization provenance before
causal interpretation or changed numerical acceptance. No word normalization,
tolerance relaxation, field/force/reaction/physics/material/manufacturing
acceptance or repair follows. Actual dt/scaling semantics remain independently
unverified;24 poor head cells and12 mechanical failures remain unchanged.

head_mesh_next authored the producer diagnostic/parser/caller/control sources.
This is producer-affiliated exact arithmetic over saved report words, not an
independent physical validation. Only bounded stdlib derived-data arithmetic
and the two requested artifact writes were performed. No target/native/strict/
full-mechanical rerun, source/runtime/API query, new solver or PUB/Git change
occurred.

