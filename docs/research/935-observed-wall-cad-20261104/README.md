# Source-supported 935 wall CAD review

Date: 2026-11-04. Result: three exact acquired-facet STEP references and one
conditional cylindrical surface study, saved in a new native FreeCAD review
document. **No complete head solid or manufacturing release.**
The [aggregate receipt](observed-wall-cad.json) binds the successful sources,
private manifest and delivered files. This follows the rejected
[full-surface remesh](../935-mesh-admission-20261104/VARIABLE_SIZING.md) by returning
to acquired observations rather than tuning a rejected volume domain.

## Position in the software chain

The [local CADAM/Qwen branch](../../architecture/cadam-local-qwen.md) remains
proposal assistance, qualified only on its synthetic coupon. The present work
uses the existing scan-feature pipeline, local OCCT/OCP and native FreeCAD;
Qwen did not generate or approve these faces. Existing STEP/FreeCAD references
retain their evidence role and PicoGK remains the new engine geometry route.
No automatic CADAM-to-PicoGK/CAE bridge or new Gmsh, OpenFOAM, CalculiX or
Adamantine result is claimed. These open surface references do not admit a new
volume or solver case. Earlier hypothesis simulations remain exploratory.

## Inputs and admission before construction

The original scan, engineering baseline and registered source-face partitions
were read only. Contract and partition SHA-256 values are respectively
`49fc806e1f9d6f129892d1cdd15505b4ed304a68ee84f37bcbf1fd1c8461f779`
and `bca11c2633ed6fae331b9bd47d420f07f170b6f34d4ba232d68c87f37f1aa824`.
Decoded arrays contain 1,281,608 vertices and 2,466,040 triangles. Project scale
is owner-confirmed millimetres, not independent metrology of the specimen.
Three previously registered masks contribute 4,787 unique acquired triangles
(0.1941% of the acquired faces). This fraction measures reference coverage,
not completion of the head. Legacy `stud_passage_*` identifiers are retained
for provenance; anatomical identity is unconfirmed.

For all three regions the frozen baseline circle origin, axis and radius were
reused unchanged. Previously fitted tilted-cylinder alternatives were not
adopted. No refit or choice of a new winner from the residual scores occurred.

| Observed region | Original faces | Radial P95 / maximum (mm) | UV orientation reversals | Analytic admission |
|---|---:|---:|---:|---|
| 1 | 1,700 | 0.21745 / 0.57022 | 0 | Rejected: maximum projection |
| 2 | 1,667 | 0.38776 / 0.65892 | 3 | Rejected: projection and folds |
| 3 | 1,420 | 0.18216 / 0.25939 | 0 | Partial exploratory fit only |

The 0.4 mm screen is inherited from the earlier primitive study and is applied
here to **all source vertices**, with no folded, degenerate or overlapping UV
coverage admitted. It is not an interface, machining or manufacturing tolerance.
It has a different purpose from the earlier 0.01 mm remesh-to-parent preservation
limit: that limit was not relaxed, and the rejected remesh remains rejected.
Full replica acceptance and physical metrology remain separate requirements.

## Actual exports and independent checks

All three exact-reference STEP files were reopened. Every selected triangle
appears exactly once, vertex round-trip error is 0.0 mm in the native check,
and original orientation is preserved. These are **unsewn faceted compounds**;
original shared-index topology remains in the private NPZ and source IDs.
They are references, not an editable solid inferred from the scan.

Region 3 also exports five native cylindrical trimmed faces, total area
99.6481369822 mm². Periodic seams and two cuts at acquired UV boundary contacts
make the domain representable without filling source gaps or extending support.
The measured relative symmetric difference of the final partition is
1.35e-18. Chart count and trim rings are not evidence of physical holes.
All five surfaces remain cylindrical after STEP reload; maximum radius
round-trip error is 2.88e-13 mm. No hidden gallery, cap or new solid was added.

Independent source membership was checked against the original decoded arrays
and registered partition hashes, including original coordinates, connectivity
and face selection. Origins, axes and radii were compared with the frozen
baseline independently of the builder. Exact OCCT point-to-trimmed-face
distances were then computed after loading the actual exported STEP:

| Comparison | Coverage | P95 / maximum (mm) |
|---|---|---:|
| Source vertices → native trimmed STEP | All 826 vertices | 0.182165 / 0.259393 |
| Source surface → actual STEP tessellation | 10,000 area-weighted samples | 0.167445 / 0.250603 |
| Actual STEP tessellation → source surface | 10,000 area-weighted samples | 0.163819 / 0.251204 |

The sampled comparisons use a 0.005 mm native tessellation deflection. Sampled
maxima are not global surface bounds. The native all-vertex distance uses no
tessellation proxy. Negative controls reject a changed source contract before
output creation and detect a deliberately introduced 0.6 mm radial error.
Two analytic controls check cylinder trim-with-hole and periodic-patch areas.
All 18 existing scan-feature pipeline tests pass in the isolated CAD runtime.

The new FreeCAD document embeds the unchanged earlier engineering reference plus
an `ObservedWallReview` group. It was saved, closed and reopened in native
FreeCAD 1.1.4. All four new Part features are valid and have zero solids; the
conditional fit has exactly five cylindrical faces. The original baseline file
hash is unchanged. Imported Part features are static review geometry, not a
fully parametric functional master; the regeneration scripts and private
model/trim JSON remain editable.

## Retained failures and privacy

Initial attempts are retained privately, with sources, logs and an attempt
ledger. Per-triangle UV arithmetic first produced subprecision segments;
canonical per-source-vertex UV coordinates replaced it. Full-period construction
then failed with intersecting wires, and half-period charts still had source
boundary contacts. An unanchored cut produced arithmetic slivers; attempted
duplicate consolidation failed and was abandoned. The successful cut passes
explicitly through the acquired contact and a hole-interior point, preserving
the domain without snapping or automatic healing. Only the successful replay
sources are published here; failed artifacts are not forwarded.

Geometry and private model parameters remain outside Git. Current catalogue
rights are owner-confirmed open reuse with the exact licence identifier not
captured; this report does not invent one or publish scan geometry. Git contains
code, aggregate metrics and hashes. No external CAD/inference service, supplier
message or new paid rental was used. OCP is a local native binding, not a remote
CAD endpoint. The independent STEP reload and distance assessment was replayed
under [the macOS outbound-denial profile](source/local-only.sb), inherited by its
child processes. Earlier construction runs are not claimed to have used that
sandbox.

## Local delivery and reproduction

Private delivery:
`~/Developer/PorschePartsArtifacts/935-observed-wall-cad-20261104/`.
Open `deliverables/935-observed-wall-review.FCStd`. The same directory contains
three exact-reference STEP files, the region-3 cylinder-study STEP and private
source-model/trim JSON. `manifest.json` binds all retained artifacts, including
failed trials and the successful verification. Never run writers in that bundle.

Recorded runtimes: preparation Python 3.13.18 / NumPy 2.3.4 / Shapely 2.1.2;
CAD Python 3.12.11 / NumPy 2.5.4 / SciPy 1.18.1 / OCP 7.9.3.1
(`cadquery-ocp-novtk` 7.9.3.1.1); support Python 3.12.11 / libigl 2.6.3;
native FreeCAD 1.1.4. Exact CAD binary hash is in the receipt. The preparation
inspector is the retained CGAL 6.2 binary built from
[inspect_surface.cpp](../935-mesh-admission-20261104/source/inspect_surface.cpp).
Its nonzero status for an intentionally open patch is expected; admission reads
its explicit validity, degeneracy and intersection fields.

Run from the repository root using the retained local environments and a fresh
private directory. Numbered directory names below are required by the bounded
independent-verification script; they do not imply omitted successful trials.

```sh
set -e
ARTIFACTS="$HOME/Developer/PorschePartsArtifacts"
SCAN="$ARTIFACTS/935-scan-tools-20261029"
PAPER="$SCAN/paper-feature-section-pairs-20261029"
BASELINE="$SCAN/engineering-20261029"
ARRAYS="$SCAN/other-tools/exact-source-arrays.npz"
SOURCE="$PWD/docs/research/935-observed-wall-cad-20261104/source"
PREP_PYTHON="$HOME/Developer/CADAM/local-calibration/.venv/bin/python"
CAD_PYTHON="$BASELINE/cad-venv/bin/python"
SUPPORT_PYTHON="$SCAN/repair-trial/venv/bin/python"
REPLAY="$(mktemp -d "$ARTIFACTS/935-observed-wall-replay.XXXXXX")"

"$PREP_PYTHON" "$SOURCE/prepare_wall_domains_v2.py" \
  --paper "$PAPER" --baseline "$BASELINE" --arrays "$ARRAYS" \
  --inspector "$ARTIFACTS/935-surface-flip-20261104/inspect_surface" \
  --output "$REPLAY/preparation-002"
"$PREP_PYTHON" "$SOURCE/split_periodic_atlas.py" \
  --input "$REPLAY/preparation-002" --output "$REPLAY/preparation-003"
"$PREP_PYTHON" "$SOURCE/split_touching_domains_v2.py" \
  --input "$REPLAY/preparation-003" --output "$REPLAY/preparation-006"
"$CAD_PYTHON" "$SOURCE/build_wall_cad.py" \
  --preparation "$REPLAY/preparation-006" --output "$REPLAY/cad-005"
/usr/bin/sandbox-exec -f "$SOURCE/local-only.sb" \
  "$SUPPORT_PYTHON" "$SOURCE/assess_wall_support.py" \
  --preparation "$REPLAY/preparation-006" --cad "$REPLAY/cad-005" \
  --arrays "$ARRAYS" --paper "$PAPER" --cad-python "$CAD_PYTHON" \
  --output "$REPLAY/support-assessment-offline-001"
"$SUPPORT_PYTHON" "$SOURCE/verify_observed_wall_evidence.py" \
  --job "$REPLAY" --arrays "$ARRAYS" --paper "$PAPER" \
  --baseline "$BASELINE" --cad-python "$CAD_PYTHON" \
  --output "$REPLAY/independent-evidence.json"
"$CAD_PYTHON" -m unittest discover -s tests -p 'test_scan_feature*.py' -v
```

For the native companion, copy the retained `review-job.json` to the replay
directory. Update only each item's path to the replay `cad-005` equivalent,
recompute its SHA-256 from the inspected file, and set new `output` and `report`
paths. Keep the original baseline path/hash and expected roles/face counts.
Pass that non-secret JSON path as `PORSCHE_WALL_REVIEW_JOB` to the installed
`FreeCADCmd`, running [create_native_review.py](source/create_native_review.py).
Require both its JSON verification report and `OBSERVED_WALL_REVIEW_OK` in the
native log; shell exit status alone is insufficient. Any modified geometry
invalidates these recorded results and needs a new full verification/manifest.

## Remaining functional gates

The overall goal stays active and incomplete. This companion adds source-backed
CAD references; it does not resolve full bare-head/component separation,
independent specimen measurements, missing internal observations, attachment
contracts, complete solid reconstruction, mesh admission, sourced loads and
material properties, calibrated/converged physics, machine-specific metal
process qualification, professional review or physical inspection/testing.
Falcontech/Farsoon and BLT remain process candidates, not selected qualified
suppliers. No print-ready or engine-ready claim follows from this result.

The subsequent [periodic freeform trial](../935-freeform-wall-study-20261104/README.md)
tests one richer surface class on region 1. Native verification rejects it under
a stricter digital-preservation screen; residuals span all acquired components.
It does not replace any geometry or acceptance decision recorded above.
