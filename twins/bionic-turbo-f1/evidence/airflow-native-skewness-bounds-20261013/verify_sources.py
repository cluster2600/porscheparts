"""Independent structural readback of pinned source members, not geometry."""
import hashlib,json,tarfile
from pathlib import Path
W=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
audit=json.loads((W/'source-audit.json').read_text());archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz')
assert sha(archive)==audit['archive_sha256']=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
with tarfile.open(archive) as tar:
 for row in audit['new_members']:
  raw=tar.extractfile(row['member']).read();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and raw==(W/Path(row['member']).name).read_bytes()
 for row in audit['inherited_sources']:
  path=Path(row['path']);raw=path.read_bytes();assert len(raw)==row['bytes'] and sha(path)==row['sha256']
  matches=[m for m in tar.getmembers() if m.isfile() and Path(m.name).name==path.name and tar.extractfile(m).read()==raw];assert len(matches)==1
normal=(W/'VectorSpaceI.H').read_text();assert 'const scalar s(mag(vs));' in normal and 'return s < ROOTVSMALL ? Zero : vs/s;' in normal
primitive=(W/'primitiveMeshCheck.C').read_text();assert 'Foam::scalar Foam::primitiveMesh::skewThreshold_    = 4;' in primitive and 'skewThreshold_ = val;' in primitive
source=Path('work/bionic-native-admission-dossier-20261013/primitiveMeshTools.C').read_text()
for token in ['normalised(fAreas[facei])','normal*(normal & Cpf)','sv/(mag(sv) + ROOTVSMALL)','0.2*mag(d) + ROOTVSMALL','0.4*mag(d) + ROOTVSMALL','fd = max(fd, mag(svHat & (p[f[pi]] - fCtrs[facei])))','return mag(sv)/fd;']:assert token in source,token
out={'source_sha256':sha(Path(__file__)),'source_audit_sha256':sha(W/'source-audit.json'),'official_members_verified':6,'default_threshold':4,'setter_present':True,'normalised_zero_branch_preserved':True,'structural_only':True,'binary_or_runtime_configuration_verified':False}
(W/'source-readback.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
