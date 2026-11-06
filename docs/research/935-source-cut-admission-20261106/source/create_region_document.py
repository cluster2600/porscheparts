"""Save/reopen or separately export a local FreeCAD source-separation review document."""
import hashlib
import json
import os
from pathlib import Path
import time

import FreeCAD as App
import Part


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def counts(shape):
    return [len(shape.Vertexes), len(shape.Edges), len(shape.Faces),
            len(shape.Shells), len(shape.Solids), len(shape.Wires)]


def inspect(document, item):
    feature = document.getObject(item['name'])
    assert feature is not None and feature.Shape.isValid()
    assert counts(feature.Shape) == item['counts']
    assert feature.Placement.Base.Length == 0 and feature.Placement.Rotation.Angle == 0
    assert feature.SourceHash == item['sha256']
    assert not feature.ManufacturingAuthorized and not feature.AnatomicalIdentityAccepted
    return feature


def main():
    job_path = Path(os.environ['PORSCHE_SOURCE_REGION_JOB'])
    job_sha = sha(job_path)
    job = json.loads(job_path.read_text())
    assert job['schema'] == '935-source-region-document-1' and len(job['items']) == 10
    for item in job['items']:
        assert sha(item['path']) == item['sha256']
    mode = os.environ['PORSCHE_SOURCE_REGION_MODE']
    output = Path(job['output'])
    started = time.monotonic()
    rows = []
    if mode == 'build':
        assert not output.exists()
        document = App.newDocument('SourceSeparationReview935')
        try:
            document.UndoMode = 0
            for item in job['items']:
                feature = document.addObject('Part::Feature', item['name'])
                feature.Label = item['label']
                feature.Shape = Part.read(item['path'])
                for name, value in [('SourceHash', item['sha256']),
                                    ('EvidenceRole', item['role']),
                                    ('OriginalArraysHash', job['arrays_sha256'])]:
                    feature.addProperty('App::PropertyString', name, 'Evidence')
                    setattr(feature, name, value)
                for name in ('ManufacturingAuthorized', 'AnatomicalIdentityAccepted'):
                    feature.addProperty('App::PropertyBool', name, 'Evidence')
                    setattr(feature, name, False)
                inspect(document, item)
            document.recompute()
            document.saveAs(str(output))
        finally:
            App.closeDocument(document.Name)
        document = App.openDocument(str(output))
        try:
            assert len(document.Objects) == 10
            for item in job['items']:
                feature = inspect(document, item)
                rows.append(dict(name=item['name'], counts=counts(feature.Shape),
                                 valid=True, identity_placement=True, physical_flags_false=True))
        finally:
            App.closeDocument(document.Name)
    else:
        assert mode == 'export'
        before = sha(output)
        saved = json.loads(Path(job['build_report']).read_text())
        assert before == saved['document_sha256']
        target = Path(job['saved_exports'])
        target.mkdir(mode=0o700, exist_ok=False)
        document = App.openDocument(str(output))
        try:
            assert len(document.Objects) == 10
            for item in job['items']:
                feature = inspect(document, item)
                destination = target / Path(item['path']).name
                if destination.suffix == '.step':
                    feature.Shape.exportStep(str(destination))
                else:
                    assert destination.suffix == '.brep'
                    feature.Shape.exportBrep(str(destination))
                assert destination.is_file()
                rows.append(dict(name=item['name'], file=destination.name,
                                 sha256=sha(destination), bytes=destination.stat().st_size,
                                 exported_from_actual_saved_document=True))
        finally:
            App.closeDocument(document.Name)
        assert sha(output) == before
    assert sha(job_path) == job_sha
    for item in job['items']:
        assert sha(item['path']) == item['sha256']
    report = dict(source_sha256=sha(__file__), job_sha256=job_sha, mode=mode,
                  document_sha256=sha(output), document_bytes=output.stat().st_size,
                  freecad_version=App.Version()[:3], objects=rows,
                  original_inputs_unchanged=True, full_bare_head_created=False,
                  physical_acceptance=False, manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    destination = job['build_report'] if mode == 'build' else job['export_report']
    with Path(destination).open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print('SOURCE_REGION_DOCUMENT_' + mode.upper() + '_OK', flush=True)


main()
