#!/usr/bin/env python3
"""Essai privé 1→4 des tétraèdres ayant au plus deux faces internes.

Sélection par incidence de tout le MSH, jamais par une liste de défauts.
Le centre est la moyenne rationnelle exacte des coordonnées décimales sources.
Chaque enfant remplace un sommet par ce centre : par multilinéarité du
déterminant, son volume orienté vaut exactement V/4. Cette identité décimale
est contrôlée séparément des calculs arrondis binary64. Aucune face parentale
n'est subdivisée ; l'essai reste conforme avec les voisins non subdivisés.
Ni amélioration globale, ni CFD, ni autorisation de fabrication ne sont prouvées.
"""
import argparse
from collections import Counter, namedtuple
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import time

SOURCE_MESH_SHA256='c0cbb257619ce378a9c9274da305d6bf34ce55dd4913a55cf122649ec45326ca'
NATIVE_DOMAIN_SHA256='fab1338a3e3cf36469977716a9cb54b3118382f592c7c41d7c789bdb5fb3aeba'
Node=namedtuple('Node','xyz tokens raw')
Element=namedtuple('Element','id kind tags nodes raw')


def sha(data):return hashlib.sha256(data).hexdigest()


def read_mesh(data):
    data.decode('ascii')
    lines=data.splitlines(keepends=True);sections={};i=0
    while i<len(lines):
        if not lines[i].strip():i+=1;continue
        name=lines[i].strip()
        if not name.startswith(b'$') or name.startswith(b'$End') or name in sections:
            raise ValueError('invalid_or_duplicate_MSH_section')
        end=b'$End'+name[1:];j=i+1
        while j<len(lines) and lines[j].strip()!=end:j+=1
        if j==len(lines):raise ValueError('unterminated_MSH_section')
        sections[name]=(i,j);i=j+1
    def body(name):
        a,b=sections[name];return lines[a+1:b]
    if [r.strip() for r in body(b'$MeshFormat')]!=[b'2.2 0 8']:
        raise ValueError('MSH22_ASCII_required')
    if set(sections)&{b'$NodeData',b'$ElementData',b'$ElementNodeData',b'$Periodic'}:
        raise ValueError('data_or_periodic_constraints_require_separate_transfer_not_supported')
    def counted(name):
        rows=body(name)
        if not rows or int(rows[0])!=len(rows)-1:raise ValueError('MSH_count_mismatch')
        return rows[1:]
    nodes={}
    for raw in counted(b'$Nodes'):
        parts=raw.split()
        if len(parts)!=4:raise ValueError('invalid_node_record')
        tag=int(parts[0]);xyz=tuple(map(float,parts[1:]))
        if tag<=0 or tag in nodes or not all(map(math.isfinite,xyz)):raise ValueError('invalid_node_identity_or_coordinate')
        nodes[tag]=Node(xyz,tuple(parts[1:]),raw)
    elements={}
    for raw in counted(b'$Elements'):
        parts=list(map(int,raw.split()))
        if len(parts)<3:raise ValueError('invalid_element_record')
        tag,kind,n=parts[:3];arity={1:2,2:3,4:4,15:1}.get(kind)
        if tag<=0 or tag in elements or n<2 or arity is None or len(parts)!=3+n+arity:
            raise ValueError('unique_tagged_linear_MSH_elements_required')
        ids=tuple(parts[3+n:])
        if len(set(ids))!=arity or any(v not in nodes for v in ids):raise ValueError('invalid_element_nodes')
        elements[tag]=Element(tag,kind,tuple(parts[3:3+n]),ids,raw)
    if not any(e.kind==4 for e in elements.values()):raise ValueError('tetrahedra_required')
    return {'lines':lines,'sections':sections,'nodes':nodes,'elements':elements}


def determinant(points):
    a,b,c,d=points
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[d[i]-a[i] for i in range(3)]
    return sum(u[i]*(v[(i+1)%3]*w[(i+2)%3]-v[(i+2)%3]*w[(i+1)%3]) for i in range(3))


def outward_faces(nodes):
    a,b,c,d=nodes;return ((a,c,b),(a,b,d),(a,d,c),(b,c,d))


def face_sign(face):
    return 1 if min(face[i:]+face[:i] for i in range(3))==tuple(sorted(face)) else -1


def topology(mesh):
    incidence={};degree=Counter();volumes=[];tetrahedra=0
    for e in mesh['elements'].values():
        if e.kind!=4:continue
        value=determinant([mesh['nodes'][n].xyz for n in e.nodes])
        if not math.isfinite(value) or value<=0:raise ValueError('strictly_positive_binary64_parent_tetrahedra_required')
        volumes.append(value/6);degree[e.id]=0;tetrahedra+=1
        for face in outward_faces(e.nodes):
            key=tuple(sorted(face));sign=face_sign(face)
            if key not in incidence:incidence[key]=(e.id,0,sign)
            else:
                owner,neighbor,previous=incidence[key]
                if neighbor or previous+sign!=0:raise ValueError('nonmanifold_or_incoherent_tetrahedral_face_incidence')
                incidence[key]=(owner,e.id,0)
    boundary={};internal=0
    for face,(owner,neighbor,sign) in incidence.items():
        if neighbor:degree[owner]+=1;degree[neighbor]+=1;internal+=1
        else:boundary[face]=sign
    surface={}
    for e in mesh['elements'].values():
        if e.kind!=2:continue
        key=tuple(sorted(e.nodes))
        if key in surface:raise ValueError('duplicate_surface_triangle')
        surface[key]=face_sign(e.nodes)
    if surface!=boundary:raise ValueError('surface_records_must_equal_oriented_tetrahedral_boundary')
    return {'degree':degree,'boundary':boundary,'tetrahedra':tetrahedra,
        'internal_faces':internal,'binary64_volume':math.fsum(volumes)}


def exact_decimal(value):
    """Écrire exactement une fraction décimale finie, sans arrondi de contexte."""
    denominator=value.denominator;twos=fives=0
    while denominator%2==0:twos+=1;denominator//=2
    while denominator%5==0:fives+=1;denominator//=5
    if denominator!=1:raise ValueError('non_terminating_decimal_coordinate')
    scale=max(twos,fives);integer=value.numerator*2**(scale-twos)*5**(scale-fives)
    sign='-' if integer<0 else '';digits=str(abs(integer))
    if scale:
        digits=digits.zfill(scale+1);digits=digits[:-scale]+'.'+digits[-scale:]
    return (sign+digits).encode('ascii')


def quarter_children(parent_points, center_points):
    """Preuve exacte sur les coordonnées sérialisées, pas seulement un estimateur."""
    volume6=determinant(parent_points)
    if volume6<=0:raise ValueError('strictly_positive_exact_parent_required')
    expected=tuple(sum(p[i] for p in parent_points)/4 for i in range(3))
    if tuple(center_points)!=expected:raise ValueError('serialized_center_is_not_exact_barycenter')
    for i in range(4):
        child=list(parent_points);child[i]=center_points
        if determinant(child)!=volume6/4:raise ValueError('exact_quarter_volume_not_proven')
    return volume6


def subdivide_mesh(data):
    original=read_mesh(data);before=topology(original)
    targets=[e for e in original['elements'].values() if e.kind==4 and before['degree'][e.id]<=2]
    if not targets:raise ValueError('no_low_degree_tetrahedron_to_subdivide')
    next_node=max(original['nodes'])+1;next_element=max(original['elements'])+1
    additions=[];replacements={};mapping=[];max_quarter_error=0.;fraction_points={}
    for parent in targets:
        points=[]
        for nid in parent.nodes:
            if nid not in fraction_points:
                fraction_points[nid]=tuple(Fraction(v.decode('ascii')) for v in original['nodes'][nid].tokens)
            points.append(fraction_points[nid])
        center=tuple(sum(p[i] for p in points)/4 for i in range(3))
        tokens=tuple(exact_decimal(v) for v in center)
        recovered=tuple(Fraction(v.decode('ascii')) for v in tokens)
        quarter_children(points,recovered)
        center_float=tuple(float(v) for v in tokens)
        if not all(map(math.isfinite,center_float)):raise ValueError('nonfinite_serialized_center')
        additions.append(str(next_node).encode()+b' '+b' '.join(tokens)+b'\n')
        children=[];child_ids=[]
        parent_float=[original['nodes'][n].xyz for n in parent.nodes];parent_det=determinant(parent_float)
        for i in range(4):
            ids=list(parent.nodes);ids[i]=next_node
            binary_points=list(parent_float);binary_points[i]=center_float
            child_det=determinant(binary_points)
            if not math.isfinite(child_det) or child_det<=0:raise ValueError('nonpositive_binary64_child_tetrahedron')
            max_quarter_error=max(max_quarter_error,abs(child_det/(parent_det/4)-1.))
            fields=(next_element,4,len(parent.tags),*parent.tags,*ids)
            children.append(b' '.join(str(v).encode() for v in fields)+b'\n')
            child_ids.append(next_element);next_element+=1
        replacements[parent.id]=children
        mapping.append({'parent_element_id':parent.id,'internal_face_count':before['degree'][parent.id],
            'centroid_node_id':next_node,'child_element_ids':child_ids})
        next_node+=1
    node_start,node_end=original['sections'][b'$Nodes'];element_start,element_end=original['sections'][b'$Elements']
    def count_line(n,old):return str(n).encode()+(b'\r\n' if old.endswith(b'\r\n') else b'\n')
    rewritten={node_start+1:[count_line(len(original['nodes'])+len(targets),original['lines'][node_start+1])],
        element_start+1:[count_line(len(original['elements'])+3*len(targets),original['lines'][element_start+1])]}
    for offset,e in enumerate(original['elements'].values(),element_start+2):
        if e.id in replacements:rewritten[offset]=replacements[e.id]
    output=[]
    for i,line in enumerate(original['lines']):
        if i==node_end:output.extend(additions)
        output.extend(rewritten.get(i,[line]))
    candidate=b''.join(output);reread=read_mesh(candidate);after=topology(reread)
    target_ids={e.id for e in targets};child_ids={c for row in mapping for c in row['child_element_ids']}
    new_nodes={row['centroid_node_id'] for row in mapping}
    untouched=all(reread['elements'].get(i)==e for i,e in original['elements'].items() if i not in target_ids)
    existing_nodes=all(reread['nodes'].get(i)==n for i,n in original['nodes'].items())
    other_sections=True
    for name,(a,b) in original['sections'].items():
        if name in (b'$Nodes',b'$Elements'):continue
        x,y=reread['sections'][name]
        other_sections=other_sections and original['lines'][a:b+1]==reread['lines'][x:y+1]
    child_tags=all(reread['elements'][c].tags==original['elements'][row['parent_element_id']].tags
        for row in mapping for c in row['child_element_ids'])
    gates={'all_and_only_tetrahedra_with_at_most_two_internal_faces_selected':
        target_ids=={i for i,d in before['degree'].items() if d<=2},
        'existing_node_lines_and_coordinates_byte_exact':existing_nodes,
        'all_untargeted_element_lines_byte_exact':untouched,
        'all_other_sections_byte_exact':other_sections,
        'exactly_one_center_and_four_children_per_target':len(child_ids)==4*len(targets) and len(new_nodes)==len(targets),
        'no_other_node_or_element_identity_changes':set(reread['nodes'])==set(original['nodes'])|new_nodes
            and set(reread['elements'])==(set(original['elements'])-target_ids)|child_ids,
        'child_physical_and_elementary_tags_identical':child_tags,
        'exact_decimal_barycenters_and_quarter_volumes':True,
        'positive_binary64_children_and_global_tetrahedra':True,
        'conforming_incidence_and_opposite_internal_face_orientation':True,
        'oriented_exterior_boundary_exactly_preserved':before['boundary']==after['boundary']}
    if not all(gates.values()):raise ValueError('subdivision_invariants_failed')
    report={'schema':'m64-native-tet-central-subdivision/v1','source_mesh_sha256':sha(data),
        'candidate_mesh_sha256':sha(candidate),'native_domain_sha256':NATIVE_DOMAIN_SHA256,
        'native_domain_provenance':'inherited_from_pinned_input_mesh; no_CAD_read_or_modified',
        'selection':{'criterion':'all_tetrahedra_with_internal_face_count_le_2_from_full_MSH_incidence',
            'input_tetrahedra':before['tetrahedra'],'output_tetrahedra':after['tetrahedra'],
            'selected_tetrahedra':len(targets),'input_degree_histogram':dict(sorted(Counter(before['degree'].values()).items())),
            'selected_degree_histogram':dict(sorted(Counter(before['degree'][e.id] for e in targets).items())),
            'defect_list_used':False},'parent_children_private':mapping,'gates':gates,
        'volume_proof':{'arithmetic':'exact rational values of serialized decimal coordinates',
            'identity':'det(child)=det(parent)/4>0 for each of four children',
            'verified_parent_count':len(targets),'verified_child_count':4*len(targets),
            'binary64_max_child_quarter_relative_error':max_quarter_error,
            'binary64_input_volume':before['binary64_volume'],'binary64_output_volume':after['binary64_volume'],
            'binary64_volume_relative_difference':abs(after['binary64_volume']/before['binary64_volume']-1.),
            'binary64_values_are_not_exact_volume_identities':True},
        'surface_boundary_triangles':len(before['boundary']),
        'CFD_qualified':False,'manufacturing_authorized':False,'OpenFOAM_checks_executed':False,
        'global_mesh_quality_improvement_proven':False,'units':'unchanged scan units; physical scale not certified'}
    return candidate,report


def run(args):
    started=time.monotonic();source=Path(args.source_mesh);output=Path(args.output_mesh);receipt=Path(args.report)
    if source.is_symlink() or not source.is_file():raise ValueError('regular_pinned_source_required')
    if output==receipt or output.exists() or output.is_symlink() or receipt.exists() or receipt.is_symlink():
        raise ValueError('new_distinct_output_files_required')
    for parent in (output.parent,receipt.parent):
        if not parent.is_dir() or parent.is_symlink() or parent.stat().st_mode&0o077:
            raise ValueError('existing_private_output_directory_mode700_required')
    data=source.read_bytes();source_code_sha=sha(Path(__file__).read_bytes())
    if sha(data)!=SOURCE_MESH_SHA256:raise ValueError('exact_source_mesh_sha256_required')
    candidate,report=subdivide_mesh(data)
    if sha(source.read_bytes())!=SOURCE_MESH_SHA256 or sha(Path(__file__).read_bytes())!=source_code_sha:
        raise ValueError('inputs_changed_during_subdivision')
    report.update(source_sha256=source_code_sha,source_mesh_unchanged=True,
        status='central_subdivision_candidate_only_independent_review_and_checkMesh_required',
        elapsed_seconds=time.monotonic()-started)
    payload=json.dumps(report,indent=2,allow_nan=False).encode()+b'\n';created=[]
    try:
        for path,content in ((output,candidate),(receipt,payload)):
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);created.append(path)
            with os.fdopen(fd,'wb') as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
    except Exception:
        for path in created:path.unlink()
        raise
    print(json.dumps({'status':report['status'],'selected_tetrahedra':report['selection']['selected_tetrahedra'],
        'candidate_sha256':sha(candidate),'report_sha256':sha(payload),'elapsed_seconds':report['elapsed_seconds']}))
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-mesh','output-mesh','report'):parser.add_argument('--'+name,type=Path,required=True)
    resource.setrlimit(resource.RLIMIT_CPU,(300,305))
    raise SystemExit(run(parser.parse_args()))
