"""Prepare a strict native hexahedral/layer experiment from the certified SI rotor."""
import json
import shutil
from run_reconstruction import ROOT,fresh,save,sha

p=ROOT/'work/935-local-relocation-20261022';out=fresh(p/'hex-template-001');old=ROOT/'work/935-cfd-pilot-20261022/rotor-001/coarse/system'
proof=json.loads((p/'graded-prepared-001/receipt.json').read_text());geometry=p/'graded-prepared-001/rotor-si.obj';assert sha(geometry)==proof['output_sha256']['rotor-si.obj']
(out/'system').mkdir();(out/'constant/triSurface').mkdir(parents=True)
for name in ['blockMeshDict','fvSchemes','fvSolution','meshQualityDict']:shutil.copyfile(old/name,out/'system'/name)
assert sha(out/'system/meshQualityDict')=='bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d'
text=(old/'snappyHexMeshDict').read_text()
for before,after in [('maxLocalCells 2500000;','maxLocalCells 6000000;'),('maxGlobalCells 2000000;','maxGlobalCells 6000000;'),('level (2 3);','level (5 6);'),('addLayers false;','addLayers true;'),('layers {}','layers { rotor { nSurfaceLayers 3; } }'),('maxNonOrtho 75;','maxNonOrtho 70;')]:
    assert text.count(before)==1;text=text.replace(before,after)
(out/'system/snappyHexMeshDict').write_text(text)
(out/'system/controlDict').write_text('FoamFile {format ascii;class dictionary;object controlDict;}\napplication snappyHexMesh;startFrom startTime;startTime 0;stopAt endTime;endTime 0;deltaT 1;writeControl timeStep;writeInterval 1;writePrecision 17;functions {};\n')
shutil.copyfile(geometry,out/'constant/triSurface/rotor.obj')
save(out/'receipt.json',{'source_sha256':sha(__file__),'parent_preparation_sha256':sha(p/'graded-prepared-001/receipt.json'),'surface_bounds_sha256':sha(p/'bounds-002/assessment.json'),'nominal_surface_levels':[5,6],'requested_surface_layers':3,'maximum_global_cells':6000000,'quality_dictionary_unchanged':True,'snappy_relaxed_nonorthogonality_also_70_degrees':True,'native_geometry_and_quality_admission_pending':True,'CFD_executed':False,'CFD_accepted':False,'manufacturing_authorized':False,'files_sha256':{str(f.relative_to(out)):sha(f) for f in sorted(out.rglob('*')) if f.is_file()}})
print(out)
