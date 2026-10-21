# PhysicsNeMo planning handoff

The [bounded source review](NOTE.md) identifies four model alternatives, three
independent data-pipeline options and two reference examples at one pinned
NVIDIA source commit. It defines dataset admission, whole-case splits, training,
held-out validation and inference mapping for the later 962 phase.

**No accepted head labels or trained model exist.** Model alternatives are not
a selection or a runtime result. The VTK reader implements STL surface loading;
its VTP and requested VTU volume paths remain unimplemented in the reviewed
source. Any volume adapter needs its own verification.

The [wording/scope correction](correction.json) preserves the prior local note
identity and the exact replacement used for this successor. Root separately
checked the pinned upstream reader and Python requirement. Earlier local notes
are retained; no source was imported, installed or executed for this publication.
The [manifest](FILES.json) binds both unchanged originals.

See the [engineering programme](../../../ENGINEERING_PROGRAM.md) for the
strength/material → LPBF → Omniverse → PhysicsNeMo handoffs.
