#!/usr/bin/env python3
"""Skin contact for a bionic frame under an exact skin (run after topopt.py).

    python bionic_skin_contact.py <PART_ID>

topopt.py leaves every element whose centre lies in a "void" region empty, so
with coarse elements the smoothed members can stop up to half an element
short of a thin skin (2-3 mm) that lies just inside that void. This step:

0. optional (bionic.json "postprocess_threshold"): a grey design is re-projected
   at a stated density level (a number) or at the level that keeps its material
   volume ("volume");

1. drops floating fragments: connected members (density > 0.5, face-connected),
   and the thick cores left by a one-element opening of them (what survives
   shaping.smooth_mm), that neither touch the skin-side void (shapes whose
   path holds "above-" or "outside-") nor reach a "solid" keep-in. They carry
   no load once the design is thresholded and would be separate bodies;
   optional (bionic.json "postprocess_bridge"): member groups are joined to
   the main frame along the densest path left by the optimizer, fragments
   without such a path are dropped, members are extended up to the skin and
   one-element-deep members get a second element (see bridge() and main());
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


def bridge(src, solid, allowed, floor, firm=0.75):
    """Join every member group (density > firm, face-connected, solid keep-ins
    included) to the group holding the most keep-ins, along the path of
    highest density the optimizer left between them (Dijkstra, step cost
    0.02 + (1 - rho)^2, inside the design domain), nearest group first. Path
    elements are set to 1, so a member that thinned out mid-span (e.g. at a
    bending inflection) stays one element thick instead of vanishing in the
    smoothing. A group without keep-in whose best path crosses an element
    below density "floor" is a fragment, not a member: it is dropped. Groups
    holding a keep-in (pads) are always joined."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    shape = src.shape
    n = src.size
    rho = src.ravel().copy()
    idx = np.arange(n).reshape(shape)
    ok = allowed.ravel()
    rows, cols, w = [], [], []
    for ax in range(3):
        a = np.take(idx, np.arange(shape[ax] - 1), axis=ax).ravel()
        b = np.take(idx, np.arange(1, shape[ax]), axis=ax).ravel()
        m = ok[a] & ok[b]
        a, b = a[m], b[m]
        c = 0.02 + 0.5 * ((1 - np.clip(rho[a], 0, 1)) ** 2 + (1 - np.clip(rho[b], 0, 1)) ** 2)
        rows += [a, b]
        cols += [b, a]
        w += [c, c]
    G = coo_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    added = n_bridges = n_small = 0
    paths = np.zeros(n, bool)
    while True:
        dense = (src > firm) | solid
        lab, nl = ndimage.label(dense)
        if nl <= 1:
            break
        pads = np.bincount(lab[solid].ravel(), minlength=nl + 1)
        main = int(np.argmax(pads[1:])) + 1
        flat = lab.ravel()
        src_nodes = np.flatnonzero(flat == main)
        dist, pred = dijkstra(G, indices=src_nodes, min_only=True, return_predecessors=True)[:2]
        others = (flat > 0) & (flat != main)
        if not np.isfinite(dist[others]).any():
            break
        end = int(np.flatnonzero(others)[np.argmin(np.where(np.isfinite(dist[others]), dist[others], np.inf))])
        path = []
        k = end
        while k >= 0 and flat[k] != main:
            path.append(k)
            k = pred[k]
        p = np.array(path, int)
        gap = p[flat[p] == 0]
        if pads[flat[end]] == 0 and (not len(gap) or rho[gap].min() < floor):
            # a group the optimizer left no material path to (it reaches the
            # frame only through near-void): a fragment, not a member - drop it
            soft, _ = ndimage.label((src > 0.5) & ~solid)
            k = soft.ravel()[end]
            src = np.where((lab == flat[end]) | ((soft == k) & (k > 0)), 0.0, src)
            n_small += 1
            continue
        cur = src.ravel().copy()
        added += int((cur[p] <= 0.5).sum())
        cur[p] = 1.0
        paths[p] = True
        src = cur.reshape(shape)
        n_bridges += 1
    # the grid path is a staircase in plan: its in-plane neighbours get 0.45,
    # so the 0.5 iso-surface fills the stair notches (a smooth 1-element member)
    ring = ndimage.binary_dilation(paths.reshape(shape), structure=np.ones((1, 3, 3), bool)) & allowed
    src = np.where(ring, np.maximum(src, 0.45), src)
    return src, (f"{n_bridges} member gaps bridged along the densest path ({added} elements set to 1), "
                 f"{n_small} fragments without a material path dropped, ")


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
    note_t = ""
    level = spec.get("postprocess_threshold")
    if isinstance(level, (int, float)) and not isinstance(level, bool):
        # grey design re-projected at a stated density level (bionic.json says why)
        free = (~void) & (~solid)
        t = float(level)
        src = np.where(free, np.clip(0.5 + (src - t) / 0.2, 0.0, 1.0), src)
        note_t = f"re-projection at density {t:.3f}; "
    elif level == "volume":
        # grey design (members at 0.3-0.5 when the run stops at beta 4): re-project
        # it at the level t that keeps its material volume, sum(rho) = count(rho > t),
        # with a soft 0.2-wide band so the iso-surface stays smooth
        free = (~void) & (~solid)
        vals = np.sort(src[free])[::-1]
        target = float(src[free].sum())
        t = float(vals[min(int(round(target)), len(vals) - 1)])
        src = np.where(free, np.clip(0.5 + (src - t) / 0.2, 0.0, 1.0), src)
        note_t = f"volume-preserving re-projection at density {t:.3f}; "

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
    # in the smoothing: keep dense elements next to a firm (> 0.65) anchored core.
    # Skipped after a re-projection at a stated level: that level was chosen so
    # the frame is connected, and its weakest links sit just above 0.5.
    if not note_t.startswith("re-projection"):
        lab, n = ndimage.label(src > 0.65)
        keep = np.zeros(n + 1, bool)
        keep[np.unique(lab[anchor])] = True
        keep[0] = False
        drop |= dense & ~ndimage.binary_dilation(keep[lab], iterations=1)
    drop &= ~solid
    src = np.where(drop, 0.0, src)
    note_b = ""
    if spec.get("postprocess_bridge"):
        allowed = (~void) & (topopt.region(opt["design"], C).reshape(shape) | solid)
        src, note_b = bridge(src, solid, allowed, float(spec["postprocess_bridge"].get("floor", 0.15)),
                             float(spec["postprocess_bridge"].get("firm", 0.75)))
        # an inner frame is bonded to the skin: a member element that the
        # optimizer placed lower in the slab is extended up its column to the
        # skin-side void (no wire hanging under the skin)
        if spec["postprocess_bridge"].get("fill_to_skin"):
            dense_v = np.where(src > 0.5, src, 0.0)
            up = dense_v.copy()
            for k in range(1, shape[0]):
                up[k] = np.where(allowed[k], np.maximum(up[k], up[k - 1]), up[k])
            n_up = int(((up > 0.5) & (src <= 0.5)).sum())
            src = np.maximum(src, up)
            note_b += f"members extended up to the skin ({n_up} elements), "
        # members the optimizer left one element deep (in the top layer they sit
        # half inside the 2 mm skin and read as broken): copy such a member
        # element to the element under it, inside the design slab
        if spec["postprocess_bridge"].get("min_two_elements_deep"):
            d = src > 0.5
            above, above2 = np.zeros_like(d), np.zeros_like(d)
            above[:-1], above2[:-2] = d[1:], d[2:]
            val = np.zeros_like(src)
            val[:-1] = src[1:]
            grow = allowed & ~d & above & ~above2
            src = np.where(grow, val, src)
            note_b += f"one-element-deep members deepened to two elements ({int(grow.sum())} elements), "
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
    meta["postprocess"] = (f"{Path(__file__).resolve().relative_to(ROOT).as_posix()}: {note_t}{int(drop.sum())} elements of "
                           f"{n_frag} floating fragments dropped, {note_b}{int(holes.sum())} pocket elements filled; members copied one element into "
                           f"adjacent void elements ({n_grown} elements), trimmed flush by the void in PicoGK")
    meta_path.write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(meta["postprocess"])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
