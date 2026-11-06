# Review of the v4 recipe and the guide's references

These four receipts are copied without modification from
`work/part-workflow/cold-v4-recipe-review-001/`. The owner of the chain
re-verified the 278 digests and the identity of the first 36 steps with v3.

- `assessment.json` links the recipe, the three other receipts and their scope.
- `argv-results.json` verifies 37 contracts: 36 v3 proofs reused after
  equality of steps, arguments, sources and runtime manifest; the new
  argument list of the v4 guide is actually parsed.
- `closure-results.json` verifies the consumed dependencies and the outputs.
- `retained-reference-readonly-binding.json` verifies the real identities of
  mesh 9 and of the K1000 linear set of run `run-001`, then the sixteen
  kept states. The Piola balance passes; the ENER diagnostic remains refused.

The v4 guide adds the constitutive results and their figure without modifying
the support generators or the admissions. The separate STEP exports are not
treated as equivalent. This review reruns neither DAT, nor solver, nor slicing,
and produces no final guide. The real outputs of the carrier keep
their own admissions.
