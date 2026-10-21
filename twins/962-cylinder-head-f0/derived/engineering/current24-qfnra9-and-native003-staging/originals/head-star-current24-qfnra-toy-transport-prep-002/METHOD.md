# Persistent-Z3 toy transport002: final deadline refusal gates

This is a SOURCE-ONLY, HELD and UNRUN successor. Preparation001 remains byte-for-byte historical evidence, including its five unrun framing expectations and its original pending-result fields. No actual, external owner, runtime refresh, solver invocation, test, source import or execution authority is created here.

Root's static review identified a real control gap in001: pump() checks its supplied deadline before select/read, but the final select/read can return late and finish the loop. The original exchange() could then decode and serialize the full response and return without checking its original per-query deadline. The global60s check did not enforce the separate5s query limit. Normal drain and each TERM/KILL drain-wait phase had the same final-blocking-operation window.

## Exact production delta

Only three lines are inserted into the complete preserved helper:

1. In exchange(), after frame.response() and complete response/transcript serialization, require time.monotonic()<until immediately before returning the response.
2. In the normal close path, after final drain, wait and returncode0 check, require time.monotonic()<until immediately before its return.
3. In each existing TERM/KILL cleanup phase, after final drain and wait, require time.monotonic()<until immediately before the existing break.

The query and normal-drain until expressions remain min(self.deadline,time.monotonic()+QUERY_SECONDS). Cleanup keeps its original time.monotonic()+grace for each existing stage. The same strict-before convention already used by pump() is retained: equality refuses. No new time allowance is granted. These are final refusal checks, not preemptive scheduling or hard real-time guarantees.

Removing exactly the three inserted lines reconstructs the full001 helper bytes. No code is moved or replaced. All imports, four other Session methods, all other definitions and the full run_fixed_toys() caller remain exact. The unchanged frame/pump code retains all raw chunks and the unchanged Capture.record retains the complete response record before a late query refusal. A final check may itself happen after the wall-clock limit; such a result refuses rather than being labelled a timely completion.

## Failure and cleanup semantics

A late query raises ToyRefusal only after its full response/transcript has been retained; the existing caller records the traceback and stops the five-session sequence. There is no alternative query, candidate, solver process or retry.

A late normal drain is recorded by the existing normal_drain exception handler. Existing cleanup still runs, and the existing caller's no-cleanup-errors gate refuses completion even when the direct solver has already exited0. Thus exit0 does not erase a missed5s drain bound.

A late TERM phase is recorded as a terminate cleanup error, then follows the already existing KILL-stage path. If the child was already reaped, that path sends no signal. A late KILL phase is recorded as a kill cleanup error. This retains the existing two-stage cleanup policy; it does not add a cleanup retry or permit successful toy acceptance after an error. Direct-child status and complete raw logs remain evidence, and the external owner's independent process-group absence/cleanup gates remain necessary. No unknown status is converted to0.

Global60s, per-query and normal-drain5s, TERM8s, KILL8s, requested thread-one environment, sampled group2GiB, inclusive32MiB, no retry, same owned group, fixed five formulas, exact expected words, pinned protocol, solver argv/options and all physical/head/native false scopes are unchanged. The future owner's complete startup/preflight/full-return clock and inclusive receipt/control/output budget are still mandatory. This packet does not author that owner.

## Unrun expectations

The five original ToyFramingExpectations methods are unchanged. Their fixture differs only in the new helper SHA256/length pin; reversing those two bindings recovers the entire original fixture.

A separate ToyDeadlineExpectations class has four source-only methods:

- Exact pinned exchange() with fake final pump and fake response-record serialization: timely completion returns, equality/late completion refuses, and the complete response record remains. An earlier global deadline also constrains the original until.
- Exact pinned close() normal path with fake final pump/wait: timely drain has no error, equality/late pump or wait retains normal_drain refusal even with direct returncode0.
- Exact pinned close() failure path with fake TERM/KILL stages: late TERM or late KILL retains the corresponding full-return error and the existing escalation/signal record.
- AST-only ordering: the three final checks follow full transcript serialization or wait, precede success return/break, and do not add or relocate until assignments.

The future fake harness extracts only the pinned ToyRefusal/need and exact Session.exchange/close definitions into a restricted namespace. Its clocks, selector, streams, capture and direct process are fake. It never imports the transport module, protocol, solver, process APIs, real selectors or time/sleep APIs. It has no mechanism to spawn, signal, wait for or probe an operating-system process. The original Frame-only harness remains separate. All nine framing/control methods are UNRUN here; no future control count or pass is implied.

## Prior evidence and limits

The separate14 emitter/protocol and9 independent word-validator synthetic methods were subsequently accepted by root at acceptance e143cf35 and final census3d2ce163. This is new002 provenance only. It neither edits historical001 pending fields nor proves any persistent-Z3 transport, framing, installed parameter, model-continuity or runtime capability. Their root acceptance expressly excludes installed-Z3 and current-head results.

The saved Z3 version/binary/link descriptors remain historical expected metadata, with current identity and installed source/ABI equivalence unproven. No runtime binary/provider body is read or hashed. Formula aliases, original predicates, complete initial/final model/projection and all mapper request/reply records remain required; a hash alone is not same-model proof.

Independent002 source/fixture review, root source review, any guard controls and guard result, runtime freshness, external owner, actual and root admission remain pending/null. No solver or toy invocation follows from this preparation. No current23-input coefficient, coordinate, model, word or499-cell validation occurs. The24 head-quality failures and12 aggregate mechanical failures remain. Material, strength, LPBF, digital twin, PhysicsNeMo, manufacturing and application qualification remain absent.

The author is lpbf_linear_refinement, who authored001 toy transport, earlier14 head-kernel donor, method/source peers, row-first sampler and independent499 word validator. The author is not an independent reviewer of this correction.
