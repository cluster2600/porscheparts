# 962 cylinder-head project instructions

These instructions apply to `twins/962-cylinder-head-f0/` and its descendants.

- The owner requires all new and updated project deliverables in English:
  documentation, diagrams, image labels, human-facing record prose, comments,
  prompts, command messages and generated reports. Keep stable identifiers,
  schema keys, filenames, paths and source citations unchanged.
- Follow [the repository translation policy](../../docs/TRANSLATION.md).
  Preserve frozen evidence, archives, logs, receipts and any file pinned by
  SHA-256 byte-for-byte. Supply a separately named English companion when
  translation would invalidate a digest; link it to the preserved original.
  Retain explicit legacy anchors when translating linked headings.
- Keep original-reference measurements, assumed design inputs and calculated
  results distinct. Missing measurements remain unknown. The owner's
  authorization permits bionic studies with explicit assumptions; it does
  not establish fitment, strength, thermal performance or manufacturing release.
- Preserve historical candidates and rejected results. New calculations and
  exports use fresh output directories with source/input/runtime provenance.
  A translation, successful render or software check adds no physical evidence.

## Required work sequence; no silent omissions

- Read [WORKFLOW.md](WORKFLOW.md) and [workflow-contract.json](workflow-contract.json)
  before planning or executing a checkpoint. Every agent must account for all
  nineteen phase IDs, even when its own task changes only one phase.
- Before a paid session, materialize a full ledger with
  `python3 twins/962-cylinder-head-f0/source/workflow_plan.py --output <new-dir>`.
  Bind every affected job's inputs and runtime; supply explicit blockers for
  the rest. Generated command templates are not executable preparation.
- Run `python3 twins/962-cylinder-head-f0/source/workflow_plan.py --check-plan <plan.json>`
  after updating that ledger. Run `--require-ready` on the selected phase before
  execution. A blocked downstream phase does not prevent independent, ready
  work; it does prevent claiming that the full chain is ready or complete.
- The required chain covers provenance/reconstruction; PicoGK with ShapeKernel,
  LatticeLibrary and applicable Fasteners; surface inspection/repair; separate
  water and metal volume admission; CFD; CHT; material and strength; LPBF melt
  pool, build thermomechanics, cooling/heat treatment/support release; Omniverse
  preflight, conversion, assignment, conformance; accepted VDB/USD fields; RTX
  rendering; PhysicsNeMo; verified delivery and owned rental cleanup.
- Use every applicable tool for its documented purpose. Justify conditional
  omissions explicitly; only reconstruction permits `not_applicable` without
  an owner-requested scope change. Do not run irrelevant or duplicate solvers
  solely to put their names in a report. Record missing runtimes as blockers.
- Keep geometry, alloy/build route, software witness, numerical acceptance and
  physical qualification separate. Water-mesh acceptance never admits metal.
  Preserve four valves/two ignition reservations and donor unknowns explicitly.
- LPBF preparation must name alloy/powder, machine/laser, scan strategy, layer
  thickness, orientation, supports, plate, material laws, calibration coupons,
  treatment, release and machining allowances. Unknown entries stay null and
  block a calibrated head result. Keep OpenFOAM 13 coolant and OpenFOAM 14
  AdditiveFOAM runtimes separate. Verify actual solver parallel/GPU support;
  do not assume Adamantine mechanics scales like its thermal MPI path.
- Omniverse uses the installed CAD-to-SimReady stages separately: preflight and
  service readiness, conversion/minimum validity, material/physics assignment,
  profile conformance, ordered validation, then rendering/package. Do not bypass
  Content Agents readiness or substitute custom USDA authoring for conversion.
  A visual assembly may be prepared earlier; physical fields need accepted,
  hash-bound results and checked units, frames, time and associations.
- Every execution needs input/source/runtime hashes, actual argv, limits,
  exit/timeout state, complete outputs and independent acceptance evidence.
  Never promote `prepared` to `executed` or `accepted` from intent alone.
  Keep rejected trials and use fresh directories. Qwen cannot approve its output.
- Every progress/final report must identify changed phase IDs and distinguish
  prepared, executed, accepted, blocked and not applicable stages. Show remaining
  blockers. Do not announce a finished head, kit, LPBF build or physical twin
  from CI, a render, synthetic coupons or a prepared cloud campaign.
- Respect the approved spending ceiling, OpenBao wrapper, deadline/cost guards,
  checkpoint collection and verified destruction. Never rent an idle machine
  while installing an unqualified toolchain. No credential retrieval through
  Keychain or raw secret-store calls is permitted.
