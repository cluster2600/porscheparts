# Mandatory workflow for every 962 head agent

The owner requires the complete software chain, not a CFD-only preparation.
This policy applies to every primary or delegated agent working on the head,
its cloud campaign, LPBF preparation, field exchange or Omniverse assets.
Read it together with [AGENTS.md](AGENTS.md) and the versioned
[phase contract](workflow-contract.json). Root instructions route agents here
even when they edit a deployment script outside this directory.

## Required phases

The contract gives each phase its software, input bindings, command templates,
repository recipes, expected outputs, prerequisites and acceptance checks.

| ID | Work that must be accounted for |
|---|---|
| `provenance` | Exact geometry family, sources/rights, donor measurements versus study assumptions, material comparison and Qwen proposal review |
| `reconstruction` | Licensed capture, COLMAP/GLOMAP, Open3D/pymeshlab/Blender, same-part scale and registration; explicitly justify if no reconstruction is needed |
| `picogk` | Editable C#, PicoGK, ShapeKernel, LatticeLibrary, applicable Fasteners, separate metal/water/dry domains, named OpenVDB round trips |
| `surface` | Independent topology, intersections, deviations and protected features; pymeshlab/Open3D/CGAL/libigl/trimesh and actual mesh views |
| `volume` | Gmsh/MMG and separate native admission of metal and coolant meshes; conformal thermal interfaces |
| `coolant_cfd` | Foundation 13, MPI scaling, bounded restarts, first-solve residuals, flux balance, stability, mesh/solver sensitivity |
| `cht` | Prepared conjugate regions, heat loads, hot properties, converged coupling and energy balance |
| `material_strength` | Process-specific material, CalculiX/MOOSE, contacts/preload/loads, stress, equilibrium, convergence and stated margins |
| `lpbf_melt_pool` | AdditiveFOAM/Foundation 14, machine/laser/powder, scan/layer settings, energy balance and coupon calibration |
| `lpbf_build` | Adamantine/MOOSE, orientation, plate/supports, activation, temperature history, calibrated build stress/distortion |
| `lpbf_release` | Cooling, heat treatment, support removal, stress redistribution, dimensional change and machining allowances |
| `omni_preflight` | Installed CAD-to-SimReady revision, declared intent, dependency manifest and required Content Agents/RTX service readiness |
| `omni_conversion` | Installed converter and minimum USD validation, source hashes, units, axes and geometry associations |
| `omni_assignment` | Sourced material then physics assignment; no invented hot properties or solver authority |
| `omni_conformance` | Post-assignment conformance, asset, geometry, physics and profile validation, with rechecks after repairs |
| `field_exchange` | Accepted native fields, named VDB grids, USD associations, units/frame/time, independent mapping errors |
| `omni_render` | Actual geometry overview/cutaways, RTX provenance and clean package source; visual-only scope when fields are unavailable |
| `physicsnemo` | Accepted datasets, whole-family evaluation split, trained model comparison and checked inference limits |
| `delivery` | Sources, cases, logs, checks, real views, verified archives, costs and owned-rental destruction/absence receipts |

Using applicable tools does not mean applying every repair algorithm blindly.
For each named tool record executed, available but unnecessary, or unavailable
with a reason. Do not pretend to run photogrammetry without captures, a trained
surrogate without labels, or functional fasteners without measured interfaces.
Only the reconstruction phase allows `not_applicable` in the unchanged contract.
Other missing inputs cause `blocked`; an explicit owner scope change requires
a separately reviewed policy change rather than deletion from a job plan.

## Prepare concrete work before renting

From the repository root, use a fresh directory:

```sh
python3 twins/962-cylinder-head-f0/source/workflow_plan.py
python3 twins/962-cylinder-head-f0/source/workflow_plan.py --output work/962-suite-new
python3 twins/962-cylinder-head-f0/source/workflow_plan.py --check-plan work/962-suite-new/plan.json
```

This creates nineteen separate **records** in one authoritative `plan.json`.
It does not execute a solver or produce a ready runtime bundle. Every record
starts blocked with null input bindings. Replace its templates with actual argv,
bind all named inputs and attach a runtime qualification receipt before calling
it prepared. Record additional host/native-library setup as separate commands.
For PicoGK preserve the shared native lock; never invoke its native DLL directly
without the qualified bounded wrapper. Qualify Linux libraries independently.

```sh
python3 twins/962-cylinder-head-f0/source/workflow_plan.py \
  --check-plan work/962-suite-new/plan.json --require-ready picogk
```

Readiness also requires accepted prerequisites. It is phase-specific: blocked
downstream physics does not prevent an independent provenance or software
qualification task. Witnesses remain separate from numerical head acceptance.
The paid instance still needs the approved budget, identity, digest, compatible
cost/deadline guard and collection/destruction controller. This plan checker
does not create an instance, authorize spending or replace those controls.

Source hashes bind the recipe snapshot. When source changes, preserve the old
plan and prepare a fresh one. Bind the exact variant, domain and material state
in each input; never mix a 3.0 L reference, 4 L study, metal mesh and water mesh.
Keep the four-valve and double-ignition requirement explicit. Unknown donor
dimensions and operating loads remain unknown.

## States and evidence

- `blocked`: actual missing prerequisite/runtime/access/data, with its reason.
- `prepared`: concrete inputs and argv, passed runtime receipt, accepted upstream
  phases; no execution or result claimed.
- `running`: the prepared task is actually running; record its job identity,
  start, limits and checkpoint location in the execution metadata.
- `executed`: successful execution receipt plus actual, hash-bound outputs.
- `accepted`: executed evidence plus a separate independent assessment, with
  acceptance scope `software` or `study_numerical`.
- `failed`: record the failure and preserve outputs; never delete it to rewrite
  the history as success.
- `not_applicable`: reconstruction only, with the explicit reason.

Evidence references have `path` relative to the plan directory and `sha256`.
Keep private results there, outside Git. A runtime companion JSON carries
`kind: runtime_qualification`, the matching `phase` and `passed: true`; its
underlying proof must identify executable/image hashes, versions, actual native
qualification and host limits. An execution companion carries `kind: execution`,
matching phase, actual `exit_code: 0`, `timed_out: false`, argv and input/runtime
bindings. An assessment companion carries `kind: independent_assessment`, matching
phase and `passed: true`, linking the independent assessor and its evidence.
Preserve older differently shaped receipts; add companions instead of editing
hash-bound originals. The ledger checker verifies structure, identities and
hashes; it cannot establish that a physical assumption or engineering result is
correct. Review and native acceptance criteria still apply.

No `accepted` value in this ledger grants physical or manufacturing qualification.
`manufacturing_authorized` stays false. Neither CI nor a synthetic coupon
qualifies the head, LPBF process, 1,000 hp target or SP95 knock envelope.

## LPBF and Omniverse execution rules

LPBF jobs need the chosen alloy/powder, machine/laser, beam profile, layer
thickness, hatch/scan strategy, orientation, supports, plate, temperature-dependent
laws, calibrated coupons, treatment/removal sequence and machining allowances.
Use null and a blocker when any is missing. Never transplant an IN625 or steel
tutorial's material parameters into the proposed aluminum/copper head.
Keep AdditiveFOAM/Foundation 14 separate from coolant/Foundation 13. Check the
actual pinned solver's CPU/GPU/MPI capabilities; do not assume Adamantine's
mechanical path scales like its thermal path. Perform local melt-pool studies
and whole-part build/release studies at appropriate, declared scales.

For Omniverse use the installed CAD-to-SimReady references as separate stages.
Preflight and required Content Agents readiness precede conversion/inspection;
minimum USD validity precedes assignment; conformance and ordered validators
follow assignment; use the actual `output_usd_path` of each report. Do not
replace the conversion step with custom USDA authoring, repair FET issues before
required assignment, or create one monolithic SimReady runner. Prepare a visual
assembly earlier if useful, with explicit scope; attach physical fields only
after their native numerical gates pass. Existing VDB import gates remain intact.

## Reporting and automated enforcement

Every handoff and checkpoint names changed phase IDs and links its complete
ledger. Every final report states which phases are prepared, executed, accepted,
blocked or not applicable, plus remaining blockers. A tool inventory or four
CFD pilots cannot be described as a fully prepared engineering chain.

`make check` discovers [the workflow tests](../../tests/test_962_workflow_contract.py).
They reject omitted phases, stale/missing recipes, unsafe references, unresolved
readiness and unsupported acceptance. This enforces workflow accounting, not
the truth of physical results. Existing solver-specific independent checks,
qualification plans and professional engineering review remain required.
