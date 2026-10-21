# Held prescribed cooling, build clamp and release — one finite coupon

This is one SOURCE-HELD successor, not a solver run or calibrated LPBF case. Existing sources, native captures, thermal fields, data and assessments remain unchanged. The new mechanical problem is replayed from t=0 with a build clamp: it is not a binary restart or continuation of the earlier unclamped displacement/stress solution. It reuses the accepted thermal history and the exact same256-HEX8/425-node geometry and material hypotheses.

## Explicit new research assumptions

Keep SI m,Pa,N,K,s; E=71e9Pa, nu=.33, alpha=1e-5/K, constant isotropy over the declared300–500K numerical interval. No measured CP1 curve, yield/plasticity, creep, melt/latent heat, scan law, contact, physical build plate or qualified process is introduced.

The complete accepted old/born nodal END temperature history through END160/.4s is retained token-for-token. The225 born-reference BEGIN80 temperature DOFs, including25 shared nodes, are copied byte-for-byte. Old stress-free T stays400K. The clamp changes displacement history: the born mechanical reference must be the NEW run's full BEGIN80 displacement, not the old unrestrained native result.

The new cooling is prescribed at every node, not solved heat loss: for j=1..20,
T[160+j]=300+(T_END160-300)*(20-j)/20.
It reaches300K at END180/.45s and remains300K through END182/.455s. Duration .05s, reservoir target300K and linear path are explicit unmeasured hypotheses. They model neither thermal diffusion nor calibrated cooldown kinetics. No original source-off cooling was present or is retrospectively asserted. Decimal80 arithmetic defines new intermediate literals before binary64 conversion; original tokens are never reformatted. The reference table is a whole-byte copy.

A temporary z=0 node-plane clamp fixes all three displacement components during heating/birth/cooling. A nodeset-only BoundingBoxNodeSetGenerator is added; coordinates/connectivity remain the same generated geometry. The six original3-2-1 component constraints are initially disabled, avoiding competing Dirichlet definitions at shared DOFs. One TimePeriod with reverse_on_false=true enables those six and disables the three plane-clamp BCs at BEGIN181/.4525s. Cooling has therefore already reached300K while clamped. Two fixed300K equilibrium solves follow. Rigid modes are never intentionally released. TimePeriod/ConditionalEnableControl follow the existing mechanical-birth source; exact-commit TimePeriodBase confirms scalar time expansion for the finite enable/disable lists. No unsupported Control execution_order_group is added.

This purely elastic constrained/released body can exhibit stress from incompatible old/born thermal references. Call it the declared postrelease elastic state, not validated AM plastic residual stress, distortion or fatigue life.

## Minimal reuse

- Same deck ICs, Aux temperature/reference, birth modifier and restore flags, small incremental strain, constitutive and30-component sampling blocks; same solver/tolerances and dt=.0025.
- prepare_continuation.py reads ONLY the three already accepted grids and their manifest. It does not reconvert321 thermal CSVs or rerun the thermal solve. Four source helpers (need,sha,table_text,checked_pins) are text/AST-exact to prepare_transfer.py. Fixed original counts36,225/18,225/225 become41,175/23,175/225;54,675 old tokens plus9,900 explicit new values.
- run_mac.py reuses the same selected19-file/13-link runtime, one Popen command, TCP-only seven-variable environment, deadline/RSS/output sampling, owned kill/wait, immutable physics mirror versus external actual, flat/recursive artifact maps and no autoassessment/retry. Seven top-level helper function ASTs remain exact; checked_contract adapts the finite new manifest/24-object registry gate, and run changes receipt declarations only.
- Six mocked controls are prepared; five remain body-identical except the necessary case/schema/hash literals. The sixth has a full valid synthetic registry/manifest fixture and negative drift paths. Eight new source/data guards cover ramp/prefix/header/card/phase/clamp/reference/resource gates. All14 are UNRUN.
- Full reversible source groups and diffs are retained. No general controller, parser framework, scheduler or material catalogue is created.

## Concrete future commands and controls

Data-only, after a separately frozen actual and root/peer source gates:
selected1699 Python -I -B PREP/prepare_continuation.py ABSOLUTE_DATA_ACTUAL EXTERNAL_SHA256.
Proposed ordinary60s/T8 owned-group cleanup, sampled2GiB/16MiB/one thread; all data inputs and source/root metadata freshly hashed before/after. The source writes only the fixed new inputs directory after complete validation; no such directory exists now.

Mechanical capture, only after accepted data, fresh24-object registry incl TimePeriod, independent continuation-assessor source/peer/root guards and exact native child:
selected1699 Python -I -B PREP/run_mac.py --stage coupon --contract ABSOLUTE_NATIVE_ACTUAL --contract-sha256 EXTERNAL_SHA256 --execute.
Inner100s/sample2GiB/512MiB/one thread; proposed ordinary115s outer, TERM10 then verified-owned KILL/wait. These are limits, not predicted completion, RAM fit or OS quotas. The adapter alone materializes the fresh native output. The exact installed prefix is work/962-engineering/moose-local-installed-002. No runtime body was read or query run during this preparation.

## Evidence needed before accepting any result

Independent data checking must verify all54,675 original tokens/axes/IDs, all9,900 new formula values, unchanged BEGIN80 reference bytes and exact425 coordinate/source-ID map. New tables and data root/peer closure must be directly pinned by the future native actual.

A separately reviewed continuation assessor is REQUIRED BEFORE native authority. Reuse existing fixed3D Q1/Hooke/weak-form/CDF1–2 and exact shared25 doublet reader kernels, but adapt phase count, reference history, prescribed temperatures and the constrained/free-DOF sets at release. Do not run the birth-only assessor unchanged or call old assessment source authority sufficient. All366 BEGIN/END phases,128old/256postbirth cells,2x2x2QPs and30 tensor components remain captured. Expected total585,728 QP-phase and123,550 unique node-phase associations are cardinality plans, not observations. Full external-ID/connectivity/block-family decoding, native storage audit and raw-lexical associations remain necessary after capture.

Check all inherited seven absolute SI limits without softening, old material history, newborn pre-equilibrium strain/stress, actual own BEGIN80 u-reference, T and shared/reference DOFs, all QP constitutive/increment relations, constrained values, every free residual and complete reactions/force+moment balance. At fixed300K compare clamped END180, pre-equilibrium BEGIN181 and relaxed END181/182. Independently integrate elastic energy and verify the minimization/nonincrease consequence of removing zero-displacement constraints. Do not claim work=2U or physical dynamic energy conservation across instantaneous support removal; no inertia/damping or real release path is modeled. Predeclare any additional energy criterion in that independent source before running.

The current raw storage shape (postbirth shared-node doublets) is inherited reader policy, not a new observation. Preserve full arrays/CSV/CDF families and every failure. No new head mesh, cooling calibration, physical strength/material/process/manufacturing qualification or public release follows.

All authority flags remain false and result/source-peer/actual slots null. No table generation, function/module/guard/solver/runtime query or scientific import has run. Only source/JSON/AST editing and finite metadata hashes occurred.
