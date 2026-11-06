# PicoGK piston screen re-run with a manifold output stage (2026-11-05)

Re-run of the F0 screen in `../picogk-f0/` (kept frozen) for issue #468.

## Diagnosis

The F0 audit found 3 to 109 "non-manifold" edges per STL. Welding the raw
PicoGK meshes exactly (1e-6 mm) shows **no** edge shared by more than two
faces and no boundary edge. Every defect is a triangle with two coincident
vertices (4 per plain variant, 148–160 on the rib variants). Its collapsed edge
is counted three times. Voxel smoothing (`Smoothen(0.25)`) was tried and
rejected: it raised the count to ~300.

## Output stage

`run_picogk_optimization_screen.cs ... --manifold-output` drops those
triangles before writing the STL. No vertex is moved, so the geometry and the
enclosed volume are unchanged. The removed count per variant is in
`geometry.removed_coincident_vertex_triangles`.

## Reproduction

1. `tessellate_step_master.py` (in the `3dprinting993-cadsim:dev` container,
   network off) tessellates
   `parts/993-eng-piston-cp1-gallery-f0-0001/derived/piston_cp1_gallery_f0.step`
   (SHA-256 `6c534476…ddea1`) with a linear tolerance of 0.05 mm and an angular
   tolerance of 0.2 rad. Source STL SHA-256 `4d70fc74…7b41`, 12,334
   triangles. The F0 source mesh (`80180e4b…`) no longer exists anywhere
   available, so F0 and this run are not byte-comparable. Volumes differ by
   about 0.9 %.
2. The PicoGK generator runs on the WSL2 host with the native runtime extracted
   from `porscheparts-picogk-native:dev` (image ID in the screen JSON).
3. `verify_picogk_optimization_outputs.py` audits with
   `trimesh process=True`, the same method as F0.

The STLs (~40 MB each) are kept out of Git. Their hashes are in the screen JSON.

## Verdict

- `picogk-output-integrity.json`: **passed_output_mesh_integrity**. All six
  meshes are single, closed, consistently wound, edge-manifold bodies.
- **Design selection: none.** Every variant still fails the provisional ambient
  plate margin of 1.50 (best 1.07), so `selected_variant` stays `null`.

This is mesh topology only. It authorizes no CAD promotion, LPBF slicing,
manufacture or engine operation.
