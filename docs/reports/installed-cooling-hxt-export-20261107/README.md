# Installed cooling: HXT export and native mesh rejection

Refs #452. This follows the [native source audit](../installed-cooling-native-source-20261107/README.md).
The full-resolution source and its native ingestion remain unchanged. This is
software and mesh-diagnostic evidence, not physical qualification.

HXT with its default optimization reached the prescribed 180-second limit
without exporting a mesh. A separate trial disabled only optimization, with the
same two threads, 4 GiB sampled-memory limit, 5 mm sizing and audited boundary.
It completed in 19.98 seconds and exported 2,108,580 tetrahedra. In-memory checks
found positive volumes and preserved all original coordinates and eight boundary
triangle sets. Those checks did not establish export fidelity or mesh acceptance.

Independent readback of the actual ASCII MSH2 export found 719,636 changed
coordinate components among the 459,068 original vertices. All equal the source
rounded to 16 significant decimal digits; the maximum change is
5.551115123125783e-17 metres. The exact-coordinate criterion rejects this export;
no tolerance was substituted.

The real OpenCFD 2406 `gmshToFoam` conversion completed. Standard `checkMesh`
failed two checks and extended checks failed seven, including 204,403
low-determinant cells, 16,568 high-aspect-ratio cells, 259 skew faces and 578 cells
flagged as concave. The native face-tet diagnostic reports 37 faces but writes a
21-face set; both counts are preserved rather than silently reconciled. A zero
process exit status did not mean acceptance. Raw mesh and failed sets remain in
the private Docker volume; the three native logs here are byte-for-byte copies.

## Export correction

[write_exact_msh.py](write_exact_msh.py) retains Gmsh's original export and writes
a separate MSH2 file. It preserves node numbering and every non-node section,
checks that the native node rows match the live values rounded to 16 significant
digits, and writes those same live values with 17 digits. It does not move nodes,
repair cells, optimize geometry or alter connectivity.

The native Gmsh 4.15.2 HXT unit-cube control independently rereads all live node
values exactly after correction, with all boundary triangles preserved and 53
positive tetrahedra summing to one cubic metre. Five coordinate components needed
the correction. All non-node sections match the retained original export exactly.
Run the small writer regression with:

```sh
python -m unittest discover -s docs/reports/installed-cooling-hxt-export-20261107 -p 'test_*.py'
```

The version-matched [Gmsh HXT implementation](https://raw.githubusercontent.com/live-clones/gmsh/gmsh_4_15_2/src/mesh/meshGRegionHxt.cpp)
passes `mesh.optimize` independently of refinement to HXT. Disabling it is a
useful diagnostic but the resulting native failures rule out adopting that mesh.
The [machine-readable results](result.json) retain source-receipt hashes. A
separate longer optimized trial is not included in this report until it has a
terminal result and independent checks. No flow solver was started for this work.
