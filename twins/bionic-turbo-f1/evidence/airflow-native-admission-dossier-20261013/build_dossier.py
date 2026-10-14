"""Build a bounded evidence/source inventory, without geometric evaluations."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
W=Path(__file__).parent
ANCHOR='ed462661ca94c843b0f8c1379d88258595f552a4'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
read=lambda p:json.loads(p.read_text())
deps=read(Path('work/bionic-boundary-embedding-20261013/dependencies.json'))['manifests']
p=Path('work/bionic-airflow-delivery-20261013-boundary-embedding/file-manifest.json');deps[str(p)]=sha(p)
count=0
for name,digest in deps.items():
 p=Path(name);phase=p.parent.name.removeprefix('bionic-airflow-delivery-20261013-')
 gitpath=f'twins/bionic-turbo-f1/evidence/airflow-{phase}-20261013/file-manifest.json'
 raw=subprocess.check_output(['git','show',ANCHOR+':'+gitpath])
 assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
 for f in json.loads(raw)['files']:
  fp=Path('work')/f['path'];assert fp.stat().st_size==f['bytes'] and sha(fp)==f['sha256'];count+=1
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
expected=read(Path('work/bionic-centre-interval-bounds-20261013/identity-readback.json'))
assert sha(archive)==expected['official_archive_sha256']
source=[]
with tarfile.open(archive) as tar:
 for n in ('primitiveMeshTools.C','doubleScalar.H','scalar.H','OSstream.C','IOstream.C','checkGeometry.C'):
  members=[m for m in tar.getmembers() if m.isfile() and m.name.endswith('/'+n)];assert len(members)==1
  raw=tar.extractfile(members[0]).read();assert raw==(W/n).read_bytes()
  source.append({'file':n,'member':members[0].name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
assert next(r['sha256'] for r in source if r['file']=='primitiveMeshTools.C')==expected['official_member_sha256']
claims=[('face_guard','primitiveMeshTools.C','if (sumA < ROOTVSMALL)'),('cell_guard','primitiveMeshTools.C','if (mag(cellVols[celli]) > VSMALL)'),('determinant_guard','primitiveMeshTools.C','if (nInternalFaces == 0 || avgArea < ROOTVSMALL)'),('orthogonality_additive','primitiveMeshTools.C','return (d & s)/(mag(d)*mag(s) + ROOTVSMALL);'),('flatness_native_centre','primitiveMeshTools.C','const solveVector fc = fCtrs[facei];'),('flatness_additive','primitiveMeshTools.C','faceFlatness[facei] = magAreas[facei]/(sumA + ROOTVSMALL);'),('openness_additive','primitiveMeshTools.C','/(sumMagClosed[celli][cmpt] + ROOTVSMALL)'),('dp_vsmall','doubleScalar.H','constexpr doubleScalar doubleScalarVSMALL = 1.0e-300;'),('dp_rootvsmall','doubleScalar.H','constexpr doubleScalar doubleScalarROOTVSMALL = 1.0e-150;'),('dp_conditional','scalar.H','#elif defined(WM_DP)'),('precision_delegation','OSstream.C','return os_.precision(p);'),('flatness_call','checkGeometry.C','if (mesh.checkFaceFlatness(true, 0.8, &faces))'),('weight_call','checkGeometry.C','if (mesh.checkFaceWeight(true, 0.05, &faces))'),('vol_ratio_call','checkGeometry.C','if (mesh.checkVolRatio(true, 0.01, &faces))'),('native_tet_call','checkGeometry.C','polyMeshTetDecomposition::checkFaceTets')]
entries=[]
for label,file,text in claims:
 lines=(W/file).read_text().splitlines();positions=[i+1 for i,line in enumerate(lines) if text in line];assert positions
 entries.append({'id':label,'file':file,'literal':text,'lines':positions})
boxes=read(Path('work/bionic-angular-independent-bounds-20261013/certificate-readback.json'))['box_results']
assert [b['parent_leaf'] for b in boxes]==list(range(1778,1931))
positive=[b['parent_leaf'] for b in boxes if b['all_variable_necessary_predicates_positive']]
assert positive==list(range(1816,1929))
partition=read(Path('work/bionic-feasibility-bounds-20261013/readback.json'))['slice_dependencies']
assert partition['fixed_cells']+partition['variable_cells']==6144
assert partition['fixed_angles']+partition['variable_angles']==13696
assert partition['constant_planes']+partition['variable_planes']==138240
rows=[]
def add(id,status,scope,evidence,gap):
 rows.append({'id':id,'status':status,'scope':scope,'evidence':evidence,'remaining_obligation':gap,'native_admission':False})
add('constant_predicates','inherited_mathematical','u=q_m, unchanged incidences','PR231/232 regression and PR233 slice dependencies','Inherit only 2304 cells, 4224 angles including MRF and 46080 ordered planes; numerical native evaluation still required.')
add('variable_predicates','inherited_mathematical','113 boxes 1816..1928','PR238 independent cells; PR239 independent angles','Necessary predicates only; retain all 153 boxes and two determinant-unknown boundary boxes.')
add('parametric_sharing_caps','inherited_geometric','closed envelope of 153 boxes','PR240','Conversion/native sharing must be checked separately.')
add('signed_volume_identity','inherited_mathematical','triangle/quad arithmetic-mean fan','PR241','No equality of first moments or native centres inferred.')
add('boundary_degree_coverage','inherited_geometric','shared fan, closed envelope of 153 boxes','PR243','Interior nonoverlap does not classify all internal lower-dimensional contacts.')
add('internal_contacts','open','internal nonincident cells','PR243 scope limitation','Establish required contact conformity or a sufficient native-topology argument; do not claim complete intersection classification.')
add('flatness','open','all faces, native face centre','primitiveMeshTools.C faceFlatness; checkGeometry.C','Bound native-centre fan ratio; coplanarity polynomial is not this criterion. Source call 0.8 recorded, no changed threshold.')
add('closedness_balance','partly_inherited','all cell faces and global boundary','PR240/241 exact chain; primitiveMeshTools.C cellClosedness','Exact vector cancellation does not bound native accumulation errors or MRF/flow balance.')
add('degeneracy_guards','open','faces, cells, internal/coupled area sum','primitiveMeshTools.C','Prove quantitative separation from guards with operation errors; cell test is on accumulated triple volume before division by 3.')
add('additive_regularizers','open','orthogonality, flatness, closedness, skewness','primitiveMeshTools.C','Bound ROOTVSMALL effects separately from inactive branch claims; not exactly absent from mathematical expression.')
add('numeric_build','open','actual future binary','scalar.H; doubleScalar.H','Bind WM_DP/solveScalar, binary and compiler/runtime receipts. DP constants are conditional source facts, not an inspected future executable.')
add('coordinate_serialization','open','future input plus native written points','OSstream.C','Keep writePrecision 16; independently read exact text/decoded binary64 and bound displacement/criteria. No exact round-trip promise from precision alone.')
add('native_tet_decomposition','open','native polyMeshTetDecomposition','checkGeometry.C','Native decomposition and minTetQuality are not the arithmetic-mean proof tetrahedra; verify before inheriting positivity.')
add('native_skewness_weights_ratios','open','all applicable native faces/cells','checkGeometry.C','Skewness, interpolation weights (call 0.05), volume ratios (call 0.01) are not certified by angle/determinant/plane predicates.')
add('native_topology_and_geometry','open','actual produced native mesh','checkGeometry.C and future checkTopology/full quality controls','Record all failed sets/warnings as well as exit result. This dossier is not a full call-graph audit or successful checkMesh.')
add('global_rest_and_flow','open','admitted physical/full-flow scope','historic 084 incomplete and 033 rejected','No reuse of synthetic three-interval proof as physical qualification; no rerun of 084; layers/rest/convergence/stability/independence and calibration remain distinct.')
out={'anchor_commit':ANCHOR,'domain_v':[boxes[0]['lower'],boxes[-1]['upper']],'fixed_u':'source q_m exact','source_boxes':153,'necessary_predicate_positive_leaves':positive,'slice_dependencies':partition,'obligations':rows,'candidate_created':False,'native_admission':False,'new_geometry_evaluations':0}
(W/'dossier.json').write_text(json.dumps(out,indent=2)+'\n')
(W/'source-audit.json').write_text(json.dumps({'archive_sha256':expected['official_archive_sha256'],'members':source,'claims':entries,'scope':'source inventory, not execution or complete native call graph'},indent=2)+'\n')
(W/'dependencies.json').write_text(json.dumps({'anchor_commit':ANCHOR,'manifests':deps,'payload_entries_verified':count},indent=2)+'\n')
(W/'readback.json').write_text(json.dumps({'source_sha256':sha(Path(__file__)),'preflight_sha256':sha(W/'preflight.md'),'dossier_sha256':sha(W/'dossier.json'),'source_audit_sha256':sha(W/'source-audit.json'),'dependencies_sha256':sha(W/'dependencies.json'),'manifests':len(deps),'payload_entries_verified':count,'obligations':len(rows),'source_claims':len(entries),'native_admission':False,'no_geometric_runs_replayed':True},indent=2)+'\n')
print('Dossier built; native admission remains false')
