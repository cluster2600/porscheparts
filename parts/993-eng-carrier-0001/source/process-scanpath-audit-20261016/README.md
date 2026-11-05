# Check of support exposures

This check complements `process-slicing-20261016/audit_scanpaths.py`, which
verifies the **part** scan paths. It reads all the real **support** vectors,
the sheet/tooth NPZ files and the six admissions of the same process. A
completed part cache is not a completed support process.

From the repository root, with the coverage PySLM runtime:

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python \
  parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/test_support_scanpaths.py

work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python \
  parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_support_scanpaths.py \
  PROCESS_OUTPUT PROCESS_OUTPUT/support-scanpath-audit \
  --source-stl work/part-workflow/run-001/surface/carrier-remeshed.stl \
  --part-cache work/carrier-process-20261016/part-layer-cache-001
```

The output directory must be new. The return code is zero only for an
accepted `assessment.json` receipt. No sampling mode can produce a complete
admission.

The criteria remain explicit:

- Each array is finite, of type float64, with no null segment or exact
  duplicate, and contains all the expected slices, with no extra segment.
- Each retained triangle belongs to a `face_range/order/type` group bound to
  the WKB material and its contact receipt. The grids cover exactly this
  material. Reproducing the frozen remapping of the skins establishes the
  identity between their parametric material, their piecewise maps and their
  triangles.
- The auditor then cuts the **real NPZ triangles** with a rational barycentric
  formula independent of the sectioner. A triangle section is convex: its
  whole segment is thus certified. The input IEEE values are interpreted
  exactly; no proximity distance welds sheets together.
- The rational endpoints are encoded by float64 round-to-nearest, ties to
  even. Their exact error is bounded by half a ULP. An encoded endpoint may
  necessarily leave a zero-thickness sheet when the rational coordinate is not
  dyadic. This strict verdict remains displayed; the section and encoding
  certificate is distinct. Collisions between two identical float64
  representations keep both their rational identities.
- The contact traces are also the exact rational intersection between the
  material and the raw interfaces. Holes are preserved. A mere point contact
  is not an anchoring interval. The former GEOS intersections may serve as
  diagnostics; their rounded points must not be used as evidence of exact
  confinement.
- The graphs of the rational sections and of the float64 vectors actually
  exposed must both pass. An intralayer edge is an exact intersection of scan
  paths. A link between layers requires an XY intersection in two
  **consecutive** layers. Each layer component must already reach a lower
  anchor; a junction that appears later does not save a sheet that has started
  to float.
- Each final component also reaches an upper contact actually exposed in the
  part section. The same piece of scan path must meet the contact band and a
  positive length in the part. The vertical penetration of 0.2 mm is the
  generator parameter, with no XY extension. Plate anchoring is limited to the
  first layer and the real 500 mm square, with a lower interface at Z=0.

The part domains are compared with the arrays of the complete cache via
`CachedLayers`. The source STL, the exact pose and the envelope store with its
native audits are verified. The sources, receipts, NPZ and CSV files must keep
their SHA before and after the run.

`exact_support_section.support_section(surface,z,face_z_bounds)` is the
separate generation hook of CORE4184. It computes the shared edges in
rationals, rounds correctly and does not use `tol.merge`. The launcher may
assign `core.support_section = hook.support_section` on its loaded module,
then freeze the hook in its extensions. The CORE file and the part cache are
unchanged. `exact_contacts.round_contact_traces(material,interfaces)` provides
the counterpart for the contact metadata.

The accepted receipt must carry `complete_build_audited=true`,
`support_scanpaths_audited=true`, `geometric_confinement_passed=true` and
`exposure_connectivity_passed=true`, and reference exactly the SHA of
`PROCESS_OUTPUT/report.json`. It covers the exposure lines and the contacts
between layers. No spot diameter or exposure order within a layer is assumed.

The witnesses and profiles are referenced in `results.json`. The complete
execution on the corrected carrier supports remains a separate step.
