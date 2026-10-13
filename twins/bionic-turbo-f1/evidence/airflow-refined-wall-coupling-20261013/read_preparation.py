"""Bound initial-input provenance, boundary metadata change and patch cleanup."""
import hashlib,json,re,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
w=Path(__file__).parent;root=Path('work/bionic-airflow-20261012');split=root/'radial-split-078';snap=root/'outer-wall-bisect-086';patch=root/'refined-wall-patches-087';case=root/'refined-wall-stitch-088'
for c in (split,snap,patch,case):
 r=json.loads((c/'report.json').read_text());assert all(sha(c/n)==h for n,h in r['output_sha256'].items())
a=w/'refined-wall-patches-087-inputs';b=w/'refined-wall-stitch-088-inputs'
core=('points','faces','owner','neighbour','boundary','cellZones','faceZones','pointZones')
for name in core:
 assert sha(a/'constant/polyMesh'/name)==sha(snap/'constant/polyMesh'/name)
 assert sha(b/'add/constant/polyMesh'/name)==sha(patch/'constant/polyMesh'/name)
 if name!='boundary':assert sha(b/'constant/polyMesh'/name)==sha(split/'constant/rotorZone/polyMesh'/name)
s=(split/'constant/rotorZone/polyMesh/boundary').read_text().replace('type            mappedWall;','type            wall;')
for key in ('sampleMode','sampleRegion','samplePatch'):s,n=re.subn(r'^\s*'+key+r'\s+[^;]+;\n','',s,flags=re.M);assert n==1
assert s==(b/'constant/polyMesh/boundary').read_text()
for mesh in (a/'constant/polyMesh',b/'constant/polyMesh',b/'add/constant/polyMesh',case/'merged-polyMesh',case/'stitched-polyMesh',case/'constant/polyMesh'):assert not list(mesh.glob('*RegionAddressing'))
# Preserved intermediate patches have zero faces only after stitching.
def patches(path):
 s=path.read_text();return {n:dict(re.findall(r'(type|nFaces|startFace)\s+([^;]+);',body)) for n,body in re.findall(r'(walls|outerWall|rotorZone_to_domain1|domain1_to_rotorZone)\s*\{(.*?)\}',s,re.S)}
m=patches(case/'merged-polyMesh/boundary');st=patches(case/'stitched-polyMesh/boundary');fin=patches(case/'constant/polyMesh/boundary')
assert all(int(m[n]['nFaces'])==6784 for n in ('rotorZone_to_domain1','domain1_to_rotorZone'))
assert all(int(st[n]['nFaces'])==0 for n in ('rotorZone_to_domain1','domain1_to_rotorZone'))
assert set(fin)=={'walls','outerWall'} and int(fin['walls']['nFaces'])==15104 and int(fin['outerWall']['nFaces'])==6784 and all(x['type']=='wall' for x in fin.values())
# Source reference is the exact pinned official archive, not a documentation paraphrase.
archive=Path('work/bionic-native-diagnostics-20261012/OpenFOAM-v2406.tgz');assert sha(archive)=='8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a'
with tarfile.open(archive) as tar:
 members=[x for x in tar.getmembers() if x.name.endswith('/createPatch.C')];assert len(members)==1
 member=members[0];data=tar.extractfile(member).read();assert b'sourceType == "set"' in data and b'set.sortedToc()' in data
reference={'url':'https://dl.openfoam.com/source/v2406/OpenFOAM-v2406.tgz','archive_sha256':sha(archive),'member':member.name,'member_sha256':hashlib.sha256(data).hexdigest(),'scope':'createPatch constructFrom set reads native faceSet and sorts labels; not a complete application proof'}
r=dict(reader_sha256=sha(Path(__file__)),all_payloads_verified=True,all_prepared_core_mesh_inputs_exact_to_parents_except_explicit_rotor_boundary_metadata=True,rotor_geometry_and_zone_inputs_byte_identical=True,rotor_boundary_only_mappedWall_to_wall_and_three_sample_keys_removed=True,no_inherited_region_addressing=True,intermediate_patches={'merged':m,'stitched':st,'final':fin},cleanup_removes_only_empty_join_patches=True,source_reference=reference)
with (w/'preparation-readback.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
