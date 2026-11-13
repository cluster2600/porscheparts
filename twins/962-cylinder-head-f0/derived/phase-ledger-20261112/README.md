# 962 head: 19-phase execution ledger, 12 November 2026

This is the public summary of a fresh, private ledger produced by
[`workflow_plan.py --output`](../../source/workflow_plan.py), as
[WORKFLOW.md](../../WORKFLOW.md) requires. It replaces the
[ledger of 6 November](../phase-ledger-20261106/README.md) as the current one,
because that ledger went stale: 21 of its 46 bound sources changed after it
was bound. The old ledger is kept unchanged. This one exists so that the
owner can carry out the independent review that
[issue #578](https://github.com/cluster2600/porscheparts/issues/578) asks for,
which is the last open item of
[#540](https://github.com/cluster2600/porscheparts/issues/540).

**Nothing was executed, rented or accepted.** One phase, `provenance`, is
`prepared`. Fifteen phases are `blocked` and three are `failed`. No phase is
`accepted`, so the chain is not ready, and `manufacturing_authorized` stays
false. **The independent review has not happened**: `independent_review` is
null in [summary.json](summary.json), and the agent that prepared this ledger
cannot supply it.

## Identity

| Item | Value |
|---|---|
| Repository commit bound | `89192b7df2d4b559fdeb3fbb171b830144f025dc` |
| Contract SHA-256 (unchanged since 6 November) | `1d80c6faa37de73fccd5a7ed27220a0c2c311b6b6b74c03908bb7cce4987974d` |
| Private `plan.json` SHA-256 (bound revision) | `cf5dbd967f0a20339aa68b0654632c7b1c6a2f677d498c822ba7960b0df6f418` |
| Private as-materialised copy SHA-256 | `95a61c5a08372fdaef48f506e517227644e706209c9ea96a0a566985f6239f0e` |
| Provenance runtime receipt SHA-256 | `21325cf8c0e9b30e16897181303dac753821161d4957cef7dc4475a7962b2c9c` |
| Recipe sources bound | 46 files; their hashes are in `summary.json` |
| Receipts bound | 15 phase attempts and 30 software witnesses, all rehashed from this commit |

`--check-plan` returned exit 0 with
`workflow_structure_checked_not_physical_validation` and
`all_phases_accepted: false`. `--require-ready provenance` returned exit 0.
`--require-ready picogk` was run as a negative control and refused with exit 1,
as it must. The checker verifies structure and hashes. It does not verify any
engineering result.

The private `plan.json`, its runtime receipt and the script that filled it stay
outside Git, in the ignored `work/962-phase-ledger-20261112/` folder on the
host that prepared them. The provenance runtime was requalified on that host
for this ledger (Python 3.12.3, six tests of
`tests/test_962_material_comparison.py`, exit 0); the 6 November receipt was
not reused.

The bound sources include the root and head `AGENTS.md`, `WORKFLOW.md` and
`ENGINEERING_PROGRAM.md`. Any later change to them makes this plan stale too.
When that happens, keep this plan as it is and prepare a fresh one.

## What changed since 6 November

No phase changed state. The counts are the same: 1 prepared, 15 blocked,
3 failed. The differences are in the reasons, the issue links and the receipts:

- **`picogk`:** the Linux runtime gap now has a receipt. A bounded Linux
  x86_64 PicoGK runtime was software-qualified on synthetic boxes
  ([#560](https://github.com/cluster2600/porscheparts/issues/560), closed on
  9 November). It did not run the head generator, and its image sits
  unpublished on one builder. The phase stays blocked on provenance acceptance
  and on the all-null donor interfaces
  ([#450](https://github.com/cluster2600/porscheparts/issues/450)).
- **`lpbf_build`, `lpbf_release`:** two END181 diagnostics of 7 November are
  bound as software witnesses. They show the force imbalance is in the saved
  solution itself (exact integration gives a constrained Fx of −2.25450e-6 N
  against the unchanged 1e-7 N limit) and that the deck's LINEAR mode never
  tests the final nonlinear residual. The 12 of 36 failures stand
  ([#446](https://github.com/cluster2600/porscheparts/issues/446)).
- **`volume`, `material_strength`, `lpbf_build`, `lpbf_release`:** the macOS
  owned-group probe for
  [#447](https://github.com/cluster2600/porscheparts/issues/447) is bound as a
  witness. It reproduced the EPERM on an exited, unreaped child. It does not
  qualify the controller.
- **`reconstruction`:** #437 is closed. Decision 0019 lets the project accept
  measurements from outside contributors. None has arrived, so the phase is
  still blocked on #450.
- **Omniverse phases and `coolant_cfd`:** the OpenBao HTTP 403 now has an
  owning issue, [#561](https://github.com/cluster2600/porscheparts/issues/561).
- **Four carried receipts have new hashes** because the British-English
  conversion (#495) rewrote their prose: the five-toy second-attempt README,
  the rich3 coupon README, `BIONIC_FIELDS.md` and `GALLERY.md`.

## Variant finding (unchanged)

Each phase in the ledger names its exact study variant. The existing meshes
do not belong to one shared variant:

- **Metal:** the bore-95 study solid. The current24 saved mesh has SHA-256
  `2b994eea…f2ba35`, with 1,097,268 nodes and 3,622,025 TET4 cells.
- **Water:** the bore-102 (4 L scenario) single-cylinder study domain. The MMG
  mesh has SHA-256 `5cf99238…e0c8` and 635,132 tetrahedra.

So there is no conformal metal/water pair for any one variant. CHT and every
later coupled phase are therefore blocked, in addition to the mesh-quality
gates. No donor specimen is identified, and every donor interface is still
null.

## Phase states

| Phase | State | Exact blocker or reason | Issues | Next permitted action |
|---|---|---|---|---|
| `provenance` | prepared | Inputs and argv bound; stdlib runtime requalified on this host for this ledger. Not executed; no result claimed. Execution and a separate independent assessment are both still required. | [#449](https://github.com/cluster2600/porscheparts/issues/449), [#450](https://github.com/cluster2600/porscheparts/issues/450) | Run --require-ready provenance, then execute the two bound commands in this private ledger, record an execution companion with outputs, and obtain an independent assessment. Acceptance would be scope software, never physical. |
| `reconstruction` | blocked | No licensed same-part capture set or same-part scale datums exist. Decision 0019 (2026-11-06, closing [#437](https://github.com/cluster2600/porscheparts/issues/437)) lets the project accept measurements from outside contributors, but none has been received and no donor is identified ([#450](https://github.com/cluster2600/porscheparts/issues/450)). Not marked not_applicable: whether a lawful donor dataset arrives as captures is undecided, so omission would be a silent scope change. | [#450](https://github.com/cluster2600/porscheparts/issues/450) | Owner/third party: decide the [#450](https://github.com/cluster2600/porscheparts/issues/450) intake format. If it is a capture set, bind licence, scale datums and capture configuration; if it is direct metrology, record a reviewed not_applicable justification. |
| `picogk` | blocked | Upstream provenance is prepared, not accepted. A bounded Linux PicoGK runtime is now software-qualified on three synthetic boxes and one lattice cell ([#560](https://github.com/cluster2600/porscheparts/issues/560), closed 2026-11-09); it did not invoke the head generator, and its image is kept on one local builder, unpublished. donor_interface_contract is all-null, which blocks functional Fasteners. Existing study geometry is historical evidence, not a ledger execution. | [#450](https://github.com/cluster2600/porscheparts/issues/450) | After provenance acceptance, bind the study inputs (solid.json, coolant.json, dry-passages.json) and the qualified runtime in this ledger, then pass --require-ready picogk; keep Fasteners non-functional until [#450](https://github.com/cluster2600/porscheparts/issues/450) supplies measured interfaces. |
| `surface` | blocked | Upstream picogk not accepted. Existing bore-95 surface audits are scoped (0.0625 mm analysis scope) and the stronger 414-cell Mesh_2 surface-quality criterion remains failed. Water surface feeaddaf... is a bore-102 export without measured interfaces. | [#445](https://github.com/cluster2600/porscheparts/issues/445), [#448](https://github.com/cluster2600/porscheparts/issues/448) | After picogk acceptance, bind domain meshes and reference hashes and rerun the independent topology/intersection/deviation audit without hidden repair. |
| `volume` | failed | Latest metal admission executed and failed: current24 saved head returns RC2 with 24 cells below SICN 0.1, minimum 0.039074265058645995 against the unchanged 0.1 gate. The bore-102 water mesh passes checkMesh separately, but water acceptance never admits metal and the two meshes belong to different variants. Upstream surface is also unaccepted. | [#445](https://github.com/cluster2600/porscheparts/issues/445), [#448](https://github.com/cluster2600/porscheparts/issues/448), [#447](https://github.com/cluster2600/porscheparts/issues/447), [#544](https://github.com/cluster2600/porscheparts/issues/544) | Resolve the 24 poor metal cells under the unchanged gate ([#445](https://github.com/cluster2600/porscheparts/issues/445)) or regenerate a matched-variant metal/water pair with conformal interfaces; preserve RC2. |
| `coolant_cfd` | failed | Seven bounded Foundation 13 steady RANS restarts (case-017..025) on the bore-102 water mesh executed; none passes the numerical flow screen. First global residuals are about 7e-4 to 9e-4 against the unchanged 1e-5 target; timeouts are not convergence. Volume is not accepted for the head. | [#448](https://github.com/cluster2600/porscheparts/issues/448), [#561](https://github.com/cluster2600/porscheparts/issues/561) | Owner: approve spending ceiling and fix OpenBao 403 ([#561](https://github.com/cluster2600/porscheparts/issues/561)) before any rental; otherwise continue bounded local diagnosis with the unchanged gates ([#448](https://github.com/cluster2600/porscheparts/issues/448)). |
| `cht` | blocked | No conformal multiregion head case: metal (bore 95) is not admitted and the admitted water mesh is bore 102. No sourced heat loads, no temperature-dependent properties, coolant CFD not accepted. The flow pilot is not a CHT case. | [#541](https://github.com/cluster2600/porscheparts/issues/541), [#445](https://github.com/cluster2600/porscheparts/issues/445), [#448](https://github.com/cluster2600/porscheparts/issues/448), [#449](https://github.com/cluster2600/porscheparts/issues/449) | None until [#445](https://github.com/cluster2600/porscheparts/issues/445)/[#448](https://github.com/cluster2600/porscheparts/issues/448)/[#449](https://github.com/cluster2600/porscheparts/issues/449) gates pass on one matched variant; then prepare a Foundation 13 multiregion case per [#541](https://github.com/cluster2600/porscheparts/issues/541). |
| `material_strength` | blocked | No admitted metal mesh, no accepted CHT fields, no process-specific material laws or allowables, no measured attachments/load paths or preload. Conditional assumed cards are study inputs only; no head solve has run. | [#542](https://github.com/cluster2600/porscheparts/issues/542), [#445](https://github.com/cluster2600/porscheparts/issues/445), [#449](https://github.com/cluster2600/porscheparts/issues/449), [#450](https://github.com/cluster2600/porscheparts/issues/450), [#447](https://github.com/cluster2600/porscheparts/issues/447) | Owner decision [#449](https://github.com/cluster2600/porscheparts/issues/449) (material/process card and loads) and donor interfaces [#450](https://github.com/cluster2600/porscheparts/issues/450) first; no deck before --require-ready material_strength. |
| `lpbf_melt_pool` | blocked | No selected alloy/powder, machine/laser profile, scan path, layer thickness or calibration coupons; no 962-bound AdditiveFOAM 2.0.0 / Foundation 14 runtime receipt or tutorial replay. | [#543](https://github.com/cluster2600/porscheparts/issues/543), [#449](https://github.com/cluster2600/porscheparts/issues/449) | Owner [#449](https://github.com/cluster2600/porscheparts/issues/449) process card; then qualify the Foundation 14 AdditiveFOAM runtime separately from Foundation 13 and replay the pinned tutorial ([#543](https://github.com/cluster2600/porscheparts/issues/543)). |
| `lpbf_build` | blocked | No accepted melt pool, no admitted metal mesh, no orientation/plate/support/scan plan, no calibrated laws; the qualified process solver is not bound. Synthetic CP1 coupons are software witnesses: END181 still fails 12 of 36 aggregate equilibrium checks. The 7 November diagnostics show the imbalance is present in the saved solution itself (exact integration: constrained Fx -2.25450e-6 N against the unchanged 1e-7 N limit) and that the deck's LINEAR (ksponly) mode never tests the final nonlinear residual. No new coupon solve has run. | [#544](https://github.com/cluster2600/porscheparts/issues/544), [#446](https://github.com/cluster2600/porscheparts/issues/446), [#449](https://github.com/cluster2600/porscheparts/issues/449), [#447](https://github.com/cluster2600/porscheparts/issues/447), [#445](https://github.com/cluster2600/porscheparts/issues/445) | Under [#446](https://github.com/cluster2600/porscheparts/issues/446) and the original 36 gates, test one additional reassembled correction within the support-release step, after independent review of the two diagnostics; decide the held HEAD499 adapter. Head build waits on [#543](https://github.com/cluster2600/porscheparts/issues/543)/[#445](https://github.com/cluster2600/porscheparts/issues/445)/[#449](https://github.com/cluster2600/porscheparts/issues/449). |
| `lpbf_release` | blocked | No accepted build history, cooling/heat-treatment, removal sequence, machining allowances or calibration. The listed mechanical-birth runner is a synthetic witness; coupon release attempts were refused on force balance, and the 7 November exact-integration diagnostic confirms that imbalance in the saved END181 field. | [#545](https://github.com/cluster2600/porscheparts/issues/545), [#446](https://github.com/cluster2600/porscheparts/issues/446), [#449](https://github.com/cluster2600/porscheparts/issues/449), [#447](https://github.com/cluster2600/porscheparts/issues/447) | None for the head until [#544](https://github.com/cluster2600/porscheparts/issues/544) is accepted; coupon diagnosis continues under [#446](https://github.com/cluster2600/porscheparts/issues/446). |
| `omni_preflight` | blocked | Validation-only preflight is ready (OpenUSD, Asset Validator, locked SimReady runtime), but no declared property-assignment intent, no Content Agents/OVRTX service readiness and no approved endpoint access (OpenBao HTTP 403, [#561](https://github.com/cluster2600/porscheparts/issues/561)) exist. | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#561](https://github.com/cluster2600/porscheparts/issues/561) | Declare intent and obtain approved access/local endpoints ([#561](https://github.com/cluster2600/porscheparts/issues/561)); rerun preflight with Content Agents/OVRTX readiness ([#451](https://github.com/cluster2600/porscheparts/issues/451)). |
| `omni_conversion` | failed | One geometry-only bore-95 conversion through the installed convert-to-usd reference (converter 0.2.0) executed and fails the frozen source-parity check: 1,804,452 vs 1,804,706 triangles (254 fewer). Minimum USD reference passed eight checks; parity failure retained. Preflight/picogk upstream not accepted. | [#451](https://github.com/cluster2600/porscheparts/issues/451) | Diagnose the 254 omitted/changed triangles before any assignment; do not substitute custom USDA authoring ([#451](https://github.com/cluster2600/porscheparts/issues/451)). |
| `omni_assignment` | blocked | No minimum-valid parity-preserving USD, no sourced material/physics context, no healthy Content Agents endpoints ([#561](https://github.com/cluster2600/porscheparts/issues/561)). | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#449](https://github.com/cluster2600/porscheparts/issues/449), [#561](https://github.com/cluster2600/porscheparts/issues/561) | None until omni_conversion is accepted and [#449](https://github.com/cluster2600/porscheparts/issues/449) supplies sourced material context. |
| `omni_conformance` | blocked | Required assignment has not occurred. The pre-assignment static validation retains VG.027 and six Prop-Robotics-Neutral profile findings (NP.006, UN.007, RB.001 x2, GSP.001, VM.MAT.001); these must stay visible and are not repaired before assignment. | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#561](https://github.com/cluster2600/porscheparts/issues/561) | None until omni_assignment is accepted. |
| `field_exchange` | blocked | No accepted native solver fields exist (coolant CFD unconverged; CHT, strength and LPBF release unrun or refused). Geometric distance/gradient grids are not velocity, temperature or stress. The Fields runner CLI is not verified. | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#448](https://github.com/cluster2600/porscheparts/issues/448), [#541](https://github.com/cluster2600/porscheparts/issues/541), [#542](https://github.com/cluster2600/porscheparts/issues/542), [#545](https://github.com/cluster2600/porscheparts/issues/545), [#561](https://github.com/cluster2600/porscheparts/issues/561) | None until upstream physical fields are accepted. |
| `omni_render` | blocked | No validated USD; existing gallery views are visual-only study renders and do not replace an RTX render of conformed USD. | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#561](https://github.com/cluster2600/porscheparts/issues/561) | A labelled visual-only assembly may be prepared earlier; physical scope waits on omni_conformance and field_exchange. |
| `physicsnemo` | blocked | No accepted dataset or labels, no disjoint whole-family evaluation split, no bound training script/config. Planning only. | [#451](https://github.com/cluster2600/porscheparts/issues/451) | None until field_exchange is accepted. |
| `delivery` | blocked | Every other phase is blocked, failed or only prepared; no bound results, no approved budget or rental identity (none created), no professional validation plan. | [#547](https://github.com/cluster2600/porscheparts/issues/547), [#546](https://github.com/cluster2600/porscheparts/issues/546), [#540](https://github.com/cluster2600/porscheparts/issues/540), [#578](https://github.com/cluster2600/porscheparts/issues/578) | Deliver a gap dossier only ([#547](https://github.com/cluster2600/porscheparts/issues/547)); physical validation plan requires [#546](https://github.com/cluster2600/porscheparts/issues/546) and professional review. |

`failed` marks a phase whose most recent head-scope attempt ran and was
rejected by its unchanged gate. Those failed outputs are kept. In
`summary.json`, each phase keeps two separate lists: attempts at the phase
itself, and software witnesses. The witnesses include synthetic CP1 coupons,
Z3 toy sessions, the MOOSE cube, the END181 diagnostics, the macOS probe, the
Linux PicoGK runtime qualification, Qwen assistance and planning notes. None of
them is a head result.

## For the reviewer

The review must come from the owner or from someone the owner names who did
not prepare this ledger. The checks listed in #578 are:

1. All 19 phase IDs, `provenance` through `delivery`, appear with a state:
   1 prepared, 3 failed, 15 blocked, none accepted.
2. Each blocker links to an issue: #445–#451, #541–#547, #561 and #447.
   #560 is now closed and appears as resolved under `picogk`.
3. The bore-95 metal / bore-102 coolant mismatch is recorded as blocking `cht`.
4. Software witnesses are kept apart from phase attempts.
5. `--check-plan` exits 0 on the bound commit.

To record the review, add a signed note next to this file (name, date, the
`summary.json` SHA-256 reviewed, findings, verdict). Do not edit
`summary.json`; a review note that finds a defect leads to a fresh ledger.

## Limits

The commands for every blocked phase are still the contract's templates,
which are not executable preparation. The prepared provenance phase covers
only the family-wide material-comparison register. It selects no variant,
alloy or process. Every missing donor dimension stays unknown. The
`accepted` state appears nowhere in this ledger, and it would not grant
physical or manufacturing qualification even if it did.
