"""Read exact official members and audit additive orthogonality source branches."""
import hashlib,json,tarfile
from pathlib import Path
W=Path(__file__).parent
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
paths=['work/bionic-native-admission-dossier-20261013/primitiveMeshTools.C','work/bionic-native-volume-ratio-bounds-20261013/polyMeshTools.C','work/bionic-native-volume-ratio-bounds-20261013/polyMeshCheck.C','work/bionic-native-skewness-bounds-20261013/primitiveMeshCheck.C','work/bionic-native-admission-dossier-20261013/doubleScalar.H','work/bionic-native-admission-dossier-20261013/scalar.H']
rows=[]
with tarfile.open(archive) as tar:
 members=tar.getmembers()
 for name in paths:
  p=Path(name);raw=p.read_bytes();matches=[m for m in members if m.isfile() and Path(m.name).name==p.name and tar.extractfile(m).read()==raw];assert len(matches)==1
  rows.append({'path':name,'member':matches[0].name,'bytes':len(raw),'sha256':sha(p)})
a,b,c,d,e,f=[Path(p).read_text() for p in paths]
assert 'return (d & s)/(mag(d)*mag(s) + ROOTVSMALL);' in a
orth=b.split('Foam::polyMeshTools::faceOrthogonality',1)[1].split('Foam::polyMeshTools::faceSkewness',1)[0]
assert 'New(mesh.nFaces(), scalar(1))' in orth and 'if (pp.coupled())' in orth and 'forAll(nei, facei)' in orth
for s in ['::cos(degToRad(primitiveMesh::nonOrthThreshold_))','if (ortho[facei] > SMALL)','severeNonOrth++;','errorNonOrth++;','if (errorNonOrth > 0)']:assert s in c
assert 'nonOrthThreshold_ = 70;' in d and 'nonOrthThreshold_ = val;' in d
assert 'doubleScalarROOTVSMALL = 1.0e-150;' in e and 'doubleScalarSMALL = 1.0e-15;' in e and 'WM_DP' in f
out={'archive_sha256':sha(archive),'source_sha256':sha(Path(__file__)),'members':rows,'default_angle_degrees':70,'threshold_mutable':True,'denominator':'mag(delta)*mag(area)+ROOTVSMALL','comparison':'cos(degToRad(nonOrthThreshold_))','warning_and_error_branches_distinct':True,'uncoupled_faces_initialized_to_one':True,'WM_DP_conditional':True,'native_binary_or_runtime_verified':False}
with (W/'source-audit.json').open('x') as stream:stream.write(json.dumps(out,indent=2)+'\n')
print('Six official members verified; source conditions only')
