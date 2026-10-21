# Held independent 3D cooling and release assessor

This is source preparation only. No function, module, guard, field reader, scientific library, decoder, solver, table generator or assessor has been invoked. There is no assessment actual or output. All execution and qualification authorities are false. The case author is existing_study_audit; this separate assessor author is replica_metrology, with prior source/reader/peer and HXT lineage. Reused mathematics is identified exactly rather than presented as a new independent derivation.

The fixed case replays mechanics from time zero on 425 nodes and 256 HEX8 cells. It does not continue the previous unclamped displacement solution. The accepted original thermal END/BEGIN history through step 160 remains the temperature reference. The original 225-node BEGIN 80 temperature reference is copied exactly, including 25 shared nodes. The displacement reference of the born region is captured from this new clamped run at BEGIN 80. No prior mechanical displacement, stress or uBirth field is an input.

## Reused 3D checks

The donor is assessor003, SHA 55f5f9ca281f9752a6dcac28afca8d18f2c12b4759cf06f8c639a1bb3b8a81bd. Eighteen function definitions and Audit remain text/AST exact: strict finite readers, lexical shared-doublet validation, source/external IDs, HEX8 order and Q1 quadrature, isotropic Hooke, old/born thermal references, tensor reconstruction, weak-form integration, native CDF1/2 decoding and full field comparison. Every changed source group reverses to the complete donor. No controller or parser framework is introduced.

The seven individual limits remain exactly temperature 1e-10 K, displacement 1e-12 m, QP coordinate 2e-13 m, strain 1e-10, stress 0.1 Pa, force 1e-7 N and moment 1e-7 N*m. Every native field, node, element and physical QP must be present. Every postbirth native shared-node doublet must be exactly two lexically identical complete rows; reference and original thermal rows remain unique. No averaging, omission, tolerance fallback or changed numbering mode is accepted.

All 183 END frames and 366 BEGIN/END samples are required. Planned coverage is 292864 QP rows per phase, 585728 total, 123550 unique node-phase associations and 46350 born-reference associations. These are source expectations, not observations. The 25 shared-node doublets in 206 postbirth nodal samples imply 5150 expected doublet groups if the declared native storage protocol is observed. A new complete storage audit and its root acceptance are mandatory; prior fine-coupon observations are not transferred.

## Phase and support derivation

Before birth the active z=0 plane has 45 nodes and 135 fixed components; from birth through END 180 it has 85 nodes and 255 fixed components. The original six point constraints are a subset of the full plane constraint set, but they are not simultaneously active as separate BCs. From BEGIN 181, only those six components are constrained. Every phase has an explicitly disjoint constrained/free partition.

BEGIN 181 is the inherited END 180 displacement, temperature and material state before the released problem has equilibrated. Only the 249 newly released components are exempt from the free-force zero check at that BEGIN phase. All other free rows must satisfy the unchanged force bound. Every END 181 and END 182 free component must satisfy it. The existing BEGIN-to-previous-END and QP history comparisons preserve the release association. Reactions are sampled at END; every END native residual is compared with the assembled independent internal force, and both full and constrained reaction resultants/moments are checked.

For steps 161 through 182, the independent temperature expectation uses the original END 160 string tokens and the declared Decimal precision 80 formula. BEGIN uses the preceding END state. END 180 reaches exactly 300 K; BEGIN 180 still carries END 179 and must not be relabelled 300 K. END 180 and both phases of 181/182 are checked against 300 K. This is prescribed cooling, not a solved heat-loss or calibrated process law.

## Release energy criterion

The donor independently integrates elastic strain energy from reconstructed stress and elastic strain at all eight QPs. This source also integrates the native tensor product and propagates the existing absolute stress and strain limits through each product:

B = 0.5 * sum(w * (stress_limit * abs(strain) + strain_limit * abs(stress) + stress_limit * strain_limit)), over all nine tensor entries.

No new Joule tolerance is selected. At fixed 300 K and fixed old/born references, removing homogeneous constraints from a positive-definite linear elastic problem cannot increase its minimized potential. The comparison allows B_before + B_after plus a conservative residual-work bound: force_limit * sum(abs(delta_u)) on free components, plus abs(after_force * delta_u) on the remaining constrained components. The same bound checks the linear trapezoidal internal-work identity for END 180 to END 181. This is a numerical criterion propagated from the seven frozen gates; it is not a floating-point roundoff theorem, physical dynamic energy conservation or work=2U shortcut.

END 181 and END 182 have identical prescribed temperature/reference/support conditions. Their complete nodal u/T/reaction and tensor fields must agree within the original individual SI gates. Their energy products must agree within the summed propagated product bounds. This checks the declared final hold; it establishes neither mechanical discretization convergence nor material/process validity.

## Required future evidence and controls

All current sources and the 322 original thermal CSV identities are direct pins. The three accepted original grids are metadata-only during preparation. No raw field or runtime body was read or hashed here. A future external assessment actual must directly bind the completed continuation data peer/root acceptance, native capture peer/root acceptance, complete new storage audit/root acceptance and exact TimePeriod 24-object presence/root closure. The native adapter already requires those registry records. They do not yet exist and all held slots remain null. Unknown future peer schemas or CDF member names are not invented.

The full future native recursive inventory, original CDF family and source snapshots must be directly pinned and checked before and after assessment. The unchanged selected decoder metadata is 2b3b2ac0f52ecef6f349d45524f26011da94c257fc0ede5067a9f236681e9713: Python1699, NumPy 2.2.6, SciPy 1.17.1, 258 finite file identities. Root alone will refresh them. Proposed saved-assessment bounds reuse 300 seconds, sampled 2 GiB RSS, 32 MiB output, one thread and an ordinary root-owned new session with TERM, 8-second grace, owned-group KILL and wait. No automatic retry or native replay is authorized.

Eight focused stdlib guard groups are prepared and UNRUN. They exercise support masks and release exemption, BEGIN cooling association, energy/work refusals, fixed-temperature final hold, all tensor product entries, missing completed evidence, complete 183-frame family and unchanged reader/math/policy/birth-reference source identity. Unchanged old math/storage guards are retained by source identity rather than duplicated or rerun by this author.

The frozen case contract has one stale narrative rule saying postbirth cells run through step 160. Its numeric steps, counts, deck and other descriptions explicitly run through 182; this assessor uses that finite declared scope and discloses the prose issue without editing the case. Source preparation is reviewable, but no native or saved-assessment admission follows. Measured CP1 laws, strength, plastic residual stress, LPBF calibration, head fields and manufacturing remain unqualified.
