# Declared reference data

Masses, envelopes and materials transcribed **from third parties**. Nothing
here was measured by this project, and the file says so on every line.

Two automatic safeguards:

- each entry carries the `source_id` of the record that attests it, and the
  validator rejects an entry whose source does not exist in the register;
- the `caveat` field flags the cases where the lightweight version is **not**
  an equivalent replacement but a removal of function or safety — race doors
  without an intrusion bar, a steering wheel without an airbag, heater removal,
  a structural welded panel.

A mass without a source is a rumor. That is exactly what this directory exists
to prevent.

## Assembly skeleton

`993-assembly-skeleton.json` carries the other half of the twin: **where each
part is**. Ten systems, 239 illustrations, 12,864 counted references, derived
from a factory catalog kept outside this repository.

It is an **aggregate**, and the validator keeps it that way: an illustration can
carry only its number, its count and its labels. Any extra key — a part number,
for example — makes `make check` fail.

Counting parts is a fact; copying a catalog's rows is a copy. The rule is
therefore enforced by the validator, not by good will.

Regenerate: `python3 scripts/twin_structure.py --listing <atlas>/oem-listed.json --out catalog/reference/993-assembly-skeleton.json`

## Filling the twin: what works and what does not

Research carried out on August 28, 2026 to find the masses of the major
assemblies.

**Yields nothing.** Forums, German ones included, weigh lightweight parts,
never assemblies. No published mass for the gearbox, the axles, the bare body
shell, the empty fuel tank or the brake system. This is not a research gap:
these values are not published.

**Yields something, but not automatically.** Vendor product pages carry a mass
per part number, and one of them organizes its catalog by PET diagrams, hence
in the same frame as the assembly skeleton: `SRC-ROSEPASSION-993-PARTS`.

**Correction of August 28, 2026.** This document claimed that this vendor
"responds to automated retrieval." That was false: its `robots.txt` closes the
entire site to Claude agents, by name and first. A server returning a page is
not permission. See
[decisions/0003-no-vendor-harvesting.md](../../docs/decisions/0003-no-vendor-harvesting.md).

**Consequence for method.** The twin is filled **part number by part number**,
targeting the ones that weigh the most: the skeleton says where they are, the
selector says which ones matter. But the mass is transcribed **by hand, in a
browser**, or obtained by written permission. No tool in this repository will
fetch it on its own.
