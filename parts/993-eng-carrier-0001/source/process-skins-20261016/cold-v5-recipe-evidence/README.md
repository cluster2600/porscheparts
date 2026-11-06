# Review of the v5 recipe

These three receipts are copied unmodified from
`work/part-workflow/cold-v5-recipe-review-001/`. The chain owner re-verified
the 285 digests, including the 278 unchanged v4 entries.

- `assessment.json` links the recipe to the two other receipts and to their scope.
- `argv-results.json` verifies 37 contracts: the ten modified commands are
  actually parsed; the 27 other proofs are carried over after equality of
  steps, arguments, sources and runtime manifest.
- `closure-results.json` verifies the consumed dependencies and the outputs.

The v6 generators keep the domains and the support parameters.
An inward-facing band is omitted only if its entire quadrilateral is already
contained in the source domain, by exact proof. Other cases remain refused.
Each construction call now keeps its inputs and its complete result. The v5
preparer chooses the construction from the authority actually recorded; it
relabels no old receipt.

The v5 guide keeps the constituent references and checks of the v4 guide; its
reproduction command points to this new recipe. This review reruns no
complete computation, slicing or solver and produces no final guide. The real
outputs keep their own admissions.
