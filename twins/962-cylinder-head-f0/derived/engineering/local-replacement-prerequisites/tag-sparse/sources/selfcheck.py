"""UNRUN stdlib/AST metadata and API mocks; no native or geometric validity oracle."""
from pathlib import Path
from types import SimpleNamespace
import ast,copy,hashlib,json,struct
SOURCE_SHA='3ca04d04ef849e6f130e6cde632a9615de911ddc9d14c8c28d410cefc4c50af5'
source=Path(__file__).with_name('reader.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()==SOURCE_SHA
tree=ast.parse(source.read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
ns={'struct':struct,'FREE':[27,28,29]}
assignments=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['NODE_TAGS','BOUNDARY','TRIANGLES','TETS','CENTRE','COUNTS'] for t in n.targets)]
selected=assignments+[functions[n] for n in ['make_case','require_outside','edit_once']]
exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),'<selected-metadata-and-mocks>','exec'),ns)
# This stub isolates new index/tag logic. The unchanged candidate validator has its own prior guards/peer.
coords=[[float(i),0.,0.] for i in range(1,17)]+[[.2,.3,.4],[.3,.4,.5],[.4,.5,.6]]
ns['candidate_rows']=lambda d,a:(coords,[28,29])
old=[{'tetrahedron_tag':200+i,'node_tags':[1435493,i%16+1,(i+1)%16+1,(i+2)%16+1]} for i in range(28)]
points=[{'node_tag':i,'coordinates_mm':[float(i),0.,0.],'binary64_hex':[float(i).hex(),float(0).hex(),float(0).hex()]} for i in range(1,17)]
points.append({'node_tag':1435493,'coordinates_mm':[.5,.5,.5],'binary64_hex':[float(.5).hex(),float(.5).hex(),float(.5).hex()]})
obs={'apex':1435493,'native_ordered_cell_rows':old,'selected_node_rows':points}
shell={'local_to_global_node_tags':list(range(1,17)),'vertex_rows':[{'source_global_node_tag':r['node_tag'],'coordinates_mm':r['coordinates_mm']} for r in points[:-1]],
 'oriented_triangle_rows':[{'local_node_tags':[i%16+1,(i+1)%16+1,(i+2)%16+1]} for i in range(28)]}
arrays={'saved_reopen':{'tetra_node_tags':[[27,1,2,3] for _ in range(39)]}}
case=ns['make_case'](obs,shell,{},arrays)
assert case['node_map'][27]==1435493 and [case['node_map'][x] for x in [28,29]]==[case['nmax']+1,case['nmax']+2]
assert case['emax']==max(case['triangles'])>max(case['cells'])
assert case['element_slots'][:28]==sorted(case['old']) and case['element_slots'][28:]==list(range(case['emax']+1,case['emax']+12))
assert len(case['triangles'])==40 and len(case['points'])==26 and len(case['proposed'])==28
assert all(case['classes'][t]==[2,401] for t in range(1,17)) and case['classes'][1435493]==[3,11]

def refuses(fn,*args):
 try:fn(*args)
 except (ValueError,RuntimeError):return
 raise AssertionError('Expected refusal')

def state(points,cells,classes):
 return {'node_tags':sorted(points),'coordinate_words':[[float(x).hex() for x in points[t]] for t in sorted(points)],
  'tetra_tags':sorted(cells),'tetra_node_tags':[cells[t] for t in sorted(cells)],
  'entities':[[2,401],[2,501],[3,11],[3,701]],'entity_boundaries':{'fixture':'fixed'},'physical_groups':[],
  'lower_dimensional_elements':[[t,row] for t,row in sorted(case['triangles'].items())],
  'classifications':{str(t):v for t,v in classes.items()}}
before=state(case['points'],case['cells'],case['classes']);after=state(case['proposed'],{**case['cube_cells'],**case['replacement']},case['after_classes'])
ns['require_outside'](before,after,case)
for field in ['coordinate_words','tetra_node_tags','classifications','lower_dimensional_elements']:
 bad=copy.deepcopy(after)
 if field=='coordinate_words':bad[field][0][1]=(-0.).hex() # signed-zero bit drift
 elif field=='tetra_node_tags':
  i=bad['tetra_tags'].index(min(case['cube_cells']));bad[field][i]=bad[field][i][::-1]
 elif field=='classifications':bad[field]['1']=[3,11]
 else:bad[field][0][1]=list(reversed(bad[field][0][1]))
 refuses(ns['require_outside'],before,bad,case)

calls=[]
mesh=SimpleNamespace(getMaxNodeTag=lambda:case['nmax'],getMaxElementTag=lambda:case['emax'],
 getElement=lambda t:(4,case['old'][t],3,11),getNode=lambda t:([],[],3,11),
 removeElements=lambda *a:calls.append(('removeElements',a)),setNode=lambda *a:calls.append(('setNode',a)),
 addNodes=lambda *a:calls.append(('addNodes',a)),addElementsByType=lambda *a:calls.append(('addElementsByType',a)),
 rebuildNodeCache=lambda *a:calls.append(('rebuildNodeCache',a)),rebuildElementCache=lambda *a:calls.append(('rebuildElementCache',a)))
gmsh=SimpleNamespace(model=SimpleNamespace(mesh=mesh));counts={k:0 for k in ns['COUNTS']}
ns['edit_once'](gmsh,case,counts)
assert [x[0] for x in calls]==['removeElements','setNode','addNodes','addElementsByType','rebuildNodeCache','rebuildElementCache']
assert len(calls[0][1][2])==28 and calls[0][1][:2]==(3,11) and calls[1][1][0]==1435493
assert calls[2][1][2]==[case['nmax']+1,case['nmax']+2] and len(calls[3][1][2])==39
assert calls[-1][1]==(False,) and calls[-2][1]==(False,)
for bad in [{},dict(list(case['old'].items())[:-1])]:
 altered=dict(case,old=bad);refuses(ns['edit_once'],gmsh,altered,{k:0 for k in ns['COUNTS']})
throw_counts={k:0 for k in ns['COUNTS']}
def throws(*a):raise RuntimeError('synthetic removal failure')
mesh.removeElements=throws;refuses(ns['edit_once'],gmsh,case,throw_counts)
assert throw_counts['removeElements']==1 and throw_counts['setNode']==0
for node in ast.walk(tree):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
  assert node.func.attr not in ['generate','optimize','createGeometry','reclassifyNodes','renumberNodes','renumberElements','removeDuplicateNodes']
print(json.dumps({'status':'pass','scope':'metadata/tag/bitwise outside guards and API mocks only','native_or_geometry_execution':False}))
