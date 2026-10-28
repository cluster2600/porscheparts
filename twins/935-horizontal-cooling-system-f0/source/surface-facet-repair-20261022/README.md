# Executed bounded surface-repair sources

These are byte-identical dated experiment sources. Existing helpers remain the
authoritative geometry, exact-orientation, kernel, TetGen, native conversion and
readback implementations. This folder does not introduce a second workflow API.
Private paths and failed attempts remain in the linked archive. Keep Python and
C++ assertions enabled and use fresh output paths for every replay.

1. `repair_poor_facets.cpp` and `CMakeLists.txt` build against the recorded CGAL
   6.2.1/Boost/MPFR headers. The retained build uses GCC 15.3, `-O2` without
   `NDEBUG`, and CGAL's `-frounding-math`. Native self-tests cover analytic
   qualities, poor-only classifiers and constrained tiny-edge repairs.
2. `run-facet-repair-005.py 0.02` replays the retained local repair on Kali1.
   Its 6 GiB address-space/2 GiB file limits and 300 s rotor deadline apply
   before the process starts. Existing/dangling outputs and malformed limits
   are refused. They are numeric resource limits, not design tolerances.
3. `quantize-and-bound-002.py` checks exchange, complete topology and independent
   bidirectional original/reference bounds using the frozen checker. Its
   single argument is the recorded attempt directory name, for example
   `limit-020-005`; it requires that attempt's `quantized` output to be absent.
4. `prepare-repaired-fluid-001.py` runs from the repository root in the existing
   scientific environment, including Trimesh. It checks the reference SI
   conversion and reuses `compose-reference-wall-001.py` unchanged.
5. The existing bounded TetGen runner creates the first, refused volume.
   `diagnose-added-boundary-point-002.py` diagnoses its unexpected split using
   arbitrary-precision integer cross products.
   `restore-repaired-fluid-edge-001.py` restores the original surface with the
   existing kernel-cone helper. The unchanged full volume auditor and native
   converter/readback then evaluate every cell and boundary marker.
6. `prepare-dual-cube-001.py` creates the synthetic native cube. Its initial
   readback parser failure and successful separate readback are preserved;
   the scientific native run is not repeated or overwritten.
   `check_cube_dual_002.py CASE FROZEN_ASCII_PARSER` checks the actual mesh
   instance, all analytic boundary planes, closed topology and unit volume.
7. `run-dual-combine-001.py INPUT_CASE NEW_OUTPUT_CASE` uses the qualified
   network-isolated Foundation 13 runtime. It requires a hash-bound native
   geometry readback, copies the input and retains its dictionary. It runs
   `polyDualMesh -overwrite -concaveMultiCells 30`, then
   `combinePatchFaces -meshQuality -concaveAngle 0.000001 0.000001`, then the
   unchanged full native quality check. The whole process group has a 600 s
   deadline, 10 GiB address-space and 2 GiB per-file limits. A zero native exit
   does not imply that the receipt's quality flag is true.
8. `render-local-repair-002.py` and `render-repaired-rotor-001.py` create the
   private inspection images from hash-checked actual geometry. The latter
   requires the existing VTK runtime. Neither image is a simulation field.

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python -m unittest discover -s tests -p test_935_surface_facet_repair.py -v
```

The [report](../../../../docs/research/935-horizontal-cooling/SURFACE_FACET_REPAIR_20261022.md)
and [checkpoint](../../../../docs/research/935-horizontal-cooling/surface-facet-repair-20261022.json)
identify the exact private inputs, outputs and retained/refused states. This
phase admits the bounded repaired surface only. Both real fluid volumes remain
refused for CFD; no manufacturing or physical validation is granted.
