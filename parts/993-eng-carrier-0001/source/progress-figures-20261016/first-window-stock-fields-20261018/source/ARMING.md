# Figure 33 exact future controls

Keep all three pending files immutable. After a separate ROOT render GO, create
plan.json, launch.json and command.json. No source, data, runtime, crop, operator,
threshold or resource may change during arming. Each entire inverse must equal
its pending JSON object and original stored bytes, preserving absent keys.

Plan whitelist: launch_ready=true, root_GO_sha256=actual GO SHA, and one added
files_sha256 entry for the existing declared ROOT GO path. The root_GO path is
already declared and stays unchanged.

Launch whitelist: launch_ready=true, root_GO_sha256=actual GO SHA; command[4]
becomes the actual plan.json path and command[5] its actual SHA; replace only the
pending-plan input key with plan.json at that same insertion position and add
one ROOT GO input pin. Keep all previous runtime/data/source pins unchanged.

Command whitelist: launch_ready=true, argv[4] becomes the actual launch.json
path and argv[6] its actual SHA. Other values remain identical. The supervisor
is the original 4d18, with 180 seconds outer and cleanup10+10. The child is the
original SYSTEM Python3.10 -B without -I, no parent nice wrapper; child nice10,
BLAS1,150-second alarm,CPU140/141 and zero Python workers. Retain original OS
user-site behaviour; render() changes cwd to / before graphics work.

Before any launch, verify all pending inverses, fresh hashes and absent output
and execution directories. Run the exact approved argv once, retain the real
handle/RC/logs/group closure, all three exports and complete render receipt.
No publication, solver, native CAD, remesh, retry, staging or commit is included.

Before the first authoring operation, run the official marker exactly once:

`/Users/maxime/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node /Users/maxime/.codex/plugins/cache/openai-primary-runtime/pdf/26.1009.11318/skills/pdf/container_tools/mark_artifact_operation_started.mjs --operation-kind create --expected-output-count 1 --output-format pdf`

Retain its actual return code and output before invoking the owned renderer. No marker or authoring is performed by source preparation.
