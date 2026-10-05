# Alloy comparison report — 993 fans and 935 system

Study executed on **3 October 2026**. Three independent centrifugal calculations
compare aluminium, magnesium and titanium on the PicoGK parametric 993 rotor.
The 935 scan underwent volumetric reconstruction experiments; results are
rejected for mass/strength calculations.

Programmes stay distinct: vertical 993 rotor and horizontal 935 rotor. Values
below concern the **993 visual reference rotor**, with dimensions/interfaces
unmeasured on the part. They describe neither 935 rotor nor complete system mass.

## Results at identical geometry

Closed rotor volume: **283.897 cm³**, excluding separate hub, inserts, coating,
fasteners, alternator, housing and transmission. Material mass/inertia changes
are calculable; absolute values depend on assumed geometry.

| Candidate | Rotor mass | Difference from Al | Polar inertia | Peak von Mises at 10000 rpm | Maximum displacement at 10000 rpm |
|---|---:|---:|---:|---:|---:|
| AlSi10Mg | 758.0 g | reference | 0.005381 kg·m² | 248.21 MPa | 0.2429 mm |
| WE43 magnesium, indicative elastic card | 519.5 g | −31.5% | 0.003688 kg·m² | 170.12 MPa | 0.2642 mm |
| Ti- 6Al-4V | 1249.1 g | +64.8% | 0.008867 kg·m² | 409.03 MPa | 0.2547 mm |

Material change alone improves neither blade shape nor flow. Magnesium reduces
mass/inertia/centrifugal stresses, but lower stiffness increases displacement
about **8.8%** here. Titanium increases displacement about **4.9%** and centrifugal
loads at common geometry. A lighter titanium rotor requires over **39.3%** volume
reduction merely to equal aluminium mass, then renewed root, mode, gap,
manufacturing and fatigue checks.

## Studied speeds and strength

Speeds belong to the **rotor**, not crankshaft. They are study scenarios; no
allowable service/overspeed range is determined. Each material is solved at 10000
rpm. Other points use exact squared-speed dependence of the linear elastic
model at fixed geometry/boundaries.

| Rotor speed | AlSi10Mg peak | WE43 peak | Ti64 peak |
|---|---:|---:|---:|
| 3000 rpm | 22.34 MPa | 15.31 MPa | 36.81 MPa |
| 6000 rpm | 89.36 MPa | 61.24 MPa | 147.25 MPa |
| 8500 rpm | 179.33 MPa | 122.91 MPa | 295.53 MPa |
| 10000 rpm | 248.21 MPa | 170.12 MPa | 409.03 MPa |
| 12000 rpm | 357.42 MPa | 244.97 MPa | 589.01 MPa |

Aluminium yield comparator is **250 MPa** on EOS M290/30 µm T 6 coupons; titanium
comparator is **1000 MPa** on EOS M290/60 µm coupons treated at 800 °C/2 h under
argon. Comparator/peak at 10000 rpm is about **1.01** and **2.44**, not validated
safety factors. Aluminium at 12000 rpm exceeds its comparator: elastic results
then predict neither real deformation nor failure.
[EOS aluminium](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-alsi10mg),
[EOS titanium](https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-titanium-ti64).

Tensile limit for WE43 **printed by our future process** remains unknown.
Compression/flexural results cannot be used as rotor tensile limits. Available
experimental research also shows geometry/build-batch dependence of defects
and properties. [Julmi et al., WE43 LPBF study](https://pmc.ncbi.nlm.nih.gov/articles/PMC7918529/).

## Vibration, energy and numerical provenance

One unprestressed modal calculation produces twelve modes on the aluminium
reference. Other modal series use exact elastic similarity: frequency
proportional to √(E/ρ) for common geometry, constraints and Poisson ratio.
[Result JSON](results/comparison.json) identifies actual solves and extrapolations.

| Card | First unprestressed mode | Method |
|---|---:|---|
| AlSi10Mg | 348.26 Hz | Executed CalculiX modal solve |
| WE43 | 333.89 Hz | Elastic similarity from aluminium |
| Ti64 | 340.08 Hz | Elastic similarity from aluminium |

[CSV](results/rpm-sweep.csv) includes mass, inertia, kinetic energy, peripheral
speed, rotation frequency and eleven-blade passing frequency for fifteen
material/speed cases. Modes exclude centrifugal prestress, gyroscopic effects,
flexible supports, damping and contact; they are not a Campbell diagram.
Installed flow and fatigue life remain unknown.

![Conditional 993 rotor comparison](results/comparison.png)

[PDF charts](results/comparison.pdf).

Three CalculiX **2.23** static calculations were rerun on **native Kali 2 Linux
x86_64 / ext 4**, non-root, each with **86640 quadratic tetrahedra and 164869 nodes**.
All elements/displacements are checked. Magnesium/titanium independently verify
expected density/modulus similarity. Mesh comes from the
[archived modal deck](../993-engine-cooling-fan-system-f0/results/program-20261003/modal/modal.inp.gz),
linked to original PicoGK surface by its [reduction audit](../993-engine-cooling-fan-system-f0/results/organic/structure/reference-structure-50k/surface-audit.json).
Mass uses the closed 80000-triangle review; structural mesh surface has 50000
triangles. Both derive from the same surface with reduction volume errors below
0.02%. Geometry checks do not establish stress peak convergence; mesh independence
remains to prove.

Cards/results are isotropic approximations at 20 °C. E is 70 GPa aluminium,
44.1 GPa magnesium and 110 GPa titanium; common ν = 0.33 is assumed to isolate
density/stiffness. Aluminium E is a study assumption. Magnesium borrows wrought
WE43C density/modulus without claiming measurement on LPBF material.
[Luxfer Elektron 43](https://www.luxfermeltechnologies.com/elektron-43/).
See [material cards and scope](materials.json).

Inherited bore constraint is hypothetical and must be replaced by measured
shaft/hub contact and bearings. Aerodynamic, thermal and residual stresses,
print defects, anisotropy, fatigue and balance are not calculated here.

## 935 reconstruction result

PicoGK **26.2.0** executed two prepared-scan voxelizations at conditional
**0.65 and 0.40 source units**, expressly assuming 1 unit = 1 mm. Outputs are
fragmented and volume differs by about **9.7** times. Globally reversing face
orientation does not fix them. Closed 993 control voxelizes correctly with less
than 1% volume difference. Failure is specific to this open-scan reconstruction,
not a 935 mass calculation.

Prepared 935 rotor retains **58 boundary contours**, one spanning more than a
hundred source units. Arbitrary closure could change blades, hub and passages.
Scale, surface repair and rear-face connection must be established before
accepting volume. Exterior drive reveals neither shafts, teeth, clearances,
bearings nor internal cavities.

[935 system model](../935-horizontal-cooling-system-f0/README.en.md) retains its
seventeen interfaces, components and calculation domains. Two exterior meshes
do not establish mechanical assembly/transmitted loads. 935 total mass, strength,
critical speeds and useful flow remain **uncalculated**. Identification/measurement
questions are already prepared for Wolfe.

## Files and design follow-up

[Executable sources](source/compare_alloys.py) preserve historical data and
create new cases. [Report generator](source/build_comparison_report.py) produces
JSON, CSV, charts and three OpenUSD files linking geometry, material, mass,
inertia and results. USD and complete native outputs remain private; parametric
reference summaries/charts are public here.

Reproduction uses Python with numpy, trimesh, matplotlib and usd-core, then
CalculiX 2.23. From repository root in a new ignored directory:

```sh
python3 twins/fan-alloy-comparison-f0/source/extract_reference_geometry.py \
  twins/993-engine-cooling-fan-system-f0/results/reference/reference.usdz \
  work/fan-alloy-rerun
python3 twins/fan-alloy-comparison-f0/source/compare_alloys.py \
  twins/993-engine-cooling-fan-system-f0/results/program-20261003/modal/modal.inp.gz \
  twins/fan-alloy-comparison-f0/materials.json \
  work/fan-alloy-rerun/993-cases
```

Run `ccx -i rotor > log.rotor` in each of three material directories, then
`ccx -i modal > log.modal` in aluminium. Private 935 trials and closed control
use [ScanScreen](../935-horizontal-cooling-system-f0/source/picogk-scan-screen/Program.cs),
compiled against PicoGK 26.2.0 and native runtime. Each call takes prepared OBJ,
expected SHA- 256, assumed scale, resolution and new directory. Generator requires
receipts and checks output integrity before reporting; repository supplies no
private scans.

Next geometry iteration must modify blade roots/sections at common mass, gap,
strength and aerodynamic objectives. Magnesium is attractive for mass, titanium
requires volume reduction, aluminium supplies the first industrial comparator.
No alloy is final. Printing dossier includes orientation, supports, treatments,
machining, inspection, fatigue, protection and galvanic isolation under the
[additive dossier](../../docs/research/935-horizontal-cooling/ADDITIVE_MATERIALS.en.md).

These files are **uncalibrated study twins**. They establish neither engine fit,
physical tests, allowable speeds nor manufacturing authorization.
