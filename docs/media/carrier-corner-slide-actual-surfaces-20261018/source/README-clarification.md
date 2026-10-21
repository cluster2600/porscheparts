# Section-record clarification

The frozen README's statement that all intersection segments remain in the
output record is too broad. The unchanged renderer computes **all segments
before the display crop** and retains the **full profile counts and coordinate
hashes**, rather than exporting every segment coordinate. The pinned source
STLs, section plane and exact helper reproduce those tessellated sections.

This sidecar corrects documentation only. The frozen renderer, source packet,
all pending controls and original numerical/display operations are unchanged.
Any publication README must use the narrower wording above. A separately
reviewed native-section stage preserves raw native curves and drawing samples;
those prospective records are not supplied by this STL preview.
