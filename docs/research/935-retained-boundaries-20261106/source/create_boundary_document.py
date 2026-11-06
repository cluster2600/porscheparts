"""Create/reopen or freshly export the complete private FreeCAD boundary-review document."""
import hashlib
import json
import os
from pathlib import Path
import time

import FreeCAD as App
import Part


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def counts(shape):
    return [len(shape.Vertexes),len(shape.Edges),len(shape.Wires),len(shape.Faces),len(shape.Solids)]


def inspect(document,item):
    feature = document.getObject(item['name'])
    assert feature is not None and feature.Shape.isValid() and counts(feature.Shape)==item['counts']
    assert feature.Placement.Base.Length==0 and feature.Placement.Rotation.Angle==0
    assert feature.SourceBRepHash==item['sha256'] and feature.BoundaryCurveIndex==item['curve']
    assert list(feature.OriginalAtlasCharts)==item['atlas_charts']
    assert list(feature.RawAcquisitionCurves)==item['raw_curve_ids']
    assert feature.DeclaredCutRegion==item['declared_cut_region'] and feature.Representation==item['representation']
    assert feature.PhysicalRole=='unreviewed' and not feature.ClosureAuthorized and not feature.ManufacturingAuthorized
    return feature


def main():
    path = Path(os.environ['PORSCHE_BOUNDARY_REVIEW_JOB']);job_sha = sha(path);job = json.loads(path.read_text())
    assert job['schema']=='935-boundary-review-document-1' and len(job['items'])==968
    for item in job['items']:assert sha(item['path'])==item['sha256']
    mode = os.environ['PORSCHE_BOUNDARY_REVIEW_MODE'];output = Path(job['output']);started = time.monotonic();rows = []
    if mode=='build':
        assert not output.exists();document = App.newDocument('RetainedSourceBoundaryReview935')
        try:
            document.UndoMode = 0
            for item in job['items']:
                feature = document.addObject('Part::Feature',item['name'])
                feature.Label = 'Unreviewed source boundary '+str(item['curve']).zfill(4)+' - '+item['representation']
                feature.Shape = Part.read(item['path'])
                for name,value in [('SourceBRepHash',item['sha256']),('SourceBoundaryPlanHash',job['boundary_sha256']),
                                   ('EdgeOriginCounts',json.dumps(item['origin_counts'],sort_keys=True)),
                                   ('Representation',item['representation']),('PhysicalRole','unreviewed'),('ReviewNotes','')]:
                    feature.addProperty('App::PropertyString',name,'Evidence');setattr(feature,name,value)
                for name,value in [('BoundaryCurveIndex',item['curve']),('DeclaredCutRegion',item['declared_cut_region'])]:
                    feature.addProperty('App::PropertyInteger',name,'Evidence');setattr(feature,name,value)
                for name,value in [('OriginalAtlasCharts',item['atlas_charts']),('RawAcquisitionCurves',item['raw_curve_ids'])]:
                    feature.addProperty('App::PropertyIntegerList',name,'Evidence');setattr(feature,name,value)
                for name in ('ClosureAuthorized','ManufacturingAuthorized'):
                    feature.addProperty('App::PropertyBool',name,'Evidence');setattr(feature,name,False)
                inspect(document,item)
            document.recompute();document.saveAs(str(output))
        finally:App.closeDocument(document.Name)
        document = App.openDocument(str(output))
        try:
            assert len(document.Objects)==968
            for item in job['items']:
                feature = inspect(document,item);rows.append(dict(curve=item['curve'],counts=counts(feature.Shape),
                    source_hash_and_chart_links_verified=True,identity_placement=True,physical_role_unreviewed=True,closure_and_manufacturing_flags_false=True))
        finally:App.closeDocument(document.Name)
    else:
        assert mode=='export';before = sha(output);prior = json.loads(Path(job['build_report']).read_text())
        assert before==prior['native_document_sha256'];target = Path(job['saved_exports']);target.mkdir(mode=0o700,exist_ok=False)
        document = App.openDocument(str(output))
        try:
            assert len(document.Objects)==968
            for item in job['items']:
                feature = inspect(document,item);destination = target/Path(item['path']).name
                feature.Shape.exportBrep(str(destination));assert destination.is_file()
                rows.append(dict(curve=item['curve'],file=destination.name,sha256=sha(destination),bytes=destination.stat().st_size,
                                 actual_saved_shape_exported=True,source_readback_required=True))
        finally:App.closeDocument(document.Name)
        assert sha(output)==before
    for item in job['items']:assert sha(item['path'])==item['sha256']
    assert sha(path)==job_sha
    report = dict(source_sha256=sha(__file__),job_sha256=job_sha,mode=mode,objects=rows,
                  native_document_sha256=sha(output),native_document_bytes=output.stat().st_size,
                  freecad_version=App.Version()[:3],object_count=len(rows),source_geometry_moved=False,
                  source_faces_or_solids_created=False,physical_classifications_accepted=0,
                  any_curve_filled=False,full_bare_head_created=False,manufacturing_authorized=False,
                  seconds=time.monotonic()-started)
    destination = job['build_report'] if mode=='build' else job['export_report']
    with Path(destination).open('x') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    print('COMPLETE_SOURCE_BOUNDARY_DOCUMENT_'+mode.upper()+'_OK',flush=True)


main()
