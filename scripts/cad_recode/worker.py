"""Run ONLY inside the disposable, networkless CAD container."""
import json
from pathlib import Path
import cadquery as cq

scope = {'__name__': '__generated__', 'cq': cq}
exec(compile(Path('/input/candidate.py').read_text(), '/input/candidate.py', 'exec'), scope)
shape = scope['r'].val()
if not shape.isValid() or not shape.Solids():
    raise ValueError('generated shape is not a valid solid')
d = json.loads(Path('/input/intake.json').read_text())
shape = shape.scale(1.0 / d['cad_recode_output_factor'] / d['normalization_scale'])
shape = shape.translate(tuple(d['center']))
cq.exporters.export(shape, '/output/candidate.step')
# Independent evaluation reads this STEP in a separate trusted process.
