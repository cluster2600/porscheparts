# Connections between support sheets

`material_connections.connected_material(vertices, faces, groups)` reads the
real float64 triangles and the generated material groups. Each group
must cover its face range without omission or duplicate and be connected before
its contacts can be grouped with those of another sheet.

The function reuses the project's rational classifier. The boxes and
the Rtree index are used only to find candidates: the decisions
rest on the exact IEEE coordinates, with no welding distance.

- Two distinct planes are connected by a segment of positive length.
- Two coplanar groups are connected by an intersection of positive area.
- A single point, or a gap of a single ULP, does not connect the groups.
- Within the same group, exact shared edges also connect
  the triangles and the pieces of a split chart.

The output keeps a forest of witnesses sufficient to establish the
connections; it does not claim to enumerate all intersections. Each
certified component must inherit an upper and a lower contact. The
contact identities come from the generator's interfaces; the complete
audit of the exposures remains mandatory for the layers actually
built.

Exactly degenerate triangles are refused before the graph. To avoid
a needless rational computation on each ordinary triangle, a filter proves
only non-nullity: with M the absolute maximum of the coordinates, in
`[2^-400, 2^400]`, a component of the floating-point cross product exceeding
`32 * eps * M²` cannot come from an exactly zero area. This conservative
absolute bound includes subtraction and product errors; all
other cases are recomputed in rationals. The intersections themselves are
always rational.

Nine native tests cover the connections, false contacts, disjoint
groups, zero or tiny triangles and the standalone copy of the sources:

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_material_connections.py -v
```

A flat copy must include the frozen file
`design-20261016/classify_mesh_contacts.py` next to this module. The receipt keeps
its two source identities and that of the geometry arrays.
