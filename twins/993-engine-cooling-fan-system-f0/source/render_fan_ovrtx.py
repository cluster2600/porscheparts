#!/usr/bin/env python3
"""Render a prepared wrapper through the pinned OVRTX 0.3.0 runtime."""
import argparse
import os
os.environ['OVRTX_SKIP_USD_CHECK'] = '1'
import numpy as np
from PIL import Image
import ovrtx
from ovrtx import Device, Renderer, RendererConfig

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('stage')
parser.add_argument('output')
parser.add_argument('--time-code', type=float, default=0.)
args = parser.parse_args()
assert ovrtx.__version__ == '0.3.0'
# This existing image predates OVStage attachment; use its standalone scene owner.
renderer = Renderer(config=RendererConfig(sync_mode=True))
renderer.open_usd(args.stage)
renderer.update_from_usd_time(args.time_code)
try:
    for _ in range(48):
        products = renderer.step(render_products={'/Session/Render/Product'}, delta_time=1/60)
        product = products['/Session/Render/Product']
        for frame in product.frames:
            if 'LdrColor' in frame.render_vars:
                with frame.render_vars['LdrColor'].map(device=Device.CPU) as rv:
                    pixels = np.from_dlpack(rv).copy()
    assert pixels.ndim == 3 and pixels.shape[2] == 4 and pixels.dtype == np.uint8
    assert np.std(pixels[:, :, :3]) > 2 and len(np.unique(pixels[:, :, :3].reshape(-1, 3), axis=0)) > 100
    assert np.count_nonzero(np.ptp(pixels[:, :, :3].astype(int), axis=2) > 20) > 1000, 'Missing field/proxy colours'
    Image.fromarray(pixels).save(args.output)
    print('Nonuniform OVRTX frame saved:', args.output)
finally:
    renderer.reset_stage()
