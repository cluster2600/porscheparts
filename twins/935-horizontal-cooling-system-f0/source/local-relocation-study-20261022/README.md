# Executed local-relocation and graded-mesh sources

These are dated experiment sources with their recorded private paths and input
hashes. They reuse the existing PicoGK-derived master, composition helpers,
serialization checks and native runtimes. They are not a new general meshing
API. Keep Python assertions enabled; never replay over preserved outputs.

1. `propose-relocation-001.py` is the unchanged first executed source, reducing
   46 poor facets to seven. `surface_relocation.py` extracts its two functions
   without changing their ASTs. Shared tests cover independent local controls.
2. `check-relocation-bounds-001.py` runs the frozen native checker on that
   complete OFF against both original and retained-reference surfaces.
3. `verify-relocation-exchange-002.py` preserves the original int64-exchange
   refusal, creates an int32 bundle in a fresh directory, and checks every
   OFF/NPZ/STL coordinate and face. The earlier failed output is an input to
   its byte-identical STL replay, not something to delete before replaying.
4. `propose-relocation-002.py` performs one smaller pass, removes the remaining
   seven poor facets, and verifies the complete STL exchange. Its helper is
   supplied by this folder. `check-relocation-bounds-002.py` performs the two
   complete independent geometric certifications.
5. `graded_size.py` defines the nodal isotropic size field. The nearest-vertex
   definition is explicit; it is not a continuous wall-distance oracle.
6. `prepare-graded-control-001.py` builds the marked analytic unit tetrahedron.
   `run-graded-tetgen-001.py PREPARED NEW_OUTPUT` executes the frozen native
   mesher with the MTR field. `audit-graded-control-001.py` checks every output
   boundary point against the analytic planes and every cell determinant,
   with the exact serialized volume compared to 1/6.
7. `prepare-graded-fluid-001.py` runs from the repository root on the Mac,
   checks the certified surface exchange, reuses the frozen composition helper,
   and writes the new PLC plus size field. The native runner's 8 GiB / 600 s
   process-group limits apply before execution. Its boundary may be retriangulated;
   the output is not admitted without an independent complete surface proof.
8. `diagnose-graded-native-001.py MESHED NEW_CASE` intentionally performs only
   native diagnostic conversion and the unchanged full mesh-quality command.
   It does not pretend to hold the exact-boundary audit required by the old
   converter. All new geometry/volume/CFD admission flags remain false.
9. `render-relocated-rotor-002.py` shows all actual surface triangles from the
   hash-bound, certified second proposal. The image is private and not a flow
   or stress result.

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python -m unittest discover -s tests -p test_935_surface_relocation.py -v
```

Mac execution uses the existing scientific environment with NumPy, SciPy,
Trimesh and VTK. Native scripts retain `/home/lolman` paths; the archive supplies
the recorded private inputs. The [report](../../../../docs/research/935-horizontal-cooling/LOCAL_RELOCATION_20261022.md)
and [checkpoint](../../../../docs/research/935-horizontal-cooling/local-relocation-20261022.json)
bind versions, source hashes, bounds, observations and private preservation.
The root software chain and original full-system acceptance criteria remain
authoritative; no part fitment, physical or manufacturing qualification follows.
