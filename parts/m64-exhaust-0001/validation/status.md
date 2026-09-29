# m64-exhaust-0001 — status and PET-dependent gaps

Date: 2026-09-29. Branch: `wave2/geo-ex-20260929`. Owner: m64-writer.

## Done (this branch)

- Parametric SDF sources authored (`Program.cs`: ManifoldRunner, HeatShield,
  ExhaustTip, OilReturnPipe) — commit `bff747c`.
- csproj wiring complete and **compiles in-container**: `dotnet 9.0.317`,
  `picogk-station:qualified-final-20260928`, `-e UpstreamRoot=/upstream`,
  build succeeded (see `compile-record.md`). Two CS0019 scalar/Vector3
  operator fixes applied; no geometry change.
- `provenance.json` parses (validated with `python3 -m json.tool` after the
  build_state update; 135 lines).
- Printability assessment recorded (`printability.md`).

## Nomenclature source (updated)

The **PET 107-xx transcription has merged on the deck branch**:
`docs/research/pet-107-transcription-2026-09-29.md` (commit `6764002`, on
`wave2/pet107-20260929` / `consolidate/wave2-20260929`; not yet an ancestor
of this branch, so cite-by-path it is). It is now the nomenclature source for
the exhaust/charge-air lines. Consequences already sourced there:

- Heat exchangers `993 211 039 55` / `993 211 040 55` (PET 202-10 pos 1–2):
  identity **sourced** (confirmed in both catalogue tables).
- Cats `993 113 213 57` / `993 113 214 57` (PET 202-15 pos 14–15, BOM line
  M64B-IN-004): identity **sourced**, with recorded caveats (213 57
  single-source locally; 214 -57/-58 suffix pair unresolved).
- Charge-air 107-45 lines confirmed (relevant to lane interfaces only).

The `bom_binding` "identity: missing" entries in `provenance.json` predate
this merge; on the next provenance revision, M64B-IN-004 identity should move
to `sourced` citing the transcription.

## PET-dependent gaps (blocking dimensional validity)

1. **Exhaust manifold / heat-exchanger assembly PET identity still open.**
   The manifold's own PET group (`107-20` on the lane's earlier reading; the
   merged transcription covers 202-10/202-15/107-45, not a manifold-specific
   107-xx fiche with manifold part numbers) does not yet publish a manifold
   part number with position confirmed locally → M64B-IN-003 identity stays
   `missing`.
2. **No dimensions from any PET.** PET fiches are number/description/position
   only — no diameter, thickness, path, flange or tolerance. Every geometry
   driver in `provenance.json` therefore remains ASSUMPTION/SYNTHETIC/DECLARED
   regardless of the identity merge. Unblocking requires scan or OEM drawing,
   not transcription.
3. **Cat/front-section geometry (M64B-IN-004)**: identity now sourced (above),
   envelope still only the Fabspeed laser-scan lead with no extracted
   geometry.
4. **Heat shield (M64B-TR-004)**: service-temperature map needed to settle
   the polymer-vs-metal question (`printability.md` §3); PET gives no
   temperature.
5. **Tip**: FVD declares outlet only; inlet/length/tolerances unpublished.

## Next actions (not this lane's finish scope)

- Run the compiled program in-container → voxel render + STL export +
  `CalculateProperties` mass cross-check against F0 (509.97 g manifold
  screen).
- Re-slice the exported tip/shield meshes through the same 40 µm screen
  pipeline used for the F0 dossiers.
- On consolidation of `consolidate/wave2-20260929`, update provenance
  identity tags and BOM citations to the transcription.
