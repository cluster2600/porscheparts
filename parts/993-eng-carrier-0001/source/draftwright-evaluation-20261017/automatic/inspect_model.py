"""Read nominal analytic cylinders/bounds from the unchanged STEP; no new solid."""
from pathlib import Path
import hashlib,json,platform,sys
from importlib import metadata
from build123d import import_step,GeomType
from OCP.BRepAdaptor import BRepAdaptor_Surface
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
step=ROOT/'parts/993-eng-carrier-0001/derived/workflow-20261016/carrier.step'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(step);assert before=='de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63'
part=import_step(step);box=part.bounding_box();faces=[]
for i,face in enumerate(part.faces()):
 if face.geom_type==GeomType.CYLINDER:
  c=BRepAdaptor_Surface(face.wrapped).Cylinder();r=float(c.Radius())
  if abs(r-5.5)<1e-10 or abs(r-6.75)<1e-10:
   a=c.Axis();v=a.Direction();p=c.Location()
   faces.append(dict(face_index=i,radius_mm=r,diameter_mm=2*r,axis=[v.X(),v.Y(),v.Z()],axis_location_mm=[p.X(),p.Y(),p.Z()],area_mm2=face.area))
result=dict(schema='carrier-draftwright-nominal-step-inspection-1',input_sha256=before,input_unchanged=sha(step)==before,
 bbox_min_mm=list(box.min),bbox_max_mm=list(box.max),bbox_size_mm=list(box.size),analytic_bore_face_candidates=faces,
 radius_selection_scope='1e-10 mm is only a numerical match against the two expected analytic radii to select inspection rows; it is not a dimensional manufacturing tolerance.',
 python=platform.python_version(),interpreter=sys.executable,versions={n:metadata.version(n) for n in ['draftwright','build123d','cadquery-ocp-novtk','quiddity','build123d-drafting-helpers']},
 recognition_is_not_measured_oem_dimensions=True)
(BASE/'nominal-model-inspection.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
