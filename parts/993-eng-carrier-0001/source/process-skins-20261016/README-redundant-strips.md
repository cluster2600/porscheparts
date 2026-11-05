# Contact strips already contained in the sheet

Chart 2 of the left region has five correct `upper` contacts on its lower
edge. The neighbouring faces and their parents agree: this is a terrace in
three dimensions, not a role to invert. The five quadrilaterals proposed
towards `+Z`, with the 0.2 mm penetration already declared, are entirely
contained in the free domain of the sheet.

`redundant_strip_interfaces.py` keeps the incremental constructor 814 and the
operations of 943. For a direction opposite to the local edge, it proves
rationally that the ENTIRE quadrilateral is included in the source domain.
Only then does it log `excluded_redundant_inside_source_domain` and not add
its triangles. The sheet, the traces and their roles remain present. The
geometric union is identical since the strip is already in D.
A strip that is partly outside, crosses a hole or is not proved keeps the
refusal. Without this case, the five former witnesses keep exactly their WKB
and their constructor receipt.

The wrapper `continuous_redundant_interfaces.py` explicitly declares the SHA
of the new constructor as the authority. The former checkpoints keep their 943
authority; they must be re-evaluated through the corresponding admission path,
without modifying their metadata. The same evidence of coverage, strip,
contacts, three-dimensional connection and exposure remains necessary.

The v6 inputs keep the arguments of the v5 inputs. They also record D, the
interfaces and their identities before each infill call for a skin, then the
result or the error in `chart-progress/`. These logs admit no geometry. They
make it possible to examine a new refusal without replaying the skins that
precede it.

The real chart passed the native infill, the complete repair, the exact
coverage and strip, the domain and component contacts, then the remap.
This witness does not replace the generation and audit of the whole region.
The compact evidence and the SHAs of the local receipts are in
`combinatorial-evidence/redundant-results.json`.
