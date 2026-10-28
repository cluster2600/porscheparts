# 935 horizontal cooling: original-export-bounded assembly checkpoint

This checkpoint replaces the earlier root-0.7 demonstration rotor in the
four-component PicoGK inspection assembly with the analysis rotor bounded by
the original PicoGK export. It is a **packaging study**, not a reconstruction
of an installed 935 cooling system. The six-cylinder engine envelope and
shroud are generated hypotheses. The drive pose is unverified. The source
coordinates are not calibrated to millimetres.

## Reproducible chain

The private OFF input is `work/935-analysis-patches-20261022/surface-001/candidate-quantized.off`
(SHA-256 `d2e86b89afe854ea4107cac170fdba7d5e73a40648c3a704dfd9ab6b5b1687e2`).
The public original-export containment certificate is
[`analysis-mesh-20261022.json`](analysis-mesh-20261022.json), SHA-256
`1fbf62bf1e8c5cbeb5d84dda583c7e674ce0a2db86b8196e3ad6177df5cf9728`.
The parent PicoGK assembly receipt has SHA-256
`104c0155a246d6acb04ca83e66988ccc3dcc345821db69349ab465bd0ec47b23`.
All private input hashes are checked before the new case is prepared.

From the repository root, with private inputs restored to their recorded paths:

```sh
mkdir -p work/935-original-bound-assembly-20261028
uv run --no-project --python 3.12 --with numpy==2.5.4 --with trimesh \
  python twins/935-horizontal-cooling-system-f0/source/prepare_original_bound_assembly.py \
  work/935-analysis-patches-20261022/surface-001/candidate-quantized.off \
  work/935-assembly-0p7-20261025/six-run-001 \
  work/935-original-bound-assembly-20261028/prepared-002
/Users/maxime/.local/bin/dotnet build \
  twins/935-horizontal-cooling-system-f0/source/picogk-assembly-refresh/AssemblyRefresh.csproj \
  -p:PicoGKAssembly=/Users/maxime/Developer/PicoGK/runtime/PicoGK.dll \
  -p:BaseIntermediateOutputPath="$PWD/work/935-original-bound-assembly-20261028/build/obj/" \
  -p:OutputPath="$PWD/work/935-original-bound-assembly-20261028/build/bin/"
DYLD_LIBRARY_PATH=/Users/maxime/Developer/PicoGK/runtime \
  /Users/maxime/.local/bin/dotnet \
  work/935-original-bound-assembly-20261028/build/bin/AssemblyRefresh.dll \
  work/935-original-bound-assembly-20261028/prepared-002/case.json \
  work/935-original-bound-assembly-20261028/native-002
```

Use a clean build output directory for each run. The absolute Mac paths above
identify the tested SDK and native runtime; substitute local paths on another
host without changing the source or case. The retained run used .NET SDK
10.0.402 and PicoGK native runtime 26.2.

The PicoGK assembly source is
[`picogk-assembly-refresh/Program.cs`](../../../twins/935-horizontal-cooling-system-f0/source/picogk-assembly-refresh/Program.cs).
The new preparer converts the certified OFF to STL with exact float32 triangle
readback. PicoGK then imports and composes the four meshes. The independent
[`review_refreshed_assembly.py`](../../../twins/935-horizontal-cooling-system-f0/source/review_refreshed_assembly.py)
checked every triangle in the native concatenation and in the GLB/USD exports.
The 12,151,174 triangles comprise 4,972,828 engine-envelope, 2,484,656
observed-drive, 871,078 rotor and 3,822,612 provisional-shroud triangles.
Native receipt SHA-256:
`b63b4830d028c3455e7e40e25180f62463057794148b380661483a02f8069a2b`.

The independent checks can be rerun with new output names (the reviewer
commands refuse to overwrite prior evidence):

```sh
source_dir=twins/935-horizontal-cooling-system-f0/source
case_dir=work/935-original-bound-assembly-20261028
receipt_sha=b63b4830d028c3455e7e40e25180f62463057794148b380661483a02f8069a2b
uv run --no-project --python 3.12 --with numpy==2.5.4 --with scipy==1.18.1 \
  --with trimesh --with usd-core python "$source_dir/review_refreshed_assembly.py" \
  review "$case_dir/native-002" "$receipt_sha" "$case_dir/exports-NEW"
uv run --no-project --python 3.12 --with numpy==2.5.4 --with python-fcl \
  python "$source_dir/review_surface_contacts.py" \
  "$case_dir/native-002" "$receipt_sha" "$case_dir/contacts-NEW.json"
uv run --no-project --python 3.12 --with numpy==2.5.4 --with python-fcl \
  python "$source_dir/review_rotor_sweep.py" \
  "$case_dir/native-002" "$receipt_sha" "$case_dir/sweep-NEW.json"
uv run --no-project --python 3.12 --with numpy==2.5.4 --with scipy==1.18.1 \
  --with trimesh --with vtk python "$source_dir/render_original_bound_assembly.py" \
  "$case_dir/native-002" "$case_dir/exports-NEW" "$case_dir/render-NEW"
```

## Surface and rotation checks

The independent [`review_surface_contacts.py`](../../../twins/935-horizontal-cooling-system-f0/source/review_surface_contacts.py)
found the following at the assumed pose. Distances are **uncalibrated source
units**, not measured millimetres or designed clearances.

| Surface pair | Result |
|---|---:|
| engine envelope / observed drive | intersection |
| engine envelope / rotor | 113.23615 units |
| engine envelope / shroud | 33.36651 units |
| observed drive / rotor | 3.83430 units |
| observed drive / shroud | 6.83367 units |
| rotor / shroud | 6.25830 units |

The [`review_rotor_sweep.py`](../../../twins/935-horizontal-cooling-system-f0/source/review_rotor_sweep.py)
checked 240 equally spaced rotor poses and bounded the motion between poses.
The lower surface-separation bounds over one rigid revolution are 1.95136
source units against the observed drive and 4.37637 against the provisional
shroud. Its fixture checks passed. This bound applies only to these surfaces,
the chosen rotation axis and their frozen relative pose. It does not check
occupied interiors, thermal growth, elastic deflection or a shaft-to-hub
connection.

The [private four-view render](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-assembly-review.png)
(SHA-256 `d93c642c91280dcc51ce288cc40f8d0c97c36f80cbffcf21a481f7f33e278931`)
was inspected visually. It shows the horizontal nine-region rotor above a
six-cylinder envelope, a lateral drive and the provisional shroud. The blade
surface remains irregular where the source scan was incomplete; the broad
shroud and simple engine banks are clearly design placeholders. VTK 9.7.1
required the generic `AddViewProp` API for the text overlays. The dedicated
[`render_original_bound_assembly.py`](../../../twins/935-horizontal-cooling-system-f0/source/render_original_bound_assembly.py)
provides that compatibility while the older hash-pinned reviewer stays frozen.

The [private geometry and receipt archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-original-bound-assembly-20261028.tar.zst)
has SHA-256 `54cb01f9343a63bc1a8366a6e0a603fa215afd3b9159f166c7c51e07d28af2c0`.
It contains the prepared case, native PicoGK assembly, GLB/USD exports,
surface-contact result and 240-phase sweep result. The archive passed a local
`zstd -t` integrity check. Failed preparatory attempts remain in the local
private work directory and are not part of this accepted checkpoint.

## Engineering status and next action

The original-export-bounded candidate is suitable for visual and geometric
inspection. It is **not** known to fit a 935. The drive/engine intersection
requires identification of the actual mounting surfaces and an aligned engine
reference. The rotor bore and drive shaft are separated in the current model;
the torque-transmitting feature, bearings and gear internals remain unknown.
The shroud outlet and engine flow network are not measured. Consequently no
CFD or FEA result from this assembly can establish historical airflow,
structural safety, printability or physical function.

The next geometric gate is to measure two independent same-part dimensions,
identify 935 engine mounting datums, and reconstruct the hub/shaft interface.
The private geometry and full receipts remain outside public Git. Every
qualification flag in the preparation and PicoGK receipts remains false.

## Software checks

The prepared rotor passed exact STL triangle readback, the PicoGK native
assembly completed, the independent export review preserved all 12,151,174
triangles, and the VTK 9.7.1 four-view render completed. The full repository
`make check` on this Mac ran 4,969 tests and reported five failures, 44 errors
and 457 skips. These are the same existing Mac baseline categories recorded
before this change; the new source was also syntax-checked and the strict
documentation link check found zero broken links. Linux CI is the publication
gate for this change.
