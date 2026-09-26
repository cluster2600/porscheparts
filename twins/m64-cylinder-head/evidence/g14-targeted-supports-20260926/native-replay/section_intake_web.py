"""Actual retained CAD cut through the intake web; visualization only."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import cadquery as cq

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT/'work/m64-g14/cad-outer-intake-web-v1/outer_intake_inboard_web_p/carrier_base_p.step'
EXPECTED = 'fa09420ccf9b49e387a59c40de87a4f0842ace53d7c04c3b1d20dda7e5f64829'
OUTPUT = ROOT/'work/m64-g14/view-intake-web-section-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(INPUT) == EXPECTED, 'retained STEP changed'
    assert cq.__version__ == '2.6.1', 'unqualified CAD export version'
    renderer = shutil.which('rsvg-convert')
    if renderer is None:
        raise RuntimeError('rsvg-convert is required')
    original = cq.importers.importStep(str(INPUT)).val()
    assert original.isValid() and len(original.Solids()) == 1
    section = original.cut(cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-30, -500, -500)))
    assert section.isValid() and 0 < section.Volume() < original.Volume()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    for name, direction in (('section-xminus30', (1, 0, 0)),
                            ('section-xminus30-isometric', (1, -1, -.8))):
        svg = OUTPUT/(name+'.svg')
        png = OUTPUT/(name+'.png')
        cq.exporters.export(cq.Workplane().add(section), str(svg), opt={
            'projectionDir': direction, 'showHidden': False, 'width': 900, 'height': 600})
        subprocess.run([renderer, '-b', 'white', '-o', str(png), str(svg)], check=True, timeout=60)
        assert png.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert sha(INPUT) == EXPECTED, 'source STEP modified during export'
    receipt = dict(classification='native_CAD_visualization_only', input_STEP_sha256=EXPECTED,
        source_sha256=sha(Path(__file__)), input_unchanged=True, section_plane_x_mm=-30,
        retained_half='x <= -30 mm', input_valid_one_solid=True, section_valid_nonempty=True,
        cadquery_version=cq.__version__, renderer_version=subprocess.check_output(
            [renderer, '--version'], text=True).strip(),
        views_sha256={p.name: sha(p) for p in sorted(OUTPUT.iterdir())},
        geometry_redesigned=False, FEA_executed=False, manufacturing_authorized=False,
        engine_start_authorized=False, scope='Isolated support cut through the new intake web; not the complete head or a stress field.')
    with (OUTPUT/'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
