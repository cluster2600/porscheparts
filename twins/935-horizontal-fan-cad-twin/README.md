# 935 horizontal fan — top-down CAD twin

Started 2026-11-06 after the owner's decisions:

- **Goal:** two flat (horizontal) fans: the original 935 fan rebuilt
  faithfully from the scan, and a new horizontal fan for the 993 in the
  spirit of Gunther Werks' flat-fan cars (our own design, not a copy).
- **Scale:** one scan unit is one millimetre, declared by the owner
  ([`H-SCALE`](hypotheses.json)). Owner declaration, not an instrument
  calibration.
- **Method:** feature-based CAD fitted to the scan, top-down, as for the
  935 head twin (in progress on branch `claude/935-cad-twin-20261106`). The bottom-up triangle
  repair and mesh-trial line is frozen; see
  [the freeze record](../../docs/research/935-horizontal-cooling/REFRAME_20261106.md).

Git holds the code, the fitted numbers and the deviation statistics. The
scan, meshes and STEP files stay private (`work/`, private releases).
The original scans come from the private release `reconstruction-20261005`
(`935-original-scans-20261005.tar.gz`, SHA-256
`69f0a58a6cce33cbdba18fcf4ded8322f27d198e511a685c95e7b8f4c85f31a6`).

## What the scan shows, in millimetres

A thin-walled revolved hub with nine blades:

| feature | fitted value | quality |
|---|---|---|
| datum A, front flange face (bolt circle) | plane, z = 0 | 0.104 mm RMS |
| hub bore | Ø 22.62 mm | 0.164 mm RMS |
| outer drum, upper band | Ø 178.58 mm | 0.137 mm RMS |
| outer drum, lower band | Ø 176.89 mm (slight draft or back misregistration) | 0.135 mm RMS |
| rolled lip top | z = 32.56 mm, about 2.7 mm across | — |
| blades | 9, root at the drum (r ≈ 89), tip r ≈ 135.5 (Ø ≈ 271 mm) | blades not fitted yet |
| overall hub height | z −45.2 to +33.2 mm | — |
| back pass misregistration | 0.27–0.69° tilt, 0.44 mm drum-centre shift | [`H-BACK-REGISTRATION`](hypotheses.json) |

The revolved hub profile ([`params/hub-profile.json`](params/hub-profile.json),
413 vertices, section 2,406 mm²) follows the observed surface with a mode
RMS of 0.076 mm. Non-revolved features (two lugs under the flange, eight
bolt bosses on datum A, two kidney windows) and the blades are fitted
separately in the next steps.

## Pipeline

| step | program | output | state |
|---|---|---|---|
| 1 frame | [`fit_frame.py`](source/fit_frame.py) | [`params/frame.json`](params/frame.json) | done |
| 2 revolved hub profile | [`fit_hub_profile.py`](source/fit_hub_profile.py) | [`params/hub-profile.json`](params/hub-profile.json) | done; residual bumps where bolt bosses and lugs sit on datum A and the back face |
| 3 local features (lugs, bosses, windows, bolt circle) | `fit_features.py` | `params/features.json` | next |
| 4 blade, fitted on all nine blades pooled | `fit_blades.py` | `params/blade.json` | next |
| 5 build123d model | `build_cad.py` | private STEP/STL | next |
| 6 independent scan-to-CAD scorecard | `score_twin.py` | `params/scorecard.json` | next |
| 7 new 993 flat fan from the fitted 935 baseline | new part | catalogue record | after 6 |

Progress is measured as the share of scan area within tolerance of the CAD,
not by the number of studies.

## Reproduce

```sh
VENV=work/flat-fan/venv   # numpy 2.5.4, scipy 1.18.1, scikit-image, matplotlib
SRC=twins/935-horizontal-fan-cad-twin/source
OBJ=work/flat-fan/private/input/rotor-original.obj   # from the private release above
$VENV/bin/python $SRC/fit_frame.py $OBJ work/flat-fan/private/cache twins/935-horizontal-fan-cad-twin/params/frame.json
$VENV/bin/python $SRC/fit_hub_profile.py $OBJ work/flat-fan/private/cache twins/935-horizontal-fan-cad-twin/params/hub-profile.json
```

Both programs refuse a scan whose SHA-256 differs from the pinned one.

Nothing here establishes a historical dimension of a particular 935 beyond
this scan, a fit to an engine, or permission to manufacture.
