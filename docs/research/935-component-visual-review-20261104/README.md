# Source component visual review

Status: executed locally on the owner Mac after the
[whole-source partition audit](../935-source-separation-20261104/README.md).
This review uses every original triangle rather than the earlier sampled point
cloud. It supplies a source-selection diagnostic, not anatomical acceptance,
metrology, a repaired mesh or a new head CAD solid.

## Findings and consequence

Six opaque orthographic views show the complete acquired mesh, with colour by
the independently verified edge-component partition. Six further views isolate
the second component. The latter is a small tubular/annular surface fragment
within one of the visible recesses on the side opposite the chamber. Its 7,289
faces do not represent all attached hardware. Threaded protrusions visibly
remain in the same largest component as the main external surfaces.

These are visual observations and a localisation, **not an accepted identification
of a guide, seat, insert or material**. No component is removed or reclassified.
The two singleton components are also retained. Removing all small disconnected
components cannot supply an accepted bare-head selection. Separating the
visible protrusions from the body requires source-supported region masks and
interface evidence within the largest connected component. The hidden body
surfaces beneath installed hardware cannot be recovered from this display.

The reviewed private images are `all-six-views.png` and
`second-component-six-views.png` under
`~/Developer/PorschePartsArtifacts/935-component-visual-review-20261104/`.
The derived scan images remain private; only code, counts and hashes are in Git.

## Method and checks

The [renderer](../935-source-separation-20261104/source/render_components.cpp)
uses all selected source triangles, per-pixel depth, double-sided flat normal
shading and fixed component colours. It does not decimate, cap, repair, weld,
smooth or drop source faces. Occlusion and subpixel/edge-on faces affect image
visibility; a raster image is not a complete surface inspection. The logged
`faces_winning_pixels` count concerns intermediate depth wins during drawing,
not the final number of visible triangles or source coverage.

The private driver uses a PCA display frame computed from all original vertices.
Its axes are visual coordinates, not anatomical datums. Views look along both
signs of each PCA axis; there is no perspective scaling. Each isolated-component
view is independently fitted to its viewport and must not be used to compare
physical size with the full view. No text-to-CAD model or external service is used.

The independent checker confirms:

- Every renderer face index equals the original decoded triangle array.
- Every projected vertex equals the original coordinate transformed by the
  declared orthonormal display frame.
- All four complete colour-rank partitions equal the independent native labels.
- All twelve render input face counts and image hashes match.
- A nearer overlapping triangle wins regardless of drawing order, reversing
  triangle winding preserves the double-sided image, invalid indices fail, and
  an existing image output is refused.

See the [verification](verification.json) and [receipt](receipt.json). These
checks qualify this diagnostic path only. They do not establish physical
dimensions, component identity or a complete-head interface contract. Reproduction
driver and checker snapshots are preserved privately; the public C++ helper
accepts private projected vertices, original indices, component ranks and counts.
It writes PPM, refuses an existing output and requires a new private destination.

## Correspondence and remaining completion gates

The known supplier thread was reread and a scoped search refreshed. It still
contains three messages; the single recent scoped result is the existing owner
reply. No new same-specimen measurement, internal drawing/CT, alloy or treatment
package was received in that scope. This is not an exhaustive mailbox search.
No message or draft was changed; the declined request remains unsent.

The [completion requirements](../935-readiness-20261104/README.md) remain open:
faithful closed geometry needs missing specimen surfaces and accepted interfaces;
functional simulation needs sourced material, loads and reference correlation;
a qualified metal job needs an exact process and measured calibration; physical
inspection, professional review and engine validation require external work.
The present diagnostic cannot replace any of those inputs. No paid computation,
solver solve, manufacturing job, specimen measurement or physical test is
claimed in this increment.
