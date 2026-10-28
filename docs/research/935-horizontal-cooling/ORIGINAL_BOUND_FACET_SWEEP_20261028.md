# 935 original-export-bounded rotor: local facet and fluid-mesh sweep

This experiment changes only the local triangulation of the closed 935 rotor
analysis surface. It compares three CGAL short-edge limits with the unchanged
outer fluid duct. The rotor input is the 871,078-face candidate bounded by
the original PicoGK export, SHA-256
`d2e86b89afe854ea4107cac170fdba7d5e73a40648c3a704dfd9ab6b5b1687e2`.
The checker reference is the complete 1,322,970-face original PicoGK export,
SHA-256 `e374fc2f850645efb6db4854a4355f541a9617833b827a6cff52d24929757587`.
This certificate is **not** a bound to the raw scan or a dimensional
calibration. The 0.5 mm and 0.21 mm filename numbers are measured accuracies,
not OBJ units.

## Surface experiment

The dated [`repair_poor_facets.cpp`](../../../twins/935-horizontal-cooling-system-f0/source/surface-facet-repair-20261022/repair_poor_facets.cpp)
was copied unchanged into private `work/`. Its CMake file was copied with
Boost changed from the original exact 1.90.0 requirement to the installed
1.92.0; CGAL remained 6.2.1. The AppleClang build used `-O2`, and its analytic
self-test passed. The complete tiled-envelope check also passed its analytic
controls. All three candidate surfaces remain closed, consistently oriented,
single-component meshes with Euler characteristic −10 and positive volume.

| CGAL edge limit, source units | Rotor faces | Poor faces, from 189 | Complete two-way 0.0225-unit envelope |
|---:|---:|---:|---|
| 0.001 | 871,060 | 171 | pass |
| 0.005 | 871,018 | 129 | pass |
| 0.020 | 870,922 | 46 | pass |

The three candidate OFF SHA-256 values, in row order, are
`b7e07e8dc790dd411494f17480c2550ca370db6fc38342dd832db44c724e0086`,
`8360724ad4d6542329f156f813a41403070b57d8a92be3a7f830be44f13fe292`
and `1cc284f5dbbd8ae574984c4e9a612605706b036831145e8f4528d7545783bd6e`.
Each complete envelope includes a 0.0025-unit numeric reserve. The bounds
preserve proximity to the original PicoGK *export*, not historical blade
accuracy or a measured fit.

## Fluid-volume comparison

[`prepare_original_bound_facet_fluid.py`](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/prepare_original_bound_facet_fluid.py)
requires each candidate's frozen hash, the corresponding successful envelope
certificate, the original export and the same parent duct. It preserves the
outer boundary and its three markers, reverses the closed rotor surface to
form the fourth wall, and checks the closed fluid PLC. Gmsh 4.15.2 then uses
the same Delaunay settings for each candidate. The independent
[`audit_fluid.py`](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/audit_fluid.py)
confirmed every wall triangle and marker by coordinate, with maximum surface
node displacement below `1e-16 m` and no zero or negative-volume tetrahedra.

| Rotor | Fluid tetrahedra | Mean ratio < 0.01 | Mean ratio < 0.05 | CFD decision |
|---|---:|---:|---:|---|
| unchanged original-bound candidate | 5,115,243 | 1,459 | 2,043 | rejected |
| 0.001 repair | 4,517,426 | 1,500 | 2,228 | rejected; worse |
| 0.005 repair | 4,651,098 | **1,426** | **1,954** | rejected; best of these trials |
| 0.020 repair | 4,552,332 | 1,431 | 1,991 | rejected |

The best trial improves the sub-0.01 count by 33 cells, or 2.3%, against the
unchanged original-bound volume. The ordering is not monotonic with surface
facet quality. The [weak-cell locator](../../../twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028/localize_original_bound_facet_weak.py)
found that all 1,426 weak cells touch a rotor-wall node and none touches the
outer duct. 1,227 weak-cell centres lie at conditional radius 70–100 mm, near
the inner annulus and blade roots. This is a location association, not proof
that the rotor surface alone causes the bad volume cells.

None of these volumes meets the quality gate for CFD. No pressure, flow,
torque, temperature or mechanical conclusion follows from this trial. The
duct shape and 1 source unit = 1 mm conversion remain hypotheses.

## Reproduction and evidence

The inputs, three CGAL outputs, full two-way envelope stdout/stderr,
hash-pinned PLC receipts, Gmsh volumes, independent audits and weak-cell data
are private geometry and remain outside public Git. The source paths and
commands below are run from the repository root; each output name must be
fresh. The CMake copy records the Boost 1.92.0 substitution.

The [private complete trial archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-original-bound-facet-sweep-20261028.tar.zst)
has SHA-256 `f7617c4e65f6b00555ef9a0e30205f9c1461d2d14daae4beb4ab425663124242`.
It passed a local `zstd -t` integrity check and retains the mesh and audit
results for all three limits plus the refined-size trial.

```sh
source_dir=twins/935-horizontal-cooling-system-f0/source
trial=work/935-original-bound-facet-sweep-20261028
rotor=work/935-analysis-volume-20261022/kali-receipts/quality-surface-001/candidate-quantized.off
original=work/935-analysis-volume-20261022/reference/original.off
mkdir -p "$trial/source"
cp "$source_dir/surface-facet-repair-20261022/repair_poor_facets.cpp" "$trial/source/"
sed 's/Boost 1.90.0 EXACT/Boost 1.92.0 EXACT/' \
  "$source_dir/surface-facet-repair-20261022/CMakeLists.txt" > "$trial/source/CMakeLists.txt"
cmake -S "$trial/source" -B "$trial/build" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS_RELEASE=-O2
cmake --build "$trial/build" -j2
ctest --test-dir "$trial/build" --output-on-failure
# Repeat for limits 0.001/0.005/0.02 and fresh numbered output files.
"$trial/build/repair_poor_facets" "$rotor" "$trial/candidate-limit-005.off" 0.005
work/935-corrected-analysis-20261025/mac-checker-001/tiled-envelope \
  "$original" "$trial/candidate-limit-005.off" > "$trial/envelope-limit-005.stdout"
uv run --no-project --python 3.12 --with numpy==2.5.4 --with scipy==1.18.1 \
  --with trimesh python "$source_dir/gmsh-fluid-study-20261028/prepare_original_bound_facet_fluid.py" \
  005 "$trial" "$trial/prepared-005"
uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 \
  python "$source_dir/gmsh-fluid-study-20261028/generate_fluid.py" \
  "$trial/prepared-005/boundary.npz" "$trial/prepared-005/gmsh-volume"
uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 \
  --with scipy==1.18.1 python "$source_dir/gmsh-fluid-study-20261028/audit_fluid.py" \
  "$trial/prepared-005/boundary.npz" "$trial/prepared-005/gmsh-volume/fluid.msh" \
  "$trial/prepared-005/gmsh-volume/audit.json"
```

An additional `refined` mode used the same 0.005 repaired wall and changed
only Gmsh's conditional `Mesh.MeshSizeMin` from 0.002 m to 0.001 m. It
again produced 984,724 nodes and 4,651,098 tetrahedra, with exactly 1,426
cells below mean ratio 0.01 and 1,954 below 0.05. Its output file has a
different SHA-256 (`1d259df0ad98cd24503be486eaac5d3c890f03fc53f972031a51a0426a0181eb`),
so this is equality of the reported counts and quality statistics, not a
claim of byte-identical meshes. This size-floor change did not improve the
measured quality gate. Reproduce it by adding `refined` as the fourth
argument to `generate_fluid.py` for the 0.005 PLC and auditing the fresh mesh.

The next route must improve near-wall *volume* topology while retaining the
bounded rotor, then pass the unchanged native OpenFOAM quality checks before
a flow solve. Historical 935 mounting datums, rotor/shaft torque transfer,
physical scale and shroud passages remain open.

## Software checks

The CGAL analytic self-test, three complete two-way envelope checks, four
Gmsh volume runs, four independent volume audits and a weak-cell locator
replay completed. The locator replay reproduced the same report SHA-256
`4e3cc545eb0e951a5dad212bca27bff7f27e9a0181415858992931b8de75bfd8`.
Python syntax checks passed and the strict documentation checker found zero
broken links. The full Mac `make check` ran 4,969 tests with the existing
Mac baseline of five failures, 44 errors and 457 skips. Linux CI is the
merge gate; no native OpenFOAM `checkMesh` or flow solution was run on these
already-rejected volumes.
