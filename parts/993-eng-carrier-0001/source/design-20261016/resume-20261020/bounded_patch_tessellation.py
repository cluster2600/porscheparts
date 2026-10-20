"""Shared-station NURBS tessellation with exact rational L1 deviation bounds.

The four error terms are U chord error, rational V chord error, bilinear-to-
triangle error, and float32 coordinate rounding. Each receives one quarter
of the unchanged 0.06 mm surface budget. No native fillet or radius change.
"""
import argparse
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import resource
import signal
import struct
import time
import traceback


def norm1(vector):return sum(abs(x)for x in vector)


def power_to_bernstein(coefficients,degree):
    return [sum(coefficients[k]*F(math.comb(i,k),math.comb(degree,k))
                for k in range(min(i+1,len(coefficients))))for i in range(degree+1)]


def split_bezier(points):
    work=list(points);left=[work[0]];right=[work[-1]]
    while len(work)>1:
        work=[tuple((a+b)/2 for a,b in zip(p,q))for p,q in zip(work,work[1:])]
        left.append(work[0]);right.append(work[-1])
    return left,list(reversed(right))


def chord_bound(points):
    degree=len(points)-1
    return max(norm1(tuple(value-((degree-i)*a+i*b)/degree
                           for value,a,b in zip(point,points[0],points[-1])))
               for i,point in enumerate(points))


def quad_triangle_bound(p00,p01,p10,p11):
    return norm1(tuple(d-c-b+a for a,b,c,d in zip(p00,p01,p10,p11)))/4


def profiles_and_injectivity(row):
    profiles={}
    for surface in row['surfaces']:
        for name,values in surface['control_columns'].items():
            values=[tuple(F(x)for x in p)for p in values]
            if name in profiles and profiles[name]!=values:raise ValueError('Shared control curve differs')
            profiles[name]=values
    if set(profiles)!=set('APBCD'):raise ValueError('Incomplete five-curve source')
    weights=[F(x)for x in row['surfaces'][0]['weights']]
    if len(weights)!=3 or not all(w>0 for w in weights):raise ValueError('Positive quadratic V weights required')
    x=[p[0]for p in profiles['P']];sign=1 if x[-1]>x[0]else -1
    differences=[sign*(b-a)for a,b in zip(x,x[1:])]
    if not all(v>0 for v in differences):raise ValueError('Strict monotone X control coefficients required')
    for points in zip(*(profiles[name]for name in 'APBCD')):
        a,p,b,c,d=points
        if not(all(q[0]==p[0]for q in points)and a[1]==p[1]and b[2]==p[2]and a[2]==d[2]and c[1]==d[1]and c[1]>p[1]and c[2]<p[2]and b[1]<=p[1]and a[2]>=p[2]):
            raise ValueError('The source cross-section separation inequalities differ')
    degree=row['aligned_curve']['degree'];knots=[F(k)for k,m in zip(row['aligned_curve']['knots'],row['aligned_curve']['multiplicities'])for _ in range(m)]
    for k in range(degree,len(x)):
        if knots[k]==knots[k+1]:continue
        active=range(k-degree,k+1)
        if not(any(profiles['A'][i][2]>profiles['P'][i][2]for i in active)and any(profiles['B'][i][1]<profiles['P'][i][1]for i in active)):
            raise ValueError('An open source span has zero radius')
    for i in [0,1,-2,-1]:
        if profiles['A'][i]!=profiles['P'][i]or profiles['B'][i]!=profiles['P'][i]:
            raise ValueError('Source endpoint position or first-derivative closure differs')
    proof=dict(strict_X_monotone=True,X_direction=sign,minimum_signed_control_X_difference_mm=str(min(differences)),positive_V_weights=[str(w)for w in weights],
               complete_control_separation_inequalities=True,positive_radius_in_every_open_knot_span=True,
               zero_radius_and_first_derivative_at_both_ends=True,
               scope='Injective section sweep defined by these complete source control nets; does not certify its tessellation')
    return profiles,weights,proof


def initial_leaves(row,profiles,scalar_module):
    degree=row['aligned_curve']['degree'];cache={};columns={}
    for name,points in profiles.items():
        columns[name]=[]
        for axis in range(3):
            values=tuple(p[axis]for p in points)
            if values not in cache:
                curve=dict(degree=degree,poles=values,knots_mm=row['aligned_curve']['knots'],multiplicities=row['aligned_curve']['multiplicities'],rational=False,periodic=False)
                cache[values]=[(a,b,power_to_bernstein(c,degree))for a,b,c in scalar_module.pieces(curve)]
            columns[name].append(cache[values])
    reference=columns['P'][0];leaves=[]
    for span,(first,last,_)in enumerate(reference):
        controls={name:[tuple(columns[name][axis][span][2][i]for axis in range(3))for i in range(degree+1)]for name in profiles}
        leaves.append(dict(first=first,last=last,controls=controls))
    return leaves


def split_leaf(leaf):
    left={};right={}
    for name,points in leaf['controls'].items():left[name],right[name]=split_bezier(points)
    middle=(leaf['first']+leaf['last'])/2
    return [dict(first=leaf['first'],last=middle,controls=left),dict(first=middle,last=leaf['last'],controls=right)]


def u_refine(leaves,budget):
    result=[];pending=list(reversed(leaves))
    while pending:
        leaf=pending.pop();bound=max(chord_bound(p)for p in leaf['controls'].values())
        if bound>budget:pending.extend(reversed(split_leaf(leaf)))
        else:leaf['U_error_L1']=bound;result.append(leaf)
    return result


def stations(leaves):
    result=[]
    for leaf in leaves:
        row={name:points[0]for name,points in leaf['controls'].items()}
        if result and row!={name:points[-1]for name,points in leaves[len(result)-1]['controls'].items()}:
            raise ValueError('Exact source span endpoints do not join')
        result.append(row)
    result.append({name:points[-1]for name,points in leaves[-1]['controls'].items()})
    return result


def mixture(homogeneous):return tuple(v/homogeneous[3]for v in homogeneous[:3])


def point_at_mix(station,mix):
    return tuple(sum(mix[j]*station[name][axis]for j,name in enumerate('APB'))for axis in range(3))


def v_refine(weights,rows,budget):
    initial=[tuple([weights[i]if j==i else F(0)for j in range(3)]+[weights[i]])for i in range(3)]
    result=[];pending=[initial]
    while pending:
        controls=pending.pop();mix=[mixture(p)for p in controls]
        delta=[mix[1][j]-(mix[0][j]+mix[2][j])/2 for j in range(3)]
        bound=max(norm1(point_at_mix(row,delta))for row in rows)
        if bound>budget:
            left,right=split_bezier(controls);pending.extend([right,left])
        else:result.append(dict(homogeneous=controls,mixes=mix,V_error_L1=bound))
    return result


def tessellate(row,epsilon,scalar_module,cleanup,np):
    profiles,weights,proof=profiles_and_injectivity(row);budget=epsilon/4
    leaves=u_refine(initial_leaves(row,profiles,scalar_module),budget)
    while True:
        rows=stations(leaves);segments=v_refine(weights,rows,budget);bad=[]
        for i,leaf in enumerate(leaves):
            for segment in segments:
                corners=[point_at_mix(rows[k],segment['mixes'][j])for k,j in [(i,0),(i,2),(i+1,0),(i+1,2)]]
                if quad_triangle_bound(*corners)>budget:bad.append(i);break
            for a,b in [('B','C'),('C','D'),('D','A')]:
                if quad_triangle_bound(rows[i][a],rows[i][b],rows[i+1][a],rows[i+1][b])>budget:bad.append(i);break
        if not bad:break
        bad=set(bad);leaves=u_refine([child for i,leaf in enumerate(leaves)for child in(split_leaf(leaf)if i in bad else[leaf])],budget)
    mixes=[segments[0]['mixes'][0],*[s['mixes'][2]for s in segments]]
    vertices=[];vertex_map={};row_ids=[];quantization=F(0)
    for station in rows:
        points=[point_at_mix(station,mix)for mix in mixes]+[station['C'],station['D']];ids=[]
        for point in points:
            stored=tuple(float(v)for v in np.asarray([float(x)for x in point],dtype='<f4'))
            error=norm1(tuple(F(v)-p for v,p in zip(stored,point)));quantization=max(quantization,error)
            if stored not in vertex_map:vertex_map[stored]=len(vertices);vertices.append(stored)
            ids.append(vertex_map[stored])
        row_ids.append(ids)
    if quantization>budget:raise ValueError('Float32 rounding exceeds its declared error budget')
    faces=[];groups=[];cells=[];width=len(row_ids[0])
    for i,leaf in enumerate(leaves):
        for j in range(width):
            following=(j+1)%width;a,b=row_ids[i][j],row_ids[i][following];c,d=row_ids[i+1][j],row_ids[i+1][following]
            faces.extend([(a,b,d),(a,d,c)])
            name='arc'if j<len(segments)else['bottom','inside','top'][j-len(segments)]
            groups.extend([name,name])
            if name=='arc':
                mix0,mix1=segments[j]['mixes'][0],segments[j]['mixes'][2]
                corners=[point_at_mix(rows[k],mix)for k,mix in [(i,mix0),(i,mix1),(i+1,mix0),(i+1,mix1)]]
                v_error=segments[j]['V_error_L1']
            else:
                pair={'bottom':('B','C'),'inside':('C','D'),'top':('D','A')}[name]
                corners=[rows[k][key]for k,key in[(i,pair[0]),(i,pair[1]),(i+1,pair[0]),(i+1,pair[1])]];v_error=F(0)
            t_error=quad_triangle_bound(*corners)
            total=leaf['U_error_L1']+v_error+t_error+quantization
            if total>epsilon:raise ValueError('Combined complete cell bound exceeds unchanged tolerance')
            cells.append(dict(U_interval=[str(leaf['first']),str(leaf['last'])],surface=name,V_segment=j if name=='arc'else None,U_error_L1=str(leaf['U_error_L1']),V_error_L1=str(v_error),triangle_error_L1=str(t_error),rounding_error_L1=str(quantization),total_L1=str(total)))
    faces.extend([(row_ids[0][0],row_ids[0][-1],row_ids[0][-2]),(row_ids[-1][0],row_ids[-1][-2],row_ids[-1][-1])]);groups.extend(['cap_first','cap_last'])
    if proof['X_direction']<0:faces=[(a,c,b)for a,b,c in faces]
    keep,clean=cleanup.cleanup_certificate(faces)
    if keep is not None:faces=[faces[i]for i in keep];groups=[groups[i]for i in keep]
    vertices=np.asarray(vertices,dtype='<f4');faces=np.asarray(faces,dtype='<u4')
    x=[v[0]for v in[vertices[ids[0]]for ids in row_ids]]
    if not all(proof['X_direction']*(b-a)>0 for a,b in zip(x,x[1:])):raise ValueError('Serialized X station order changed')
    triangles=vertices[faces].astype(np.float64);cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);area2=np.linalg.norm(cross,axis=1)
    if not np.all(area2>0):raise ValueError('A non-redundant zero-area facet remains')
    volume=float(np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6)
    if not volume>0:raise ValueError('Structured patch orientation or volume differs')
    certificate=dict(injectivity=proof,tolerance_mm=float(epsilon),norm='L1 (therefore also an upper bound in Euclidean distance)',four_term_budget_mm=str(budget),U_intervals=len(leaves),V_arc_intervals=len(segments),quantization_L1_bound_mm=str(quantization),maximum_complete_cell_L1_bound_mm=str(max(F(c['total_L1'])for c in cells)),all_cells_bounded=True,cells=cells,exact_redundant_facet_cleanup=clean,volume_mm3=volume,vertices=len(vertices),triangles=len(faces),face_surface_groups=groups,scope='Complete source parametric patch surfaces and planar endcaps only; independent mesh topology/intersection audit remains required')
    return vertices,faces,certificate


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--control-nets',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists():raise ValueError('Fresh output required')
    out.mkdir(parents=True);start=time.monotonic();report=dict(status='incomplete',patches=[])
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('150 second bound')));signal.alarm(150);resource.setrlimit(resource.RLIMIT_CPU,(140,141))
    try:
        import numpy as np
        def load(name,path):
            s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
        scalar=load('_bounded_scalar_pieces',Path(__file__).with_name('law_certificate.py'));cleanup=load('_bounded_exact_cleanup',Path(__file__).with_name('exact_triangle_cleanup.py'))
        raw=args.control_nets.read_bytes();data=json.loads(raw);report['source_control_nets_sha256']=hashlib.sha256(raw).hexdigest()
        for i,row in enumerate(data['patches']):
            v,f,certificate=tessellate(row,F(.06),scalar,cleanup,np)
            path=out/f'patch-{i}.stl';tri=v[f].astype('<f4');normals=np.cross(tri[:,1].astype(np.float64)-tri[:,0],tri[:,2].astype(np.float64)-tri[:,0]);normals/=np.linalg.norm(normals,axis=1)[:,None]
            dtype=np.dtype([('normal','<f4',(3,)),('xyz','<f4',(3,3)),('attribute','<u2')]);records=np.zeros(len(f),dtype=dtype);records['normal']=normals;records['xyz']=tri
            path.write_bytes(b'Bounded source NURBS patch study'.ljust(80,b' ')+struct.pack('<I',len(f))+records.tobytes())
            certificate['STL_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();report['patches'].append(certificate)
            (out/'progress.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        report['status']='two_complete_parametric_patch_mesh_error_bounds_passed'
    except Exception as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
    finally:signal.alarm(0);report['elapsed_seconds']=time.monotonic()-start;(out/'assessment.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=report['status'],elapsed_seconds=report['elapsed_seconds'])))
    return 0 if report['status']=='two_complete_parametric_patch_mesh_error_bounds_passed'else 1


if __name__=='__main__':raise SystemExit(main())
