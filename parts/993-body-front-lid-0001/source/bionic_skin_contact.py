#!/usr/bin/env python3
"""Skin contact for a bionic frame under an exact skin (run after topopt.py).

    python bionic_skin_contact.py <PART_ID>

topopt.py leaves every element whose centre lies in a "void" region empty, so
with coarse elements the smoothed members can stop up to half an element
short of a thin skin (2-3 mm) that lies just inside that void. This step:

1. drops floating fragments: connected members (density > 0.5, face-connected),
   and the thick cores left by a one-element opening of them (what survives
   shaping.smooth_mm), that neither touch the skin-side void (shapes whose
   path holds "above-" or "outside-") nor reach a "solid" keep-in. They carry
   no load once the design is thresholded and would be separate bodies;
   pockets enclosed by members and the skin are filled (no sealed void);
2. copies every remaining member one element further, into the void elements
   that touch it (6-neighbours, max of their densities). BionicTopology then
   subtracts the same void exactly, so the members end flush with the outer
   skin surface and always overlap the skin. Nothing grows anywhere else.

Idempotent: the topopt.py density is saved once as .density.raw.bin and
every run starts from it (a fresh topopt.py run, which clears "postprocess"
in .density.json, refreshes that copy). Rewrites parts/picogk-catalog/out/bionic/<PART_ID>.density.bin and
records the step in .density.json ("postprocess").
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "parts" / "picogk-catalog" / "bionic"))
import topopt  # noqa: E402  (region tests only)


def main(part_id):
    spec = json.loads((ROOT / "parts" / part_id.lower() / "source" / "bionic.json").read_text(encoding="utf-8"))
    opt = spec["optimization"]
    out = ROOT / "parts" / "picogk-catalog" / "out" / "bionic"
    meta_path = out / f"{spec['part_id']}.density.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    nx, ny, nz = meta["shape_xyz"]
    h = float(meta["element_mm"])
    lo = np.array(meta["origin_mm"], float)
    ix, iy, iz = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    order = lambda a: a.transpose(2, 1, 0).ravel()
    C = lo + (np.stack([order(ix), order(iy), order(iz)], 1) + 0.5) * h
    shape = (nz, ny, nx)
    voids = opt.get("void", [])
    void = topopt.region(voids, C).reshape(shape)
    skin = topopt.region([s for s in voids if s["type"] == "stl" and ("above-" in s["path"] or "outside-" in s["path"])], C).reshape(shape)
    solid = topopt.region(opt.get("solid", []), C).reshape(shape)
    raw = out / f"{spec['part_id']}.density.raw.bin"            # topopt.py output, kept for reruns
    if not raw.exists() or not meta.get("postprocess"):
        raw.write_bytes((out / f"{spec['part_id']}.density.bin").read_bytes())
    rho = np.fromfile(raw, np.float32).reshape(shape)
    src = np.where(void, 0.0, rho)

    # members one element thin do not survive shaping.smooth_mm (an opening),
    # so connectivity is judged on the opened member set
    dense = src > 0.5
    opened = ndimage.binary_opening(dense, structure=ndimage.generate_binary_structure(3, 1))
    anchor = ndimage.binary_dilation(skin) | ndimage.binary_dilation(solid, iterations=2)
    drop = np.zeros_like(dense)
    n_frag = 0
    for mask in (dense, opened):                  # whole members, then their thick cores
        lab, n = ndimage.label(mask)                 # face-connected: edge contacts vanish in the iso-surface
        keep = np.zeros(n + 1, bool)
        keep[np.unique(lab[anchor])] = True
        keep[0] = True
        drop |= ~keep[lab]
        n_frag += int((~keep[1:]).sum())
    # marginal struts (0.5-0.65) that hang only on other marginal elements break
    # in the smoothing: keep dense elements next to a firm (> 0.65) anchored core
    lab, n = ndimage.label(src > 0.65)
    keep = np.zeros(n + 1, bool)
    keep[np.unique(lab[anchor])] = True
    keep[0] = False
    drop |= dense & ~ndimage.binary_dilation(keep[lab], iterations=1)
    drop &= ~solid
    src = np.where(drop, 0.0, src)
    # pockets closed by members and the skin would be sealed voids: fill them
    shut = (src > 0.3) | skin
    holes = ndimage.binary_fill_holes(shut) & ~shut & ~void
    src = np.where(holes, 1.0, src)

    grown = np.zeros_like(src)
    for ax in range(3):
        for sh in (1, -1):
            s = np.roll(src, sh, axis=ax)
            idx = [slice(None)] * 3
            idx[ax] = slice(0, 1) if sh == 1 else slice(-1, None)
            s[tuple(idx)] = 0.0                    # no wrap-around
            grown = np.maximum(grown, s)
    new = np.where(void, grown, src).astype(np.float32)
    n_grown = int(((new > 0.5) & void).sum())
    new.ravel().tofile(out / f"{spec['part_id']}.density.bin")
    meta["postprocess"] = (f"{Path(__file__).resolve().relative_to(ROOT).as_posix()}: {int(drop.sum())} elements of "
                           f"{n_frag} floating fragments dropped, {int(holes.sum())} pocket elements filled; members copied one element into "
                           f"adjacent void elements ({n_grown} elements), trimmed flush by the void in PicoGK")
    meta_path.write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(meta["postprocess"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
