"""Fixed literal cube integer-tag adapter; no native import or geometry operation."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


def need(ok,message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse(text):
    lines=text.splitlines();need(lines[:10]==['$MeshFormat','2.2 0 8','$EndMeshFormat','$PhysicalNames','2','2 11 "all_boundary"','3 21 "solid"','$EndPhysicalNames','$Nodes','9'], 'Exact fixed ASCII2.2 header/physical names/nine nodes')
    need(len(lines)==47 and lines[19:22]==['$EndNodes','$Elements','24'] and lines[-1]=='$EndElements', 'Complete fixed cube sections/no extra records')
    nodes=[row.split() for row in lines[10:19]];elements=[row.split() for row in lines[22:46]]
    need(all(len(row)==4 and row[0].isdigit() and int(row[0])>0 for row in nodes) and len({row[0] for row in nodes})==9, 'Nine unique positive node IDs')
    for row in elements:
        need(all(v.isdigit() for v in row) and len(row)>=5 and row[2]=='2' and row[4]=='1' and ((row[1:4]==['2','2','11'] and len(row)==8) or (row[1:4]==['4','2','21'] and len(row)==9)), 'Fixed triangle/tetrahedron element records')
    need(len({row[0] for row in elements})==24 and all(int(row[0])>0 for row in elements), 'Unique positive element tags')
    return lines,nodes,elements


def restore(text,reference):
    lines,nodes,elements=parse(text);bits=lambda xyz:struct.pack('<ddd',*map(float,xyz))
    expected={bits(p):tag for tag,p in zip(reference['node_tags'],reference['coordinates_mm'])}
    need(len(expected)==9, 'Unique exact reference coordinate bits')
    mapping={int(row[0]):expected.get(bits(row[1:])) for row in nodes}
    need(None not in mapping.values() and len(set(mapping.values()))==9, 'Bijective binary64 coordinate association required')
    known={}
    for kind,records,tags in [('2',reference['outward_triangles_node_tags'],reference['triangle_tags']),('4',reference['positive_tetrahedra_node_tags'],reference['tetrahedron_tags'])]:
        for row,tag in zip(records,tags):
            key=min(tuple(row[i:]+row[:i]) for i in range(3)) if kind=='2' else tuple(row)
            need((kind,key) not in known, 'Unique reference element association');known[kind,key]=tag
    element_map={};written=[]
    for row in elements:
        need(all(int(v) in mapping for v in row[5:]), 'Element refers to an unknown written node')
        mapped=[mapping[int(v)] for v in row[5:]];kind=row[1]
        key=min(tuple(mapped[i:]+mapped[:i]) for i in range(3)) if kind=='2' else tuple(mapped)
        need((kind,key) in known, 'Oriented triangle or exact positive reference tetrahedron row required')
        tag=known[kind,key];need(tag not in element_map.values(), 'Bijective reference element association')
        element_map[int(row[0])]=tag;written.append(' '.join([str(tag)]+row[1:5]+list(map(str,mapped))))
    need(len(known)==len(element_map)==24, 'Complete reference element set')
    result=lines.copy();result[10:19]=[' '.join([str(mapping[int(row[0])])]+row[1:]) for row in nodes];result[22:46]=written
    return '\n'.join(result)+'\n',mapping,element_map


def verify(before,after,node_map,element_map,reference):
    old,on,oe=parse(before);new,nn,ne=parse(after)
    need(old[:10]==new[:10] and old[19:22]==new[19:22] and old[-1]==new[-1], 'Header/physical/section metadata changed')
    need({int(row[0]) for row in nn}==set(reference['node_tags']), 'Complete restored node tags')
    for a,b in zip(on,nn): need(int(b[0])==node_map[int(a[0])] and a[1:]==b[1:], 'Coordinate words/order changed')
    for a,b in zip(oe,ne): need(int(b[0])==element_map[int(a[0])] and a[1:5]==b[1:5] and [node_map[int(v)] for v in a[5:]]==list(map(int,b[5:])), 'Element metadata/oriented connectivity changed')
    need({int(row[0]) for row in ne}==set(reference['triangle_tags']+reference['tetrahedron_tags']), 'Complete restored element tags')
    return True


def main(contract_path,digest,output):
    need(sha(contract_path)==digest, 'Exact frozen adapter contract required');c=json.loads(Path(contract_path).read_text())
    need(c['adapter_launch_authorized'] is True and c['root_and_peer_review_complete'] is True, 'Separate reviewed adapter launch required')
    output=Path(output);need(str(output.resolve())==c['expected_output'] and not output.exists() and not output.is_symlink(), 'Fresh exact adapter output required')
    need(sha(__file__)==c['adapter_sha256'] and sha(sys.executable)==c['python_sha256'], 'Adapter/interpreter identity')
    for name,h in c['input_sha256'].items():need(sha(name)==h, 'Before input drift: '+name)
    source=Path(c['input_mesh']);reference=json.loads(Path(c['reference']).read_text());original=source.read_text();adapted,nodes,elements=restore(original,reference)
    need(verify(original,adapted,nodes,elements,reference), 'Full in-memory independent parse')
    output.mkdir();target=output/'imported-cube.msh'
    with target.open('x') as stream:stream.write(adapted)
    need(target.read_text()==adapted and verify(original,target.read_text(),nodes,elements,reference), 'Full file parse-after-write')
    for name,h in c['input_sha256'].items():need(sha(name)==h, 'After input drift: '+name)
    need(sha(contract_path)==digest, 'Contract drift')
    result=dict(status='complete_integer_tag_restoration_only',contract_sha256=digest,input_sha256=c['input_sha256'],
        output_sha256={'imported-cube.msh':sha(target)},output_bytes={'imported-cube.msh':target.stat().st_size},
        node_written_to_reference_IDs=nodes,element_written_to_reference_IDs=elements,all9_nodes_and24_elements_bijective=True,
        coordinate_words_physical_names_and_ordered_connectivity_preserved=True,full_parse_after_write=True,
        Gmsh_or_solver_rerun=False,geometry_or_quality_modified=False,head_or_physical_qualification=False)
    with (output/'manifest.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--contract-sha256',required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    main(a.contract,a.contract_sha256,a.output)
