# Four source-exact solid USD exports

The four inspected project solids now have native USDC exports that preserve every oriented source triangle at the original STL float32 precision. The complete independent comparison found no missing or extra triangles and zero world-bound discrepancy in each case. All eight official minimum USD checks passed for each file.

| Bore (mm) | Source triangles | Indexed points | USDC bytes | Missing / extra triangles | Bound delta (mm) | Minimum checks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 95 | 1,804,706 | 902,145 | 17,370,409 | 0 / 0 | 0 | 8 / 8 |
| 98 | 1,810,730 | 905,157 | 17,454,761 | 0 / 0 | 0 | 8 / 8 |
| 100 | 1,815,416 | 907,500 | 17,530,213 | 0 / 0 | 0 | 8 / 8 |
| 102 | 1,819,798 | 909,691 | 17,592,545 | 0 / 0 | 0 | 8 / 8 |

[manifest.json](manifest.json) binds the source, output and evidence hashes. The raw files are retained as byte-exact local copies for user-review archives; no raw runtime, private path, host or command is published here. Each stage uses millimetres, Z-up, identity transforms and subdivision disabled. It contains no external asset references, assigned materials, physical properties or solver fields. The native outputs were neither stripped nor repaired.

The [bore 95 record](../usd-exact-bore95/README.md) established and independently reviewed this explicit source-authoring route. The separately frozen [98](../usd-exact-bore98/README.md), [100](../usd-exact-bore100/README.md) and [102](../usd-exact-bore102/README.md) records use the unchanged code, exact mapping policy, genuine minimum-validator prerequisite and bounded native execution. The earlier [vendor derivative](../usd-bore95-conversion/README.md) remains rejected for its topology/coordinate changes.

This establishes preservation of the existing study meshes. Historical accuracy, fitment, full Asset Validator/SimReady validation, rendering, head CFD/CHT/FEA and calibrated LPBF/material performance remain open. These exports do not authorize manufacturing.

[Download the four verified review ZIPs](../usd-review-delivery/README.md) from the existing draft release. The publication receipt verifies new server digests and preservation of the twelve older assets.
