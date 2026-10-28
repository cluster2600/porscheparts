# 935 drive: lower-flange opening pattern candidate

The observed drive scan contains a circular lower flange. Four-view depth
projections and four local axial slices show eight small round surface
openings around its outer edge, plus larger openings farther inboard. This
checkpoint audits **only the eight outer openings**. It does not identify the
flange's mating component or define a mounting pattern.

The input is the pinned private observed-drive STL with SHA-256
`fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35`.
Its coordinates are uncalibrated source units. The
[audit program](../../../twins/935-horizontal-cooling-system-f0/source/audit_drive_lower_flange.py)
uses eight visual XY seeds and selects acquired face centroids within 4.5
source units of each seed. It retains sidewalls with absolute geometric-normal
Z below 0.7 in two non-overlapping Z bands, −190 to −180 and −180 to −170.
Each opening is fitted separately by robust radial least squares. A circle is
then fitted to the eight resulting centres in each band. Synthetic circle and
eight-point fixtures pass before the real scan is read.

| Z band, source units | Fitted outer-circle centre XY, source units | Radius, source units | Diameter, source units | Radial RMS, source units | Largest departure from 45° spacing |
|---|---|---:|---:|---:|---:|
| −190 to −180 | (99.279, 2.153) | 57.956 | 115.912 | 0.076 | 0.294° |
| −180 to −170 | (99.283, 1.932) | 57.952 | 115.904 | 0.043 | 0.181° |

The individual acquired sidewall fits use 459–2,944 face centroids per
opening and band. Angular coverage ranges from 214° to 359° in the lower
band and from 223° to 359° in the upper band. The fitted opening radii span
2.570–2.800 and 2.511–2.718 source units respectively. The two band fits
have nearly the same outer-circle radius, but their centres differ by about
0.221 source unit, mostly in Y. These are correlated samples of the **same
scan**, not two independent measurements. Their deviations cannot be used as
machining tolerances, a coaxiality specification, or scanner uncertainty.

The [private report, fitted-pattern image and wider context projections](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-drive-lower-flange-20261028.tar.zst)
were inspected visually and saved with archive SHA-256
`a3f80da0e98a7ddd562e16cb005c6168cdff4cb5f6ec4eca5b4ecae0548c5eb3`,
matching the GitHub asset digest. The detailed report SHA-256 is
`da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c`;
the fitted-pattern image SHA-256 is
`b5b9734e8157adae4b75ec007d910dda75cac4938663bade18d117e79a9c96bf`.
No scan mesh is committed to public Git.

Reproduce with the private input restored to the recorded path and a new
private output directory:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/audit_drive_lower_flange.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/NEW/lower-flange
```

The eight seeds came from a visual projection and do not prove that there are
only eight openings elsewhere. The inward larger openings are not classified.
A fitted circle through selected surface patches does not prove through-holes,
threading, fastener size, mating-face flatness or structural load path. It
cannot set a physical pitch-circle diameter until the drive's source-unit
scale is independently calibrated. The next assembly check needs an acquired
opposing engine/support face and two same-part dimensions, followed by direct
hole-to-hole registration and axial-stack inspection. This candidate is not
yet used to generate a functional PicoGK mount.
