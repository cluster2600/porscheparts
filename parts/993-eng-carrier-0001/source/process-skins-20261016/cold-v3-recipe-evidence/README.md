# Review of the v3 recipe

The [recipe](../../../../../manufacturing/workflows/993-carrier-lpbf-v3.json)
has 37 steps and 271 pinned files. The
[receipt](assessment.json) preserves the verification of identities, commands
and source closure needed by the calculations and the installers.
The first twelve steps, the 45 v1 entries and the 211 v2 entries remain
identical. Binary software archives are kept outside Git.

The [arguments](argv-results.json) were accepted by 36 actually imported
parsers; the remaining single-path CLI was checked statically.
No command body, solver or slicing was executed by this review.
The [source closure](closure-results.json) distinguishes the dependencies
used from the output files and from old optional paths.

The three receipts are exact copies of the check carried out before the freeze.
They do not constitute a complete replay of the carrier. The real runs and
their admissions keep their own results.
