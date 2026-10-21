# Arming the one candidate trial

Preserve all three pending controls. Only a separate ROOT GO can derive `plan.json`, `launch-plan.json` and `command.json`.

For the case plan, set `launch_ready` to true, set `root_GO` and `root_GO_sha256` to the actual reviewed GO, and add exactly that GO file/hash to `files_sha256`. For the launch, change those readiness/GO fields, replace child-command indices **5 and 6** with the active case-plan path/hash, replace the pending-plan input key/hash in place with the active one, and add the GO pin. For the command, change those readiness/GO fields and replace argv indices **4 and 6** with the active launch-plan path/hash. No other fields may change.

For each active control require the entire inverse object and the original serialized bytes to equal its pending file. Preserve map-key order. Rehash all merged source/input/runtime pins and require both nonsymlink output destinations to be absent. Execute the exact original supervisor argv once without nicing the parent or adding host limits. Keep the actual tool handle, native return code, complete outputs, source maps and fresh owned-group closure. There is no retry or downstream authorization.
