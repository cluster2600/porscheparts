# Observer lifetime correction: actual build checkpoint

The new registration shim and plugin compiled and linked once, using the unchanged
original production observer object. Both commands and the corrected controller
returned 0. The [full receipt](execution002/receipt.json) preserves all statuses,
arguments, resource observations and logs, including the complete duplicate-rpath
linker warning. The previous [host SIGSEGV](../cp1-END181-observer-host-check-failure/README.md)
remains unchanged.

The [2,291-byte shim](source004/src/CouponEnd181ObserverRegistration.C) adds one
process-lifetime counted reference to its own loaded image after path and entry-point
base checks. A successful reference is intentionally retained through application
teardown. The [proposal](lifetime-proposal/proposal.json) documents why a mapped-image
flag alone would not provide the required C++ object lifetime. This candidate is a
specific loader-lifetime correction; the original crash cause is still unproved.
The operational observer source, header and 18-assertion fixture are byte-identical;
the fixture was not rerun by this build.

The exact recipe contains one 326-argument shim compile and one 36-argument plugin
link. The 153 ordered include pairs and previous SDK/link route are preserved.
Only the new shim/object and plugin output paths change. The captured new object
is 11,952 bytes (SHA-256 `daf8648bc4bfe0d77a33c9986a192ca20db67cf1e2e21ef067d22b4f6fb1137b`);
the plugin is 167,504 bytes (`29539701e9436234fdbc52ba8f5ccbef3c489b1b4d6f504e0b1eb0218b70c2bd`).
Binaries are retained in the engineering workspace; their identities are published here.

The original [held owner001 review](held-exact-child-peer001/review.json) caught
three observation gaps before execution. The [additive correction](owner002/correction.json)
retains an exit-race exception, keeps an unsampled RSS peak unknown and checks the
60-second limit after the full receipt write. Owner001 remains unrun. The
[corrected exact-child review](exact-child-peer002/review.json),
[saved-result review](result-peer002/review.json) and
[separate root decision](root-observation002/result-peer-acceptance.json) retain
reviewer lineage and the mandatory outer-return-code condition.

The admitted build completed in 5.495906166 seconds at the saved pre-final boundary.
All 75 identities and 12 selected path associations remain unchanged. Both owned
process groups are absent after waiting; there are no stop or cleanup failures.
The build and result directories total 264,887 bytes, or 268,949 including the
external root admission. Peak sampled group RSS was 431,882,240 bytes during
compilation. These observations do not establish a hard resource quota.

This capsule contains byte-exact first-party source and metadata copies.
[FILES.json](FILES.json) records every capsule file except itself. Frozen records
retain original workspace paths; the publication map records their copied locations.
Raw grids, native fields, runtime libraries, third-party source trees and object/plugin
binaries are excluded. Static exports/dependencies, host shutdown, callbacks and
live DOF capture remain separate checks. The twelve aggregate equilibrium failures,
head material/strength, calibrated LPBF and manufacturing gates remain open.
