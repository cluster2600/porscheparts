# 935 original-export-bounded fluid mesh: weak rotor-wall faces

The 0.005 local facet-repair fluid mesh remains rejected for CFD. This
diagnostic traces its 1,426 tetrahedra with mean ratio below 0.01 to exact
rotor-wall triangles. It uses the unchanged 4,651,098-cell Gmsh volume,
SHA-256
`0f6d5cadd5b48c3345e8440c5a881018ca463b005641c46e0b376d9ecbcd8bb7`,
and the [weak-cell locator](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/localize_original_bound_facet_weak.py)
output, SHA-256
`2a684d5590671a8ed2f866a3193fddb77718b7680a3b3a530f77ec154e6cb2ca`.

The [exact-face audit](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_original_bound_wall_faces.py)
finds that 1,356 weak cells share at least one complete rotor triangle;
70 touch a rotor node without sharing a complete rotor triangle. There are
2,132 incident rotor-face occurrences, of which 500 have triangle quality
below 0.1. The incident-face median quality is 0.188, against 0.812 for
the full rotor wall. This is an association between weak fluid cells and
poor wall triangles, not proof that a particular surface repair will fix the
volume mesh.

In the **conditional** 1 source unit = 1 mm scale, 901 weak-cell centres
have radius 84–86 mm. The private two-view point map shows a nearly
continuous annular concentration at this radius. Neither this radius nor
the wall shape is a confirmed historical 935 dimension. Local remeshing
should target this annulus and retain a two-way bound against the original
PicoGK export, followed by a fresh volume audit and native OpenFOAM
`checkMesh`.

An independent Gmsh 4.15.2 frontal 3D volume trial (`Mesh.Algorithm3D=4`)
used the same 888,020-triangle PLC and unchanged size settings as the
Delaunay trial. It reached the 900-second execution limit while meshing and
was terminated with exit code 124. It wrote **no volume mesh**, so there is
no boundary or cell-quality audit for this candidate. This result measures
only the failure to complete within that local time limit.

From the repository root, reproduce the numerical face audit with:

```sh
src=twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028
mesh=work/935-original-bound-facet-sweep-20261028/prepared-005/gmsh-volume/fluid.msh
weak=work/935-original-bound-facet-sweep-20261028/weak-005/weak-cells.npz
uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 \
  python "$src/audit_original_bound_wall_faces.py" "$mesh" "$weak" \
  work/935-fluid-relocate-20261028/original-bound-wall-face-audit-v2.json
```

The output path must be fresh. The diagnostic report and point map remain
private because they derive from restricted geometry; only aggregate counts
and methods are committed publicly. No airflow, fitment or manufacturing
claim follows from this diagnostic.

The [private diagnostic archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-original-bound-wall-diagnostic-20261028.tar.zst)
contains the face-audit report, two-view weak-cell map, frontal trial source,
termination receipt and full log. Its SHA-256 is
`255b258b40ec4cb0599b22b85aef3bc6a1e30967bf0de52db41e75504699a490`,
matching the GitHub release digest after a local archive integrity check.
