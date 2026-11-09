# macOS controller closure: owned-group diagnostic

Read AGENTS.md, WORKFLOW.md and workflow-contract.json. A fresh complete
19-phase ledger was generated and checked in the private
`962-controller-closure-20261106/plan.json`. All engineering phases remain
blocked; this is an independent software diagnostic associated with `volume`,
`material_strength`, `lpbf_build` and `lpbf_release`. No phase job executes.

The historical owner005 controller, adapter, actual contract and selected
Python 3.10.11 match their accepted hashes. Do not execute their consumed
once-only admission. Native003 remains prohibited; native005 is untouched.

Before constructing a fresh owner run, test a narrow hypothesis: macOS may
refuse signals to an already-exited but deliberately unreaped group leader.
Use only children created by this diagnostic, with a stopped-child handshake,
PID=PGID=SID certificate, kqueue NOTE_EXIT and deliberate exact-child reap.

Three fixed cases: (1) normal exit, then attempt TERM and KILL before reap;
(2) TERM while live, then KILL after NOTE_EXIT before reap; (3) a TERM-ignoring
live child, then KILL. Record every errno without interpreting EPERM as absence.
After explicit reap, check group absence. No signal is sent after reap.

Use the pinned owner interpreter with -B -I -S. Bound handshake, event wait and
reap to two seconds each; child alarm ten seconds; whole diagnostic thirty
seconds with external observation capped at sixty seconds. Create at most one
child at a time, no network, no Z3, native coupon, head data or geometry.
Save all results in a new private directory. Unexpected errors refuse the
diagnostic and remain recorded. A successful probe does not qualify the
historical controller, its full 60-second interval or any engineering phase.
