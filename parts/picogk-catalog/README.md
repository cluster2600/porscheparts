# PicoGK catalogue models

> [!CAUTION]
> **Concept models, not parts.** Every model here is a voxel rendition of a
> catalogue record's own concept: *not fitted, not tested, not safe, not
> released, not a print file*. Overall envelopes come from the record's cited
> sources where they exist; features added to make the part read as itself
> (flanges, bosses, fillets, lattices, vanes, grooves) are **assumptions**,
> tagged as such. Safety classes are unchanged; nothing here relaxes
> [SAFETY.md](../../SAFETY.md) or a record's status.

The catalogue gallery in the [README](../../README.md) used to show the
concept CAD blocks of `scripts/build_*` and `parts/*/source/*.py`. This
folder replaces those blocks, for every part that has CAD, with a model built
on the pinned PicoGK kernel: hollow where the concept is hollow, filleted, with
the blades, galleries, ribs, double walls and flanges the concept describes.

## How it works

| piece | role |
|---|---|
| `parts/<id>/source/picogk.json` | the part's parameters, each with its basis (`published`, `catalogue`, `community`, `assumption`) and source; `envelope` names the published overall dimensions to check, `envelope_axes` pins each to its axis |
| `<group>/*.cs` | one `IPartGenerator` per part family; groups `rotating`, `engine`, `exhaust`, `body`, `trim` are separate projects |
| `common/` | signed-distance helpers, open-cell lattice, parameters, and the runner that finds generators by reflection |
| `tools/run_part.py` | builds a group and runs one part under a machine-wide lock (parallel native runs crashed the kernel) |
| `tools/finish.py` | independent QA of the STL, then publishes `parts/<id>/derived/<stem>-picogk.stl` (decimated) and a provenance `.json`, and re-renders the preview |

34 of the 35 parts with CAD have a published PicoGK model. The archived
Carrera F0 cooling impeller is deliberately left without one: its images were
withdrawn on 2026-09-29 so a synthetic Carrera block is not read as the Turbo
rotor, and a nicer render would undo that.

`scripts/render_part_previews.py` renders the `-picogk.stl` when one exists,
so the gallery, the part pages and `make part-previews-check` all follow it.
The original concept CAD stays in `derived/` untouched: some of it is pinned by
evidence files.

    python tools/run_part.py <group> <PART_ID>   # needs UpstreamRoot = pinned LEAP 71 sources
    python tools/finish.py <PART_ID>

## What `finish.py` checks before publishing

- **one solid body** and **no sealed void**: a sealed cavity hides from
  inspection and traps powder, resin or water, so hollow parts are drained or
  vented;
- a closed main surface: no open edge, non-manifold edges within
  max(4, 10⁻⁵ of the edges);
- each `envelope` parameter within max(1.5 mm, 2 voxels) of the model's
  extent, on its axis when `envelope_axes` gives one;
- the new bounding box is recorded next to the old concept's, so drift is
  visible. Notable drifts, each explained in the part's `picogk.json`: the front
  lid (67.8 → 109.6 mm tall, the old block was a cylinder-cap placeholder), the
  exhaust-valve record (two valves side by side), the K16 pair (878 mm across
  against 890).

## Lessons from building the models (PicoGK 2.3.0, runtime 26.2)

- `Voxels.IntersectImplicit` does not hollow a solid interior (sparse grid):
  render the infill as its own field and use `BoolIntersect`.
- Every contact needs volume: zero-thickness touches leave separate bodies.
- `Fillet()` after hollowing closes the voids: fillet the outer shape first.
- Clipped gyroids and lattices in thin regions leave sealed pockets and
  crumbs: use an open-cell BCC lattice only where the region is several cells
  thick, otherwise draw it solid.
- Implicit rendering calls back into C# per voxel: keep implicit boxes tight,
  prefer native lattice beams for tubes and struts.
- `.NET` file calls with relative paths resolve against the process
  directory, not the shell's: use absolute paths.

## Limits

- The gallery shows the outside. Internal galleries, lattices, vanes and the
  hollow valve's ribs exist in the models but do not show in a three-quarter
  view.
- Published meshes are decimated (30,000 triangles by default, 90,000 for
  six large smooth parts), after a light Taubin smoothing that removes voxel
  terracing (bounding-box shift recorded, typically under 0.1 mm); the
  full-resolution STL is regenerable in `out/`.
- No model carries a measured interface. Every bolt pattern, pivot and clip is
  a design assumption until measured on a car or a part.
