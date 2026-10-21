# Exact source-only arming contract

No rendering is authorized by these pending controls. Preserve each pending
file byte for byte. After a separate ROOT GO, create distinct `plan.json`,
`launch-plan.json`, and `command.json` only.

For `plan.json`, change `status` to `ARMED_ROOT_AUTHORIZED` and `launch_ready`
to true; set `root_GO` and `root_GO_sha256` to the actual relative GO path and
whole byte SHA. Add that one GO path/SHA to `files_sha256`. No other value or
existing pin changes.

For `launch-plan.json`, make those same four status/readiness/GO changes. Set
`command[8]` to the actual armed plan SHA. Add exactly the actual GO pin and
actual armed `plan.json` pin to `inputs_sha256`; the original pending-plan pin
remains. No other change is permitted. In particular, command paths, isolated
interpreter flags, cwd shim, output/execution paths and budgets remain exact.

For `command.json`, make those same four status/readiness/GO changes, set
`rendering_not_authorized` to false, and replace only `argv[6]` with the armed
launch SHA. The original pending plan/launch hashes remain historical fields.

For each object, undo exactly these edits and require the complete JSON object
and its canonical stored bytes to equal the original pending file. Record all
three inverses. Then verify all current input/source/runtime hashes, actual
argv, fresh outputs and GO before the single owned supervisor call. The outer
parent is not given a second nice setting. No render or scientific import is
part of this preparation.
