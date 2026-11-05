"""Read-only FreeCAD reopen and actual saved-feature STEP round trip."""
import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            result.update(block)
    return result.hexdigest()


job = json.loads(Path(os.environ['PORSCHE_SOURCE_CHART_JOB']).read_text())
expected = json.loads(Path(job['report']).read_text())
output = Path(os.environ['PORSCHE_OBSERVED_SHEET_ROUNDTRIP_DIR'])
if output.exists() or sha(job['output']) != expected['output_sha256']:
    raise RuntimeError('Existing round-trip output or changed native document refused')
document = App.openDocument(job['output'])
for item in job['items']:
    feature = document.getObject(item['name'])
    shape = feature.Shape
    counts = [len(shape.Vertexes), len(shape.Edges), len(shape.Faces), len(shape.Shells), len(shape.Solids)]
    if (counts != item['counts'] or not shape.isValid() or feature.ManufacturingAuthorized
            or feature.SourceSTEPHash != item['sha256'] or not feature.Placement.isIdentity()):
        raise RuntimeError('Saved feature topology, placement or evidence metadata changed')
output.mkdir(parents=True)
step = output/'saved-observed-sheet.step'
document.getObject('ObservedAxialSheet').Shape.exportStep(str(step))
App.closeDocument(document.Name)
if sha(job['output']) != expected['output_sha256']:
    raise RuntimeError('Read-only native reopen changed the input document')
(output/'native-reopen.json').write_text(json.dumps({
    'native_document_readonly_reopen_passed': True, 'document_sha256': expected['output_sha256'],
    'all_feature_counts_and_placements_match': True, 'actual_saved_feature_exported': True,
    'step_sha256': sha(step), 'source_sha256': sha(__file__),
    'independent_export_geometry_check_pending': True, 'physical_acceptance': False,
    'manufacturing_authorized': False}, indent=2)+'\n')
print('OBSERVED_SHEET_NATIVE_ROUNDTRIP_EXPORTED')
