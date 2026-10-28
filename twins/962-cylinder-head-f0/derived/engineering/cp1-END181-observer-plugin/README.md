# END181 passive DOF-map observer plugin — compiled, runtime pending

The [observer source](source/CouponEnd181DofMap.C) and
[registration shim](source/CouponEnd181ObserverRegistration.C) are prepared for
the existing MOOSE Combined host. The
[independent source review](review/source-peer.json) passes within its source
scope. The plugin and standalone validator executable compile and link.
Standalone guards, positive host registration and native measurement remain
separate pending results in this checkpoint.

Observer003 changes exactly one registration label from observer002 and adds a
three-pointer registration entry. Its operational functions, header and all
18 synthetic validator assertions are preserved. It uses the direct Output
base, reads existing global DOF/coordinate/scaling metadata and performs no
assembly or solution update. Six constraint flags are explicitly expected
original-case labels; they are not live boundary-condition observations.

The map is intended to connect the coupon's 1,275 displacement DOFs to the
passively captured solution, residual and update vectors at END181. The existing
[coupon equilibrium diagnostic](../cp1-richardson2-END181-equilibrium/README.md)
still retains its twelve aggregate failures; no cause or numerical floor is
established by this source preparation.

The [finite build recipe](source/build-recipe.json) contains two compilations,
one owned plugin link and a separate standalone guard link. A fresh library
descriptor is materialized only after the actual plugin exists. No framework,
module or Fortran build is proposed. Root
[build admission](build/root-admission.json) and
[toolchain probes](build/toolchain-probe.json) record the local attempt scope.
They describe preparation; the later build result below records compilation
and linking. ABI compatibility and solver execution remain unverified.

Two first compilation attempts stopped in their resource monitors before any
compiler diagnostic or artifact: [attempt 001](build/attempt001-receipt.json)
and [attempt 002](build/attempt002-receipt.json). The first treated an unavailable
non-gating thread observation as fatal; the second refused a nonpositive RSS
observation. The offending raw row and exact process/state association were not
retained. Both owned groups were absent at
closure. These are monitor failures, not compiler/ABI diagnoses; no build success
or native measurement follows. A corrected monitor retains reported nonnegative
RSS rows under the same aggregate cap.

In [attempt 003](build/attempt003-receipt.json), both production source files
compiled. Its plugin link returned zero with SDK-description warnings, and the
standalone validator link failed on unresolved system symbols. The bundled
linker could not parse the selected SDK's newer system-library description.
[Attempt 004](build/attempt004-receipt.json) selected the matching Command Line
Tools linker but stopped at its `libLTO.dylib` filename requirement. Both failed
checkpoints and their diagnostic text remain.

The [successful build 005](build/attempt005/build-result.json) reuses both
production objects unchanged. It substitutes the matching Command Line Tools
linker and LTO library in the captured linker arguments, compiles the unchanged
standalone validator main and links both outputs. All three commands returned
zero; the [static link metadata](build/attempt005/compiled-link-metadata.json)
records the registration export and system-library load commands. Duplicate
rpath warnings remain. All 67 protected records and the clean source revision
remained unchanged. Peak sampled owned-group RSS was 450,002,944 bytes and
owned build/log output was 568,154 bytes; these are sampled observations.

The validator still inherits an absolute historical `libmoose` load dependency.
Resolving it through an explicit supported loader environment is required before
execution. Link success establishes neither runtime resolution nor ABI acceptance.
The [build result](build/attempt005/BUILD-RESULT.md),
[literal commands](build/attempt005/finite-build-argv.json) and
[owned receipt](build/attempt005/receipt.json) preserve the exact checkpoint.
The [independent build review](review/build005-peer.json) passes the saved build
and static link associations only; it grants no runtime or ABI acceptance.

The exact [MOOSE source acquisition](build/public-source-acquisition.json) is
commit 7c06bdcefd02f9f31f4508839f21f410561309a4, tree
4106bbd47b9387bda37cff0d679735c57c5391bc. Upstream source remains separate;
this archive includes our observer and metadata only. Installed solver libraries
are preserved. The [input fragment](source/plugin-input.i.fragment) is held and
must preserve the original coupon physics/settings when later integrated.

[FILES.json](FILES.json) binds the archived originals. No guard execution,
accepted mechanical trajectory, strength, material/process qualification or
manufacturing release is claimed.
