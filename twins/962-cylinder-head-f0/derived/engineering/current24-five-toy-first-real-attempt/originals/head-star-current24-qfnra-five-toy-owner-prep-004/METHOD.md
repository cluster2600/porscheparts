# Full five-toy owner004: C01/C02 source policy

HELD/UNRUN source preparation only. Root authority665c9b2abf06be390b5ecc5313933b50c26203cdec314b74ecb24dd3de9b3f45 permits only the C01 continuation boundary, C02 private non-polling leader lifetime policy, and three source-preparation namespace003-to004 changes. Frozen003 and the F1-pinned source002 remain unchanged. The existing operational HOLD is not lifted by this source packet.

## C01: continuation intent and acknowledgement

The owner latches local and recorded continuation intent before SIGCONT. A distinct continuation_acknowledged flag is set only after the syscall returns. If it raises, continuation_error preserves the actual traceback and the original outer failure path still records its failure. Acknowledgement means only that the syscall returned; it does not prove adapter execution, solver startup or a child observation.

Cleanup selects the retained certified group after any attempted continuation, whether the return was acknowledged or raised. It never infers that a raised return means no signal delivery. Before a retained certificate/continuation intent, the original own-direct-PID-only boundary remains. No new signal, child, retry, observation loop or deadline renewal is introduced. Original TERM/KILL/reap gates and unknown-direct-relationship refusals remain unchanged.

## C02: private destructor and unknown construction

A private _RetainedPopen subclass has exactly one method: a no-op __del__. Construction uses that class; every successfully returned handle is still held in HELD_LEADERS and by the local reference. No inherited poll, wait, communicate, context-manager or signal cleanup method is added. Existing exact-PID/kernel/group operations are not otherwise changed.

The constructor boundary records attempted, returned and actual exception evidence separately. If construction raises, partial_construction_unknown and the existing direct_relationship_unknown are set. No PID/group is read from an exception or invented partial object, no signal/wait/absence is guessed, and no constructor retry is performed. Existing failure/normal predicates refuse that path; a partial construction is never a positive candidate or an inferred zero/absence.

Installed base-constructor and subprocess active-list behavior remain independently unproved. A private destructor is an explicit source policy, not proof that the installed constructor cannot create, wait, poll, register, release or partially fail in another way. Runtime/guard review must address that boundary separately; this packet makes no observed-runtime claim.

Root separately confirmed the existing bounded raw os._exit(2) refusal may also cover unknown partial construction. A separate last_resort_partial_construction_exit flag records this path. The existing last_resort_unreaped_exit flag continues to describe a returned unreaped handle. After permitted bounded preservation/flush attempts, either case takes raw _exit(2), bypassing ordinary owner teardown. This is neither hard preemption nor cleanup/reap/group-absence proof. Missing/partial receipt or preservation failure stays unknown/nonzero. Returned leaders remain strongly retained; no positive handle is invented for the partial-construction path.

## Exact unchanged boundary

The stable argv_prefix fix, future execution D/toys names, selected historical3.10.11 -B -I -S route, T002 transport/protocol, five case IDs/formulas/queries, sampled RSS/query code and all science/physical predicates remain unchanged. The owner's final F1 complete_candidate and RC conjunctions remain byte exact; new failures still flow through their original refusal conditions. The F1 nine-case fixture remains pinned to source002 and is not rebound or rerun.

Limits remain absolute40normal/48TERM/56KILL-reap/60full, TERM8/KILL8, min(5,remaining normal40) RSS-command timeout, sampled owned2GiB, inclusive32MiB, thread-one environment and no retry. These source bounds are not new timing, hard-wall, true-peak, hard-quota, API, ABI or installed-behavior results. The adapter and wrapper change only their one preparation namespace literal each.

Bindings enumerate every exact source replacement, original/new line block, global/definition/import disposition, the new class/method and eight new diagnostic fields. Complete forward and inverse diffs recover all three original003 units. No new module import or scientific kernel is added.

Preparation reads only named first-party source/metadata and performs text/hash/JSON/AST checks. No target or fragment is imported, compiled, evaluated, executed or tested; no runtime/provider/alias body or process/API/query is observed; no future operational path is inspected or created. No actual, admission, output, native005, PUB/Git, solver/head, material/LPBF, twin, PhysicsNeMo, physical or manufacturing action is authorized. Independent full source review, meaningful fake guards, current finite runtime/API acceptance and actual/control/admission review remain separate.
