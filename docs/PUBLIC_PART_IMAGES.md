# Public part images for PorscheFanatics

Requirement `REQ-PUBLIC-PART-IMAGES`: every catalogue record has a public visual,
and every created CAD part has views made from its own archived geometry. This
applies to new parts and geometry updates, not just the current batch.

`catalog/parts/*.json` remains the source of truth. The renderer writes
`parts/<lowercase-part-id>/media/preview.png` and `preview.json`; CAD renders also
have `views.png`. These paths match PorscheFanatics's pinned Git importer.

The current catalogue has 43 records: 36 geometry renders and 7 status cards.
Status cards do not close part-image gaps; see [the image gap register](PART_IMAGE_GAPS.md).
Six cards explicitly say that no geometry has been created. The seventh preserves
the withdrawal of the synthetic Carrera F0 impeller views, which could be mistaken
for the Turbo fan. A card depicts no part geometry and must never be captioned as
a CAD rendering. Digital-twin CAD listed in a record is supported, including the
engine bracket and mount whose STL files live outside their part folders.

Each `preview.json` records the part identifier, image kind, caption (`note`),
publication terms, source CAD hashes, catalogue record hash and image hashes.
Repository-owned images are prepared for owner-authorized PorscheFanatics use;
third-party photographs and PET illustrations are not copied. A render provides
no evidence of dimensional accuracy, fit, material qualification or print release.

## Create or update images

```sh
make part-previews
# Or use a local Python environment with pyvista/VTK, build123d and Pillow >= 10.1:
python scripts/render_part_previews.py --write --only PART_ID
python3 scripts/render_part_pages.py --write
make part-previews-check
make check
```

`--list` includes all records, so the batch includes status cards. Missing declared
CAD fails rather than silently producing a card. `make check` rejects missing
previews, empty image lists, wrong image kinds, changed CAD, changed records,
missing images and image bytes that differ from their recorded hashes.
The focused regression suite is `tests/test_render_part_previews.py`.

## Import into the website

Commit the catalogue and images together. In the PorscheFanatics checkout, import
that exact commit:

```sh
node scripts/import-porscheparts.mjs --repo /path/to/porscheparts --rev COMMIT_SHA
npm test
npm run build
npm run audit:build
```

The website importer verifies publication manifests before replacing its existing
assets, converts the PNGs to WebP and retains their kinds and public captions.
Catalogue status cards have their own captions and alternative text. Source
geometry and internal evidence paths stay in the private repository.
Importing and building locally do not publish the website; production deployment
and its public verification remain a separate step.
