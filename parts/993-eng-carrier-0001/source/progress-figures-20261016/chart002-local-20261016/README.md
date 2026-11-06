# Local correction of skin 2 — 16 October 2026

Historical status: **Local case admitted — complete region in progress**. This
plate explains a local result; it grants no global admission to the region or
to the layers of the engine support.

The three JSON files in `inputs/` are strictly identical copies of the real
inputs and results of the `full-repair-003` replay. The renderer checks their
SHA-256 digests, the computed polygons and the five certificates of quadrilaterals
fully contained in the source domain. The historical paths present in these
receipts remain metadata: the render does not open them.

From this directory, with Python, Matplotlib **3.11.2** and Shapely **2.2.0**:

```sh
python render.py /tmp/993-chart002-replay-001
```

The output directory must be new. The command exports the same plate as
PNG, SVG and PDF, then a receipt binding the script, the local inputs and the
three exports. It runs no `native_infill`, remapping or support generation
computation. `reference/` keeps the render replayed with this script and its
receipt; the PNG is identical to the accepted local plate. Internal dates of
the vector exports may vary on reproduction.

The [portability receipt](portable-validation.json) keeps the replay after
extraction, the PNG identity and the refusal of an already existing output.
