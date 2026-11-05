# 993 carrier H7: localize the complete mechanical correction

The complete gravity H6-to-H7 correction has now been localized over all
**18,670,283 fine cells**. The 135 protected source cells contribute only
**2.32145e-10 of the correction energy**. They do not explain the measured
gravity energy increment. **87.4088%** lies in children of refined parents and
**12.5912%** in unchanged, unprotected cells.

This result directs the next mesh audit toward ordinary refined regions.
It does not justify discarding protected cells or changing the original
stabilization criterion. The [H7 mechanical report](carrier-h7-native-results-20261105.md)
remains authoritative for the two complete increments: 2.654% and 3.257%,
both above the unchanged 1% screen. Nominal mass remains **1.2941382 kg**.

![Complete gravity correction energy at fine-cell centroids](../media/carrier-h7-gravity-correction-localization-20261105.png)

The image projects a complete 16 × 16 × 16 centroid histogram onto XY, XZ
and YZ. Every fine cell contributes its positive compliance correction energy.
Each projection sums to the same full energy, not to a selected slice.
Coordinate axes are scaled independently for legibility; cells are not smoothed
or interpreted as a reconstructed surface. Gray bins have no contribution.
The [published numerical aggregate](carrier-h7-correction-localization-20261105.json)
contains the exact bin bounds, totals, source identities and largest 100 cells.

## Complete partition and concentration

| Disjoint group | Fine cells | Correction energy, N mm | Share |
|---|---:|---:|---:|
| Children of refined parents | 8,460,854 | 0.4523975626069143 | 87.40878674% |
| Unchanged and unprotected | 10,209,294 | 0.06516775247135573 | 12.59121324% |
| Protected source cells | 135 | 1.201502886574257e-10 | 2.32145e-8% |

The complete sum is **0.5175653151984208 N mm**, identical to the previously
admitted stress-difference compliance energy. At least **293,975 fine cells**
are needed to accumulate half the correction, **2,298,079** for 90%, and
**6,074,838** for 99%, when sorted by decreasing cell contribution. The largest
100 contribute only **0.385145%**. The gravity correction is therefore spread
across many cells; attributing it to a few pointwise peaks is unsupported.

## Executed method and checks

For every fine cell, the checked H6-to-H7 nesting map identifies its coarse
parent. The unchanged comparator's isotropic compliance expression integrates
`volume × density(sigma_h7 − sigma_h6)` using the same study material and exact
integration volumes. No scalar stress statistic substitutes for this complete
field calculation. Both full lossless DAT streams are replayed into RAM; all
original force, moment and energy checks pass again before localization.

The classification is disjoint and exhaustive. The independently retained
protected-cell roster contains 135 cells; none is a split parent. Known-energy
partition controls pass, while negative weights, foreign labels and noninteger
labels are rejected. Group and spatial-bin sums agree with the complete energy
to relative 1e-12. There is no certified error-bound or new spatial-stabilization
claim. No new native solve or paid instance was used.

The private entry point is
`work/carrier-h7-correction-localization-001/analyze.py`, which reuses the
qualified full replay and comparison with only a fresh output root. Its complete
receipt SHA-256 is
`0a57ff31379748eb2b2b6926a9fd9dfb7fb9115d560b16302ef4576dfb61866a`.
Raw meshes and field arrays remain outside Git.

## Combined case and next refinement

The gravity localization completed before the first local supervisor stopped
on a five-second process-list observation timeout. Its receipt remains intact.
The old worker and supervisor are terminal and absent. A fresh **combined-only**
replay is running under a new supervisor that records telemetry failures,
tolerates a single transient failure, and always records child cleanup. The
combined localization is **pending**, not inferred from gravity.

RAM-backed face storage additionally matches the unchanged disk-based complete
face-pairing algorithm byte for byte on four synthetic populations through
4,096 tetrahedra. Three-owner faces, repeated vertices and allocation above the
cap are rejected. This qualifies the storage substitution on those controls;
actual complete H7 traction-jump ranking and an H8 mesh remain unexecuted.

The immediate sequence is: finish combined localization; bind both complete H7
traction-jump fields; admit a targeted H8 geometry; run both independent cases
in parallel on authorized workers; recover and compare the complete fields.
All geometry and mechanical acceptance thresholds remain unchanged.

## Storage and repository verification

The internal disk is below the mesh producer's 8 GiB reserve. Analysis therefore
writes only bounded metadata and figures, not new mesh or field arrays. The
external evidence mount reports available capacity, but a fresh exclusive
receiver-creation witness timed out. It is not admitted as a new scientific
receiver. Both bounded probes were killed and reaped; the first attempted root
was independently observed absent before the second, instrumented attempt.
No existing scientific files were modified.

The full hosted repository check for commit `3434804d5` passed:
[GitHub Actions run](https://github.com/cluster2600/porscheparts/actions/runs/42112884652).
Locally, 5,191 principal tests passed with 405 skips. The full local make stopped
when Docker was off; after starting it, the affected container target passed
all 15 tests. This is not a claim that the entire local make completed. Docker
was subsequently stopped after confirming there were no running containers.
