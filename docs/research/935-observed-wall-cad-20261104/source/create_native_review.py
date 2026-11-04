"""Run inside FreeCAD's native console with a non-secret review job specification."""
import hashlib
import json
import os
from pathlib import Path
import FreeCAD as App
import Part


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8388608),b''):h.update(block)
    return h.hexdigest()


spec=json.loads(Path(os.environ['PORSCHE_WALL_REVIEW_JOB']).read_text())
baseline=Path(spec['baseline']);output=Path(spec['output']);report=Path(spec['report'])
if output.exists() or report.exists():raise RuntimeError('Existing native delivery refused')
if digest(baseline)!=spec['baseline_sha256']:raise RuntimeError('Frozen baseline mismatch')
for item in spec['items']:
    if digest(item['path'])!=item['sha256']:raise RuntimeError('Checked STEP input mismatch')
doc=App.openDocument(str(baseline));group=doc.addObject('App::DocumentObjectGroup','ObservedWallReview')
created=[]
for item in spec['items']:
    feature=doc.addObject('Part::Feature',item['name']);feature.Label=item['label'];feature.Shape=Part.read(item['path'])
    if not feature.Shape.isValid() or len(feature.Shape.Faces)!=item['faces'] or feature.Shape.Solids:raise RuntimeError('Native imported surface check failed')
    feature.addProperty('App::PropertyString','EvidenceRole','Evidence');feature.EvidenceRole=item['role']
    feature.addProperty('App::PropertyString','InputSHA256','Evidence');feature.InputSHA256=item['sha256']
    feature.addProperty('App::PropertyBool','ManufacturingAuthorized','Evidence');feature.ManufacturingAuthorized=False
    group.addObject(feature);created.append(feature.Name)
doc.recompute();output.parent.mkdir(parents=True,exist_ok=True);doc.saveAs(str(output));App.closeDocument(doc.Name)
opened=App.openDocument(str(output));checks=[]
for name,item in zip(created,spec['items']):
    obj=opened.getObject(name)
    if obj is None or not obj.Shape.isValid() or len(obj.Shape.Faces)!=item['faces'] or obj.Shape.Solids or obj.ManufacturingAuthorized:raise RuntimeError('Native saved-document check failed')
    cylindrical=sum(type(face.Surface).__name__=='Cylinder' for face in obj.Shape.Faces)
    if item['role']=='conditional_cylindrical_fit' and cylindrical!=item['faces']:raise RuntimeError('Native document lost analytical cylinder surfaces')
    checks.append({'object':name,'role':item['role'],'faces':len(obj.Shape.Faces),'solids':len(obj.Shape.Solids),'valid':obj.Shape.isValid(),'cylindrical_faces':cylindrical})
App.closeDocument(opened.Name)
if digest(baseline)!=spec['baseline_sha256']:raise RuntimeError('Baseline changed during review generation')
result={'native_reopen_verified':True,'new_objects':checks,'baseline_unchanged':True,'freecad_version':App.Version()[:3],
    'new_solid_created':False,'functional_head_accepted':False,'manufacturing_authorized':False,'output_sha256':digest(output)}
with report.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print('OBSERVED_WALL_REVIEW_OK')
