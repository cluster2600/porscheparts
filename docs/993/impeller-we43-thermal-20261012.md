# WE43 impeller: exploratory transient build thermal study

Part: `993-ENG-COOLING-IMPELLER-WE43-F1-0001`.

This study computes transient bulk heat transfer during the LPBF build of the
existing concept impeller. It uses the actual admitted STL and all 6,286 physical
30 µm part slices. The user has no selected machine or machine parameter file;
the reference recipe and missing calibration are therefore explicit.

The earlier [layer-stack preview](../../parts/993-eng-cooling-impeller-we43-f1-0001/media/print-simulation/build.gif)
is a geometric animation. It does not contain a thermal calculation. Its generic
support proxy is not a supplier support design. Correction PR #167 was merged
into `main` at `0cbee3710ea6b23f210e872011f8a7f5452e6676`.

## Inputs and provenance

- [Hyer et al., ORNL publication record](https://impact.ornl.gov/en/publications/additive-manufacturing-of-dense-we43-mg-alloy-by-laser-powder-bed/):
  200 W, 1,100 mm/s, 0.13 mm hatch spacing, 0.03 mm layers. These are published
  coupon parameters, not a qualified recipe for this impeller.
- [Luxfer conventional wrought-alloy table](https://www.luxfermeltechnologies.com/wp-content/uploads/2021/07/Luxfer-MEL-Technologies-Elektron-Wrought-Alloys.pdf):
  WE43 density 1,840 kg/m³, conductivity 51 W/(m·K), heat capacity 966 J/(kg·K).
  Density and conductivity are quoted at 20 °C; heat capacity at 20–100 °C.
  The primary PDF's indexed table was readable, while direct download returned
  a challenge page. No supplier document is redistributed.
- [Study card](../../parts/993-eng-cooling-impeller-we43-f1-0001/source/lpbf-thermal-study.json):
  assumed absorption 0.35, plate 30 °C, ambient 25 °C, 6 mm standoff,
  15% solid-fraction support columns, 8 s recoating per physical layer,
  convection 12 W/(m²·K), emissivity 0.4, cooldown 120 s.
- [Admitted geometry report](../../parts/993-eng-cooling-impeller-we43-f1-0001/evidence/lpbf-f0/993-eng-cooling-impeller-we43-f1-0001-lpbf-geometry-report.json):
  `roll_y_45` orientation and STL SHA-256
  `f9c8462c634dc92aa23de09535e372b5ae14d7665616e3249c4d54251eed1f88`.
  This remains estimated concept geometry, with no measured fitment claim.

## Equations and discretization

[The calculation](../../parts/993-eng-cooling-impeller-we43-f1-0001/source/simulate_lpbf_thermal.py)
reuses the repository's backward-Euler sparse conjugate-gradient thermal step.
For each active cell it solves, in SI units:

```text
C_i (T_i(new) - T_i(old)) / dt
  + sum_j G_ij (T_i(new) - T_j(new))
  + H_i T_i(new) = Q_i + H_i T_bath
C_i = rho cp dx^3 f_i
G_ij = k dx 2 f_i f_j / (f_i + f_j)
```

Cells activate progressively in Z. New cells start at the assumed plate
reference temperature. Supports occupy columns below the first part cell at each
XY position and use an effective solid fraction of 0.15 for capacity,
conductance and scan energy. This is an assumed thermal connection, not a
manufacturable support layout. Plate attachment is perfect contact to an
isothermal reservoir. All other exposed faces exchange heat with ambient gas by
convection and linearized radiation; surrounding powder conduction is omitted.

Each macro layer alternates heating and recoating substeps. The deposited laser
energy is integrated from the physical slice areas using `P / (v h t)` and the
assumed absorption; support energy uses the homogenized support solid volume.
Heating is distributed over the current macro layer. Individual tracks, contours,
jumps and the moving laser spot are unresolved. All cells of a macro layer are
activated together; time refinement does not eliminate this spatial lumping.

The calculation checks the CAD checksum, manifold solid, full slice sequence,
slice volume against CAD (0.1% tolerance), voxel volume against CAD (2% tolerance),
finite solved temperatures, iterative convergence and each step's energy balance
(relative tolerance 1e-6). Input hashes are frozen at start and rechecked before
publication; field and history hashes are included in the summary.

## Mesh admission and rejected runs

| Grid | Part volume error vs CAD | Decision |
|---|---:|---|
| 2 mm | −4.022% | rejected before thermal solve |
| 1.5 mm | −4.816% | rejected before thermal solve |
| 1 mm | +0.247% | admitted for exploratory bulk calculation |

Volume agreement is an admission check, not evidence of spatial convergence or
accurate blade temperatures. Thin features and heat paths remain voxelized.
A spatially converged prediction has not been established.

Early development runs used an incorrectly translated ray-classification frame.
They are excluded in full, including their temperature fields. The defect was
fixed by translating all three mesh minima to zero before voxel classification;
a regression checks translation invariance and full solid volume. An initial
2 mm odd-intersection rejection made before that fix is superseded by the
corrected-frame volume audit above.

## Reproduction

Use Python with NumPy, SciPy, trimesh, rtree and matplotlib. The local run uses
Python 3.10, NumPy 2.2.6, SciPy 1.13.1 and trimesh 5.0.0. The source imports the
existing repository geometry kernel; retain the repository layout.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  parts/993-eng-cooling-impeller-we43-f1-0001/source/simulate_lpbf_thermal.py \
  --output work/we43-thermal-s4 --pitch-mm 1 --substeps 4
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 \
  parts/993-eng-cooling-impeller-we43-f1-0001/source/simulate_lpbf_thermal.py \
  --output work/we43-thermal-s8 --pitch-mm 1 --substeps 8
python3 parts/993-eng-cooling-impeller-we43-f1-0001/source/render_lpbf_thermal.py \
  work/we43-thermal-s8 work/we43-thermal-s4 --output work/we43-thermal-visuals
python3 -m unittest discover -s tests -p test_impeller_lpbf_thermal.py -v
```

Output directories must be new. The NPZ contains cell centres in mm, the part
mask, peak/end-build/cooled temperatures in kelvin, and post-recoat snapshots.
Inactive cells in snapshots are NaN deliberately; the final temperature fields
must be finite. The JSON history records scan/recoat phase times and maxima.

## Interpretation limits

This is an actual numerical bulk heat-transfer calculation, with numerical
verification distinct from experimental validation. Constant wrought-alloy
properties, assumed thermal supports and missing powder conduction limit its
physical accuracy. Exceeding 100 °C also exceeds the reference heat-capacity
range and must be flagged, not treated as a qualified temperature prediction.

Melt-pool temperature and shape, melting/solidification enthalpy, evaporation,
porosity, residual stress, warping and support-release distortion are not solved.
There is no machine calibration or coupon validation. The calculation cannot
establish print success, support removal access, dimensional accuracy or rotor
safety. Those require a machine-specific process/material card, measured
interfaces, designed supports, convergence studies and physical validation.
