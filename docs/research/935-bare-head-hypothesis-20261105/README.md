# 935 head reconstruction under explicit hypotheses

Date: 2026-11-05. Status: **digital geometry, export and neutral contour checks
passed; functional metal build qualification remains open**. The owner resumed
the engineering goal and explicitly authorised work with documented hypotheses.
This revision advances the existing
[935 scan research record](../../../catalog/scans/scan-935-xtreme-cylinder-head.json);
it creates no 993 fitment or released catalogue part.

The private delivery now contains a head-only 3MF, a supported composite 3MF,
editable indexed mesh, source recipes and complete 50 micrometre neutral CLI
contours. The [aggregate results](results.json) bind their actual hashes and
checks. Source coordinates, meshes, face selections, scan and review images
remain private. There is no qualified exposure/hatch file or machine job.

## Inputs and authority

The original Wolfe/Xtreme OBJ remains unchanged, SHA-256
`4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
One OBJ unit is treated as one millimetre by owner instruction; this does not
establish physical metrology, an exact variant or calibrated interfaces.
No dimension from another head is used to scale the scan.

The construction input is the frozen fine envelope from the
[earlier hypothesis study](../935-hypothesis-study-20261029.md), SHA-256
`bcced05cf880809afc007b546f2f1ceba8fb5b71870ed8dd4fb6ea11bfdeb7aa`.
It already contains inferred closures and represents a scanned assembly.
Preserving its triangles is distinct from recovering original scan triangles
or proving a complete measured bare head. Earlier exact native CAD observation
documents and the local CADAM/Qwen coupon are preserved unchanged.

## Reconstruction and rejected interpretations

Three candidate mounting planes come from existing source fits. A provisional
0.75 mm stock offset is a construction assumption, not a machining tolerance.
The first global three-plane cut was closed and digitally checkable but visibly
removed fin material. It is rejected for delivery. Attempting local assembly
from that global result also failed its crossing-region guard.

The accepted construction clips the **unchanged parent independently by each
single plane**. It then selects only isolated protrusions with cap area
10–150 mm², circularity at least 0.7 and outward extension at least 5 mm.
A selected outside component must have exactly one cap domain and must not
overlap another selected region. These thresholds identify a provisional
construction domain; they do not establish hardware identity or material.

Eleven domains pass this hypothesis: seven at the back and two at each side.
Every unselected parent triangle is restored, including the fins and an
ambiguous short irregular boss. There is no coordinate welding or smoothing.
The [local plan](local-cut-plan.json) is retained as executed input. Its
global-mesh construction sentence describes the rejected intermediate; the
effective single-plane method above and
[assembly source](source/assemble_single_plane_local.py) govern the delivery.

The result has 4,106,745 vertices and 8,219,310 triangles:

- 8,212,038 parent triangles are identical in coordinates and orientation;
- 4,380 partial skin triangles remain inside their original parent triangles;
- 2,892 cap triangles are explicitly assumed, with total areas of 316.453,
  76.222 and 78.755 mm² at the three construction planes.

An independent complete-triangle containment check bounds the partial-skin
displacement outside its parent triangle by 2.06 × 10⁻¹² mm. This is a
floating-point construction check, not a physical dimensional uncertainty.
The rigid build-frame transform and inverse are checked independently.

The actual PicoGK branch was also executed at 0.25 mm voxels using the same
global cuts. Independent checks find 29 components, eight positive shells and
21 negative shells. Its delivery gate fails; no islands or cavities are silently
deleted. PicoGK's role remains explicit in the chain, but it did not author or
approve the accepted local CGAL construction. The final output is an editable
mesh and reconstruction recipe, not a complete analytic STEP/FreeCAD master.

## Independent geometry and export checks

The actual final build-frame mesh has one positive material shell, a volume of
1,094,352.343555 mm³, and dimensions 119.722160 × 224.160991 × 93.644060 mm.
Full independent checks find zero open or nonmanifold edges, inconsistent
edge orientations, degenerate faces or nonadjacent intersections. Vertex
manifoldness and shell classification pass. No contact filtering is needed
for this final aligned mesh.

Earlier global/source-frame trials produced reported contacts. An independent
exact-rational projected intersection proof classifies only contacts equal to
the expected indexed shared simplex as admissible; extra overlap and unproved
projection controls are rejected. All raw reports remain intact. An initial
Gram-based containment calculation failed on one ill-conditioned triangle;
the retained diagnostic and a dominant-axis determinant calculation resolve
that numerical failure without relaxing the 10⁻⁸ mm construction guard.

Every coordinate, triangle index and millimetre unit in the preferred 3MF is
read back exactly. A binary STL of the **rejected global trial** introduced
23 degenerate faces and 22 nonmanifold edges after float32 conversion and was
rejected. No final local binary STL qualification is claimed.

Kali1 independently checks the exact final mesh bytes on native ext4 with a
separate standard C++ implementation: all 12,328,965 edges pair consistently,
there is one edge-connected component, no zero-area faces or unused vertices,
and volume agrees with the Mac within 10⁻¹² relative error. Cube, inverted,
open, wrong-winding, nonmanifold and existing-output controls pass. This Kali
program does not check self-intersections; the Mac's full geometry check does.

## Full-denominator deviation report

Each direction uses 100,000 area-weighted samples, without anatomical exclusions.
They are reproducible sample statistics, not a global distance bound or metrology.

| Direction | Median mm | P95 mm | P99 mm | Maximum mm |
|---|---:|---:|---:|---:|
| Original scan → parent envelope | 0.003502 | 0.024683 | 0.063427 | 3.330101 |
| Original scan → local reconstruction | 0.003681 | 0.097860 | 28.184238 | 49.755819 |
| Local reconstruction → original scan | 0.004468 | 1.523448 | 4.329602 | 10.898026 |

Removed protrusions remain in the original-scan denominator, and inherited
closures remain in the reverse denominator. 4,533 original-scan samples increase
their distance by more than 0.01 mm relative to the parent. Neither the small
median nor P95 proves an identical specimen or validates assumed closures.

## Supports and complete neutral slicing

New provisional supports use a 6 mm grid, 1.2 mm stem radius, 0.5 mm tip radius
and 0.25 mm axial contact overlap. A new 2 mm outside-air flood screen rejects
98 inaccessible intervals; uncertain cells are conservatively occupied.
This coarse screen is not support-removal or powder-evacuation qualification.

The composite 3MF contains the head, 1,117 support resources from 1,118 columns,
a 5 mm sacrificial plate and a cylindrical coupon: 1,120 resources in total.
Every resource and the actual component graph pass geometry/readback checks.
Every support has positive axial overlap; the intended union contact graph is
connected. The plate is 169.722160 × 244.160991 × 5 mm. The composite is not a
single merged triangle mesh: its overlapping resources must be united by the
consumer. The CLI below explicitly performs and checks that union per layer.

CGAL exact-decimal slicing uses 0.05 mm planes, with analytic cube/tetrahedron,
tangent and existing-output controls. One exactly collinear tangent section
has zero material area and is recorded. Raw native contours are preserved;
fixed-decimal formatting changes no vertex order or count and rounds each scalar
by at most 5.12 × 10⁻¹³ mm onto the previously qualified 10⁻¹² mm grid.

| Complete check | Head only | Head, supports, plate and coupon |
|---|---:|---:|
| Layers including empty zero level | 2,074 | 2,074 |
| Closed contours | 59,242 | 382,930 |
| Coordinate pairs | 23,552,588 | 39,813,640 |
| Invalid layers after full readback | 0 | 0 |
| Integrated volume mm³ | 1,094,349.925616 | 1,380,130.100367 |

Head layer integration differs from the 3D surface volume by 0.000220947%.
Common-plane layer-spacing comparisons at 0.2, 0.1 and 0.05 mm are retained;
they check contour discretisation, not physics convergence. Every supported
layer is united by integer Clipper and independently compared with GEOS.
The largest symmetric difference is 1.14 × 10⁻⁹ mm². Full exported CLI readback
agrees with that independent layer integral to 1.52 × 10⁻¹⁵ relative difference.
There is no laser exposure, hatch strategy or accepted machine profile.

## Execution, software and remaining work

The [phase ledger](phase-ledger.json) separates executed work from pending
physics and physical qualification. [Replay notes](REPLAY.md), source hashes,
actual commands, failed trials, controls and runtime receipts are retained.
Mac native CGAL 6.2.1 performs exact construction/slicing; libigl 2.6.3 performs
full geometry/distance checks; Shapely 2.1.2 / GEOS 3.13.1 and pyclipper
1.3.0.post6 independently check all layers. Rtree 1.4.1 assists ray queries.
Downloaded wheels are hash-verified and isolated from existing environments.
Kali1 uses Python 3.12.11, NumPy 2.5.4 and GCC 15.3.0 on x86_64/ext4.

The [documented CADAM/Qwen branch](../../architecture/cadam-local-qwen.md)
remains an auxiliary local coupon service. No new head prompt was sent to an
external service. Gmsh, OpenFOAM, CalculiX and Adamantine retain their admission
requirements. **No new-geometry physics solve has been executed for this
revision. Earlier envelope simulations are not validation of this head.**

Required follow-up includes wall/thin-feature and support-removal checks,
independently admitted physics meshes, thermal/mechanical studies with declared
loads and material hypotheses, and process-specific calibration. The effective
physical contract still accepts 0/8 functional interfaces and provides 0/8
operating fields. Alloy, hidden geometry, datums/tolerances, actual machine,
powder, thermal properties, exposure and post-processing remain unqualified.
Physical inspection, leakage/thermal/fatigue tests and professional engineering
review remain necessary for functional engine acceptance. These open criteria
do not stop independent work under explicit hypotheses.

The owner-private capsule is
`~/Developer/PorschePartsArtifacts/935-bare-head-hypothesis-20261105-001/`;
`delivery/files.json` indexes the actual preferred files and the nonduplicated
neutral CLI paths. Its frozen manifest binds all retained bytes. This increment
uses Mac and existing Kali1 resources, with **$0 new paid compute** and no new
Vast resource. The existing $35 total cap and $5 closure reserve are unchanged;
this statement does not reset any earlier spending. No supplier message, scan
transfer, fabrication order or manufacturing release is made. The goal is active.

Primary software references:
[CGAL clipping](https://doc.cgal.org/latest/PMP_Boolean_operations/group__PMP__clip__grp.html),
[Rtree 1.4.1](https://pypi.org/project/rtree/1.4.1/),
[Shapely 2.1.2](https://pypi.org/project/shapely/2.1.2/),
[pyclipper 1.3.0.post6](https://pypi.org/project/pyclipper/1.3.0.post6/).
