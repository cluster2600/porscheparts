"""Source and dependency audit only; no turbo geometry evaluation."""
import hashlib,json,subprocess,tarfile,time
from pathlib import Path
W=Path(__file__).parent;BASE='8318891519d7271186115cca007d9e0b12eddcaa'
def sha(p):
 with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
access=json.loads((W/'source-access.json').read_text());members=[]
extra=['OpenFOAM-v2406/src/OpenFOAM/meshes/primitiveShapes/tetrahedron/tetrahedron.H','OpenFOAM-v2406/src/OpenFOAM/primitives/Scalar/Scalar.H']
inherited=['work/bionic-native-admission-dossier-20261013/checkGeometry.C','work/bionic-native-admission-dossier-20261013/doubleScalar.H','work/bionic-native-admission-dossier-20261013/scalar.H']
with tarfile.open(archive) as tar:
 for r in access['members']:
  raw=tar.extractfile(r['member']).read();assert raw==Path(r['path']).read_bytes() and hashlib.sha256(raw).hexdigest()==r['sha256'];members.append(r)
 for name in extra:
  raw=tar.extractfile(name).read();p=W/Path(name).name
  with p.open('xb') as stream:stream.write(raw)
  members.append({'member':name,'path':str(p),'bytes':len(raw),'sha256':sha(p)})
 for name in inherited:
  p=Path(name);raw=p.read_bytes();match=[m for m in tar.getmembers() if m.isfile() and Path(m.name).name==p.name and tar.extractfile(m).read()==raw];assert len(match)==1
  members.append({'member':match[0].name,'path':name,'bytes':len(raw),'sha256':sha(p)})
s=(W/'polyMeshTetDecomposition.C').read_text();q=(W/'tetrahedronI.H').read_text();scalar=(W/'Scalar.H').read_text();header=(W/'tetrahedron.H').read_text()
for token in ['minTetQuality = sqr(SMALL);','if (tetQual > -tol)','if (tetQual < tol)','if (min(ownQuality, neiQuality) > tol)','if (quality > tol)','if (nErrorTets > 0)']:assert token in s
for token in ['if (Foam::mag(denom) < ROOTVSMALL)','return GREAT;','8.0/(9.0*sqrt(3.0))','pow3(Foam::min(circumRadius(), GREAT))','+ ROOTVSMALL']:assert token in q
assert 'return s*s;' in scalar and 'return s*sqr(s);' in scalar and 'typedef tetrahedron<point, const point&> tetPointRef;' in header
parents=json.loads(Path('work/bionic-native-orthogonality-bounds-20261013/input-inventory.json').read_text())['manifests'];parents['work/bionic-airflow-delivery-20261013-native-orthogonality-bounds/file-manifest.json']='ca39a535390dcf0a846f035d3c03198679249c36cb02041b4c137b9275f2ed8f';count=0
for name,digest in parents.items():
 p=Path(name);phase=p.parent.name.split('20261013-',1)[1];raw=subprocess.check_output(['git','show',BASE+':twins/bionic-turbo-f1/evidence/airflow-'+phase+'-20261013/file-manifest.json']);assert hashlib.sha256(raw).hexdigest()==digest==sha(p)
 for row in json.loads(raw)['files']:
  p=Path('work')/row['path'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];count+=1
assert len(parents)==18 and count==460
out={'time_unix':time.time(),'source_sha256':sha(Path(__file__)),'anchor_commit':BASE,'official_archive_sha256':sha(archive),'members':members,'manifests':parents,'payload_entries_verified':count,'structural_only':True,'turbo_geometry_evaluated':False,'native_binary_verified':False}
with (W/'source-audit.json').open('x') as stream:stream.write(json.dumps(out,indent=2)+'\n')
print('Eight official members; eighteen manifests and 460 entries verified')
