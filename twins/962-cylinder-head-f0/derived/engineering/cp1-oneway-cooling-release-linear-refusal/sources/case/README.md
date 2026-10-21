# LINEAR cooling and support-release profile

This separate source-held profile uses the accepted 256-HEX8 prescribed-temperature coupon from t=0. It changes the solver formulation to LINEAR and explicitly requests a final updated-solution residual evaluation through a PETSc monitor and the ALWAYS norm schedule. It is unrun and contains no actual contract or native output.

The material, SI geometry, prescribed temperature tables, own BEGIN80 birth reference, clamped cooling, BEGIN181 release and END182 hold are unchanged. The original hypothesis card and thermal metadata index are byte-exact copies. The accepted tables are reused in their existing directory; no data preparer is copied or run.

The original NEWTON run remains a terminal failed capture, including internal timestep cutbacks and the source timer's native SIGKILL. It is not resumed. A future admitted LINEAR profile must capture its own entire trajectory, own BEGIN80 displacement/reference and all required phases.

The retained nonlinear tolerance literals are inactive under LINEAR. KSPONLY completion does not certify absolute equilibrium. The seven independent SI limits, full QP/tensor/weak-form/reaction checks, storage and ID mapping, release-energy and final-hold checks remain mandatory and can fail. Source trace and runtime metadata do not establish installed-source ABI equivalence.

Read [METHOD.md](METHOD.md), [case-contract.json](case-contract.json), [source-evidence.json](source-evidence.json), [source-reuse.json](source-reuse.json) and [held-preparation.json](held-preparation.json). The eight source guards and six lifecycle mocks are prepared UNRUN. Independent source review, root guard review, a binding-only assessor successor and exact native child review remain required. No head, LPBF, material, strength, manufacturing or physical qualification follows.
