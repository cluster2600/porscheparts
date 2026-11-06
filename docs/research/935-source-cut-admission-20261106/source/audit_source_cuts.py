"""Audit the existing three stock planes directly on admitted acquired facets.

The size/roundness/extension classifier is the prior construction hypothesis,
not anatomical evidence. No triangle is clipped, capped, moved or discarded.
Open section graphs and multi-loop outside components cannot supply a proposed
single-protrusion region. Exact-plane vertex contacts are refused explicitly.
"""
import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1024**2),b''):h.update(data)
    return h.hexdigest()


def signs(vertices, plane):
    """Outward interval enclosure; Fraction resolves every uncertain scalar."""
    product = vertices*plane[:3]
    low = np.nextafter(product,-np.inf); high = np.nextafter(product,np.inf)
    for array, direction in ((low,-np.inf),(high,np.inf)):
        array[:,0] = np.nextafter(array[:,0]+array[:,1],direction)
        array[:,0] = np.nextafter(array[:,0]+array[:,2],direction)
        array[:,0] = np.nextafter(array[:,0]+plane[3],direction)
    result = np.where(low[:,0]>0,1,np.where(high[:,0]<0,-1,0)).astype(np.int8)
    uncertain = np.flatnonzero(result==0); coefficients = list(map(Fraction.from_float,map(float,plane)))
    for index in uncertain:
        value = sum((Fraction.from_float(float(vertices[index,j]))*coefficients[j] for j in range(3)),coefficients[3])
        result[index] = (value>0)-(value<0)
    return result,len(uncertain)


def section(vertices, faces, ids, plane):
    started = time.monotonic(); direction,fallbacks = signs(vertices,plane)
    vertex_ids = np.unique(faces[ids]); zeros = vertex_ids[direction[vertex_ids]==0]
    if len(zeros):
        return {'admitted':False,'reason':'exact_source_vertex_on_plane','on_plane_vertices':len(zeros)},{}
    active = ids[(direction[faces[ids]]>0).any(axis=1)]
    tri = faces[active]; edges = np.stack((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]),axis=1).reshape(-1,2)
    face_row = np.repeat(np.arange(len(active),dtype=np.int64),3)
    positive = (direction[edges]>0).any(axis=1); e = edges[positive]; row = face_row[positive]
    count_vertices = len(vertices); code = e.min(axis=1)*count_vertices+e.max(axis=1)
    order = np.argsort(code,kind='stable'); code,row = code[order],row[order]
    starts = np.r_[0,np.flatnonzero(code[1:]!=code[:-1])+1] if len(code) else np.empty(0,dtype=np.int64)
    uses = np.diff(np.r_[starts,len(code)]); assert np.all((uses==1)|(uses==2))
    paired = starts[uses==2]; first,second = row[paired],row[paired+1]
    graph = coo_matrix((np.ones(2*len(paired),dtype=np.int8),(np.r_[first,second],np.r_[second,first])),shape=(len(active),len(active))).tocsr()
    count,labels = connected_components(graph,directed=False)
    crossing = (direction[tri]>0).any(axis=1)&(direction[tri]<0).any(axis=1)
    face_component = np.full(len(faces),-1,dtype=np.int32);face_component[active] = labels
    source_faces = active[crossing]; crossing_tri = faces[source_faces]
    edge_pairs = np.stack((crossing_tri[:,[0,1]],crossing_tri[:,[1,2]],crossing_tri[:,[2,0]]),axis=1)
    cut = direction[edge_pairs[:,:,0]]!=direction[edge_pairs[:,:,1]]
    assert np.all(cut.sum(axis=1)==2)
    cut_edges = np.sort(edge_pairs[cut],axis=1)
    segments = (cut_edges[:,0]*count_vertices+cut_edges[:,1]).reshape(-1,2)
    owners = face_component[source_faces]; by_component = defaultdict(list)
    for index,owner in enumerate(owners):by_component[int(owner)].append(index)
    cut_codes = np.unique(segments); points = {}; exact_plane = list(map(Fraction.from_float,map(float,plane)))
    for key in cut_codes:
        a,b = divmod(int(key),count_vertices)
        va,vb = [[Fraction.from_float(float(x)) for x in vertices[i]] for i in (a,b)]
        da = sum((va[j]*exact_plane[j] for j in range(3)),exact_plane[3])
        db = sum((vb[j]*exact_plane[j] for j in range(3)),exact_plane[3]); ratio = da/(da-db)
        assert 0<ratio<1
        point = [va[j]+ratio*(vb[j]-va[j]) for j in range(3)]
        assert sum((point[j]*exact_plane[j] for j in range(3)),exact_plane[3])==0
        points[int(key)] = np.array([float(x) for x in point])
    rows = []; private = {}; normal = plane[:3]; norm = np.linalg.norm(normal); drop = int(np.argmax(np.abs(normal)))
    axes = [j for j in range(3) if j!=drop]
    for component in range(count):
        segment_ids = by_component.get(component,[]); adjacency = defaultdict(list)
        for sid in segment_ids:
            a,b = map(int,segments[sid]);adjacency[a].append(b);adjacency[b].append(a)
        regular = bool(adjacency) and all(len(neighbours)==2 and len(set(neighbours))==2 for neighbours in adjacency.values())
        loops = []; visited = set()
        if regular:
            for seed in sorted(adjacency):
                if seed in visited:continue
                loop = []; previous = None;current = seed
                while current not in visited:
                    visited.add(current);loop.append(current)
                    neighbours = sorted(adjacency[current]);nxt = neighbours[0] if neighbours[0]!=previous else neighbours[1]
                    previous,current = current,nxt
                assert current==seed
                loops.append(loop)
        members = active[labels==component]; extent = float(np.max(vertices[np.unique(faces[members])]@normal+plane[3])/norm)
        area = perimeter = circularity = None; reason = 'no_cut_section' if not adjacency else 'non_closed_or_branched_source_section'
        selected = False
        if regular:
            reason = 'outside_component_has_multiple_section_loops'
            if len(loops)==1:
                p = np.array([points[key] for key in loops[0]]);q = p[:,axes]-p[0,axes]
                area = float(abs(np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1)))*.5*norm/abs(normal[drop]))
                lengths = np.linalg.norm(np.roll(p,-1,axis=0)-p,axis=1);perimeter = float(lengths.sum())
                circularity = 4*np.pi*area/perimeter**2 if perimeter else 0.
                margins = [abs(area-10),abs(area-150),abs(circularity-.7),abs(extent-5)]
                safe = min(margins)>1e-8 and bool(np.all(lengths>0))
                selected = bool(safe and 10<=area<=150 and circularity>=.7 and extent>=5)
                reason = 'provisional_geometric_region' if selected else 'fixed_classifier_not_passed'
                if not safe:reason = 'arithmetic_or_classifier_boundary_ambiguous'
        item = dict(component=component,source_faces=len(members),section_segments=len(segment_ids),
                    section_graph_closed=regular,section_loops=len(loops),area_nominal_mm2=area,
                    perimeter_nominal_mm=perimeter,circularity=circularity,outward_extension_nominal_mm=extent,
                    selected_provisional_region=selected,reason=reason,anatomical_acceptance=False)
        rows.append(item)
        private['component_'+str(component)+'_source_faces'] = members
        if regular:
            for loop_id,loop in enumerate(loops):private['component_'+str(component)+'_loop_'+str(loop_id)+'_edge_codes'] = np.array(loop,dtype=np.int64)
    keys = np.array(sorted(points),dtype=np.int64)
    private.update(active_source_face_ids=active,active_component_labels=labels,section_source_face_ids=source_faces,
                   section_edge_codes=segments,section_component_labels=owners,cut_edge_codes=keys,
                   rounded_source_edge_intersections=np.array([points[int(key)] for key in keys]).reshape(-1,3))
    report = dict(admitted=True,active_source_faces=len(active),positive_surface_components=count,
                  section_source_faces=len(source_faces),section_nodes=len(points),interval_fraction_fallbacks=fallbacks,
                  selected_regions=sum(x['selected_provisional_region'] for x in rows),regions=rows,seconds=time.monotonic()-started)
    return report,private


def cylinder(radius=3.,bottom=-1.,top=8.,sides=32,open_strip=False):
    angle = (np.arange(sides)+.5)*2*np.pi/sides
    ring = np.c_[radius*np.cos(angle),radius*np.sin(angle)]
    vertices = np.r_[np.c_[ring,np.full(sides,bottom)],np.c_[ring,np.full(sides,top)]]
    faces = []
    for i in range(sides-int(open_strip)):
        j = (i+1)%sides;faces.extend([[i,j,j+sides],[i,j+sides,i+sides]])
    return vertices,np.array(faces,dtype=np.int64)


def controls():
    plane = np.array([0.,0.,1.,0.]);v,f = cylinder()
    r,_ = section(v,f,np.arange(len(f)),plane);assert r['selected_regions']==1
    expected_area = .5*32*3**2*np.sin(2*np.pi/32)
    assert abs(r['regions'][0]['area_nominal_mm2']-expected_area)<1e-10
    v,f = cylinder(open_strip=True);r,_ = section(v,f,np.arange(len(f)),plane)
    assert r['selected_regions']==0 and not r['regions'][0]['section_graph_closed']
    u = (np.arange(32)+.5)*2*np.pi/32;w = np.arange(24)*2*np.pi/24
    a,b = np.meshgrid(u,w,indexing='ij');v = np.c_[((8+3*np.cos(b))*np.cos(a)).ravel(),(3*np.sin(b)).ravel(),((8+3*np.cos(b))*np.sin(a)).ravel()]
    f = []
    for i in range(32):
        for j in range(24):
            p=i*24+j;q=((i+1)%32)*24+j;s=i*24+(j+1)%24;t=((i+1)%32)*24+(j+1)%24
            f.extend([[p,q,t],[p,t,s]])
    f=np.array(f);r,_=section(v,f,np.arange(len(f)),plane)
    assert r['positive_surface_components']==1 and r['regions'][0]['section_loops']==2 and r['selected_regions']==0
    v,f=cylinder();v[0,2]=0;r,_=section(v,f,np.arange(len(f)),plane)
    assert not r['admitted'] and r['reason']=='exact_source_vertex_on_plane'
    values,_=signs(np.array([[0.,0.,2.**-100],[0.,0.,-2.**-100],[0.,0.,0.]]),plane)
    assert values.tolist()==[1,-1,0]
    return dict(polygonal_cylinder_analytic_area=True,open_source_section_refused=True,
                two_loop_connected_torus_not_a_single_protrusion=True,exact_vertex_contact_refused=True,
                tiny_signed_offsets_distinguished=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--controls-only',action='store_true')
    args=parser.parse_args();spec=json.loads(args.job.read_text());args.output.mkdir(mode=0o700,exist_ok=False)
    assert spec['schema']=='935-source-cut-admission-1'
    for item in spec['inputs']:assert sha(item['path'])==item['sha256']
    checks=controls();(args.output/'controls.json').write_text(json.dumps(checks,indent=2)+'\n')
    rows=[]
    if not args.controls_only:
        with np.load(spec['arrays'],allow_pickle=False) as a:vertices,faces=a['vertices'],a['triangles']
        with np.load(spec['admission'],allow_pickle=False) as a:ids=a['admitted_source_face_ids']
        assert vertices.shape==(1281608,3) and faces.shape==(2466040,3) and len(ids)==2465836
        planes=json.loads(Path(spec['planes']).read_text());assert len(planes)==3
        for index,item in enumerate(planes):
            report,private=section(vertices,faces,ids,np.array(item['keep_negative_halfspace_coefficients']))
            np.savez_compressed(args.output/('private-plane-'+str(index)+'.npz'),**private)
            rows.append(dict(plane=index,**report));print(json.dumps({k:v for k,v in rows[-1].items() if k!='regions'}),flush=True)
    for item in spec['inputs']:assert sha(item['path'])==item['sha256']
    report=dict(source_sha256=sha(__file__),job_sha256=sha(args.job),controls=checks,planes=rows,
                original_data_unchanged=True,source_geometry_clipped_or_capped=False,physical_acceptance=False,
                manufacturing_authorized=False,independent_source_graph_and_partition_check_required=True)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
