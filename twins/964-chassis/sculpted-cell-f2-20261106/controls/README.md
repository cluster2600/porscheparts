# Generic mesh control

`generic-floor-sill.json` is an authored two-surface numerical control with
explicit assumed coordinates. It is not a vehicle reconstruction, a full cell,
a measured interface set or a manufacturing model. Its fixture identifiers
exist to exercise the mesh schema; the two torsion sets intentionally refer to
the same synthetic end and must not be used as a vehicle load case.

`../mesh_transfinite.py` is byte-identical to the tested private generator. It
partitions the exact tensor surfaces at canonical profile knots, harmonizes
opposite edge counts, and generates quadratic triangular S6 elements. This
bounded method rejects trimmed/nonrectangular faces. It does not supply an
admitted mesher for the full cell's intersecting structural junctions.

The actual control produced 8,464 S6 elements and 17,112 used nodes. Native
adaptive Jacobians had no negative elements; the unchanged independent sampled
quality screen also passed. Closed-profile seam topology and the complete-edge
floor/sill connection passed. These are mesh-method results, with no solver
response or physical qualification.

The source/helper hashes and read-only public-helper replay are recorded in
`../mesh-admission.json`. The current public geometry module differs from its
original capsule, while the relevant evaluator functions have identical ASTs;
598 source-position/normal comparisons gave zero difference. This was a helper
replay, not another meshing or FE run. All raw fields remain private.

Run from the repository root with an already existing empty private parent:

```sh
docker run --rm --platform linux/amd64 --network none --read-only \
  --cpus 1 --memory 2g --memory-swap 2g \
  --tmpfs /tmp:rw,nosuid,size=256m \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  --mount "type=bind,src=/absolute/private/parent,dst=/out" \
  --entrypoint python3 \
  sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f \
  /src/twins/964-chassis/sculpted-cell-f2-20261106/mesh_transfinite.py \
  --model /src/twins/964-chassis/sculpted-cell-f2-20261106/controls/generic-floor-sill.json \
  --h 120 --max-elements 20000 --output /out/new-control
```

Use a fresh output directory. The image is the exercised Gmsh4.12.1/OCC runtime;
this command does not install dependencies or rent compute. A successful mesh
export still needs the separate quality/geometry review before any solve.
