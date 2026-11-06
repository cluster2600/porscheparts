"""Independently prove exact original-triangle tilings and source-cut interfaces."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import time

import numpy as np


def sha(path):
    return hashlib.file_digest(Path(path).open('rb'), 'sha256').hexdigest()


def fpoint(point):
    return tuple(F.from_float(float(x)) for x in point)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def subtract(a, b):
    return tuple(x-y for x,y in zip(a,b))


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def det(a, b, c, axes):
    i,j = axes
    return (b[i]-a[i])*(c[j]-a[j])-(b[j]-a[j])*(c[i]-a[i])


def boundary(triangles):
    edges = Counter((a,b) for tri in triangles for a,b in zip(tri,tri[1:]+tri[:1]))
    result = {}
    for a,b in set(tuple(sorted(e)) for e in edges):
        difference = edges[(a,b)]-edges[(b,a)]
        if difference:
            assert abs(difference)==1, 'Duplicate boundary use'
            result[(a,b) if difference>0 else (b,a)] = 1
        assert edges[(a,b)]<=1 and edges[(b,a)]<=1, 'Repeated triangle edge'
    return result


def inspect_parent(original, exact, rounded, triangles, sides, original_nodes, cut_nodes, plane):
    """Prove each clipped convex polygon through its boundary chain and exact area."""
    a,b,c = original
    normal = cross(subtract(b,a),subtract(c,a));drop = max(range(3),key=lambda i:abs(normal[i]))
    assert normal[drop]!=0
    axes = [i for i in range(3) if i!=drop];area = det(a,b,c,axes)
    signs = [dot(p,plane[:3])+plane[3] for p in original]
    assert all(signs) and min(signs)<0<max(signs)
    allowed = set(original_nodes) | set(cut_nodes.values())
    assert len(triangles)==3 and set(sides)=={-1,1}
    sums = {};worst_rounding = F(0);minimum_stored_edge_squared = None
    for side in (-1,1):
        polygon = []
        for i in range(3):
            j = (i+1)%3
            if signs[i]*side>0:
                polygon.append(original_nodes[i])
            if signs[i]*signs[j]<0:
                polygon.append(cut_nodes[tuple(sorted((i,j)))])
        assert len(polygon) in (3,4)
        wanted = {(u,v):1 for u,v in zip(polygon,polygon[1:]+polygon[:1])}
        chosen = [tuple(map(int,t)) for t,s in zip(triangles,sides) if s==side]
        assert len(chosen)==len(polygon)-2
        assert boundary(chosen)==wanted, 'Fragment boundary differs from independent source half-polygon'
        child_area = F(0)
        for tri in chosen:
            assert len(set(tri))==3 and set(tri)<=allowed
            points = [exact[i] for i in tri]
            local = det(*points,axes);assert local*area>0, 'Degenerate or reversed fragment'
            child_area += local
            for i,p in zip(tri,points):
                assert dot(subtract(p,a),normal)==0
                barycentric = (det(p,b,c,axes)/area,det(a,p,c,axes)/area,det(a,b,p,axes)/area)
                assert sum(barycentric)==1 and min(barycentric)>=0
                assert (dot(p,plane[:3])+plane[3])*side>=0
                error = dot(subtract(rounded[i],p),subtract(rounded[i],p))
                worst_rounding = max(worst_rounding,error)
                assert error<=F.from_float(1e-8)**2
            stored_normal = cross(subtract(rounded[tri[1]],rounded[tri[0]]),subtract(rounded[tri[2]],rounded[tri[0]]))
            assert dot(stored_normal,normal)>0, 'Stored rounded triangle collapsed or reversed'
            for u,v in zip(tri,tri[1:]+tri[:1]):
                delta = subtract(rounded[u],rounded[v]);squared = dot(delta,delta);assert squared>0
                minimum_stored_edge_squared = squared if minimum_stored_edge_squared is None else min(minimum_stored_edge_squared,squared)
        expected_area = sum(det(exact[polygon[0]],exact[polygon[i]],exact[polygon[i+1]],axes) for i in range(1,len(polygon)-1))
        assert child_area==expected_area
        sums[side] = child_area
    assert sums[-1]+sums[1]==area, 'Both halves do not tile the original source triangle'
    return worst_rounding,minimum_stored_edge_squared


def controls():
    original = [(F(0),F(0),F(-1)),(F(2),F(0),F(1)),(F(0),F(2),F(1))]
    exact = original+[(F(1),F(0),F(0)),(F(0),F(1),F(0))]
    # Literal triangles are independent of the producer's clipping/fan choice.
    triangles = [(0,3,4),(3,1,2),(3,2,4)];sides = [-1,1,1]
    plane = tuple(map(F,(0,0,1,0)));cuts = {(0,1):3,(0,2):4}
    inspect_parent(original,exact,exact,triangles,sides,[0,1,2],cuts,plane)
    try:
        inspect_parent(original,exact,exact,[triangles[0],triangles[1],triangles[1]],sides,[0,1,2],cuts,plane)
    except AssertionError:
        pass
    else:
        raise AssertionError('Duplicate tiling triangle accepted')
    forged = list(exact);forged[3] = (F(1),F(0),F(1,100))
    try:
        inspect_parent(original,exact,forged,triangles,sides,[0,1,2],cuts,plane)
    except AssertionError:
        pass
    else:
        raise AssertionError('Moved stored cut point accepted')
    return dict(literal_both_half_tiling=True,duplicate_same_count_fragment_refused=True,
                moved_stored_cut_endpoint_refused=True)


def inspect(vertices,faces,planes,region_rows,region_data,data):
    assert data['points'].ndim==2 and data['points'].shape[1]==3
    assert data['triangles'].ndim==2 and data['triangles'].shape[1]==3
    assert all(len(data[key])==len(data['points']) for key in ('source_vertex_ids','source_edge_codes','node_plane_indices'))
    exact = [];source_lookup = {};cut_lookup = {};worst = F(0)
    for i,(source,code,plane) in enumerate(zip(data['source_vertex_ids'],data['source_edge_codes'],data['node_plane_indices'])):
        source,code,plane = int(source),int(code),int(plane)
        if source>=0:
            assert code==plane==-1 and source not in source_lookup
            source_lookup[source] = i;p = fpoint(vertices[source])
        else:
            assert source==-1 and code>=0 and plane>=0 and (plane,code) not in cut_lookup
            cut_lookup[(plane,code)] = i;a,b = divmod(code,len(vertices))
            x,y = fpoint(vertices[a]),fpoint(vertices[b]);n = planes[plane]
            da,db = dot(x,n[:3])+n[3],dot(y,n[:3])+n[3];assert da*db<0
            p = tuple((da*y[j]-db*x[j])/(da-db) for j in range(3))
            assert dot(p,n[:3])+n[3]==0
        assert np.array_equal(data['points'][i],np.array(list(map(float,p))))
        exact.append(p)
    rounded = [fpoint(p) for p in data['points']]
    assert len(exact)==len(data['points']) and len(set(map(tuple,data['points'])))==len(exact)
    assert set(map(int,data['triangles'].ravel()))==set(range(len(exact)))
    wanted_parents = {};wanted_cuts = set();expected_sections = {}
    for row in region_rows:
        region = row['region'];plane = row['plane'];r = region_data[region]
        for parent in r['transition_source_face_ids']:
            assert int(parent) not in wanted_parents;wanted_parents[int(parent)] = (region,plane)
        codes = list(map(int,r['section_edge_codes']))
        wanted_cuts.update((plane,code) for code in codes)
        expected_sections[region] = {tuple(sorted((cut_lookup[(plane,a)],cut_lookup[(plane,b)])))
                                     for a,b in zip(codes,codes[1:]+codes[:1])}
    assert set(cut_lookup)==wanted_cuts
    parents = data['parent_source_face_ids'];triangles = data['triangles'];sides = data['triangle_halfspaces']
    assert len(parents)==len(triangles)==len(sides)==len(data['triangle_regions'])
    assert Counter(map(int,parents))==Counter({p:3 for p in wanted_parents})
    groups = defaultdict(list)
    for index,parent in enumerate(parents):groups[int(parent)].append(index)
    section_uses = defaultdict(lambda: {-1:Counter(),1:Counter()})
    minimum = None
    for parent,(region,plane_index) in wanted_parents.items():
        selected = groups[parent];assert np.all(data['triangle_regions'][selected]==region)
        source = list(map(int,faces[parent]));original = [fpoint(vertices[i]) for i in source];plane = planes[plane_index]
        original_nodes = [source_lookup[i] for i in source];cuts = {}
        for i in range(3):
            j = (i+1)%3;a,b = sorted((source[i],source[j]))
            if (dot(original[i],plane[:3])+plane[3])*(dot(original[j],plane[:3])+plane[3])<0:
                cuts[tuple(sorted((i,j)))] = cut_lookup[(plane_index,a*len(vertices)+b)]
        error,smallest = inspect_parent(original,exact,rounded,triangles[selected].tolist(),sides[selected].tolist(),original_nodes,cuts,plane)
        worst = max(worst,error);minimum = smallest if minimum is None else min(minimum,smallest)
        for index in selected:
            tri = list(map(int,triangles[index]));side = int(sides[index])
            for a,b in zip(tri,tri[1:]+tri[:1]):
                if data['source_vertex_ids'][a]==data['source_vertex_ids'][b]==-1:
                    section_uses[region][side][(a,b)] += 1
    for region,wanted in expected_sections.items():
        negative,positive = section_uses[region][-1],section_uses[region][1]
        assert set(tuple(sorted(e)) for e in negative)==wanted
        assert all(count==1 for count in negative.values()) and positive==Counter({(b,a):n for (a,b),n in negative.items()})
    return dict(original_transition_triangles=len(groups),derived_triangles=len(triangles),
                each_original_triangle_exactly_tiled_by_two_opposite_halves=True,
                all_fragment_vertices_in_original_triangle_and_correct_halfspace=True,
                original_winding_and_exact_area_preserved=True,all_cut_interfaces_match_original_section_graph=True,
                opposite_halves_share_identical_nodes_and_reversed_section_edges=True,
                stored_rounded_triangles_nonzero_and_correctly_oriented=True,
                maximum_once_rounded_endpoint_error_nominal_mm=float(worst)**.5,
                minimum_stored_fragment_edge_nominal_mm=float(minimum)**.5,
                caps_or_hidden_surfaces_added=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('job','built','output'):parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args();job = json.loads(args.job.read_text());started = time.monotonic()
    assert job['schema']=='935-source-transition-cuts-1'
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    args.output.mkdir(mode=0o700,exist_ok=False);control = controls()
    report = json.loads((args.built/'report.json').read_text());file = args.built/'private-transition-fragments.npz'
    assert sha(file)==report['private_fragments_sha256'] and report['job_sha256']==sha(args.job)
    with np.load(file,allow_pickle=False) as p:data = {key:p[key] for key in p.files}
    with np.load(job['arrays'],allow_pickle=False) as p:vertices,faces = p['vertices'],p['triangles']
    planes = [fpoint(row['keep_negative_halfspace_coefficients']) for row in json.loads(Path(job['planes']).read_text())]
    admitted = json.loads(Path(job['admitted_regions']).read_text());regions = {}
    for row in admitted['regions']:
        path = Path(job['admitted_regions']).parent/('private-region-'+str(row['region'])+'.npz')
        assert sha(path)==row['private_region_sha256']
        with np.load(path,allow_pickle=False) as p:regions[row['region']] = {key:p[key] for key in p.files}
    result = inspect(vertices,faces,planes,admitted['regions'],regions,data)
    for item in job['inputs']:assert sha(item['path'])==item['sha256']
    assert sha(file)==report['private_fragments_sha256']
    result.update(source_sha256=sha(__file__),job_sha256=sha(args.job),controls=control,
                  fragments_sha256=sha(file),full_bare_head_created=False,physical_acceptance=False,
                  manufacturing_authorized=False,seconds=time.monotonic()-started)
    (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print('EXACT_SOURCE_TRANSITION_TILING_AND_INTERFACE_CHECK_OK',flush=True)


if __name__=='__main__':main()
