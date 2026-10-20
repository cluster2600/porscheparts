# Seventeenth flip fixture: duplicate outputs with disjoint removals

This is an additive synthetic association-level test only, held and unrun. It
isolates the output-duplicate branch of `association_conflicts` from its
removed-cell overlap branch. There is no real-context enumeration, coordinate
arithmetic, cavity eligibility, global embedding or mesh application claim.

Association A describes symbolic3→2 edge(4,5), linktriangle(1,2,3), distinct old
tags201/202/203 and outputs1234/1235. Association B describes symbolic3→2
edge(1,6), linktriangle(2,3,4), oldtags301/302/303 and outputs2341/2346. The old
tag sets are explicitly disjoint. Exactly one unordered replacement4-set1234
is common, with different node order in its two occurrences. The expected
compatibility output is exactly one pair with EMPTY shared_removed_cell_tags
and duplicate_replacement4sets equal to[[1,2,3,4]]. Such a pair is conflicting;
no combined eligibility or application is produced. No missing source API or
runtime outcome is invented.

The independent fixture reviewer agreed with this semantic construction in a
source-only message. A separate successor source review is still required.
The frozen16-test file, original five-versus-six METHOD erratum, original plan,
original held preparation and worker remain unchanged. The successor is a full
literal source copy with one appended method; deleting the inserted method and
its surrounding new whitespace restores the complete old bytes. All16 original
methods plus their helper retain exact text and AST, and all module helpers
are unchanged. Removing the new method also restores the complete old AST.

There is one direct unittest.TestCase class. The successor neither imports the
original fixture module nor inherits its test class. A future direct invocation
of this one successor file would discover17 methods once, not16+17. No such
invocation, original fixture, guard/helper, prepared source, native program or
real arithmetic has run. No driver, actual, controller, launch, installation,
new threshold or execution authority is created. The original bounded future
plan applies only if root later admits this exact17-test successor; all limits
and later real-context/physical gates remain unchanged.
