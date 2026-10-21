# Arming the saved-stock local check

Preserve `pending-plan.json`, `pending-launch-plan.json` and `pending-command.json`. A separate ROOT GO may derive three active controls only.

In the case plan, change `launch_ready`, `root_GO`, `root_GO_sha256` and add that one actual GO pin. In the launch, change the readiness/GO fields, child command indices **5 and 6** to the active plan path/hash, replace its pending-plan input key/hash in place, and add that same GO pin. In the command, change readiness/GO fields and argv indices **4 and 6** to the active launch path/hash. No other field may change.

Require all three whole inverse objects and original serialized-byte inverses, preserving map order. Rehash the full current merged pins and require fresh nonsymlink output/execution paths. Execute the exact original supervisor argv once; do not nice or add limits to the parent. Collect the real tool handle, return code, all raw/results/source maps and fresh owned-group closure. No retry or downstream stage is authorized.
