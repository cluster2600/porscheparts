# 993 Turbo engine carrier — rework with the control chain, 16 October 2026

The provisional **V6f geometry is kept**. The new energy balance passes
on its twelve archived linear cases; the strict DfAM geometric check
rejects it. **The part is not deliverable for functional manufacturing**: its
Porsche interfaces remain unmeasured, mechanical convergence is not
established and no complete printing process is qualified for it.

The deliverable of this rework is a reproducible digital dossier:
[results and digests](../../parts/993-eng-carrier-0001/source/revalidation-20261016/results.json),
[energy audit](../../parts/993-eng-carrier-0001/source/revalidation-20261016/audit_energy.py),
[DfAM check](../../parts/993-eng-carrier-0001/source/revalidation-20261016/dfam/assessment.json),
and the [unchanged V6f STEP](../../parts/993-eng-carrier-0001/derived/correction-20261013/carrier.step).
The catalogue F0 master is not replaced by this study.

## Identity and scope

Part number **993 115 021 53, 993 Turbo**, distinct from the intermediate support
993 115 103 52. The selected STEP has the SHA-256 digest
`834cc01a69c8205d854c611f7a8b7c2b6192687d547191deabbd25fe5c74049f`.
Its integrated volume is 268,853.113 mm³ and its nominal mass 1.188331 kg
with the reference density 4.42 g/cm³. The axes, the central 100 × 40 mm
spacing and the 8 mm seat remain **study assumptions**.

The raw files of the last calculation were recovered and their identities
cross-checked against the inventory already published. No new mechanical solve,
repair, removal of positive faces or modification of the STEP was made.
The checked STL keeps exactly the coordinates and orientation of the
33,634 triangles of the archived V6f surface.

## Checks actually run on V6f

| Check | Result | What it establishes |
| --- | --- | --- |
| Solid + spring internal energy, compared with ½ F·u | 12/12 cases; maximum relative deviation 3.334 × 10⁻⁸, threshold set at 10⁻⁴ | Energy consistency of the archived linear model |
| Surface topology | 1 component; 0 open edges, non-manifold edges, inconsistent orientations or degenerate triangles | Consistent closed surface |
| Self-intersections, libigl 2.6.3 | 0 pairs detected | Independent check of this triangulated surface |
| Sliver triangles, strict criterion | **74**, against 0 allowed | Mesh rejected by this criterion; this is not a measure of strength |
| Ray thickness, exploratory threshold 1.5 mm | **54.994 %** of the area below the threshold; p01 and p05 = **1.300 mm** | Failure of the chosen screening, not of a qualified supplier criterion |
| Closed cavities, 0.3 mm parity grid | No enclosed volume detected | Result limited to this resolution; actual powder removal not demonstrated |

The energy audit re-integrates σ:ε/2 at the four Gauss points of each
affine C3D10 tetrahedron, with the six stress components and the E and ν
of the dataset. It adds ½ k u² for the springs and verifies the identities
of the elements, integration points, nodes, loads and files.
The [ten mesh-9 cases](../../parts/993-eng-carrier-0001/source/revalidation-20261016/energy-mesh-9.json)
and [two mesh-7 cases](../../parts/993-eng-carrier-0001/source/revalidation-20261016/energy-mesh-7.json)
are kept separately. The 10⁻⁴ threshold was set before the evaluation;
the printed stresses and displacements have seven significant figures.
Curved tetrahedra, non-linear cases and thermal cases are refused.
Six tests cover analytical energies, the springs and corrupted inputs.

DfAM strict-v3 and its libigl check ran their witness tests before the
carrier. The carrier calculation took 50.46 s, then 0.71 s for the intersection
check, without exceeding the caps of 4 GiB, two CPUs and 600 s.
The [software digests](../../parts/993-eng-carrier-0001/source/revalidation-20261016/dfam/runtime-provenance.json)
and the text outputs are kept. The 1.5 mm threshold must be replaced
by a criterion justified by the selected process before any industrial decision.

## What still prevents validation

The [earlier structural results](../../parts/993-eng-carrier-0001/source/bionic-20261011/correction-20261013/README.md)
remain rejected: under −4 kN along Z and 850 N·m about the model's Y,
refinement raises the peak from 740.86 to 800.63 MPa. With the assumed
supports of 1,000 N/mm per end, the fine mesh reaches 2,082.84 MPa
in the elastic model. No LPBF allowable and no post-yield behaviour
is established. The successful energy balance resolves neither this
sensitivity to the supports nor the absence of convergence, contact or preload.
The figures of the historical R9 study use other loads and axes.

The [new Adamantine verification](LPBF_NATIVE_VERIFICATION_20261015.md)
establishes the correct export of stresses and a one-element thermoelastic witness.
It does not yet provide a calibrated simulation of deposition, melting,
plasticity, cooling, supports and cutting of this engine carrier.
The old 60 µm contours and the V6f uniform shrinkage check
do not become such a simulation by transferring these results.

## Public research verified on 16 October 2026

The [official Porsche PET](https://files.porsche.com/f/332100/cfbfd366e3/kat017-e-911-98-katalog.pdf),
group 109-00, PDF pages 115–116, confirms the cradle item 17, the intermediate
support item 18, four M10 × 20 and four M10 nuts, two rubber mounts
and four M8 × 40 to the body. It does not dimension spacings, axes, reference
surfaces or tolerances. The targeted search on the 53/54 part numbers,
drawings, scans and STEP/STL identified no exact model with metrology and
a reusable licence. This is a bounded search, not evidence of absence.

| Industrial lead | Public data | Point still to confirm |
| --- | --- | --- |
| [BLT S600](https://www.xa-blt.com/en/product/blt-s600/?solution=45) | 650 × 650 × 850 mm, titanium alloys; [BLT manufacturing](https://www.xa-blt.com/en/aerospace/) with Grade 5, machining, treatments and testing | Grade 5 process on this machine and acceptance of this carrier |
| [Nikon NXG XII 600](https://nikon-slm-solutions.com/slm-systems/nxg-xii-600/) | 600 × 600 × 600 mm; [material data sheet of November 2025](https://nikon-slm-solutions.com/wp-content/uploads/2025/11/mds5137.pdf), page 10, Ti6Al4V Grade 23 ELI at 60 µm | Separate Grade 5 route; Grade 23 properties are not transferred |
| [AMEXCI](https://amexci.com/services/metal-3d-printing) | NXG XII 600 and Ti64 in its offer | Ti64/NXG600 and Grade 5 association not publicly established; [Nikon press release](https://nikon-slm-solutions.com/newsroom/amexci-and-nikon-slm-solutions-strengthen-their-collaboration-in-the-nordics-with-am-technology/) explicitly attributing titanium to the SLM500 |

The V6f footprint lying flat with the 45° in-plane rotation and the assumed
margins requires a square build plate of at least **471.134 mm**. The large
machines above are envelope leads, with no booking and no validation
of the job. No supplier was contacted, no file sent.

## Next steps needed to obtain a deliverable functional part

1. Measure the exact cradle with its intermediate support and rubber mounts:
   centres, axes, seats, datums, tolerances, bolt stack-up and packaging.
   The [existing measurement plan](../../parts/993-eng-carrier-0001/evidence/measurement-plan.md)
   provides the starting point.
2. Freeze the loads, the support stiffness and the contact/preload model;
   then rework the geometry and establish mechanical convergence.
3. Choose a manufacturer and its exact process: alloy, flat orientation,
   accessible supports, depowdering, parameters, treatments, machining
   allowances and inspection. Calibrate the build simulation on this process.
4. Have the criteria and the test plan approved, then inspect the prototype
   and carry out representative load/fatigue tests with competent review.

The current handover is therefore **a verified rework of the study dossier**.
It is neither a machine file, nor a manufacturing authorisation,
nor a validation of fitment or service life.

## Reproduction and repository verification

With the archived raw data and NumPy, the new check runs as follows,
giving a fresh output directory for each mesh:

```sh
python3 parts/993-eng-carrier-0001/source/revalidation-20261016/audit_energy.py "$RAW/v6f/mesh-9" "$NEW_OUTPUT"
```

The **16 targeted tests** of V6f correction and energy audit pass in
the existing scientific container, with the three surface tests run.
The ten page-generation tests also pass. Schemas, catalogue,
generated pages, report index and strict links are verified.

An additional re-run of the old CAD inspector under emulation was
stopped at 604.8 s after exceeding its 600 s budget, without a final report.
Its partial outputs remain in the working directory and provide no
new evidence. The interface results already archived remain historical.

The local run of `make check` on the basis of this rework is **not
green**: 3,979 tests, two exact floating-point comparison failures in the
unchanged WE43 impeller/AlSi10Mg stator tests, 27 errors related to SciPy
PROPACK/Python 3.10, and 254 skipped tests. These problems are not fixed
in this rework. No remote CI, merge or publication is claimed.
