# CP1 assumed thermal-birth LINEAR variant, held source only

This is one separately frozen numerical hypothesis after the preserved Newton
failure. The sole deck edit is `solve_type = NEWTON` to `solve_type = LINEAR`.
The card, assessor, time-level input, physical Kelvin field, birth rule, source,
geometry and all literal tolerances remain exact. The numerical reference is
the original level-2 contract with only its deck digest and solver-scope prose
updated. Its authority flags remain false.

The version-associated public MOOSE source identified by the root maps LINEAR
to PETSc KSPONLY. That mode performs a linear correction and does not apply the
original nonlinear convergence test. Keeping `nl_rel_tol`, `nl_abs_tol` and
`nl_max_its` literal does not establish that the failed Newton residual would
pass. The unchanged `0548fcbf` assessor still requires the complete converged
history, physical fields, birth associations and frozen energy thresholds; it
may reject this variant. No temperature shift, scaling, time-step, line-search,
thermal-property, source or acceptance-threshold variant is included.

The direct primary-context pins retain URLs, revision, hashes, licences and
limits. The resolved public MOOSE revision is
`7c06bdcefd02f9f31f4508839f21f410561309a4`; PETSc source is tag `v3.25.4`.
These source associations do not attest source-to-installed-binary equivalence,
complete ABI closure, the assembled residual, or the cause of the Newton
failure. Raw upstream source bodies are excluded from this preparation.

The full 22-file failed native closure, stopped peer, saved-data check,
historical diagnosis and root acceptance are pinned. The original 33 internal
time-step attempts and zero converged steps remain failed evidence. Internal
cutbacks were part of that one invocation; no external launch retry occurred.
The native PID was not captured: reaping is attributed to the frozen adapter's
wait/finally path and receipt, with only the root-observed controller absence.

The sibling Mac adapter changes only its CASE pointer. Its nine function ASTs,
owned lifecycle, seven-variable TCP environment, 19-file/13-link runtime
metadata and 100 s / sampled 2 GiB / 32 MiB controls are unchanged. The separate
external actual and numerical reference retain their different roles and
filenames. The inherited six mocked methods change only the selected source
digest. Three additional source assertions are prepared, unrun; neither tests
nor prepared modules/functions, native or scientific code were executed by
the author.

Root full-source review, independent source peer, authorized source/mocked
guards, fresh runtime/resource checks, an exact external actual, independent
child review and a root launch guard are required before any separately chosen
run. There is no actual contract, output, native or assessment authority here.
Any later assessment is a separate root-owned phase. No head, material,
process, LPBF, physical or manufacturing qualification is claimed.
