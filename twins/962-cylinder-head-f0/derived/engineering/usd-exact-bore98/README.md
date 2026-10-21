# Bore 98: source-exact USD geometry preparation

The inspected bore 98 solid passed the unchanged exact geometry gate and all eight official minimum USD checks. Its 1,810,730 original oriented triangles and 905,157 indexed points survive the native OpenUSD serialization, with no missing or extra triangles and zero world-bound discrepancy. Units are millimetres, up-axis Z, the transform is identity and subdivision is disabled.

This uses the [reviewed bore 95 source-authoring route](../usd-exact-bore95/README.md), with the same frozen writer, reader, comparator and limits. The original vendor derivative remains rejected and unchanged. The frozen preparation contract precedes execution; the separately retained first95 clearance permitted this case. The local author and native serialization reports describe their respective intermediate phases; [receipt.json](receipt.json) records the subsequent independent audit and minimum results.

The byte-exact raw USDC is retained locally for user review; this capsule publishes only safe provenance. No private paths, commands, runtime binaries, external asset references, authored materials, physics schemas or solver fields are included. The raw output was never stripped or repaired. Complete artifact captures were authenticated against their original execution capture hash.

This demonstrates source-mesh preservation only. Historical fidelity, full Asset Validator/SimReady validation, rendering, head CFD/CHT/FEA, calibrated materials/process and manufacturing qualification remain open.
