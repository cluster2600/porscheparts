#!/usr/bin/env python3
"""Compose two same-scan open CAD fragments in their derived support frame."""
import argparse
import hashlib
import json
from pathlib import Path
import FreeCAD as App
import Part


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('shaft',type=Path); p.add_argument('support',type=Path); p.add_argument('transform',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
work=Path(__file__).resolve().parents[4]/'work'
if a.output.exists() or not a.output.resolve().is_relative_to(work.resolve()): raise SystemExit('use fresh private work output')
expected=('8d78c70ae3f2a43bc5f4cadb0e43980c4b3b853465b0806060d738b58074c89b','3246d98fca2c5df2bdbe2b8457be3f87fa6ffba2b98f46de97886417969c0d00','11039619a1e206090b28ee919faaf4d2f96107d47a63809a9f77a39811cf0d04')
if tuple(sha(x) for x in (a.shaft,a.support,a.transform))!=expected: raise ValueError('input hash mismatch')
data=json.loads(a.transform.read_text())
if data['status']!='same_scan_coordinate_mapping_not_fit_validation' or data['scale_verified'] or data['physical_registration_verified'] or data['mating_interface_verified']: raise ValueError('invalid mapping status')
m=data['shaft_cad_to_support_cad']; matrix=App.Matrix()
for i in range(4):
    for j in range(4): setattr(matrix,f'A{i+1}{j+1}',m[i][j])
shaft=Part.read(str(a.shaft)); support=Part.read(str(a.support))
for shape in (shaft,support):
    if not shape.isValid() or len(shape.Solids) or not shape.Faces: raise ValueError('invalid or solid input')
area0=shaft.Area; point0=shaft.Vertexes[0].Point; moved=shaft.copy(); moved.transformShape(matrix)
expected_point=matrix.multVec(point0)
if not moved.isValid() or len(moved.Solids) or len(moved.Faces)!=len(shaft.Faces) or abs(moved.Area/area0-1)>1e-7 or (moved.Vertexes[0].Point-expected_point).Length>1e-7: raise ValueError('rigid transformation check failed')
a.output.mkdir(mode=0o700,parents=True); doc=App.newDocument('Partial935DriveFrameStudy')
items=[]
for label,shape in [('support_open_candidate',support),('shaft_open_candidate_transformed',moved)]:
    obj=doc.addObject('PartDesign::Feature',label); obj.Shape=shape; obj.Label=label+' - uncalibrated open surface'; items.append(obj)
doc.recompute(); fc=a.output/'935-drive-fragments.FCStd'; step=a.output/'935-drive-fragments.step'; doc.saveAs(str(fc)); Part.export(items,str(step))
combined=Part.read(str(step)); area=moved.Area+support.Area
if not combined.isValid() or len(combined.Solids) or len(combined.Faces)!=len(moved.Faces)+len(support.Faces) or abs(combined.Area/area-1)>1e-6: raise ValueError('STEP reread failed')
App.closeDocument(doc.Name); check=App.openDocument(str(fc)); objects=[o for o in check.Objects if hasattr(o,'Shape')]
if len(objects)!=2 or any(not o.Shape.isValid() or len(o.Shape.Solids) for o in objects): raise ValueError('FCStd reread failed')
App.closeDocument(check.Name)
result={'status':'same_scan_open_fragments_pose_study_not_mechanical_assembly','input_sha256':{'shaft':expected[0],'support':expected[1],'transform':expected[2]},'output_sha256':{'fcstd':sha(fc),'step':sha(step)},'shaft_faces':len(shaft.Faces),'support_faces':len(support.Faces),'solids':0,'area_and_vertex_rigid_checks':True,'step_and_fcstd_reread':True,'assumed_mm_per_source_unit':1.0,'scale_verified':False,'physical_registration_verified':False,'mating_interface_verified':False,'manufacturing_authorized':False,'freecad_version':App.Version()[:3]}
(a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result))
