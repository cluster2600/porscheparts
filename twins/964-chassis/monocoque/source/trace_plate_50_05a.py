"""Trace the 964 body-in-white outline from plate 50-05a of volume V.

Plate 50-05a ("Dimensions for assembly - from Model 91 onward") draws the
body-in-white in side and plan view, to scale: front wings, doors and lids
off, which is the outline of a monocoque. This script turns those two views
into curves in millimetres:

- side view: the upper profile (front lid, windscreen, roof, rear deck) and
  the lower profile (front apron, floor, rear structure);
- side view: three enclosed openings, the door aperture, the quarter window
  and the rear wheel house;
- plan view: the half width along the car.

Scale and origin come from the plate's own published dimensions: both views
are fitted at 1.1253 / 1.1287 mm per pixel at 400 dpi on the markers whose
fore-aft position is published (see ../../source/plate_50_05a_scale.py). The
fore-aft coordinate d is the distance behind the plate's 0 line (front strut
mounts), as in the datum chain. Heights are anchored on the published
964 height, 1310 mm to the roof.

The plate itself is not in the repository (see
SRC-PORSCHE-WORKSHOP-MANUAL-964-VOL5-BODY). Render page 9 of the local copy at
400 dpi and pass it here; the output, ../data/profiles-50-05a.json, is what
the rest of the pipeline reads. It is a coarse transcription (one point every
13.5 mm), not a copy of the drawing.

    pdftoppm -r 400 -f 9 -l 9 -png "Vol 5 - Body.pdf" page9
    python3 trace_plate_50_05a.py page9-009.png
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.ndimage import median_filter

HERE = pathlib.Path(__file__).parent
OUT = HERE.parent / "data" / "profiles-50-05a.json"

SIDE_CROP = (0.0, 0.10, 0.68, 0.40)     # fractions of the page: side view
SIDE_MM_PX, SIDE_X0 = 1.1253, 1091.0    # mm/px and the 0 line, in the side crop
PLAN_MM_PX, PLAN_X0 = 1.1287, 1222.8    # mm/px and the 0 line, on the page
PLAN_CENTRE_Y = 3164                    # page row of the plan view's centre line
ROOF_MM = 1310.0                        # published 964 height
SEEDS = {"door_aperture": (2100, 650), "quarter_window": (2850, 450), "rear_wheel_house": (3080, 900)}


def side_profiles(page):
    w, h = page.size
    box = (int(w * SIDE_CROP[0]), int(h * SIDE_CROP[1]), int(w * SIDE_CROP[2]), int(h * SIDE_CROP[3]))
    im = np.asarray(page.crop(box).convert("L")) < 128
    width = im.shape[1]
    for r in np.where(im.sum(1) > 0.45 * width)[0]:   # the long horizontal 0 line
        im[r - 1:r + 2, :] = False
    cols = np.arange(430, 3900)
    top = np.full(len(cols), np.nan)
    for i, x in enumerate(cols):
        if 1080 <= x <= 1102:                            # the vertical 0 line
            continue
        ys = np.where(im[160:1215, x])[0]
        if len(ys):
            top[i] = ys[0] + 160
    ok = np.isfinite(top)
    top = np.interp(cols, cols[ok], top[ok])
    tm = median_filter(top, 25)
    top = np.where(np.abs(top - tm) > 25, tm, top)
    body = ndimage.binary_opening(ndimage.binary_fill_holes(im), structure=np.ones((1, 15)))
    bot = np.full(len(cols), np.nan)
    for i, x in enumerate(cols):
        ys = np.where(body[600:1216, x])[0]
        if len(ys):
            bot[i] = ys[-1] + 600
    ok = np.isfinite(bot)
    bot = median_filter(np.interp(cols, cols[ok], bot[ok]), 15)
    ytop = top.min()
    d = lambda x: (np.asarray(x, float) - SIDE_X0) * SIDE_MM_PX
    z = lambda y: ROOF_MM - (np.asarray(y, float) - ytop) * SIDE_MM_PX
    from contourpy import contour_generator
    lab, _ = ndimage.label(~im)
    openings = {}
    for name, (sx, sy) in SEEDS.items():
        mask = ndimage.binary_closing(lab == lab[sy, sx], iterations=3)
        line = max(contour_generator(z=mask[::2, ::2].astype(float)).lines(0.5), key=len) * 2.0
        line = line[::max(1, len(line) // 90)]
        openings[name] = [[round(float(d(p[0])), 1), round(float(z(p[1])), 1)] for p in line]
    step = slice(None, None, 12)
    return ([[round(float(a), 1), round(float(b), 1)] for a, b in zip(d(cols)[step], z(top)[step])],
            [[round(float(a), 1), round(float(b), 1)] for a, b in zip(d(cols)[step], z(bot)[step])],
            openings)


def plan_half_width(page):
    p = np.asarray(page.convert("L")) < 128
    sub = ndimage.binary_opening(p[PLAN_CENTRE_Y:PLAN_CENTRE_Y + 820, :], structure=np.ones((1, 13)))
    pc = np.arange(560, 3960)
    w = np.full(len(pc), np.nan)
    for i, x in enumerate(pc):
        ys = np.where(sub[30:820, x])[0]
        if len(ys):
            w[i] = ys[-1] + 30
    ok = np.isfinite(w)
    w = median_filter(np.interp(pc, pc[ok], w[ok]), 15)
    step = slice(None, None, 12)
    return [[round(float((x - PLAN_X0) * PLAN_MM_PX), 1), round(float(y * PLAN_MM_PX), 1)]
            for x, y in zip(pc[step], w[step])]


def main():
    page = Image.open(sys.argv[1])
    top, bottom, openings = side_profiles(page)
    out = {
        "source": "SRC-PORSCHE-WORKSHOP-MANUAL-964-VOL5-BODY, plate 50-05a, traced at 400 dpi",
        "frame": "d = mm behind the plate 0 line (front strut mounts); z = mm above ground, roof anchored at the published 1310 mm; half width in mm",
        "classification": "coarse transcription of a published drawing; outline only, no section, thickness or surface detail",
        "side_top": top,
        "side_bottom": bottom,
        "plan_half_width": plan_half_width(page),
        "openings": openings,
    }
    OUT.write_text(json.dumps(out, indent=0) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
