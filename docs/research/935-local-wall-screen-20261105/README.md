# Revision-specific normal-chord and thin-feature screen

Date: 2026-11-05. This is a follow-up to the
[digitally checked local reconstruction](../935-bare-head-hypothesis-20261105/README.md).
The delivered mesh and both 3MFs remain unchanged. The
[aggregate receipt](results.json) binds actual native, independent and
source-frame checks. All sample positions, face IDs and scan-derived images
remain in a separate owner-private capsule.

## Upstream verdict

The actual delivered mesh has sampled short material paths that require
resolution before any process-wall acceptance or a simulation mesh claiming to
resolve every thin feature. No minimum-wall manufacturing criterion is selected
without a process. No mesh-parameter sweep, arbitrary thickening, small-face
deletion or reinterpretation as physical metrology follows this screen.
Independent work can continue by investigating these fixed local regions and
declaring the scope of a subsequent numerical surrogate explicitly.

## Executed measurement and independent checks

The geometry input is exactly the delivered build mesh, SHA-256
`05159cdbf903729da5b8556d2ff2c2d29680a45c2b4bd42b34e031a122205594`.
Its full manifold/intersection admission is checked before the screen. Actual
little-endian vertex and triangle bytes match the admitted NPZ and previous
cross-host receipt. The private source/build frame is verified against the
frozen parent manifest before raw-scan distances are evaluated.

Five thousand area-weighted surface points are drawn with fixed seed 935055,
without anatomical exclusions. A ray follows each inward flat-triangle normal;
only its originating face is skipped. CGAL's nearest forward intersection
returns the next boundary point. The measured length is a **normal chord**:
it is not a global minimum wall, printable-feature threshold or physical
measurement. This distinction also applies to long paths through the body.

All 5,000 queries return point hits with positive forward distance and exiting
surface orientation; none is missed, a segment intersection or an ambiguous
near-zero hit. Cube, oblique cube, 0.03 mm thin-box, miss, segment-ambiguity and
existing-output controls pass. The CGAL implementation uses exact predicates
and inexact constructions; it is not an exact-rational distance certificate.

An independent NumPy Moller–Trumbore implementation searches every non-source
triangle for sixteen rays: the eight shortest chords and eight distributed
samples. Its greatest distance discrepancy is 2.28 × 10⁻¹³ mm. Only those
sixteen distances receive this second full search; the remaining native
queries are not described as independently distance-verified.

| Statistic | Normal chord, mm |
|---|---:|
| Minimum among sampled points | 0.031963 |
| P01 | 0.316016 |
| P05 | 1.551284 |
| Median | 22.887207 |
| P95 | 85.725600 |
| Maximum | 211.446201 |

| Diagnostic threshold, mm | Sampled chords below it |
|---|---:|
| 0.1 | 5 |
| 0.25 | 26 |
| 0.5 | 160 |
| 1 | 218 |
| 2 | 354 |

These thresholds are reporting bins, not selected machine requirements. Every
one of the 354 chords below 2 mm has both endpoints on retained parent skin;
none touches an eleven-cut assumed cap. Parent skin already inherits envelope
reconstruction uncertainty; it is not automatically an original acquired facet.

For the 160 chords below 0.5 mm, endpoint distances to the original scan are
computed after restoring the source frame. Across all 320 endpoints the median
is 0.003510 mm, P95 is 0.083680 mm and maximum is 0.428610 mm. Ninety-four chord
pairs have both endpoints within the diagnostic 0.01 mm distance. Proximity
does not prove a physical wall, validate an inherited closure or identify the
cause of a short chord.

An initial endpoint-distance trial incorrectly compared build-frame points
with the source-frame scan. That trial and its source are retained as rejected;
none of its proximity values is used. The corrected query verifies the frame
against the frozen manifest and checks a source/build round-trip with maximum
error 8.17 × 10⁻¹⁴ mm. The native chord lengths and cap/skin index attribution
do not depend on this coordinate-frame correction.

## Replay and retained evidence

Compile [normal_chords.cpp](source/normal_chords.cpp) with C++17, CGAL 6.2.1 and
GMP/MPFR. [screen_normal_chords.py](source/screen_normal_chords.py) documents
explicit mesh, prior geometry receipt, binary vertex/face, executable and new
output arguments. It runs controls and the actual complete 5,000-ray screen,
then the sixteen independent full-triangle searches. The run took 16.63 s
including its independent searches on the Mac; compilation is separate.

[classify_probes.py](source/classify_probes.py) accepts the retained samples,
actual local construction tags, original scan arrays, registered rigid frame,
and frozen parent manifest. It attributes every threshold bin and computes
same-frame scan proximity without changing geometry. Source hashes, binary,
commands, terminal logs, samples, rejected trial and corrected report are
retained in `~/Developer/PorschePartsArtifacts/935-local-head-wall-screen-20261105-001/`.
Existing outputs are refused; use a new directory for replay.

This is an upstream geometry screen, with $0 new paid compute. It is not Gmsh,
OpenFOAM, CalculiX or Adamantine validation, a calibrated metal job or engine
acceptance. The engineering goal remains active with those criteria open.

Primary API reference:
[CGAL AABB nearest-ray intersection](https://doc.cgal.org/latest/AABB_tree/).
