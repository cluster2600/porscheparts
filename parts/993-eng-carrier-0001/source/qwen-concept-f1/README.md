# Qwen-assisted concept — 993 Turbo engine carrier

**993 115 021 53 · concept only · NON VALIDATED FOR MANUFACTURING.**

This is a new digital concept alongside the catalogue's existing F0 master,
not a reconstruction of measured OEM geometry. No physical access to this exact
part, scan, interface measurements, material certificate or load validation is
confirmed. The central engine-bracket bolt pattern was omitted. Generating the
outline before establishing that attachment was a workflow error; the result
cannot perform the requested carrier function.

## Attachment correction

The reviewed [interface contract](interface-contract.json) records the missing
four-site engine-bracket attachment and both unmeasured end interfaces. The
[independent preflight](interfaces.py) rejects this shape even though its mesh
checks pass. It binds the audit to the source and STL hashes, rejects deleted
requirements and does not consume model-generated inspection claims. Ordinary
generation and the [checked exporter](export_checked.py) stop before loading
the model or native geometry libraries. `--shape-study` explicitly permits the
incomplete exercise; it does not clear the attachment blockers.

This is a documentary preflight for the audited prototype, not a qualified CAD
interface inspector. New geometry requires a new independent audit; reviewed
dimensions, hole axes, mating faces and tolerances must then be checked against
the actual geometry. Manufacturing approval remains outside the model.

The [correction curriculum and local runner](train_interfaces.py) provide 48
training cases, 16 validation cases from separate part families, 24 frozen test
cases and the exact carrier incident as a separate regression. Cases include
absent attachments, guessed holes, PET-only dimensions, an incomplete bolt
pattern, mismatched axes, the wrong variant, a fully checked synthetic fixture,
and requests to invent measurements. A material shader never supplies a grade.
Shared templates make this a narrow contract benchmark, not engineering
qualification. No manual pages, scans or vendor images enter the dataset.

The first 120-step continuation passes 16/16 validation cases, versus 0/16 for
the selected adapter, but passes only 18/25 final cases. It correctly refuses
the carrier while missing its unverified end interfaces, and miscopies some
compound role names. It is rejected; the failure receipts and weights remain
under `work/qwen-attachment-001/`. No acceptance threshold was relaxed.

The [second continuation](train_interfaces_v2.py) adds all 27 combinations of
three ready/absent/unverified interface states and compound role names. It has
210 training rows, 70 validation rows including the earlier validation cases,
81 fresh tests from new families, and the 25 opened tests as regressions. Old
tests are never training rows. The incident input is shortened without changing
its requirements, observations or oracle; it remains a regression.

The fixed 360-step second continuation starts from the first candidate, with
four LoRA layers, rank 8, scale 20, learning rate 0.0001 and seed 42. The reused
evaluator checks a maximum 512-token sequence without truncation. All 70
validation cases must pass before fresh tests open; all fresh tests and
regressions must then pass. Its weights remain isolated as an attachment-review
candidate, and the selected coding adapter is never overwritten. Shared rules
and templates limit what this benchmark proves.

The initial second-run process stopped during its final training evaluation
without saving weights. Its cause is unestablished; its logs remain under
`work/qwen-attachment-002/`. The unchanged curriculum was rerun under
`work/qwen-attachment-003/` and completed 360 steps. Validation improved from
20/70 to 39/70 and preserved the original 16 validation passes, but joint
interface states remain misclassified. This candidate is rejected at the
70/70 validation gate; the 81 fresh tests and 25 regressions were not opened.
Neither correction candidate is selected. Actual weights and raw responses
are retained separately; training completion is not acceptance.

The initial disk-reserve block was resolved by pip's built-in cache purge:
12,607.3 MB of cached packages removed, without deleting installed runtimes or
Qwen weights. The independent preflight applies regardless of training outcome.
See [training status and receipts](training-status.json). Reproduce both runs
with new output directories:

```sh
TRAIN=/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993
"$TRAIN/work/m64-qwen/venv/bin/python" \
  parts/993-eng-carrier-0001/source/qwen-concept-f1/train_interfaces.py \
  --training-checkout "$TRAIN" --output work/qwen-attachment-new-first
"$TRAIN/work/m64-qwen/venv/bin/python" \
  parts/993-eng-carrier-0001/source/qwen-concept-f1/train_interfaces_v2.py \
  --training-checkout "$TRAIN" --output work/qwen-attachment-new-second \
  --first-run work/qwen-attachment-new-first
```

The model is not the acceptance authority. The preflight and repository
instructions apply even if it confidently recommends an incomplete shape.

The selected locally trained **Qwen2.5-Coder-1.5B-Instruct, 4-bit MLX** adapter,
`coding-003/checkpoint-600`, generated the eight `AddBeam` statements retained
verbatim in [Program.cs](Program.cs). Codex supplied hypothetical vertices,
checked the generated graph, and wrote the surrounding blade trim, bosses,
bores and export code. The model did not infer dimensions or validate physics.

The first diameter-based prompt produced wrong radii on both sides and omitted
one edge. Both responses were rejected. An explicit-radius prompt then passed
both four-edge contracts. [inference.json](inference.json) retains every prompt,
raw answer, decoding setting, model/adapter hash and acceptance result.

The selected adapter's completed benchmark passes 10/32 PicoGK tasks, including
only 1/16 fresh graphs; compilation alone is insufficient. The separate
`coding-004` training run was still being evaluated when this concept was made.
This concept uses the completed checkpoint, not an unselected replacement.

## Inputs and assumptions

The [FVD product listing](https://www.fvd.net/en-us/shop/engine-suspension-bracket-carrier-993-turbo-99311502153~p248965)
declares 600 × 50 × 50 mm and 1.96 kg. These are vendor claims, not measurements.
The existing [catalogue record](../../../../catalog/parts/993-eng-carrier-0001.json)
identifies the Turbo application and documents the observed blade, two round
openings and end features. Photographs were not imported or used
as training data; their reuse rights are not established.

| Parameter | Concept value | Authority |
|---|---:|---|
| Maximum envelope | 600 × 50 × 50 mm | Vendor-declared bound, not a calibrated reference |
| Boss center separation | 560 mm | Design hypothesis |
| Boss outside diameter / height | 40 / 50 mm | Design hypothesis |
| End bore diameter | 13 mm | Design hypothesis; no fastener fit claim |
| Blade thickness / graph-beam diameter | 6 / 12 mm | Design hypotheses |
| Profile vertices | Literal coordinates in Program.cs, scaled by 10 | Design hypotheses |
| Mirror symmetry and boss axes | X symmetry, Z axes | Design hypotheses |
| Native voxel size for retained exports | 1 mm | Numerical discretization, not OEM accuracy |
| OEM material, interface tolerances, loads | Unknown | No values selected |

The segmented graph provides a bowed outline with two windows. It does not
reproduce the OEM curvature, variable section, mounting faces or bracket holes.
Vendor mass was not used to tune or qualify the shape.

## Retained files and checks

- [STL concept](../../derived/qwen-concept-f1/carrier-concept.stl).
- [OpenUSD concept](../../derived/qwen-concept-f1/carrier-concept.usdc), Z-up,
  millimeter units, with the actual exported mesh and no physics schemas.
- [Native and export checks](../../derived/qwen-concept-f1/checks.json).

The source compiled with .NET 9 and PicoGK revision
`0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3` on the existing Mac runtime.
Native probes found solid central web/boss walls and open windows/bores.
The retained mesh has one connected closed surface, consistent winding and
Euler characteristic −6, corresponding to four through openings. USD was
reopened with Pixar USD and its mesh arrays compared with the STL source mesh.
Self-intersections, CAD fidelity, fit, structural strength, fatigue, printability
and SimReady qualification were not established.

Initial Mac verification ran 3,263 main-suite tests successfully, with 152
optional runtime skips. Full `make check` then stopped at the existing Docker-based
`917-manufacturing-f37-lpbf-audit-check` because the Docker daemon was unavailable.
The focused concept test, catalogue validation, generated pages and strict
documentation links passed.

On 2026-10-02, full `make check` passed on Kali2's native ext4 checkout of
commit `2bcca62`: 3,270 main-suite tests ran with 144 optional runtime skips,
the pinned Docker F37 audit ran all 15 tests without skips, and all subsequent
checks passed. Python user-site packages were excluded from that run. These
repository checks do not establish carrier fit, strength or fatigue life.

The raw STL contains degenerate facets and coincident vertices. The exporter
welds to three decimal places in millimeters and removes degenerate/duplicate
faces, then rejects disconnected or open results. The report records the
original/final counts and maximum original-vertex distance. This cleanup is
bounded digital mesh processing, not a repair of the original part.

## Reproduce on the existing Mac

Use the trained checkout and cached weights; inference stays offline. Existing
receipts are never overwritten by the inference command.

```sh
TRAIN=/Users/maxime/.codex/worktrees/m64-local-architecture-qwen/3dprinting993
PICO=/Users/maxime/projects/3dprinting993/work/m64-private-20260907/nemo-picogk-20260928.ADELugEK
SOURCE=parts/993-eng-carrier-0001/source/qwen-concept-f1
OUT=work/engine-carrier-qwen-reproduction
mkdir "$OUT"
"$TRAIN/work/m64-qwen/venv/bin/python" "$SOURCE/infer.py" "$TRAIN" "$OUT/inference.json" --shape-study
"$PICO/dotnet/dotnet" build "$SOURCE/Carrier.csproj" -c Release \
  -p:PicoGKPath="$PICO/picogk-bin/PicoGK.dll" -o "$OUT/bin"
DYLD_LIBRARY_PATH="$PICO/picogk-bin" "$PICO/dotnet/dotnet" \
  "$OUT/bin/Carrier.dll" "$OUT/native" 1
/Users/maxime/projects/3dprinting993/work/cad-recode-tools-venv/bin/python \
  "$SOURCE/export_checked.py" "$OUT/native" "$OUT/export" --shape-study
python3 tests/test_993_engine_carrier_qwen.py
```

`Program.cs` contains the reviewed, accepted graph. A fresh inference receipt
does not automatically replace it or bypass its semantic checks. Rebuilding
uses the accepted source; voxel sizes from 0.25 to 1 mm are allowed for trials,
but the retained exporter accepts the documented 1 mm setting only.

## PET-led improved replacement

The [new research and redesign brief](../pet-redo/README.md) records the exact
PET assembly, four visually reviewed FVD photographs, missing dimensions and
the user's high-output durability/cost objective. It corrects the earlier
one-piece assumption and identifies a flange/gusset candidate for evaluation.
No functional replacement is generated while interface and load evidence is
missing. The trained review experiment cannot grant that evidence.

## Next gates

1. Obtain the exact Turbo carrier and follow the existing
   [measurement plan](../../evidence/measurement-plan.md), including independent
   end axes, bracket bolt pattern, datums, curvature and section thickness.
2. Replace the hypothetical graph with measured editable geometry; inspect
   interfaces and establish loads, material, corrosion and fatigue requirements
   with professional engineering review.
3. Approve a validation plan before any functional manufacture or vehicle use.
   A polymer mock-up may only study interfaces; it must never support the engine.
