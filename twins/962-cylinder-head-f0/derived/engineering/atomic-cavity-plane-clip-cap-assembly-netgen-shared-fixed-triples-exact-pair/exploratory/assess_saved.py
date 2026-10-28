"""Bounded saved-row counts and diagnostic FLOAT ball margins, never certificates."""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-fixed-triples-001/readback-report.json': 'd65f86d5d1cabd3e2013a127c1cd9713a232cb1d1bd7817d459f84949d1e1c14',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-full-stars-001/readback-report.json': '5946ffbd9f2f127306673d967b583b11d8906793e2079971bc0430d65ae65f88',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-assessment-001/review.json': '44a1e632adfc35be9f352fc46dd9d305597b04a2d502bd8dd49e97d4a2ee2a3a',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-assessment-001/minimum-ties.json': 'fa39306ff18637869f0d1b2b9fa7db4c65009c8cbe2f30b61f3a5ca13030587f',
    'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-shared-fixed-triples-ball-screen-001/report.json': '365abee9064744777a25804434d35109b7e27a225c914ccf22d87da1e86abc1d',
}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rf = lambda x: Fraction(int(x['numerator']), int(x['denominator']))
dot = lambda a,b: sum(x*y for x,y in zip(a,b))


def floating_bounds(S, T, centre, normal):
    B = 899*T-S*S
    delta = B*B-4*S*S*T
    assert S > 0 and T > 0 and delta >= 0
    plus = (B+math.sqrt(delta))/(2*S)
    minus = T/plus  # Avoid cancellation in the small positive root.
    tangent_squared = 841*T/S-S
    assert minus > 0 and tangent_squared >= 0
    hminus,hplus = math.sqrt(2*minus/3),math.sqrt(2*plus/3)
    middle,halfwidth = (hminus+hplus)/2,(hplus-hminus)/2
    return dict(root_plus=plus,root_minus=minus,
        upper_root_centroid_centre_mm=centre,upper_root_centroid_radius_mm=math.sqrt(2*plus/3),
        shifted_cylinder_centre_mm=[c+middle*n for c,n in zip(centre,normal)],
        shifted_cylinder_radius_mm=math.sqrt(2*tangent_squared/3+halfwidth*halfwidth),
        hminus_mm=hminus,hplus_mm=hplus,tangent_squared_ideal_mm2=tangent_squared)


def main():
    assert not (HERE/'report.json').exists()
    # Tiny exact regular case plus exact-threshold FLOAT enclosure self-check.
    assert Fraction(9)/(Fraction(2)+1)/(1+Fraction(2)) == 1
    threshold=floating_bounds(29.,1.,[0.,0.,0.],[0.,0.,1.])
    assert threshold['root_plus']==threshold['root_minus']==1.
    assert threshold['shifted_cylinder_radius_mm']==0.
    assert threshold['shifted_cylinder_centre_mm']==[0.,0.,math.sqrt(2./3.)]
    for path,digest in PINS.items():assert sha(ROOT/path)==digest
    fixed,first,previous,ties,exact=[json.loads((ROOT/path).read_text()) for path in PINS]
    census=first['complete_seed_star_census'];seed=set(census['movable_node_tags'])
    nodes={r['node_tag']:r for r in census['unique_incident_nodes']}
    assert len(seed)==156 and len(census['complete_incident_tetrahedra'])==5355
    all_class3=defaultdict(list)
    for row in census['complete_incident_tetrahedra']:
        if sum(t<=871731 for t in row['node_tags'])!=3:continue
        apex=next(t for t in row['node_tags'] if t>871731)
        assert apex in seed and row['movable_node_tags']==[apex]
        assert all(nodes[t]['source_boundary_tag']==(t<=871731) for t in row['node_tags'])
        all_class3[apex].append(row)
    all_counts=[dict(interior_apex_node_tag=a,total_cells=len(rows),
        initially_poor=sum(r['initially_positive_poor'] for r in rows),
        initially_good=sum(not r['initially_positive_poor'] for r in rows),
        within_apex_pairs=len(rows)*(len(rows)-1)//2) for a,rows in sorted(all_class3.items())]
    groups=defaultdict(list)
    for row in fixed['fixed_boundary_triple_ceiling_analysis']['rows']:groups[row['interior_apex_node_tag']].append(row)
    assert sum(len(r) for r in groups.values())==195
    assert dict(Counter(map(len,groups.values())))=={1:96,2:46,3:1,4:1}
    shared={a:sorted(r,key=lambda r:r['tetrahedron_tag']) for a,r in groups.items() if len(r)>1}
    assert {a:[r['tetrahedron_tag'] for r in v] for a,v in shared.items()}=={
        g['interior_apex_node_tag']:[r['tetrahedron_tag'] for r in g['fixed_triples']]
        for g in previous['shared_apex_groups_only']}
    faces={}
    for apex,rows in sorted(shared.items()):
        for row in rows:
            points=[[Fraction.from_float(float(x)) for x in p] for p in row['fixed_triple_coordinates_mm']]
            assert [[float(x).hex() for x in p] for p in points]==row['fixed_triple_binary64_hex']
            e,f=[[p[k]-points[0][k] for k in range(3)] for p in points[1:]]
            cross=[e[1]*f[2]-e[2]*f[1],e[2]*f[0]-e[0]*f[2],e[0]*f[1]-e[1]*f[0]]
            C=dot(cross,cross);edge_sum=sum(dot([points[i][k]-points[j][k] for k in range(3)],
                [points[i][k]-points[j][k] for k in range(3)]) for i,j in [(0,1),(1,2),(2,0)])
            proof=row['exact_fixed_face_certificate']
            assert C==rf(proof['cross_squared_mm4']) and edge_sum==rf(proof['sum_squared_edge_lengths_mm2'])
            S,T=Fraction(2,3)*edge_sum,Fraction(4,3)*C
            assert 4*T/(S*S)==rf(row['tight_isolated_apex_ceiling']['exact_triangle_SICN_squared'])
            centre=[sum(p[k] for p in points)/3 for k in range(3)]
            apex_point=[Fraction.from_float(float(x)) for x in nodes[apex]['coordinates_mm']]
            side=dot(cross,[x-y for x,y in zip(apex_point,centre)]);assert side!=0
            sign=1 if side>0 else -1
            normal=[sign*float(x)/math.sqrt(float(C)) for x in cross]
            bound=floating_bounds(float(S),float(T),[float(x) for x in centre],normal)
            faces[row['tetrahedron_tag']]=dict(tetrahedron_tag=row['tetrahedron_tag'],
                interior_apex_node_tag=apex,normal_oriented_using_exact_original_apex_side=sign,
                normal_length_squared_float=dot(normal,normal),**bound)
    pairs=[]
    for apex,rows in sorted(shared.items()):
        for a,b in combinations(rows,2):
            tags=[a['tetrahedron_tag'],b['tetrahedron_tag']];A,B=[faces[t] for t in tags]
            record=dict(interior_apex_node_tag=apex,tetrahedron_tags=tags)
            for method in ['upper_root_centroid','shifted_cylinder']:
                distance=math.sqrt(sum((x-y)**2 for x,y in zip(A[method+'_centre_mm'],B[method+'_centre_mm'])))
                radii=A[method+'_radius_mm']+B[method+'_radius_mm']
                record[method]=dict(centre_distance_mm=distance,sum_radii_mm=radii,
                    separation_margin_mm=distance-radii,positive_margin_is_not_a_certificate=True)
            pairs.append(record)
    assert len(faces)==99 and len(pairs)==55 and exact['certified_disjoint_pair_count']==0
    summary={method:dict(apparent_positive_margins=sum(p[method]['separation_margin_mm']>0 for p in pairs),
        minimum_margin_mm=min(p[method]['separation_margin_mm'] for p in pairs),
        maximum_margin_mm=max(p[method]['separation_margin_mm'] for p in pairs),
        largest_margin_pair=max(pairs,key=lambda p:p[method]['separation_margin_mm'])['tetrahedron_tags'])
        for method in ['upper_root_centroid','shifted_cylinder']}
    report=dict(schema='962-saved-fixed-triple-refinement-diagnostic/v1',source_sha256=sha(Path(__file__)),
        input_hashes=PINS,scope='Saved-row arithmetic only. Counts do not reprove global incidence; FLOAT margins cannot certify either feasibility or infeasibility.',
        all_class3_from_original5355=dict(cells=sum(g['total_cells'] for g in all_counts),apices=len(all_counts),
            initially_poor=sum(g['initially_poor'] for g in all_counts),initially_good=sum(g['initially_good'] for g in all_counts),
            within_apex_pairs=sum(g['within_apex_pairs'] for g in all_counts),
            apex_cell_multiplicity_histogram=dict(sorted(Counter(g['total_cells'] for g in all_counts).items())),
            per_apex_counts=all_counts,complete_global_incidence_remains_prior_reader_attestation=True),
        formulas=dict(S='2/3*sum_three_squared_edges',T='4/3*cross_squared',
            roots='B=899T-S²; delta=B²-4S²T; w+=(B+sqrt(delta))/(2S); w-=T/w+',
            centroid='centre=exact_face_centroid; radius=sqrt(2w+/3)',
            shifted='R²=841T/S-S; h±=sqrt(2w±/3); centre=centroid+(h−+h+)/2*normal; radius=sqrt(2R²/3+((h+−h−)/2)²)',
            margin='FLOAT norm(centre1-centre2)-(radius1+radius2); positive is only a candidate for exact certification'),
        tiny_regular_and_threshold_assertions_passed=True,summary=summary,
        face_FLOAT_bounds=[faces[t] for t in sorted(faces)],all55_FLOAT_pair_margins=pairs,
        exact_interval_refinement_implemented=False,optimizer_or_native_calls=0,
        engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
    for path,digest in PINS.items():assert sha(ROOT/path)==digest
    report['bound_inputs_unchanged']=True
    with (HERE/'report.json').open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(all_class3={k:v for k,v in report['all_class3_from_original5355'].items()
        if k!='per_apex_counts'},summary=summary),sort_keys=True))


if __name__=='__main__':main()
