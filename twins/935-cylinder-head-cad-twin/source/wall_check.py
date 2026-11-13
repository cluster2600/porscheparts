#!/usr/bin/env python3
"""Share of the print body's surface that lies in thin walls, on the occupancy grid.

A second measurement beside the layer screen's thickness probe, which grows a
tangent sphere on a triangle surface and is stopped by the roughness of that
surface: on the 0.5 mm marching-cubes surface it reported 25% of its probes
below 1.5 mm, on the 1.0 mm surface 7%.

Here a voxel is in a wall thinner than t when no ball of diameter t that fits
inside the solid covers it (a morphological opening, by two distance
transforms on the 0.25 mm grid). The ball also cannot reach into a sharp
convex edge, so edges count as thin: the shares are upper bounds for walls.

Usage: wall_check.py OCC_DIR OUT.json      (about 6 GiB; run it capped)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage


def thin_shares(solid: np.ndarray, pitch: float, walls=(1.0, 1.5, 2.0)) -> dict:
    edt = ndimage.distance_transform_edt(solid, sampling=pitch).astype(np.float32)        # distance to air
    surface = solid & ~ndimage.binary_erosion(solid)
    out = {"pitch_mm": pitch, "solid_voxels": int(solid.sum()), "surface_voxels": int(surface.sum()), "walls": {}}
    for wall in walls:
        radius = wall / 2.0
        centres = edt > radius                                   # centres of the balls of this radius that fit
        if not centres.any():
            thin = solid
        else:
            reach = ndimage.distance_transform_edt(~centres, sampling=pitch).astype(np.float32)
            thin = solid & ~(reach <= radius + 0.5 * pitch)
        out["walls"][f"below_{wall:g}_mm"] = {
            "share_of_surface_voxels": round(float((thin & surface).sum() / surface.sum()), 4),
            "share_of_volume": round(float(thin.sum() / solid.sum()), 4)}
    return out


def main(occ_dir, out) -> None:
    occ_dir = Path(occ_dir)
    grid = json.loads((occ_dir / "occupancy-grid.json").read_text())
    array = occ_dir / grid["array"]
    solid = np.asarray(np.load(array, mmap_mode="r") > 0.5)
    record = {"schema": "935-cad-twin-print-body-wall-check/1",
              "method": "morphological opening of the occupancy with balls of 1.0, 1.5 and 2.0 mm diameter; a voxel no "
                        "fitting ball covers is in a thinner wall or at a sharp convex edge",
              "occupancy_sha256": hashlib.sha256(array.read_bytes()).hexdigest(),
              **thin_shares(solid, float(grid["pitch_mm"])),
              "claims": "an upper bound for the share of thin walls at the grid pitch; not a minimum-wall map and not a "
                        "dimension of the specimen"}
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["walls"]))


if __name__ == "__main__":
    main(*sys.argv[1:])
