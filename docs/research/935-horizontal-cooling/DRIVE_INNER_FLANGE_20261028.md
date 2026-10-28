# 935 drive: inner flange surface-opening candidates

The [outer flange audit](DRIVE_LOWER_FLANGE_20261028.md) identified eight small
openings on the observed drive. A separate inspection of the same scan shows
eight larger circular-looking interior recesses in a higher axial band. This
checkpoint fits those **observed surface features** and compares their fitted
ring with the outer ring. It does not assign either ring a mounting role.

The [audit source](../../../twins/935-horizontal-cooling-system-f0/source/audit_drive_inner_flange.py)
checks the private drive STL SHA-256
`fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35`
and the earlier outer report SHA-256
`da8093bb6c71cd364035dfcf5ced88732062a108c0a8af2ead21e6b111900c3c`.
It selects acquired sidewall face centroids in radial range 22–50 source
units and two Z bands. Eight visually seeded local circles are robustly fitted
after radial clipping; the resulting centres are fitted to one ring per band.
Synthetic ring and opening fixtures run before the private scan is read.

| Z band, uncalibrated source units | Inner ring centre XY | Inner radius | Inner diameter | Ring radial RMS | Largest departure from 45° spacing | Inner/outer radius ratio |
|---|---|---:|---:|---:|---:|---:|
| −175 to −170 | (99.302, 2.086) | 39.259 | 78.517 | 0.517 | 1.705° | 0.6774 |
| −170 to −165 | (99.337, 1.667) | 38.923 | 77.847 | 0.067 | 0.176° | 0.6716 |

The lower band is visibly contaminated by neighbouring walls and has a much
larger ring residual. The upper band is a stronger **geometric candidate**,
not an accepted nominal dimension. Its eight fitted local arcs retain
551–927 face centroids each, cover 213–343° per opening, and have clipped
radial RMS residuals up to 0.203 source unit. The inner and outer fitted ring
centres differ by 0.071 and 0.271 source unit in the two comparisons. These
are correlated observations from one open scan. They cannot establish
coaxiality tolerance, scanner accuracy, blind-versus-through condition,
threads, bolts, or a mating part. The contours change substantially with Z;
one fixed circular cylinder would misrepresent the whole axial feature.

The [private overlay image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/inner-flange.png)
has SHA-256 `73d29186ce129d21255539316c1fe21f231d0c8287e862f31f2b60bd44aff0ce`.
The [private report and image archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-inner-flange-audit-20261028.tar.zst)
has SHA-256 `49edd40e6689a06835eca08405a80011ca5410edce50c034c28ab2c4b4e79d40`;
the report SHA-256 is
`83b48412b7b32aadca894713f26e6e4f4f4aa01da29f50a9bca7c6ba49660112`.
The archive passed `zstd -t`. No source scan or derived mesh is committed to
public Git.

To reproduce from the repository root, restore the private inputs to their
recorded paths and choose a fresh private output directory:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/audit_drive_inner_flange.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/935-drive-flange-review-20261028/audit-001/lower-flange.json \
  work/NEW/inner-flange-audit
```

This adds a second observed ring to the drive's interface inventory. The
opposing 935 engine/support face, two independent same-part calibration
dimensions, and the function and axial termination of these recesses are
still needed before a functional PicoGK mount can be defined.
