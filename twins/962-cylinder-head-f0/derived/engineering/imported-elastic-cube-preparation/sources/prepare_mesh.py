"""HELD fixed Netgen toy JSON to tag-preserving ASCII2.2; no native/scientific import."""
import argparse,hashlib,json,math,struct,sys,time
from collections import Counter,defaultdict
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/'
OUTPUT='work/962-engineering/imported-elastic-cube-mesh-001'
INPUTS={BASE+'arrays.json':'ea9e6ccdc8d735c3fde2401dfba56f3c29ceece8c6945438bebb611b2f0287f6',BASE+'cube.msh':'0db89b0cf7b4e57af1c6a091d999a7f521cd365f052f699a1798f05ba75eb92d',BASE+'fixture-report.json':'7d6f638b20388348810ea564e6fa7ffcdd2c5555fcbdc6d0d2c792e3d42defb7','work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-result-peer-001/review.json':'cc1e1c3b830d0a735161045b755fc0eaa01036a20b09731f9cad8a28e3c83b0c'}
P=[[0.,0.,0.],[7.,0.,0.],[7.,7.,0.],[0.,7.,0.],[0.,0.,7.],[7.,0.,7.],[7.,7.,7.],[0.,7.,7.]]
TRI=[[1,3,2],[1,4,3],[5,6,7],[5,7,8],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,4,8],[3,8,7],[4,1,5],[4,5,8]]
def need(ok,message):
 if not ok:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bits(x):return struct.pack('<d',x)
def oriented(row):return min(tuple(row[i:]+row[:i]) for i in range(3))
def determinant(p):
 e=[tuple(p[j][k]-p[0][k] for k in range(3)) for j in [1,2,3]]
 return sum(e[0][k]*(e[1][(k+1)%3]*e[2][(k+2)%3]-e[1][(k+2)%3]*e[2][(k+1)%3]) for k in range(3))
def typed(state):
 need(set(state)=={'node_tags','coordinates_mm','tetra_tags','tetra_node_tags','native_qualities','independent_signed_volume_mm3'},'Exact saved toy state keys')
 nt,xyz,et,en=[state[k] for k in ['node_tags','coordinates_mm','tetra_tags','tetra_node_tags']]
 need(len(nt)==len(xyz)==15 and len(et)==len(en)==40,'Complete15-node/40-cell state')
 need(all(type(v)is int and 0<v<2**64 for v in nt+et) and len(set(nt))==15 and len(set(et))==40 and nt==sorted(nt) and et==sorted(et),'Unique sorted uint64 node/tetra tags')
 need(all(len(p)==3 and all(type(v)in(int,float) and math.isfinite(v) for v in p) for p in xyz),'Complete finite binary64 coordinate triples')
 need(all(len(row)==4 and all(type(v)is int and v in nt for v in row) and len(set(row))==4 for row in en),'Four distinct known source node tags per tetrahedron')
 vectors={'sorted_node_tags_sha256':struct.pack('<15Q',*nt),'sorted_coordinates_sha256':b''.join(bits(v) for p in xyz for v in p),'tetra_tags_sha256':struct.pack('<40Q',*et),'tagged_tetra_connectivity_sha256':struct.pack('<160Q',*(v for row in en for v in row))}
 need(set(state['native_qualities'])=={'SICN','Jacobian','native_volume_mm3'},'Three complete native metrics required')
 for k,v in [*state['native_qualities'].items(),('independent_signed_volume_mm3',state['independent_signed_volume_mm3'])]:
  need(len(v)==40 and all(type(x)in(int,float) and math.isfinite(x) and x>0 for x in v),'Complete finite positive native/signed metric')
  vectors[k]=b''.join(bits(x) for x in v)
 return vectors
def reference(payload,report):
 need(set(payload)=={'before','after_geometry_flag','after','saved_reopen'},'Complete four-stage Netgen export')
 a=payload['after'];packed=typed(a);need(packed==typed(payload['saved_reopen']),'Bitwise full saved-reopen identity')
 need(report.get('status')=='completed_cube_only' and report.get('saved_mesh_identity_exact') is True and report.get('actual_SICN_gate_passed') is True and report.get('fixture_procedural_checks_passed') is True,'Accepted toy source report required')
 need(report.get('mesh_sha256')==INPUTS[BASE+'cube.msh'] and report.get('full_tiny_arrays_sha256')==INPUTS[BASE+'arrays.json'],'RawMSH/fullJSON report identity')
 for k in ['sorted_node_tags_sha256','sorted_coordinates_sha256','tetra_tags_sha256','tagged_tetra_connectivity_sha256']:
  need(hashlib.sha256(packed[k]).hexdigest()==report['after'][k],'Complete typed source hash join')
 nt,xyz,et,en=[a[k] for k in ['node_tags','coordinates_mm','tetra_tags','tetra_node_tags']];coords=dict(zip(nt,xyz))
 need(nt[:8]==list(range(1,9)) and all(b''.join(bits(v) for v in coords[i])==b''.join(bits(v) for v in P[i-1]) for i in range(1,9)),'Exact original eight boundary coordinate bits')
 need(all(all(0<v<7 for v in coords[i]) for i in nt[8:]),'Seven strictly interior source nodes')
 for name,values in a['native_qualities'].items():
  row=report['after']['quality'][name];need(row['count']==40 and row['nonpositive_count']==0 and row['array_sha256']==hashlib.sha256(packed[name]).hexdigest(),'Full native metric source join')
 need(min(a['native_qualities']['SICN'])>=.1,'Accepted source SICN>=.1')
 faces=defaultdict(list);vol=[]
 for tag,row in zip(et,en):
  det=determinant([[F(v) for v in coords[n]] for n in row]);need(det>0,'Exact positive source tetra orientation');vol.append(det/6)
  for ix in [(1,2,3),(0,3,2),(0,1,3),(0,2,1)]:
   f=[row[k] for k in ix];faces[tuple(sorted(f))].append(oriented(f))
 need({n for row in en for n in row}==set(nt) and len({tuple(sorted(row)) for row in en})==40,'No orphan node or duplicate cell')
 exterior=[]
 for rows in faces.values():
  need(len(rows)in(1,2),'Manifold tetra face incidence')
  if len(rows)==1:exterior.append(rows[0])
  else:need(rows[1]==oriented(list(reversed(rows[0]))),'Opposite complete internal faces')
 need(Counter(exterior)==Counter(oriented(row) for row in TRI),'Exact complete oriented source cube exterior')
 need(sum(vol)==F(343),'Exact-source independent volume bookkeeping343')
 # Source JSON contains no explicit surface element tags: these new labels are metadata only.
 triangles=list(range(max(et)+1,max(et)+13))
 return dict(schema='962-fixed-Netgen-toy-ASCII22-reference/v1',node_tags=nt,coordinates_mm=xyz,tetrahedron_tags=et,positive_tetrahedra_node_tags=en,triangle_tags=triangles,outward_triangles_node_tags=TRI,physical_tags={'all_boundary':11,'solid':21},source_coordinate_and_ordered_tetra_tags_preserved=True,triangle_element_labels_are_new_noncolliding_metadata=True,original_surface_element_labels_claimed=False,source_typed_sha256={k:hashlib.sha256(v).hexdigest() for k,v in packed.items()},volume_mm3=343,head_geometry=False)
def ascii22(ref):
 lines=['$MeshFormat','2.2 0 8','$EndMeshFormat','$PhysicalNames','2','2 11 "all_boundary"','3 21 "solid"','$EndPhysicalNames','$Nodes','15']
 lines += [' '.join([str(tag),*(format(v,'.17g') for v in xyz)]) for tag,xyz in zip(ref['node_tags'],ref['coordinates_mm'])]
 lines += ['$EndNodes','$Elements','52']
 lines += [' '.join(map(str,[tag,2,2,11,1,*row])) for tag,row in zip(ref['triangle_tags'],ref['outward_triangles_node_tags'])]
 lines += [' '.join(map(str,[tag,4,2,21,1,*row])) for tag,row in zip(ref['tetrahedron_tags'],ref['positive_tetrahedra_node_tags'])]
 return '\n'.join(lines+['$EndElements'])+'\n'
def verify_ascii(text,ref):
 lines=text.splitlines();need(len(lines)==81 and lines[:10]==['$MeshFormat','2.2 0 8','$EndMeshFormat','$PhysicalNames','2','2 11 "all_boundary"','3 21 "solid"','$EndPhysicalNames','$Nodes','15'] and lines[25:28]==['$EndNodes','$Elements','52'] and lines[-1]=='$EndElements','Exact ASCII2.2 framing/physical names/counts')
 for line,tag,xyz in zip(lines[10:25],ref['node_tags'],ref['coordinates_mm']):
  row=line.split();need(len(row)==4 and int(row[0])==tag and b''.join(bits(float(v)) for v in row[1:])==b''.join(bits(v) for v in xyz),'All coordinate bits/node tags roundtrip')
 wanted=[[tag,2,2,11,1,*row] for tag,row in zip(ref['triangle_tags'],ref['outward_triangles_node_tags'])]+[[tag,4,2,21,1,*row] for tag,row in zip(ref['tetrahedron_tags'],ref['positive_tetrahedra_node_tags'])]
 need([list(map(int,line.split())) for line in lines[28:80]]==wanted,'All ordered element tags/connectivity roundtrip')
 return True
def main(contract,digest):
 start=time.monotonic();contract=Path(contract);need(not contract.is_symlink() and sha(contract)==digest,'Exact adapter child');c=json.loads(contract.read_text())
 need(c.get('adapter_launch_authorized')is True and c.get('root_and_peer_review_complete')is True,'HELD: separate exact root/peer adapter child required')
 need(c.get('adapter_sha256')==sha(__file__) and c.get('python_sha256')==sha(sys.executable),'Executed source/interpreter pins')
 need(c.get('output')==OUTPUT and c.get('fixed_source_sha256')==INPUTS,'Fixed source/output scope')
 for name,h in c['input_sha256'].items():need(sha(ROOT/name)==h,'Before adapter pin drift')
 need(all(c['input_sha256'].get(k)==v for k,v in INPUTS.items()),'All source files directly bound')
 need((ROOT/(BASE+'arrays.json')).stat().st_size==96413 and (ROOT/(BASE+'cube.msh')).stat().st_size==2886,'Tiny fixed input sizes')
 payload=json.loads((ROOT/(BASE+'arrays.json')).read_text());report=json.loads((ROOT/(BASE+'fixture-report.json')).read_text());ref=reference(payload,report);text=ascii22(ref);verify_ascii(text,ref)
 output=ROOT/OUTPUT;need(not output.exists() and not output.is_symlink(),'Fresh fixed adapter output/no retry');need(time.monotonic()-start<5,'Bounded small adapter computation')
 output.mkdir();mesh=output/'imported-cube.msh';mesh.write_text(text);verify_ascii(mesh.read_text(),ref)
 (output/'cube-reference.json').write_text(json.dumps(ref,indent=2,sort_keys=True)+'\n')
 for name,h in c['input_sha256'].items():need(sha(ROOT/name)==h,'After adapter pin drift')
 need(sha(contract)==digest and time.monotonic()-start<5,'Contract/final elapsed bound')
 result=dict(status='complete_fixed_ASCII22_format_only',source_sha256=INPUTS,contract_sha256=digest,output_sha256={n:sha(output/n) for n in ['imported-cube.msh','cube-reference.json']},full_parse_after_write=True,native_or_scientific_calls=0,geometry_modified=False,triangle_labels_new_metadata=True,MOOSE_import_or_solve_verified=False,head_or_strength_or_manufacturing_qualification=False)
 (output/'adapter-receipt.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--contract',required=True);ap.add_argument('--contract-sha256',required=True);a=ap.parse_args();main(a.contract,a.contract_sha256)
