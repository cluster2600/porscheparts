# 935 rotor: constrained interior-node correction

This follows the root README's geometry → mesh → reference-solver chain. The
PicoGK design master and certified analysis boundary remain unchanged. The
[preceding quadratic study](QUADRATIC_ROTOR_CONTINUATION_20261022.md) found a
stress peak in the worst-conditioned tetrahedron. This continuation investigates
that numerical sensitivity on the Mac and Kali1, without another rental.

The [aggregate native receipt](interior-star-20261022.json) binds the public source
hashes, exact audits, numerical comparisons and
[private evidence archives](https://github.com/cluster2600/porscheparts-935-private/releases/tag/analysis-mesh-935-20261022).

## Diagnosis and refused proposals

The worst parent tetrahedron has three boundary vertices and one interior
vertex almost on their plane. Only **126 of 436,838 nodes** are interior. Of the
33 parent cells below mean ratio 1e-4, five involve an interior node and 28 have
only boundary vertices. Interior relocation therefore cannot repair every poor
cell without a separate boundary or connectivity change.

The previously refused TetGen quality refinement has now received its **own**
complete surface certificate. Its actual changed triangulation passes the
unchanged bidirectional 0.0225-unit bound against every original PicoGK triangle,
including topology and self-intersections. All boundary coordinates survive the
float32 export exactly; only global winding is reversed for outward orientation.
The old certificate is not silently reused. Its 2,952,749-cell volume still has
very poor cells and is retained as a diagnostic proposal, without a strength
solve or mechanical admission. Reconstructing without requesting q-refinement
returns exactly the original node, cell and boundary arrays.

Native Gmsh 4.15.2 `Relocate3D` passes the synthetic four-tetrahedron interior-star
control and relocates 92 rotor nodes while preserving the boundary and
connectivity. The independent whole-volume audit nevertheless finds **11 inverted
cells**, even though exact total volume is unchanged. This proposal is refused;
no CalculiX job runs on it. Its source, fields and audit are retained.

## Constrained correction

The [star-kernel worker](../../../twins/935-horizontal-cooling-system-f0/source/optimize_interior_stars.py)
uses the installed SciPy/HiGHS linear program to propose the centre of each
interior vertex's feasible star kernel. Each incident tetrahedron defines a
positive-determinant half-space. The program solves in displacement coordinates,
then tries sixteen step sizes and requires improvement of the minimum local mean
ratio. Before accepting a move, it checks the exact orientation of **every
incident cell**. Three passes are allowed. All boundary vertices remain fixed.

The analytic right-tetrahedron control recovers the incenter
`(r,r,r), r=1/(3+sqrt(3))`. The near-boundary interior-star witness improves its
minimum mean ratio from 2.87747e-5 to 0.475553, preserving exact volume 1/6 and
positive orientation. Unit controls also refuse changed boundaries, changed
connectivity, nonfinite coordinates, tampered parent receipts and flat or
inverted cells whose total volume still matches.

The native rotor worker completes in **3.79 seconds** including process setup,
with **204 accepted moves affecting 106 interior nodes**. Its largest interior
shift is 2.43574 uncalibrated scan units. This changes finite-element node
placement inside the solid, not the scanned or design surfaces.

The [independent audit](../../../twins/935-horizontal-cooling-system-f0/source/audit_interior_relocation.py)
checks the complete 1,426,554-cell output. Every boundary coordinate and every
connectivity index remains exact, every node is used, the mesh has one connected
body, and there are **zero inverted or exactly flat cells**. The exact rational
total volume equals the parent's value. The worst Jacobian condition falls from
8.32013e7 to **5.95916e6**; minimum mean ratio rises to **5.83570e-6**. Poor
all-boundary cells remain, and mechanical mesh-quality admission stays false.

The [executed recipe](../../../twins/935-horizontal-cooling-system-f0/source/interior-star-study-20261022/)
reproduces the bounded control, worker and provenance receipts from the private
parent archive. The new audit accepts only its declared supported optimizer
sources and matching parent/output hashes.

## Structural comparison

The unchanged preparer verifies all quadratic whole-simplex mappings and numerical
coordinate transport before writing new C3D4/C3D10 cases. Both retain AlSi10Mg,
6,000 rpm, assumed 1 mm per scan unit and the unmeasured rigid bore band. Actual
solver node sets remain identical: **12,492 constrained C3D4 nodes and 52,251
C3D10 nodes**. Geometry, connectivity, material, speed, support membership and
solver binary match the preceding study.

The C3D4 solve and complete independent result audit finish. Maximum displacement
changes by only **0.00178%**, from 0.0926668 to 0.0926685 assumed mm; the outside
r=25 mm element-peak stress p95 changes by **−0.00516%**. The peak elastic stress
changes from 2,240.96 to **827.04 assumed MPa**, a 63.09% reduction.

The C3D10 solve completes in **665 seconds**, peaking at **37.28 GiB** under the
same 48 GiB limit. The complete audit covers 2,736,957 nodes and **5,706,216
integration points**. Relative force and moment balance errors are 2.9848e-9 and
3.4244e-9. The fixed-support displacement remains zero.

| C3D10 quantity | Before | After | Relative change |
|---|---:|---:|---:|
| Maximum displacement, assumed mm | 0.309288 | 0.309292 | +0.00121% |
| Element-peak stress p95 outside assumed r=25 mm | 36.5515 MPa | 36.5499 MPa | −0.00440% |
| Peak elastic von Mises, assumed MPa | 1,643.10 | 526.81 | −67.94% |

The vector displacement difference at the same 436,712 boundary corner samples
is at most 5.7505e-5 assumed mm, or **0.01859%** of the preceding maximum boundary
displacement. Peak stress in the 1,423,027 geometrically unchanged cells can still
differ by up to 13.65 assumed MPa. A stable maximum displacement and percentile
do not establish agreement of every stress sample. A peak that changes this much
under an interior-only correction is unsuitable as a material-strength or
usable-speed conclusion.

This is a controlled mesh-quality sensitivity study, not a three-level spatial
refinement series. Matching resultants, stable displacement or lower peaks do not
establish fatigue, convergence, physical fit or manufacture.

## Rigid-rotor cross-check and remaining work

The existing rigid-rotor and surface-moment helpers independently reproduce the
tetrahedral centrifugal force and moment integrals with relative differences
below 4e-14. Cube mass/inertia and translated-origin controls pass. Under the
same assumed scale, uniform density and axis, the current geometry gives a
764.46 N geometric unbalance-force amplitude and 1.89 kJ rotational energy at
6,000 rpm. These are as-modelled conditional quantities, not measurements of an
original 935 fan. They must not be confused with the older assumed residual
unbalance after balancing. Physical axis registration and balance remain open.

The next required calculations remain a quadratic spatial-refinement series,
prestressed modes, the qualified-runtime MRF/SST pilot and its fan curves. The
spatial series needs fixed physical comparison locations and documented
singularity exclusions; an element-count percentile alone is insufficient. The
17-interface definition, hidden transmission, material/process data, assembly
loads, balancing and bench validation still govern the complete system. The
993 adaptation remains a separate programme; manufacturing is not authorized.
