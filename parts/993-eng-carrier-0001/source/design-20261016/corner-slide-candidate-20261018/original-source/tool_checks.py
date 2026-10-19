"""Original four-column native Common block on this newly saved raw candidate."""
import importlib.util,json,traceback
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
RAW=load('_retained_raw_shape_preservation',H.with_name('bounded-webs-stock-rib-seven-edge-rounding-preparation-001')/'trial.py')
BOUNDARY=load('_original_exact_pad_contact_supports',H/'boundary.py')
def evaluate(candidate_path,out,c,settings,summary,event,require,write):
  from build123d import import_brep,Pos,Cylinder
  from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
  from OCP.BRepTools import BRepTools
  from OCP.TopTools import TopTools_ListOfShape
  p=dict(candidate_BREP=str(candidate_path.relative_to(R)));report=dict(four_columns=[])
  top=settings['geometry']['central_back_ribs']['top_z_mm']
  for index,(x,y)in enumerate(c['study_central_centres_xy_mm']):
   row=dict(index=index,centre_XY_mm=[x,y],radius_mm=c['study_tool_radius_mm'],start_Z_mm=4.,end_Z_mm=44.,completed=False);report['four_columns'].append(row)
   try:
    candidate=import_brep(R/p['candidate_BREP']);require(candidate.is_valid and len(candidate.solids())==1,'Fresh candidate is not one valid Solid')
    cutter=Pos(x,y,4+(top+10)/2)*Cylinder(c['study_tool_radius_mm'],top+10)
    row['source_column_BREP']=RAW.preserved_shape(cutter.wrapped,out/(f'column{index}-source.brep'),BRepTools.Write_s)
    common=BRepAlgoAPI_Common();args=TopTools_ListOfShape();tools=TopTools_ListOfShape();args.Append(candidate.wrapped);tools.Append(cutter.wrapped);common.SetArguments(args);common.SetTools(tools);common.SetNonDestructive(True);common.SetRunParallel(False);common.SetFuzzyValue(0.)
    event('before_Common',column=index,NonDestructive=True,RunParallel=False,FuzzyValue=0.);common.Build();row['completed']=bool(common.IsDone());event('after_Common',column=index,IsDone=row['completed'])
    if not row['completed']:
     row['raw_Common_preservation']=dict(path=None,sha256=None,reason='Common_incomplete_no_Shape_accessor_retry');write(out/(f'column{index}-raw-preservation.json'),row['raw_Common_preservation']);continue
    raw=common.Shape();row['raw_Common_preservation']=RAW.preserved_shape(raw,out/(f'column{index}-Common-raw.brep'),BRepTools.Write_s);write(out/(f'column{index}-raw-preservation.json'),row['raw_Common_preservation'])
    row['whole_native_summary']=summary(raw);write(out/(f'column{index}-summary.json'),row['whole_native_summary'])
    row['complete_boundary_supports']=BOUNDARY.native_records(raw);write(out/(f'column{index}-boundary-supports.json'),row['complete_boundary_supports'])
   except TimeoutError:raise
   except Exception as error:row['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
  # Every completed result is preserved before any admission predicate is applied.
  write(out/'all-four-before-gates.json',report['four_columns'])
  require(len(report['four_columns'])==4 and all(r['completed']and 'failure'not in r for r in report['four_columns']),'An original Common is incomplete or could not be fully recorded')
  gates=[]
  for row in report['four_columns']:
   try:gates.append(dict(index=row['index'],passed=True,predicate=BOUNDARY.validate(row['whole_native_summary'],row['complete_boundary_supports'])))
   except ValueError as error:gates.append(dict(index=row['index'],passed=False,reason=str(error)))
  report['four_actual_Common_predicates']=gates;write(out/'four-Common-predicates.json',gates)
  require(all(r['passed']for r in gates),'Actual original tool-column intersection or unresolved/non-pad contact')
  return report
