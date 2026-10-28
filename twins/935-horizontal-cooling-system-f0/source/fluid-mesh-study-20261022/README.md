# 935 fluid-mesh diagnostics

These dated recipes continue the root README chain after PicoGK geometry checks.
They preserve failed candidates and never grant CFD or manufacturing acceptance.
The [study report](../../../../docs/research/935-horizontal-cooling/FLUID_MESH_CORRECTION_20261022.md)
and its checkpoint identify the actual runs. Geometry and native cases require
access to the private archive; no raw scan or mesh belongs in this directory.

Use the existing scientific Python environment, without `-O`, with the F0 source
directory on `PYTHONPATH`. NumPy and SciPy serve preparation and complete volume
audits. VTK 9.6.2 is needed only for the independent native-cell readback.
There are no new Python dependencies or solver images.

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
STUDY="$PYTHONPATH/fluid-mesh-study-20261022"

# A completed native meshing case, including its failed full-quality log:
python "$STUDY/capture-snapshot-001.py" "$NATIVE_SNAP_CASE" "$NEW_SNAPSHOT"
python "$STUDY/export-fluid-plc-005.py" "$NEW_SNAPSHOT" "$NEW_PLC"

# After the exact closed-surface check and bounded native mesher execution:
python "$STUDY/audit-tetgen-002.py" "$NEW_PLC" "$MESHED" "$NEW_AUDIT"

# After native conversion and patch restoration, independently read every cell:
python "$STUDY/verify-native-mesh-003.py" "$NATIVE_CASE" "$NEW_AUDIT" "$NEW_VERIFICATION_JSON"
python "$STUDY/diagnose-native-tets-002.py" "$NATIVE_CASE" "$NEW_DIAGNOSTIC_JSON"
```

Output paths must be fresh. The archived bounded runner supplies the native
execution receipt, verifies the exact-predicate surface checker and limits
TetGen to 8 GiB and 600 s. The two tested switches are `-pYq1.4MzCf` and
`-pYq1.2/10O5MzCf`; both remain rejected for CFD. The actual Foundation 13
conversion runner, rootless command, source hashes and unchanged quality
dictionary are preserved in the same archive. Do not substitute an OpenCFD
image or infer named patches from TetGen's encounter order.

`export-fluid-plc-005.py` accepts bounded **ASCII** lists, preserves every original
boundary polygon vertex and triangulates nonplanar polygons with native-style
face-centre fans. It does not silently correct intersections. The exact CGAL
closed-surface check is mandatory before meshing. Its ordinary header cap is
two million; the independent tetrahedral-face reader explicitly allows ten
million. Reproducing preparation with version 005 changes no NPZ/OBJ/PLC bytes
relative to version 004; the private reproduction receipt records all hashes.

`audit-tetgen-002.py` reuses the existing exact-orientation and indexed-connectivity
helpers, binds reference bundle/input hashes, and verifies the full boundary
coordinate/triangle/**marker** bijection. It does not claim that positive tets
pass finite-volume quality. The import verifier independently compares all
coordinates, cell connectivity and named patch markers to these audited arrays.

`diagnose-native-tets-002.py` reconstructs native cell centres, internal-face
area tensors and non-orthogonality for tetrahedral meshes. It asserts exact
agreement with the native reported failure counts before publishing its
diagnostic. This is a diagnosis of the supplied native mesh, not a mesh repair.

Two explicitly rejected experiments are retained:

- `split-boundary-tets-001.py` subdivides only cells with multiple boundary faces.
  Its unit-tetrahedron exact-partition self-check runs before actual input, and
  the complete volume audit follows. Native quality worsens after subdivision.
- `cfd_skin_simplify.cpp` derives from the existing quality-preserving CGAL
  simplifier, adding CGAL 6.2.1's `Polyhedral_envelope_filter`. Compile using the
  frozen native headers/libraries and `-std=c++17 -O2 -frounding-math`, with
  assertions enabled. Run `--self-test` before the **millimetre** OFF input.
  A separate complete bidirectional checker is still required. The resulting
  skin passes that geometric bound but worsens the native CFD mesh.

Focused software verification:

```sh
python -m unittest discover -s tests -p test_935_fluid_mesh_boundary.py -v
```

The synthetic tests exercise strict list headers, winding classification,
exact positive volume, marker rejection and reference-input tampering. The
actual native runs provide additional complete-mesh checks; no synthetic
fixture is passed off as the measured rotor.
