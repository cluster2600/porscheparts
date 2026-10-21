# New functional-law candidate: smallest actual-STL image route

This is source/path/display-spec preparation only. The new STL has not been
read, imported or rendered here. No geometry, mesh, existing image or tracked
document has changed. The actual generation ROOT and source hashes are bound
in `sources-and-pending-display-spec.json`.

The smallest existing route is the published surface-remesh figure's
`read_binary()` plus its unchanged `raster_unlit.raster()`. The binary loader
requires exact STL length, finite coordinates and retains every triangle. Its
exact-coordinate indexing is not a tolerance-based repair. The raster helper
already accepts the complete real triangle surface, orthographic camera and
explicit bounds. Reuse its original 30-degree elevation and zero azimuth for
the overview. No old needle count, mask, topology or fidelity verdict is used.

The second panel can reuse the old renderer's projection/depth-sort approach
on every actual STL triangle whose closed 3D bounding box intersects a display
ROI. The proposed ROI is the closed box of the two retained physical source
endpoints of edge 431, expanded on every side by the actual 1 mm radius ceiling.
This covers the whole transition region using measured source datums and an
existing design parameter. It is a display crop, not a thickness, intersection,
stress-peak or candidate boundary-membership measurement. No triangle is
altered, re-triangulated or decimated.

The current source section helper is
`work/carrier-C1-taper-section-preparation-001/extract.py`; the closed section
renderer is `work/carrier-C1-taper-profile-figure-preparation-001/render.py`.
They contain useful oblique-plane and section presentation code, but their
actual cached sections belong to earlier candidates. None can be relabelled
as a section of the new 07b354 master. A new native BREP section would require
a separate reviewed extraction. It is unnecessary for the minimal STL overview
and junction projection proposed here.

The future English caption should identify the actual 637,850-triangle
generation candidate and its 07b354 BREP / 8d0b09 STL authorities. It must say
that this image grants no surface-audit, interface or mechanical qualification.
Any newly closed audit result belongs to its own explicit receipt and cannot
be inherited from earlier C1 or taper images.

A new small renderer can therefore reuse the exact binary loader and raster
source, replace only the old two-surface/needle comparison flow with one
candidate and a source-derived display crop, and keep the real geometry in its
original coordinates. The original VisPy/Matplotlib runtime must be pinned in
that separate full source preparation; no package installation or graphics
probe has been performed here. No render is authorized by this note.
