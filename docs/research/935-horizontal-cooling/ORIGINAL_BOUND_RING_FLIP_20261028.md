# 935 original-export-bounded rotor: near-planar ring flips

This is an exploratory surface and fluid-volume correction on the 935
horizontal rotor. It starts from the 0.005 CGAL facet-repair surface,
SHA-256
`8360724ad4d6542329f156f813a41403070b57d8a92be3a7f830be44f13fe292`.
The [wall-face diagnostic](ORIGINAL_BOUND_WALL_DIAGNOSTIC_20261028.md)
localized many rejected fluid cells near radius 84–86 mm in a **conditional**
1 source unit = 1 mm scale. The radius and mounting dimensions are not
historically calibrated.

## Surface trial and admission

The [dated CGAL source](../../../twins/935-horizontal-cooling-system-f0/source/surface-ring-flip-20261028/ring_flip_trial.cpp)
selects face centres at conditional radius 83–87 mm. By default it permits one pass of
edge flips only: no vertex split, collapse, relaxation or projection.
It constrains edges whose two adjacent triangles deviate from one plane by
more than 0.001 source unit. The fixed values are trial settings, not
manufacturing tolerances. A replay built from the committed C++ source
produced the same output SHA-256 as the original trial.

| Surface | Vertices | Faces | Annulus faces with quality < 0.1 | Two-way original-export envelope |
|---|---:|---:|---:|---|
| 0.005 facet repair | 435,499 | 871,018 | 7,904 | pass |
| unrestricted one-pass flips | 435,499 | 871,018 | 2,834 | **fail; rejected** |
| near-planar constrained flips | 435,499 | 871,018 | 5,192 | pass |

The accepted-for-analysis near-planar candidate is SHA-256
`58991f3f74107dceaf64227a6034b7a700a92e4807e32ca188c0a0f4468f6476`.
Its vertex coordinate array is byte-identical to the input; it is closed,
consistently oriented, single-component and has Euler characteristic −10.
The complete two-way tiled checker against the original 1,322,970-face
PicoGK export passed the 0.0225-source-unit envelope with a 0.0025-unit
numeric reserve, including topology and self-intersection checks. The
certificate contains no measured-scan accuracy or fitment claim.

## Fluid-volume result

The same four-patch outer duct was recomposed from the near-planar rotor.
The PLC SHA-256 is
`394f201ce9cdb20760429f7db050eafe7415d4aa76a80c2133ac2f3711ca2c50`.
The committed preparation code reproduced this PLC byte for byte. Gmsh
4.15.2 Delaunay generated a new volume; the committed independent auditor
verified all boundary triangle coordinate sets and markers, with maximum
surface-node difference below `1e-16 m` and zero inverted or zero-volume
tetrahedra. One further interior-node relocation preserved those checks.

| Volume | Tetrahedra | Mean ratio < 0.01 | Mean ratio < 0.05 | Minimum mean ratio | CFD decision |
|---|---:|---:|---:|---:|---|
| Prior 0.005 surface | 4,651,098 | 1,426 | 1,954 | 4.22e-5 | rejected |
| Near-planar ring flips | 4,594,408 | 903 | 1,224 | 7.05e-11 | rejected |
| Ring flips, then one `Relocate3D` | 4,594,408 | **878** | **1,076** | **5.70e-5** | rejected |

The raw volume SHA-256 is
`edbea4908c1d8431e51977fd5a2300ab2687a491d41f6dcd79a47e6115644acd`;
the relocated volume SHA-256 is
`d6d8d11e980cd30e30583542d6a619c1337fdb054352b5744d4b74fed5df707b`.
The committed relocation source reproduced the latter byte for byte.

The raw ring-flip volume's extreme minimum is an internal near-coplanar
tetrahedron at conditional radius 89.38 mm; it has no complete rotor-wall
face. Relocation removes this extreme minimum and further reduces the weak
cell counts. The best volume still has 878 cells below 0.01, so it is **not
admitted for CFD**. No flow, pressure, torque or cooling conclusion follows.
The outer duct remains conditional; actual 935 engine passages, physical
scale and mounting datums remain unresolved. No physical fitment or metal
manufacturing is authorized.

## Two-pass comparison and rejection

The same source was replayed with the optional final argument `2`, keeping
the input surface, coplanarity limit and conditional ring unchanged. The
second-pass surface has the same 435,499 vertices and 871,018 faces; its
SHA-256 is
`f9a338ea90fd810537a2441872b5adf501489a6876c2684e552d4156bc62175e`.
The annulus face count below quality 0.1 falls further, from 5,192 to
4,351. It remains closed, single-component and consistently oriented. The
complete two-way export envelope passes again.

| Two-pass fluid volume | Tetrahedra | Mean ratio < 0.01 | Mean ratio < 0.05 | Minimum mean ratio |
|---|---:|---:|---:|---:|
| Gmsh Delaunay, SHA-256 `1af85154…` | 4,596,239 | 1,126 | 1,639 | 5.08e-5 |
| One `Relocate3D`, SHA-256 `c2bb6434…` | 4,596,239 | 1,110 | 1,424 | 5.08e-5 |

The full raw and relocated volume SHA-256 values, respectively, are
`1af85154edb0e06a9fcc0bd7bb7a728cf7fb70fd99597ed4dd0a025b4ad942ea`
and `c2bb643474b6157d9d308a0db03b6d38f9b8f7a6e46fa987c3de3b97a375e8dd`.

The two-pass PLC SHA-256 is
`5d5826fc6701c502003fd456e8dfa2b590bbb1551557f05c9c1a483837bd584f`.
Its four boundary patches and tetrahedral orientation pass the same
independent audit. The committed preparation code reproduced the PLC byte
for byte; the committed auditor reproduced the relocated quality counts.
The committed relocation source reproduced the relocated mesh byte for byte.
Both two-pass volumes are worse than the one-pass relocated volume on the
remaining weak-cell counts. **The two-pass candidate is rejected.** Better
surface triangle scores do not imply better fluid tetrahedra for this case.

The [private two-pass archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-ring-flip-two-pass-20261028.tar.zst)
retains the rejected surface, envelope certificate, PLC, both volumes,
audits and logs. Its SHA-256 is
`c80378c949791eee71782bdfb0360cfc34c3c927b5d1bf4c99eb0777bd3ef722`,
matching the private release digest after a local integrity check. To
reproduce it, pass `2` after the output OFF path in the C++ invocation below,
use `candidate-limit-two.off` and `envelope-limit-two.stdout` for the private
trial paths, and pass `two` to the PLC preparer. The later Gmsh and audit
commands are identical with the resulting `prepared-two` directory.

## Reproduction

The private input surface and complete export checker are retained in the
935 private release. The [private ring-flip study archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-ring-flip-study-20261028.tar.zst)
contains the accepted and rejected trial surfaces, complete checker log,
PLC, both volume meshes, audits and source receipts. Its SHA-256 is
`5c0e82eeb770264fa663f84e7e93fa5c37fa125aa660f2c6c383c569e39225c9`,
matching the private release digest after a local integrity check. Run the
following from the repository root with fresh output paths under `work/`:

```sh
src=twins/935-horizontal-cooling-system-f0/source
trial=work/935-original-bound-wall-diagnostic-20261028
cmake -S "$src/surface-ring-flip-20261028" -B "$trial/public-build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O2
cmake --build "$trial/public-build" -j2
"$trial/public-build/ring_flip_trial" \
  work/935-original-bound-facet-sweep-20261028/candidate-limit-005.off \
  "$trial/candidate-limit-flat.off"
work/935-corrected-analysis-20261025/mac-checker-001/tiled-envelope \
  work/935-analysis-volume-20261022/reference/original.off \
  "$trial/candidate-limit-flat.off" > "$trial/envelope-limit-flat.log"
tail -n 1 "$trial/envelope-limit-flat.log" > "$trial/envelope-limit-flat.stdout"
uv run --no-project --python 3.12 --with numpy==2.5.4 \
  --with scipy==1.18.1 --with trimesh \
  python "$src/gmsh-fluid-study-20261028/prepare_original_bound_facet_fluid.py" \
  flat "$trial" "$trial/prepared-flat"
uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 \
  python "$src/gmsh-fluid-study-20261028/generate_fluid.py" \
  "$trial/prepared-flat/boundary.npz" "$trial/prepared-flat/gmsh-volume"
uv run --no-project --python 3.12 --with gmsh==4.15.2 --with numpy==2.5.4 \
  --with scipy==1.18.1 python "$src/gmsh-fluid-study-20261028/audit_fluid.py" \
  "$trial/prepared-flat/boundary.npz" \
  "$trial/prepared-flat/gmsh-volume/fluid.msh" \
  "$trial/prepared-flat/gmsh-volume/audit.json"
uv run --no-project --python 3.12 --with gmsh==4.15.2 \
  python "$src/gmsh-fluid-study-20261028/relocate_original_bound_fluid.py" \
  "$trial/prepared-flat/gmsh-volume/fluid.msh" \
  "$trial/relocate-flat-001" --iterations 1
```

Audit the relocated mesh with the same `audit_fluid.py` command and its
fresh output path. Private trial outputs, the rejected unrestricted surface,
checker logs and full meshes are excluded from public Git. The next work is
to remove the remaining rotor-wall-adjacent weak cells while retaining this
two-way export bound, then run native OpenFOAM `checkMesh` before any CFD
solve. A bounded export is still not a bound to the raw scan.
