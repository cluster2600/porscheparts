# Held stage-local cap/side region continuity

This source-only adapter compares d2af (869,355 vertices / 1,739,126 faces) to
assembled9d62 (871,731 / 1,743,878). It uses the complete frozen 9,872-face list
in patch-census8750db7d as region authority. That observed region contains 3,470
cap and 6,402 noncap faces. Its measured topology is one component, Euler -4
and six abstract boundary cycles. These cycles are not automatically physical
holes. No old228-disk partition or assumed Euler1 is reused. The current task
selects this exact region for a numerical continuity screen; the old census
itself did not approve repair constraints or semantic feature identity.

`patch_helpers.py` copies connected/patch_groups/patch_topology exactly from
existing audit_quality_features.py. The codec and cyclic-oriented integer face
helper are also exact source slices. No legacy audit entrypoint is called.
The candidate region is every MAX-source new cap face plus every retained
face whose source belongs to the old exact region. MAX is tested before any
original-index lookup. New interior vertices remain local. Known origins are
unique/in-range and retain exact coordinate bytes. All candidate faces with
MAX source must occur in the complete bound cap-to-head face map.

The exterior complements must have a complete one-to-one original face-source
bijection. Every oriented exterior triangle and all retained coordinate bytes
must remain exact; no face is discarded on size, quality, proximity or a grid.
The 38 cap faces identified as exterior by repair-referenceebf9 remain once
outside the region, with exact geometry and orientation, and within the bound
candidate cap map. Their preservation is part of the exterior proof.

Both selected regions are passed to the same retained manifold/vertex-link/
connected-boundary topology helper in their own vertex numbering. The before
result must reproduce the frozen old V/E/F/component/Euler/cycle count, mask,
complete exterior index-row hash, directed boundary edges and coordinate hash.
Candidate component/Euler/loop/boundary counts must equal that measured before
signature. Interior V/E/F changes are reported, not forced equal. Every candidate
boundary vertex must have a known original ID; mapped directed boundary edges
and sorted exact binary64 coordinate-edge bytes must match completely. There
is no approximate boundary association or ambiguous-owner fallback.

Four tiny tests are prepared unrun, with literal fixture inputs/expectations:
a square refined with one new interior point and one fixed exterior triangle;
an annulus refined without changing its two loops/Euler0; retained-coordinate
and MAX-boundary refusals; exterior-winding and duplicate-source refusals.
No arrays, test, adapter, scientific package or native query has run here.
Root owns source/peer review, tiny checks, interpreter/NumPy/resource preflight
and the separate authorized child. Both held authority fields are false.
The script has no hard OS resource controller or automatic retry.

A pass establishes only continuity of this declared d2af-to-9d62 local region,
its fixed exterior and boundary. It is not a complete original894 feature map,
channel/void connectivity or cross-section proof, coolant/dry separation,
wall thickness, OEM identity, global distance/intersection/neighbor admission,
head/volume solver acceptance, strength, LPBF or manufacturing qualification.
