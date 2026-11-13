from pathlib import Path
from fractions import Fraction as F
import re,json,hashlib
r=Path(__file__).parent;m=r/'recovered/constant/polyMesh'
def payload(name):
 s=(m/name).read_text().split('}',1)[1];return re.sub(r'//[^\n]*','',s).strip()
def label_list(name):
 s=payload(name);match=re.fullmatch(r'(\d+)\s*\((.*?)\)',s,re.S);assert match;values=list(map(int,match[2].split()));assert len(values)==int(match[1]);return values
s=payload('points');points=[tuple(map(F,p.split())) for p in re.findall(r'\(([^()]*)\)',s)];assert len(points)==9 and all(len(p)==3 for p in points)
s=payload('faces');faces=[tuple(map(int,p.split())) for p in re.findall(r'3\(([^()]*)\)',s)];assert len(faces)==30
owner=label_list('owner');neighbour=label_list('neighbour');assert len(owner)==30 and len(neighbour)==18 and max(owner)==11
assert hashlib.sha256((r/'cube.msh').read_bytes()).hexdigest()=='54a2fe81dfcb612cbf287704718509b1f28597b03426fa0354e101910df6d5b2';src=(r/'cube.msh').read_text();nodes={int(t[0])-1:tuple(t[1:]) for line in src.split('$Nodes\n')[1].split('$EndNodes')[0].splitlines()[1:] if (t:=line.split())};assert len(nodes)==9
assert all(tuple(F(format(float(x),'.10g')) for x in nodes[i])==p for i,p in enumerate(points))
physical={int(tag):name for dim,tag,name in re.findall(r'(\d+) (\d+) "([^"]+)"',src.split('$PhysicalNames\n')[1].split('$EndPhysicalNames')[0]) if dim=='2'}
source_faces={name:[] for name in physical.values()}
for line in src.split('$Elements\n')[1].split('$EndElements')[0].splitlines()[1:]:
 row=list(map(int,line.split()))
 if row[1]==2:source_faces[physical[row[3]]].append(tuple(i-1 for i in row[3+row[2]:]))
def canon(t):return min(t[i:]+t[:i] for i in range(3))
checks={}
for name,body in re.findall(r'(\w+)\s*\{([^{}]*)\}',payload('boundary')):
 start=int(re.search(r'startFace\s+(\d+)',body)[1]);n=int(re.search(r'nFaces\s+(\d+)',body)[1]);assert n==2;checks[name]=sorted(map(canon,faces[start:start+n]))==sorted(map(canon,source_faces[name]))
assert set(checks)==set(physical.values()) and all(checks.values())
def cross(a,b):return a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]
volumes=[F(0)]*12
for i,face in enumerate(faces):
 a,b,c=(points[v] for v in face);six=sum(x*y for x,y in zip(a,cross(b,c)));volumes[owner[i]]+=six/6
 if i<len(neighbour):volumes[neighbour[i]]-=six/6
assert all(v>0 for v in volumes) and sum(volumes)==1
for name in ['log.checkMesh-standard','log.checkMesh-extended']:assert 'Mesh OK.' in (r/'recovered'/name).read_text()
result={'cells':12,'points':9,'oriented_boundary_triangles_and_names_preserved':checks,'point_values_match_declared_10_digit_write_precision':True,'all_cell_volumes_positive_exactly':True,'sum_volume_exact_m3':str(sum(volumes)),'native_standard_check':'passed','native_extended_check':'passed','physical_qualification':False,'files':{name:hashlib.sha256((m/name).read_bytes()).hexdigest() for name in ['points','faces','owner','neighbour','boundary']}}
(r/'verification-v2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
