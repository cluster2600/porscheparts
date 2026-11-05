# Review of the cold v6 recipe

These four JSON files are exact copies of the receipts kept in
`work/part-workflow/cold-v6-recipe-review-001/`. They describe the commands,
their dependencies and their identities; they are not a full replay
of the part. References to one-off scripts and logs in the working
directory remain references to that run, not files supplied here.

- [Assessment](assessment.json): 37 steps, 293 digests, with the 285 old ones kept.
- [Commands](argv-results.json): ten commands actually parsed; 27 contracts reused after strict identity of their objects, sources and runtime.
- [Dependencies](closure-results.json): new dependencies covered, generator snapshots, bootstrap files and no output collisions.
- [Exact difference](exact-delta.json): eight sources added, first twelve steps unchanged, nine budgets of 14,400 s and a new admissions execution receipt declared.

Launcher v2 changes only its duration bound and the corresponding text,
from 3,600 to 14,400 s. The checks on paths, digests, logs and
process-group termination remain identical. The new generations
use the v7 producers, then the v6 preparer and guide.

The ongoing campaign keeps its true earlier producer versions
and its separate resource extension. Neither the checkpoints nor the old
rejections are relabelled by this recipe. The seven regions, the six
admissions and the two trajectory audits must pass on the
files actually delivered before the final guide is produced.
