# Native rounded-cavity study

This editable study trims the inner hollow ends at |X| = 70 mm, rounds their
floor corners to R0.6 mm and fills four explicitly identified closed pockets.
The native body is valid, has one solid and one shell, and has nominal dense
mass 1.277797 kg at 4,420 kg/m³. The strict retained-parent difference is empty.

- `candidate-native.brep` is the audited native source.
- `candidate.step` is its editable exchange export.
- `candidate-fine.stl` is the native tessellation before bounded mesh edits.
- `surface-bounded.mesh64.gz` is the independently audited 71,244-triangle surface.
- `volume.npz` retains the outward-boundary, 213,854-cell TetGen study.

The whole-face rational radial certificate bounds the native floor arcs against
R0.6 mm. The mesh-edit bound of 0.044644 mm is relative to the exported STL;
it is not a complete CAD tessellation certificate. The first coarse mechanical
case still shows a severe lateral-junction hotspot. This variant is not adopted.

[Detailed results and actual images](../../../../../../docs/reports/carrier-resume-20261020/README.md#native-cavity-end-iteration).
