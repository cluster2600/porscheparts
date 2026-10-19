"""One authored F0 sheet; only placement lint, with no recognition claim."""
from pathlib import Path
from dataclasses import asdict,is_dataclass
import hashlib,json
from build123d import import_step
from draftwright import Sheet
from draftwright.model import hole
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
STEP=ROOT/'parts/993-eng-carrier-0001/derived/workflow-20261016/carrier.step'
PROOF=ROOT/'work/carrier-draftwright-20261017/nominal-model-inspection.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value):
 (BASE/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,default=lambda x:asdict(x) if is_dataclass(x) else str(x))+'\n')
def phase(name):print(json.dumps(dict(phase=name)),flush=True)
assert sha(STEP)=='de0e55a3150dacc5428bbc301d18d2e43477f038c3f4df295d9373af8e906b63'
raw=json.loads(PROOF.read_text());assert raw['input_sha256']==sha(STEP) and raw['input_unchanged']
central=[r for r in raw['analytic_bore_face_candidates'] if r['diameter_mm']==11.]
eyes=[r for r in raw['analytic_bore_face_candidates'] if r['diameter_mm']==13.5]
assert len(central)==4 and len(eyes)==2
assert {(r['axis_location_mm'][0],r['axis_location_mm'][1]) for r in central}=={(-50.,-20.),(-50.,20.),(50.,-20.),(50.,20.)}
assert all(r['axis']==[0.,0.,1.] for r in central)
assert {r['axis_location_mm'][0] for r in eyes}=={-280.,280.}
span=lambda rows,k:max(r['axis_location_mm'][k] for r in rows)-min(r['axis_location_mm'][k] for r in rows)
assert span(central,0)==100. and span(central,1)==40. and span(eyes,0)==560.
assert [round(v,3) for v in raw['bbox_size_mm']]==[592.,73.,52.]
write('f0-proof-before-export.json',dict(STEP_sha256=sha(STEP),independent_inspection_sha256=sha(PROOF),
 source='Retained analytic OCP STEP inspection from the first isolated trial, independent of Draftwright recognition.',
 nominal_envelope_mm=[592,73,52],raw_kernel_bbox_size_mm=raw['bbox_size_mm'],
 bbox_difference_mm=[a-b for a,b in zip(raw['bbox_size_mm'],[592,73,52])],
 display_rounding='3 decimal display equality only; no manufacturing tolerance or dimensional acceptance introduced.',
 central=central,eyes=eyes,central_pitch_mm=[span(central,0),span(central,1)],eye_pitch_mm=span(eyes,0),
 eye_axis_residuals_to_Y=[dict(x=r['axis'][0],abs_y_minus_1=abs(r['axis'][1])-1,z=r['axis'][2]) for r in eyes],
 dimensions_scope='Eight F0 nominal values only: 592/73/52; 4×Ø11 plus 100/40; 2×Ø13.5 plus 560. Not measured OEM dimensions.'))
part=import_step(STEP);phase('STEP_loaded')
sheet=Sheet(part,title='Support 993 — hypothèses F0',number='993-CARRIER-F0',
 tolerance='',material='',revision='',date='',drawn_by='',pmi='off',
 document_type='Cotes nominales CAO',projection='first',page='A3',scale=.5,
 scale_policy='strict',detail_view=False)
sheet.take_over(dimensions='authored',principal_views='authored',derived_views='authored')
for name in ('front','plan','side'):sheet.view(name)
env=sheet.envelope()
for key in ('width.length','depth.length','height.length'):sheet.dimension(env,key)
central=sheet.pattern(hole(diameter=11.,at=(0.,0.,4.),axis='z'),kind='grid',count=4,
 at=(0.,0.,4.),axis='z',grid=(40.,100.),rows=2,cols=2)
assert set(sheet.features[-1].members)=={(-50.,-20.,4.),(50.,-20.,4.),(-50.,20.,4.),(50.,20.,4.)}
for key in ('bore.diameter','grid_pitch.length.row','grid_pitch.length.col'):sheet.dimension(central,key)
eyes=sheet.pattern(hole(diameter=13.5,at=(0.,0.,0.),axis='y'),kind='linear',count=2,
 at=(0.,0.,0.),axis='y',direction=(1.,0.,0.),pitch=560.)
assert set(sheet.features[-1].members)=={(-280.,0.,0.),(280.,0.,0.)}
for key in ('bore.diameter','pitch.length'):sheet.dimension(eyes,key)
sheet.notes(['Hypothèses F0 — modèle CAO nominal',
 'Axes : 4 alésages Z ; 2 alésages Y',
 'Tolérances, finition, PMI : non renseignés'],number=False,title='PORTÉE F0',prefer='tr')
write('declarations.json',dict(envelope_ids=env.dimension_ids(),central_ids=central.dimension_ids(),eye_ids=eyes.dimension_ids(),
 public_export_lint=False,public_placement_lint_physical=False,authored_views=['front','plan','side'],scale=.5,page='A3'))
phase('F0_declarations_ready')
drawing=sheet.build();phase('sheet_built')
assert drawing.recognition is None,'Unexpected recognition inventory in the authored build'
issues=drawing.lint(physical=False)
write('placement-lint.json',dict(scope='Official Drawing.lint(physical=False): placement/standards only; physical feature recognition and completeness were not evaluated.',
 physical=False,issues=[dict(severity=str(i.severity),code=i.code,message=i.message) for i in issues],
 error_count=sum(str(i.severity).lower()=='error' for i in issues),warning_count=sum(str(i.severity).lower()=='warning' for i in issues)))
write('dimension-sources.json',drawing.dimension_sources())
phase('placement_lint_saved')
assert drawing.recognition is None,'Placement lint unexpectedly triggered recognition'
outputs=drawing.export(str(BASE/'drawing'/'carrier-F0'),formats=('pdf','svg','dxf','png'),lint=False,dpi=120)
phase('exports_written')
assert drawing.recognition is None,'Export unexpectedly triggered recognition'
write('drawing-result.json',dict(outputs=outputs,recognition_performed=False,
 lint_scope='placement_only',page_w_mm=drawing.page_w,page_h_mm=drawing.page_h,
 dimensional_scope='Eight F0 nominal values explicitly authored. No OEM or manufacturing approval.',
 no_tolerances_fits_GDT_or_surface_finish_declared=True))
