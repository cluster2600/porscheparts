# V5 carrier — mechanical and additive-process study

12 October 2026. The user authorised continued calculations using provisional
geometry and loads. **The 1.185 kg V5 remains rejected under those assumptions.**
It meets the 1.2 kg fallback ceiling, misses the 1.0 kg target, and does not meet
the structural screen. Its original assumed 8 mm bolt seats were not thickened.
No manufacturing, vehicle-use or fitment approval follows from this study.

This continues the [lightweight review](lightweight-review.md) on its exact V5
solid. [Inputs](study-comprehensive.json), [selected material/process](material-process.json),
[load analysis](comprehensive.py), [plastic load/unload analysis](plastic_check.py),
[printing model](print_simulation.py) and [actual-layer slicer](slice_print.py)
are editable, reproducible sources. The [numerical summary](comprehensive-results.json)
records **40 structural solves, three staged printing solves and one whole-part
contraction control**, separately from the analytical benchmarks and failed
diagnostic attempts. The staged printing predictions are rejected for use.

## Exact proposed metal and manufacturing route

**Ti-6Al-4V, Grade 5 chemistry, EOS Titanium Ti64 powder, article 9011-0039.**
The selected study route is **LPBF on EOS M 400-4, Ti64_060_FlexM404, 60 µm,
argon, followed by 800 °C for two hours in argon**. The
[EOS process sheet](https://www.eos.info/metal-solutions/data-sheets/titanium/pds-eos-titanium-ti64-eos-m-400-4-60um)
reports heat-treated coupon yield values of 955 MPa horizontally and 990 MPa
vertically; corresponding tensile strengths are 1,070 and 1,080 MPa. Those
coupon values are comparison data, not statistical part allowables.
The [powder listing](https://store.eos.info/products/eos-titanium-ti64) establishes
the product and chemistry reference; it does not certify this carrier.

The numerical elasticity remains E = 107 GPa, Poisson ratio 0.31, density
4.42 g/cm³ and expansion 9×10⁻⁶/K, from the
[dense TIMET reference](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf).
They are not a measured LPBF material card. The study screen uses the lower
published coupon yield, 955 MPa, divided by an **assumed factor of 1.5**:
636.7 MPa. This factor is an explicit study decision, not a Porsche requirement.

HIP is not assumed: changing the heat-treatment route requires new material
data. Finish machining is required on the central mating face, four central
bolt seats/bores, and both end-eye bores and seats. Finished joint thickness
must match measured OEM values; no longer bolts are proposed. Powder/build
traceability, relevant-direction coupons, defect inspection including suitable
CT, penetrant inspection after finishing, CMM inspection and fatigue-critical
surface finishing are specified in the process card. Dissimilar-metal interfaces
need a qualified corrosion barrier that preserves clamp geometry and preload.

## Frozen interfaces and load hypotheses

The STEP SHA-256 is
`5b2f092c5e53a6e34a895645b534fb8a0ca2cfbb31ab286e37c06cee9d40fe9e`.
CAD volume is 268,046.107 mm³; nominal dense-reference mass is 1.184764 kg.
The protection check retains the assumed V1 central mating face, four bolt/tool
columns, two central openings, end bores and end seating faces. It is an
independent comparison with frozen assumed geometry, not OEM inspection.

PET identifies carrier `993 115 021 53`, separate bracket `993 115 103 52`,
four M10 × 20 central bolts and two end mounting interfaces. The load path is
engine → bracket → four joints → carrier → mounts → body, with the gearbox
support changing load sharing. Measured positions, grip, thread engagement,
bolt grade/preload, mating surfaces and installed clearance remain unknown.

X is the carrier span, Y the assumed eye axis, and Z the central-pad normal.
There is no measured vehicle-coordinate transform. The cases are Fx = 2 kN,
Fy = 2 kN, Fz = −2 kN, Mx = 100 Nm, My = 850 Nm, Mz = 100 Nm, and combined
Fz = −4 kN with My = 850 Nm. X torsion is explicitly tested, in addition to
the earlier Y-axis moment. Applying the whole 850 Nm to this carrier is a
load hypothesis, not a measured reaction or a power rating.

Each case was solved with fixed eyes, and distributed springs of 1,000 and
10,000 N/mm per eye per direction. Equivalent bore forces preserve all six
force/moment resultants. They do not reproduce bolt preload, friction, contact,
bracket flexibility, joint opening or rubber hysteresis.

## Strength, torsion, stability and temperature

| Case / fixture | Maximum displacement | Peak elastic von Mises demand |
| --- | ---: | ---: |
| Combined, fine mesh, fixed eyes | 3.913 mm | 1,034 MPa |
| Combined, fine mesh, 1,000 N/mm eyes | 23.143 mm | 2,002 MPa |
| My = 850 Nm alone, fine mesh, fixed | 1.774 mm | 659 MPa |
| My = 850 Nm alone, fine mesh, 1,000 N/mm | 2.810 mm | 838 MPa |
| Mx = 100 Nm alone, fine mesh, fixed | 0.297 mm | 154 MPa |
| Mx = 100 Nm alone, fine mesh, 1,000 N/mm | 9.271 mm | 156 MPa |
| Combined, geometric nonlinear, fixed | 3.839 mm | 995 MPa |
| Combined, geometric nonlinear, 1,000 N/mm | 22.900 mm | 1,969 MPa |

These are conditional demands, not physical failure predictions. The combined
case exceeds even the coupon yield reference, before applying the assumed 1.5
factor. Geometric nonlinearity does not remove that concern.

The energy-conjugate central rotation under Mx = 100 Nm is 0.383° with fixed
eyes, 1.750° at 10,000 N/mm, and 14.032° at 1,000 N/mm in the linear model.
The soft-fixture case was therefore repeated with geometric nonlinearity:
8.945 mm maximum displacement and 132 MPa peak stress. The large rotation is
dominated by the assumed mount restraint; it must not be attributed entirely to
metal strain. All three rotational stiffnesses and the reciprocal six-component
compliance matrix are retained in the numerical assessment.

Thirty-two signed combinations of the independent axis limits were evaluated
by **tensor superposition**, with Fz held at −4 kN. Coarse-mesh worst elastic
demands are 1,059 MPa for fixed eyes, 1,856 MPa at 10,000 N/mm and 1,940 MPa
at 1,000 N/mm. These are an algebraic envelope, not 32 extra solver runs or a
measured duty cycle. They cannot validate behaviour after yielding.

Ideal elastic buckling factors under combined load begin at 8.95 for fixed
eyes and 3.93 for soft mounts. They are perfect-geometry eigenvalues; yielding,
contact, defects and fatigue are not represented by these factors. They are
not strength safety factors.

A uniform +60 K operational-temperature hypothesis gives 0.170 mm / 219 MPa
with fixed ends and 0.159 mm / 2.25 MPa with soft mounts. Constant reference
properties were used. This illustrates the restraint sensitivity; it is not
a solved engine temperature field or a temperature-dependent AM qualification.

## Permanent deformation and fatigue

The load/unload calculation uses ideal perfect plasticity at the 955 MPa coupon
reference. There is no calibrated hardening, fracture strain or damage law.
With fixed eyes, three integration points develop equivalent plastic strain
above 10⁻⁶; peak plastic strain is 0.000279, and residual maximum displacement
after unloading is 0.000053 mm on this mesh. These very local values require
hotspot refinement and must not be converted to service life.

With 1,000 N/mm mounts, the ideal plastic model reaches 23.767 mm under load
and leaves **0.974 mm permanent displacement after unloading**. Peak equivalent
plastic strain reaches 0.852 locally. Such extreme local strain is far outside
a credible damage-free material model; it is a rejection signal, not a claim
that the real part would remain intact up to that strain. A measured hardening
and fracture law is absent.

Fatigue **stress demand** is computed from tensor ranges, with no invented S–N
curve. The gravity-to-combined cycle gives peak equivalent amplitudes of
355.6 MPa with fixed eyes and 680.5 MPa with soft mounts on the coarse mesh.
Reversing X and Y couples with gravity present are also recorded, including
the mean stress tensor at the amplitude hotspot. Surface condition, defects,
mean-stress correction, real load spectrum and fatigue life remain unqualified.

## Vibration with and without an attached mass

| Modal hypothesis | Fixed eyes, first mode | Soft mounts, first mode |
| --- | ---: | ---: |
| Bare V5 carrier | 284.67 Hz | 90.89 Hz |
| Additional 200 kg, split equally among the four bores | 14.60 Hz | 4.95 Hz |

The added mass is a sensitivity case. Engine centre of gravity, inertia tensor,
gearbox support and damping are unmeasured. Eight modes per case were computed;
none of these cases is a verified complete-powertrain resonance analysis.

## 3D printing: placement, actual slices and sequential mechanics

The [M 400-4 nominal envelope](https://www.eos.info/metal-solutions/metal-printers/eos-m-400-4)
is 400 × 400 × 400 mm **including its build platform**. Using a hypothetical
20 mm plate and 10 mm minimum support gap, the actual CAD fits at approximately
35.54° span elevation and 45° in the platform plane. The rotated part occupies
377.37 × 377.37 × 357.50 mm. Its placed top is Z = 387.50 mm. Machine-specific
edge exclusions, recoater clearance and support details are not qualified.

The actual STL was intersected at every 60 µm layer plane: **6,126 intervals
above the assumed platform, of which 5,958 contain part contours**. All contours
close. Their integrated volume differs from the STL by 0.000046%; the STL
differs from the editable CAD by about 0.047%. This checks geometric slicing,
not laser scan vectors or manufacturing capability. No support scan file or
machine job file was generated.

The mechanical printing model activates the actual C3D10 elements in 16 or
32 macro layers, first placing each layer stress-free and then applying its
shrinkage in a separate step. It uses assumed contraction of **0.10% in the
build plane and 0.05% along the build axis**. Downward faces over 45° receive
homogenised support springs, using assumed support E = 1 GPa and lateral
stiffness one tenth of axial stiffness. Supports are then removed. Nonlinear
geometry is enabled throughout.

The artificial temperature field is a deposition clock that imposes eigenstrain;
it is **not a computed laser temperature**. Macro layers are much thicker than
the 60 µm fabrication layers. The model does not solve melt pools, cooling
rates, phase transformations, 800 °C stress relaxation or detailed support
contact/removal access. A third run adds ideal 955 MPa plasticity to assess the
elastic stress spikes. All shrinkage and support parameters require calibration.

| Printing hypothesis | Released shape change after rigid registration | Change on support release | Peak released stress |
| --- | ---: | ---: | ---: |
| 16 macro layers, elastic | 0.329 mm | 0.249 mm | 5,083 MPa |
| 32 macro layers, elastic | 0.408 mm | 0.315 mm | 2,137 MPa |
| 16 macro layers, ideal plastic reference | 0.329 mm | 0.249 mm | 5,085 MPa |
| Whole-part one-step contraction control | 0.252 mm | 0.030 mm | approximately zero |

**The three staged results are rejected as physical printing predictions.**
The 16-to-32-layer change increases registered distortion by 24%; activation
resolution is not converged. The elastic peaks exceed the material reference.
More seriously, the ideal plastic staged run retains peaks above 5 GPa despite
its 955 MPa reference yield. The values are present in the raw integration-point
output, not introduced by the parser. Solver convergence therefore does not
establish a trustworthy constitutive response for this activation setup.

The whole-part control uses the same geometry, mesh, orientation, support
distribution, contraction and ideal material, but activates all elements together.
It gives 48.4 MPa on the plate and approximately 10⁻⁸ MPa after release, consistent
with free uniform contraction. This isolates the anomaly to the staged setup,
but does not identify or repair its root cause. A deliberately severe plastic
cube diagnostic also failed to converge on release and is retained as failed.
No compensation, support design or manufacturing claim is based on those runs.

The [NIST Ti64 validation study](https://www.nist.gov/publications/coupled-experimental-and-computational-study-residual-stresses-additively-manufactured)
illustrates why measured residual strain/stress data are needed; its calibration
has not been transferred to this geometry or machine setup.

## Numerical verification and remaining engineering work

The Gmsh/CalculiX unit-cube analytical solution passes. The print model has a
separate free-contraction cube check, a birth-before-shrinkage check, rigid-motion
registration tests, and solid/hollow slicing area checks. Six-axis equilibrium,
virtual work, compliance reciprocity and independent combined-load superposition
checks pass for the elastic and geometric-nonlinear campaign. Both meshes have
positive sampled Jacobians. Additional reaction checks pass for plastic loading
and for unloading with soft mounts. The fixed-eye plastic unloading deck did
not request reactions; that independent equilibrium check remains unperformed.

Seven focused numerical-bookkeeping tests and four existing carrier-regression
tests pass, as do the catalogue, generated-page and Markdown-link checks.
The full `make check` was not repeated in this extension. Its earlier native-Linux
run stopped at a nested Docker target because the validation container lacked
the Docker CLI; a fully green repository check is not claimed.

Refining from 72,440 to 149,737 nodes changes combined-load displacement by
1.94–2.27% and peak stress by 5.03–5.38%. The X-torsion hotspot changes by
14.4–14.6%, so **stress convergence is not claimed there**. Refinement is not
extended merely to qualify a geometry that already fails the selected screen.

| Required next evidence | What it resolves |
| --- | --- |
| Measured OEM datums, holes, seats, bracket and available fastener grip | Fitment and the unchanged-fastener requirement |
| Actual engine/gearbox loads, torque reaction, inertias and mount stiffness | Load sharing, distortion and loaded vibration |
| Bolt grade, preload, friction and joint contact model | Slip, separation, bearing and bolt fatigue |
| Process coupons with final surface condition and service-temperature data | Plasticity, strength allowables and fatigue life |
| On-plate / released distortion coupons and supplier support CAD | Inherent-strain calibration, heat-treatment sequence, support removal and compensation |
| Professional review and instrumented carrier rig tests | Acceptance and eventual manufacture/use release |

The design requirement stays at 1.0 kg target / 1.2 kg ceiling with unchanged
finished joint stack. A future revision needs a more effective central section
and arm/eye transitions outside the protected joints, within a measured vehicle
envelope. This study does not prescribe longer fasteners or accept the earlier
2.108 kg plate.

## Files and reproduction

Local CAD, meshes, raw solver input/output, figures and layer contours are in
`work/carrier-bionic-comprehensive-20261012/`. Historical V1–V5 campaigns and
their manifests remain unchanged. Each retained output is associated with the
actual STEP, mesh and input hashes. The solver is native ARM CalculiX 2.21-1;
its SHA-256 is `271f8411371b978d7a8d31a7a13d0765e6e1f872e8a8b1d6aac6d0856c71ec6c`.
The final local resource limit is three CPUs and four GiB, one thread per job.
`native-solver-raw.tar.gz` preserves the container calculation directory;
`archive-verification.json` and `remote-solver-sha256.txt` record its full-file
comparison. `sha256.json` covers the final local study files, including source
snapshots. Diagnostic failures remain identifiable and are not counted as
completed engineering cases.

Use the existing CAD Python environment and a prepared native CalculiX container
selected through `CARRIER_STUDY_CONTAINER`. Use fresh output directories:

```sh
python cad.py study-comprehensive.json /absolute/path/new-study/v5
python check_lightweight.py /absolute/path/new-study/v5 /absolute/path/frozen-v1/carrier.step
python simulate.py /absolute/path/new-study/v5 --mesh 9
python comprehensive.py /absolute/path/new-study/v5/mesh-9 --run
python comprehensive.py /absolute/path/new-study/v5/mesh-9
python plastic_check.py /absolute/path/new-study/v5/mesh-9
python plastic_check.py /absolute/path/new-study/v5/mesh-9 1000
python print_simulation.py /absolute/path/new-study/v5/mesh-9 /absolute/path/new-study/print-16-staged --orientation print-orientation.json --layers 16
python print_simulation.py /absolute/path/new-study/v5/mesh-9 /absolute/path/new-study/print-32-staged --orientation print-orientation.json --layers 32
python print_simulation.py /absolute/path/new-study/v5/mesh-9 /absolute/path/new-study/print-16-plastic --orientation print-orientation.json --layers 16 --plastic-reference
```

Copy `print-orientation.json` to the study root before running `slice_print.py`
or `render_comprehensive.py`. Every raw `.inp` deck is also directly executable
with its sibling `mesh.inp`, preserving the original job names and outputs.
