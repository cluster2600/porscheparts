# 935 lower flange: PicoGK feature witnesses

The [lower-flange scan audit](DRIVE_LOWER_FLANGE_20261028.md) located eight
candidate outer openings in two axial bands of the observed drive. This step
turns those fitted sidewall locations into **parametric PicoGK witness
surfaces**. The witness shells are geometric markers for registration and
comparison; they are not the body of the flange, an adapter, bolts, or any
manufacturing geometry.

## Native construction

The [PicoGK source](../../../twins/935-horizontal-cooling-system-f0/source/picogk-flange-witness/Program.cs)
pins the private `lower-flange.json` report with SHA-256
`da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c`
and the observed drive SHA-256
`fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35`.
For each of eight openings, it linearly interpolates the two fitted XY centres
and radii across Z = −190 to −170 source units. An implicit annular shell of
±0.4 source unit around each fitted wall becomes a separate PicoGK voxel mesh.
The 0.25 runtime voxel size and 1 source unit = 1 PicoGK mm are **computational
assumptions**, not a physical scale calibration or wall specification.

With the private report restored to its recorded path:

```sh
mkdir -p work/935-flange-witness-20261028/build
/Users/maxime/.local/bin/dotnet build \
  twins/935-horizontal-cooling-system-f0/source/picogk-flange-witness/FlangeWitness.csproj \
  -p:PicoGKAssembly=/Users/maxime/Developer/PicoGK/runtime/PicoGK.dll \
  -p:BaseIntermediateOutputPath="$PWD/work/935-flange-witness-20261028/build/obj/" \
  -p:OutputPath="$PWD/work/935-flange-witness-20261028/build/bin/"
DYLD_LIBRARY_PATH=/Users/maxime/Developer/PicoGK/runtime \
  /Users/maxime/.local/bin/dotnet \
  work/935-flange-witness-20261028/build/bin/FlangeWitness.dll \
  work/935-drive-flange-review-20261028/audit-001/lower-flange.json \
  da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c \
  work/NEW/native
```

Use a fresh private output and build directory for each rerun. The tested
native runtime reported PicoGK Core Library 26.2.0. It generated eight
individual STLs and a combined 221,304-triangle STL. The combined mesh
SHA-256 is
`479e2c5d129d37a5821dbbda59695f5910facda97492a47571787fd32f5ec769`;
the construction receipt SHA-256 is
`f6304f013e73a86d1604b3ae7ded76fde09e85830be3f606cb6da068ad65fdd7`.

## Independent geometry review

The [reviewer](../../../twins/935-horizontal-cooling-system-f0/source/review_flange_witness.py)
checks the pinned scan and report, reads all eight native STLs independently,
and confirms exact vertex order and coordinates in the combined native STL.
It found no zero-area triangle. It also checks the radial location of the
generated shells and the acquired sidewall centroids against the interpolated
fit, and renders an overlay.

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/review_flange_witness.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/935-drive-flange-review-20261028/audit-001/lower-flange.json \
  work/NEW/native work/NEW/review
```

Across the eight native meshes, the largest 95th-percentile distance from a
generated shell vertex to its prescribed analytic shell is 0.0053 source unit.
The largest 95th-percentile radial discrepancy of the acquired sidewall
centroids is 0.259 source unit. One individual acquired point reaches 3.364
source units; the 95th percentile does not erase this outlier. The acquired
sidewalls are the **same scan used to derive the fits**. This comparison
checks implementation and local representation, not independent scan accuracy
or physical fit.

The [private overlay image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-flange-witness-overlay-20261028.png)
was visually inspected; its SHA-256 is
`6c1accc15231ad8acaad45c906650ffeb05c144e24bed414b06a56f2aa8e69dc`.
The [private archive of native geometry, receipts and review](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-picogk-flange-witness-20261028.tar.zst)
has SHA-256 `27044ec86a19585137e7715de237a8ad6c2c9410cb4dc5fedbb20258e14d63f2`,
matching the GitHub asset digest. The review report SHA-256 is
`36e76b5b36e49bf0b4322b3e0b109b8076c98af327800ca21605caad9d987f6a`.
All derived meshes stay outside public Git.

## Assembly boundary

The witness geometry supplies eight reproducible candidate wall locations in
the drive's provisional frame. It does not determine the flange body, hole
through condition, thread, fastening method, opposing engine/support face,
scale, axial stack or load path. The next assembly task is to identify and
measure that opposing face and register its openings against these eight
candidates. No functional PicoGK mount or manufacturing release follows from
this checkpoint.
