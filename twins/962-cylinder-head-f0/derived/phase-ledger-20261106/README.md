# 962 head: 19-phase execution ledger, 6 November 2026

This is the public summary of one fresh, private ledger produced by
[`workflow_plan.py --output`](../../source/workflow_plan.py), as
[WORKFLOW.md](../../WORKFLOW.md) requires
([issue #540](https://github.com/cluster2600/porscheparts/issues/540)). The
private `plan.json` stays outside Git. Only its hashes, the state of each phase
and the repository receipts it binds are published, in
[summary.json](summary.json).

**Nothing was executed, rented or accepted.** One phase, `provenance`, is
`prepared`. Fifteen phases are `blocked` and three are `failed`. No phase is
`accepted`, so the chain is not ready, and `manufacturing_authorized` stays
false. The independent review of this ledger's completeness has **not**
happened yet. The preparer cannot supply that review.

## Identity

| Item | Value |
|---|---|
| Repository commit bound | `cedec73485074a092f75fdd2a176b213d726ff34` |
| Contract SHA-256 | `1d80c6faa37de73fccd5a7ed27220a0c2c311b6b6b74c03908bb7cce4987974d` |
| Private `plan.json` SHA-256 (bound revision) | `969f62c7ddbb7ba7f354adac909f5e33970c1ddc7fbc0d8e59a21d0a97f5f14b` |
| Private as-materialized copy SHA-256 | `47cd6d25ff08db3e080051afcbdbc5d5781d88209c1024971fef9d6fbe4c0f3a` |
| Provenance runtime receipt SHA-256 | `ad5ffaefa7ea290f3d8158d654d945e8c6e23b81bd7b51086ee3d1aa48976dc9` |
| Recipe sources bound | 46 files; their hashes are in `summary.json` |

`--check-plan` returned exit 0 with
`workflow_structure_checked_not_physical_validation` and
`all_phases_accepted: false`. `--require-ready provenance` returned exit 0.
No other phase was checked for readiness, because none has accepted
prerequisites. The checker verifies structure and hashes. It does not verify
any engineering result.

The bound sources include the root and head `AGENTS.md`, `WORKFLOW.md` and
`ENGINEERING_PROGRAM.md`. Any later change to them makes this plan stale.
When that happens, keep this plan as it is and prepare a fresh one.

## Variant finding

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
| `provenance` | prepared | Inputs bound at family scope: four study bores, sourced recipes with rights, all-null donor interfaces. Bounded argv for `compare_materials.py`, and a stdlib runtime qualification that passed (6 tests). Not executed. | [#449](https://github.com/cluster2600/porscheparts/issues/449), [#450](https://github.com/cluster2600/porscheparts/issues/450) (downstream) | Execute both bound commands in the private ledger, then obtain an independent assessment |
| `reconstruction` | blocked | No licensed same-part capture set or scale datums exist. It is not marked `not_applicable`, because the intake format for #450 is undecided. | [#450](https://github.com/cluster2600/porscheparts/issues/450), [#437](https://github.com/cluster2600/porscheparts/issues/437) | Owner or third party decides the format of the donor dataset |
| `picogk` | blocked | Upstream is not accepted. The PicoGK driver is Mac-only, and no Linux wrapper has been qualified. Without measured datums, Fasteners cannot be functional. | [#450](https://github.com/cluster2600/porscheparts/issues/450); Linux wrapper has no issue | Qualify a bounded native wrapper |
| `surface` | blocked | `picogk` is not accepted. The bore-95 audits are scoped, and the 414-cell Mesh_2 failures are still open. | [#445](https://github.com/cluster2600/porscheparts/issues/445), [#448](https://github.com/cluster2600/porscheparts/issues/448) | Wait for `picogk` |
| `volume` | failed | Metal: RC2, 24 cells below SICN 0.1, minimum 0.039074265058645995. The bore-102 water mesh passes checkMesh separately, but that does not admit metal. | [#445](https://github.com/cluster2600/porscheparts/issues/445), [#448](https://github.com/cluster2600/porscheparts/issues/448), [#447](https://github.com/cluster2600/porscheparts/issues/447), [#544](https://github.com/cluster2600/porscheparts/issues/544) | Repair the metal mesh under the unchanged gate, or build a mesh pair for one matched variant |
| `coolant_cfd` | failed | Seven bounded Foundation 13 restarts (case-017 to case-025) did not converge. First residuals are about 7e-4 to 9e-4, against a target of 1e-5. | [#448](https://github.com/cluster2600/porscheparts/issues/448) | Owner approves a spending ceiling and OpenBao is fixed before any rental; otherwise continue local diagnosis |
| `cht` | blocked | There is no matched-variant conformal case, no sourced heat loads and no hot properties. | [#541](https://github.com/cluster2600/porscheparts/issues/541), [#445](https://github.com/cluster2600/porscheparts/issues/445), [#448](https://github.com/cluster2600/porscheparts/issues/448), [#449](https://github.com/cluster2600/porscheparts/issues/449) | Wait for upstream gates |
| `material_strength` | blocked | There is no admitted mesh, no CHT fields, no material laws or allowables, and no measured attachments. | [#542](https://github.com/cluster2600/porscheparts/issues/542), [#445](https://github.com/cluster2600/porscheparts/issues/445), [#449](https://github.com/cluster2600/porscheparts/issues/449), [#450](https://github.com/cluster2600/porscheparts/issues/450), [#447](https://github.com/cluster2600/porscheparts/issues/447) | Owner decisions #449 and #450 |
| `lpbf_melt_pool` | blocked | No alloy, powder, machine, laser, scan path, layer or coupons are defined. The Foundation 14 AdditiveFOAM runtime is not qualified for the 962. | [#543](https://github.com/cluster2600/porscheparts/issues/543), [#449](https://github.com/cluster2600/porscheparts/issues/449) | Process card, then qualify the runtime separately from Foundation 13 |
| `lpbf_build` | blocked | Upstream is not accepted. The process solver is not bound. The END181 coupon witness fails 12 of 36 checks. | [#544](https://github.com/cluster2600/porscheparts/issues/544), [#446](https://github.com/cluster2600/porscheparts/issues/446), [#449](https://github.com/cluster2600/porscheparts/issues/449), [#447](https://github.com/cluster2600/porscheparts/issues/447), [#445](https://github.com/cluster2600/porscheparts/issues/445) | Diagnose END181 under #446 |
| `lpbf_release` | blocked | There is no accepted build history. The coupon release witnesses were refused on force balance. | [#545](https://github.com/cluster2600/porscheparts/issues/545), [#446](https://github.com/cluster2600/porscheparts/issues/446), [#449](https://github.com/cluster2600/porscheparts/issues/449) | Wait for #544 |
| `omni_preflight` | blocked | Only the validation preflight is ready. There is no declared intent, no Content Agents/OVRTX readiness and no approved access (OpenBao 403). | [#451](https://github.com/cluster2600/porscheparts/issues/451); access has no issue | Declare intent and obtain approved endpoints |
| `omni_conversion` | failed | The bore-95 conversion fails strict source parity: 254 triangles fewer than the source. | [#451](https://github.com/cluster2600/porscheparts/issues/451) | Diagnose the parity loss; do not use custom USDA authoring as a substitute |
| `omni_assignment` | blocked | There is no parity-valid USD and no sourced material/physics context. | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#449](https://github.com/cluster2600/porscheparts/issues/449) | Wait for conversion |
| `omni_conformance` | blocked | Assignment has not happened. VG.027 and the six profile findings from the earlier validation remain visible. | [#451](https://github.com/cluster2600/porscheparts/issues/451) | Wait for assignment |
| `field_exchange` | blocked | No accepted solver fields exist. Geometric grids are not physics fields. | [#451](https://github.com/cluster2600/porscheparts/issues/451), [#448](https://github.com/cluster2600/porscheparts/issues/448), [#541](https://github.com/cluster2600/porscheparts/issues/541), [#542](https://github.com/cluster2600/porscheparts/issues/542), [#545](https://github.com/cluster2600/porscheparts/issues/545) | Wait for accepted fields |
| `omni_render` | blocked | There is no validated USD. The gallery holds visual-only renders. | [#451](https://github.com/cluster2600/porscheparts/issues/451) | A visual-only assembly may come earlier if it is labelled as such |
| `physicsnemo` | blocked | There is no accepted dataset and no split; only planning exists. | [#451](https://github.com/cluster2600/porscheparts/issues/451) | Wait for `field_exchange` |
| `delivery` | blocked | Every upstream phase is not accepted. There is no budget or rental identity, and no professional validation plan. | [#547](https://github.com/cluster2600/porscheparts/issues/547), [#546](https://github.com/cluster2600/porscheparts/issues/546) | Gap dossier only |

`failed` marks a phase whose most recent head-scope attempt ran and was
rejected by its unchanged gate. Those failed outputs are kept. In
`summary.json`, each phase keeps two separate lists: attempts at the phase
itself, and software witnesses. The witnesses include synthetic CP1 coupons,
Z3 toy sessions, the MOOSE cube, Qwen assistance and planning notes. None of
them is a head result.

## Limits

The commands for every blocked phase are still the contract's templates,
which are not executable preparation. The prepared provenance phase covers
only the family-wide material-comparison register. It selects no variant,
alloy or process. Every missing donor dimension stays unknown. The
`accepted` state appears nowhere in this ledger, and it would not grant
physical or manufacturing qualification even if it did.
