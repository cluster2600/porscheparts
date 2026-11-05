# Four-valve / 85 mm bore interface

This step turns the assembly's radial overrun signal into a
**shared-volume check** between the inherited valves, the cylinder and the
piston. It then proposes four **compact layout silhouettes**
generated with PicoGK. The previous engine, its cylinder heads, its turbos and its receipts
remain intact. The new silhouettes require a reconstruction of the cylinder head
body, seats, guides and ports before any integration.

The [plan](plan.json) keeps the documentary bore/stroke of 85 × 66 mm. The
head diameters of 34 mm intake / 29 mm exhaust, the centres
`X = ±18 mm, Y = ±17 mm, Z = 4 mm`, the 6 mm stems and their lengths of
80 mm are **new design assumptions**. The axes are inclined
by 8°. Discs and stems serve for packaging; tulip, seat cone,
fillets, metal and manufacturing are not defined. No diameter choice is
validated by a flow calculation or a measurement of a Porsche part.

The [receipt](execution-20261012.json) covers 384 cases: four valves, six lifts
from 0 to 12 mm, four crank angles of the positive bank from TDC,
two variants and two native meshes with a 1 / 0.5 mm grid. The inherited valves
keep their triangles and coordinates, under the unverified assumption
1 unit = 1 mm. Their motion follows the estimated guide axes.
The piston keeps the connecting rod–crank mechanism already present in the repository.
The intersections use [Manifold](https://github.com/elalish/manifold)
via the existing F37 helper. These are operations on triangles with floating-point
coordinates, without proof of BRep or metrological exactness. A Boolean
error stops the check; it never becomes an accepted zero volume.

Sums of the intersections of the four valves, fine 0.5 mm grid:

| Variant and diagnostic pose | With the cylinder | With the piston at TDC |
|---|---:|---:|
| Inherited valves, 0 mm lift | 112.994 mm³ | 0 mm³ |
| Inherited valves, 2 mm lift | 836.652 mm³ | 143.118 mm³ |
| Compact silhouettes, 2 mm lift | 0 mm³ | 0 mm³ |
| Compact silhouettes, 4 mm lift | 0 mm³ | 741.027 mm³ |

The compact silhouettes have no contact with the cylinder in the
48 valve/lift configurations checked on both grids. At 2 mm
lift at TDC, their minimum axial box gap to the flat piston is only
**0.261 mm on the fine grid**, less than 0.5 mm. A zero shared volume
therefore qualifies neither a positive clearance nor this lift as admissible.
Poses at 4 mm and above at TDC remain in contact with the piston.
Contact volumes can decrease after the crown is crossed into
the piston cavity; that does not make this motion acceptable.

The curves join the computed poses for readability. No continuous sweep,
720° cycle, timing of the two banks, valve-to-valve contact, thermal expansion,
deformation or manufacturing tolerance is validated. The real alloy, the
manufacturing process and the measured interfaces remain `null` in the plan.

The local directory keeps STL/VDB per grid, a comparison GLB at 2 mm
lift, the complete contact report, an opaque-surface preview and curves.
The bottom of the cylinder and piston is masked at Z = −35 mm and the cylinder is
shown in half-section for presentation only. The complete GLB remains
unchanged by this render. These geometries are not published in Git.

```sh
python models/917-engine-reconstruction/clearance/check_clearance.py \
  --previous work/917-4v-biturbo-20261011 \
  --dotnet /chemin/vers/dotnet \
  --output work/917-head-clearance-essai-001
python models/917-engine-reconstruction/clearance/render_review.py \
  --run work/917-head-clearance-essai-001 \
  --output work/917-head-clearance-apercu-001
```

Use .NET 9 / PicoGK 2.3.0 and Python with NumPy, Trimesh, SciPy, Rtree,
NetworkX, Matplotlib, Manifold3D 3.5.4; VTK 9.7.1 is used for rendering. The outputs
must be new directories under `work/`. The input files are
bound to the digests of the previous receipt; the grids are not tolerances.

The next step is to build a parametric cylinder head around this layout,
define the cam laws and the clearance criteria, then carry out the thermal,
flow and strength calculations with documented materials and processes.
**No authorisation to manufacture or to run is granted.**
