"""Exact signed P2 tetrahedron/triangle integrals; integers and fixed factorial weights."""
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import factorial

PAIRS=((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
FACES=((0,2,1),(0,1,3),(0,3,2),(1,2,3))

def require(value,message):
    if not value:raise ValueError(message)

def add(*polynomials):
    result={}
    for polynomial in polynomials:
        for exponent,value in polynomial.items():result[exponent]=result.get(exponent,0)+value
    return {exponent:value for exponent,value in result.items()if value}

def scale(polynomial,value):return {exponent:coefficient*value for exponent,coefficient in polynomial.items()if coefficient*value}

def multiply(left,right):
    result={}
    for a,x in left.items():
        for b,y in right.items():
            exponent=tuple(i+j for i,j in zip(a,b));result[exponent]=result.get(exponent,0)+x*y
    return {exponent:value for exponent,value in result.items()if value}

def derivative(polynomial,axis):
    result={}
    for exponent,value in polynomial.items():
        if exponent[axis]:
            changed=list(exponent);changed[axis]-=1;result[tuple(changed)]=value*exponent[axis]
    return result

def determinant_polynomial(rows):
    a,b,c=rows
    return add(multiply(a[0],add(multiply(b[1],c[2]),scale(multiply(b[2],c[1]),-1))),
               scale(multiply(a[1],add(multiply(b[0],c[2]),scale(multiply(b[2],c[0]),-1))),-1),
               multiply(a[2],add(multiply(b[0],c[1]),scale(multiply(b[1],c[0]),-1))))

def integral720(polynomial,dimension,maximum_degree):
    answer=0
    for exponent,value in polynomial.items():
        require(len(exponent)==dimension and sum(exponent)<=maximum_degree,'Polynomial degree/dimension differs')
        numerator=720
        for degree in exponent:numerator*=factorial(degree)
        denominator=factorial(sum(exponent)+dimension)
        require(numerator%denominator==0,'Fixed factorial denominator is insufficient')
        answer+=value*(numerator//denominator)
    return answer

def shapes(dimension):
    one={(0,)*dimension:1};variables=[]
    for axis in range(dimension):
        exponent=[0]*dimension;exponent[axis]=1;variables.append({tuple(exponent):1})
    barycentric=[add(one,*(scale(v,-1)for v in variables)),*variables]
    pairs=PAIRS if dimension==3 else ((0,1),(1,2),(2,0))
    return [multiply(v,add(scale(v,2),scale(one,-1)))for v in barycentric]+[scale(multiply(barycentric[i],barycentric[j]),4)for i,j in pairs]

@lru_cache(maxsize=2)
def tensors(dimension):
    basis=shapes(dimension);result=[]
    # For cells, translate every point by corner 0: N0 then contributes zero.
    indices=range(1,10)if dimension==3 else range(6)
    for triple in combinations(indices,3):
        if dimension==3:rows=[[derivative(basis[i],axis)for axis in range(3)]for i in triple]
        else:rows=[[basis[i],derivative(basis[i],0),derivative(basis[i],1)]for i in triple]
        coefficient=integral720(determinant_polynomial(rows),dimension,3 if dimension==3 else 4)
        if coefficient:result.append((triple,coefficient))
    return tuple(result)

def determinant(a,b,c):
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])

def cell720(coordinates):
    require(len(coordinates)==10,'Complete T10 coordinates required')
    origin=coordinates[0];points=[tuple(x-y for x,y in zip(point,origin))for point in coordinates]
    return sum(coefficient*determinant(*(points[i]for i in triple))for triple,coefficient in tensors(3))

def face2160(coordinates):
    require(len(coordinates)==6,'Complete oriented T6 coordinates required')
    # The fixed tensor integrates x dot (xu cross xv); denominator 2160 includes /3.
    return sum(coefficient*determinant(*(coordinates[i]for i in triple))for triple,coefficient in tensors(2))

def edge_mids(elements):
    answer={}
    for eid,row in elements:
        require(type(eid)is int and len(row)==len(set(row))==10,'Unique complete T10 row required')
        for position,(i,j)in enumerate(PAIRS,4):
            edge=tuple(sorted((row[i],row[j])));tag=row[position]
            require(edge not in answer or answer[edge]==tag,'Conflicting shared-edge midside identity')
            answer[edge]=tag
    return answer

def face6(corners,mids):
    a,b,c=corners
    return (*corners,*(mids[tuple(sorted(edge))]for edge in [(a,b),(b,c),(c,a)]))

def mapped_chain(integer,elements,boundary,power,emit_cell,emit_face):
    mids=edge_mids(elements);cells={};faces={};total_cell=0;total_face=0;negative=zero=0
    for eid,row in elements:
        value=cell720([integer[tag]for tag in row]);cells[eid]=value;total_cell+=value
        negative+=value<0;zero+=value==0
        a,b,c,d=(integer[tag]for tag in row[:4]);corner=120*determinant(*(tuple(x-y for x,y in zip(point,a))for point in [b,c,d]))
        emit_cell(dict(element=eid,corner_numerator_720=str(corner),T10_numerator_720=str(value),T10_minus_corner_numerator_720=str(value-corner)))
    for corners in boundary:
        tags=face6(corners,mids);value=face2160([integer[tag]for tag in tags]);key=tuple(sorted(corners));require(key not in faces,'Duplicate complete boundary face')
        faces[key]=value;total_face+=value;corner=360*determinant(*(integer[tag]for tag in corners))
        emit_face(dict(oriented_corner_tags=list(corners),oriented_T6_tags=list(tags),corner_numerator_2160=str(corner),T6_numerator_2160=str(value),T6_minus_corner_numerator_2160=str(value-corner)))
    require(3*total_cell==total_face,'Exact full quadratic cell/boundary identity failed')
    denominator=720*(1<<(3*power))
    return dict(cells=cells,faces=faces,total=Fraction(total_cell,denominator),report=dict(T10_elements=len(cells),outward_T6_faces=len(faces),cell_numerator_720=str(total_cell),boundary_numerator_2160=str(total_face),common_coordinate_denominator_power2=power,cell_boundary_integrals_exactly_equal=True,negative_signed_T10_integrals=negative,zero_signed_T10_integrals=zero,physical_mapping_validity_not_established_by_algebra=True,tetra_tensor_nonzero_terms=len(tensors(3)),triangle_tensor_nonzero_terms=len(tensors(2))))

def compose_parents(proofs,coarse_ids,final_ids):
    require(proofs and [p['pass_number']for p in proofs]==list(range(1,len(proofs)+1)),'Complete ordered pass lineage required')
    chains={eid:[]for eid in final_ids};current={eid:eid for eid in final_ids}
    for proof in reversed(proofs):
        parents={int(child):parent for child,parent in proof['parent_elements'].items()}
        require(set(parents)==set(range(1,proof['output_elements']+1))and all(type(v)is int for v in parents.values()),'Incomplete typed pass parent map')
        for eid,now in current.items():
            require(now in parents,'Final child has no retained parent');parent=parents[now]
            require(parent in coarse_ids if proof['pass_number']==1 else 1<=parent<=proof['input_elements'],'Parent outside immediately preceding mesh')
            chains[eid].append(dict(pass_number=proof['pass_number'],child=now,parent=parent));current[eid]=parent
    require(set(current.values())==set(coarse_ids),'A coarse parent disappeared')
    return current,chains

def compose_faces(proofs,coarse_faces,final_faces):
    current={face:face for face in final_faces}
    for proof in reversed(proofs):
        parents={tuple(row['child']):tuple(row['parent'])for row in proof['boundary_parent_faces']}
        require(len(parents)==len(proof['boundary_parent_faces']),'Duplicate retained boundary child')
        for face,now in current.items():require(now in parents,'Final exterior face has no retained parent');current[face]=parents[now]
    require(set(current.values())==set(coarse_faces),'An original exterior parent disappeared')
    return current

def parent_ledger(coarse,current,parents,coarse_corner,current_corner,denominator,emit):
    mapped={eid:0 for eid in coarse};corner={eid:0 for eid in coarse};counts={eid:0 for eid in coarse}
    for child,parent in parents.items():mapped[parent]+=current[child];corner[parent]+=current_corner[child];counts[parent]+=1
    for parent in sorted(coarse):
        require(counts[parent]>0,'A coarse parent has no descendants')
        emit(dict(coarse_parent_element=parent,final_child_count=counts[parent],coarse_corner_numerator=str(coarse_corner[parent]),children_corner_numerator=str(corner[parent]),corner_delta_numerator=str(corner[parent]-coarse_corner[parent]),coarse_T10_numerator=str(coarse[parent]),children_T10_numerator=str(mapped[parent]),T10_delta_numerator=str(mapped[parent]-coarse[parent]),common_denominator=str(denominator)))
    require(sum(mapped.values())==sum(current.values())and sum(corner.values())==sum(current_corner.values()),'Parent ledger does not cover complete current mesh')
    return dict(coarse_parents=len(counts),final_children=len(parents),corner_delta=Fraction(sum(corner.values())-sum(coarse_corner.values()),denominator),T10_delta=Fraction(sum(mapped.values())-sum(coarse.values()),denominator),nonzero_corner_parent_count=sum(corner[e]!=coarse_corner[e]for e in counts),nonzero_T10_parent_count=sum(mapped[e]!=coarse[e]for e in counts),immediate_pass_geometries_not_reconstructed=True)
