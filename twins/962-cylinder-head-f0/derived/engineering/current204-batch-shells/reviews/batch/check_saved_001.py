"""Independent stdlib saved-association check; no prepared module or geometry predicate runs."""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
E = 'work/962-engineering/'
ACTUAL = E+'head-star-current204-batch-shells-execution-prep-001/actual-contract.json'
CHILD = E+'head-star-current204-batch-shells-child-peer-001/review.json'
OUT = E+'head-star-current204-batch-shells-001/'
RUN = E+'head-star-current204-batch-shells-root-execution-001/'
CENSUS = E+'head-star-current204-full-stars-001/readback-report.json'
EXPECTED = {
 ACTUAL:'daf7c31a9cb24bdad32bf6ddf281d82dbd1a805b0d5a2a5bac159a32c6cb9d06',
 CHILD:'017e98176a7b4eb3eabcad2e3d20544a714a5be646276ff6fbd4b0d6a6f63e39',
 OUT+'report.json':'4f9fc0354918a907083006484d534c34c3b2621dfcc83b00cc4a4b731f009e86',
 OUT+'receipt.json':'78e215c5c85f01ca614e44e4e443fd4181086f63e2edc5d5aee81fbef77dbedb',
 RUN+'closed-result.json':'67d9b2763fcd5ac887eddca79010d8a21dc6365b19f56224512acbaf7a3150e2',
 RUN+'launch.json':'276a2cfaf81f202aa62e4d755b1a704b864a18f530d8628bd2f022007a348ac5',
 RUN+'stdout.log':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 RUN+'stderr.log':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
}
FACES = ((0,2,1),(0,1,3),(1,2,3),(2,0,3))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(name):
    return json.loads((ROOT/name).read_text())

def need(value, label):
    if not value:
        raise AssertionError(label)

def ratio(row):
    return Fraction(int(row['numerator']), int(row['denominator']))

def words(values):
    return struct.pack('<3d', *values)

def cycle(row):
    row = tuple(row)
    return min(row[i:]+row[:i] for i in range(3))

def connected(graph):
    seen = set()
    pending = [next(iter(graph))]
    while pending:
        point = pending.pop()
        if point not in seen:
            seen.add(point)
            pending.extend(graph[point]-seen)
    return seen == set(graph)

def main():
    actual = load(ACTUAL)
    pins = dict(actual['input_sha256'])
    need(len(pins)==33, '33 inputs')
    pins.update(EXPECTED)
    pins[str(Path(__file__).relative_to(ROOT))] = digest(Path(__file__))
    before = {}
    for name, expected in pins.items():
        path = ROOT/name
        need(not path.is_symlink() and path.is_file(), 'regular explicit input: '+name)
        before[name] = digest(path)
        need(before[name]==expected, 'input digest: '+name)
    report, receipt, closed, launch, census = [load(p) for p in
        (OUT+'report.json',OUT+'receipt.json',RUN+'closed-result.json',RUN+'launch.json',CENSUS)]
    need(set(p.name for p in (ROOT/OUT).iterdir())=={'report.json','receipt.json'}, 'two-file closure')
    need(report['input_sha256']==receipt['input_sha256']==actual['input_sha256'], 'full 33 maps')
    need(receipt['contract_sha256']==EXPECTED[ACTUAL] and receipt['source_sha256']==actual['source_sha256'], 'receipt source/child')
    need(receipt['returncode']==closed['returncode']==0 and receipt['all_bound_inputs_unchanged'] is True, 'RC and input stability')
    need(closed['actual_sha256']==EXPECTED[ACTUAL] and closed['child_peer_sha256']==EXPECTED[CHILD], 'closed source joins')
    need(closed['process_reaped'] is True and closed['individual_leader_absent'] is True and closed['stop_reason'] is None, 'root lifecycle')
    need(closed['all33_inputs_actual_peer_python_unchanged'] is True, 'root interpreter attribution')
    need(closed['root_launch_sha256']==EXPECTED[RUN+'launch.json'] and launch['actual_sha256']==EXPECTED[ACTUAL] and launch['peer_sha256']==EXPECTED[CHILD], 'launch joins')
    need(launch['argv'][1:3]==['-I','-B'] and launch['argv'][-1]==EXPECTED[ACTUAL] and launch['controls']==actual['root_controls'], 'launch declaration')
    need(actual['python_sha256']=='1699bf8aa705a8bb71613bef5cdd7d7c8c9d9a188a841f41679aa9b5830b8f60', 'root-selected Python metadata')
    for name in ['report.json','receipt.json']:
        need(closed['output_files'][name]=={'sha256':EXPECTED[OUT+name], 'bytes':(ROOT/OUT/name).stat().st_size}, 'output inventory')
    need(receipt['outputs']=={'report.json':{'bytes':35251435,'sha256':EXPECTED[OUT+'report.json']}}, 'receipt report inventory')
    for name in ['stdout','stderr']:
        need(closed[name+'_sha256']==EXPECTED[RUN+name+'.log'], 'root streams')
    rss=closed['RSS_samples']
    need(len(rss)==17 and max(r['RSS_bytes'] for r in rss)==closed['max_observed_RSS_bytes']==173670400, 'RSS saved maximum')
    need(closed['RSS_is_sampled_owned_leader_not_true_peak'] is True and closed['wall_seconds']==1.852212042082101, 'wall/RSS scope')
    need(report['source_census_sha256']==actual['input_sha256'][CENSUS] and report['source_MSH_sha256']==actual['source_baseline']['MSH_sha256'], 'current data identities')
    need(report['source_partial_head_report_sha256']==actual['source_baseline']['report_sha256'], 'partial proof identity')
    need(receipt['native_or_meshing_calls']==report['native_or_meshing_calls']==0 and closed['native_execution_performed'] is False, 'no native query')
    for key in ['generation_authorized','optimization_authorized','head_edit_authorized','stitching_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']:
        need(report[key] is False and actual[key] is False, 'false authority '+key)
    need(report['next_candidate'] is None and report['embedding_domain_parent_owner_or_containment_checks_performed'] is False and report['tag_disjointness_is_not_a_geometric_nonoverlap_proof'] is True, 'retained limits')

    star=census['complete_seed_star_census']
    rows=star['complete_incident_tetrahedra']; nodes={r['node_tag']:r for r in star['unique_incident_nodes']}
    seeds=star['movable_node_tags']; poor=set(star['positive_poor_tetrahedron_tags'])
    need(len(rows)==5267 and len(nodes)==2905 and len(seeds)==154 and len(poor)==204, 'fresh census sizes')
    typed={
      'movable_node_tags_u64':('Q',seeds),
      'selected_tetrahedron_tags_u64':('Q',[r['tetrahedron_tag'] for r in rows]),
      'selected_tetrahedron_connectivity_u64':('Q',[t for r in rows for t in r['node_tags']]),
      'union_node_tags_u64':('Q',list(nodes)),
      'union_coordinates_f64':('d',[v for r in nodes.values() for v in r['coordinates_mm']]),
      'selected_initial_SICN_f64':('d',[r['initial_native_SICN'] for r in rows])}
    for name,(fmt,values) in typed.items():
        need(hashlib.sha256(struct.pack('<'+fmt*len(values),*values)).hexdigest()==star['ordered_tagged_array_sha256s'][name], 'typed census '+name)
    records=report['all_candidate_star_records']
    need([r['apex'] for r in records]==seeds, 'all154 in census order')
    summaries=[]; negative=[]; totals=Counter()
    for record in records:
        apex=record['apex']; selected=[r for r in rows if apex in r['node_tags']]
        celltags=[r['tetrahedron_tag'] for r in selected]
        vertices=sorted({t for r in selected for t in r['node_tags']})
        thispoor=[r['tetrahedron_tag'] for r in selected if r['initially_positive_poor']]
        need(record['source_complete_incident_cell_count']==len(selected) and record['source_tetrahedron_tags']==celltags, 'all incident cells')
        need(record['source_native_array_indices']==[r['native_array_index'] for r in selected] and record['all_vertex_tags']==vertices, 'indices/vertices')
        need(record['poor_tetrahedron_tags']==thispoor and record['poor_coverage']==len(thispoor), 'poor support')
        observation=record['observation']; shell=record['shell']; screen=record['necessary_face_screen']
        need(observation['native_ordered_cell_rows']==selected and observation['apex']==apex, 'complete original rows')
        need(observation['source_census_sha256']==report['source_census_sha256'] and observation['original_parent_MSH_sha256']==report['source_MSH_sha256'], 'observation provenance')
        expected_nodes=[dict(nodes[t],binary64_little_endian_bytes_hex=words(nodes[t]['coordinates_mm']).hex()) for t in vertices]
        need(observation['selected_node_rows']==expected_nodes, 'all selected node records')
        for row in observation['selected_node_rows']:
            original=nodes[row['node_tag']]
            need(words(row['coordinates_mm'])==words(original['coordinates_mm']) and [float(x).hex() for x in row['coordinates_mm']]==row['binary64_hex'], 'node coordinate words')
        owners=defaultdict(list)
        for cell in selected:
            for face_pattern in FACES:
                face=[cell['node_tags'][i] for i in face_pattern]
                owners[tuple(sorted(face))].append({'source_owner_tetrahedron_tag':cell['tetrahedron_tag'],'global_node_tags':face,'native_corner_indices':list(face_pattern)})
        outer=[]; internal=0
        for key, hits in sorted(owners.items()):
            if len(hits)==1:
                need(apex not in key, 'complete apex star boundary')
                outer.append(hits[0])
            else:
                need(len(hits)==2 and cycle(hits[0]['global_node_tags'])==cycle(hits[1]['global_node_tags'][::-1]), 'opposed cell faces')
                internal+=1
        surface=observation['outer_surface']; complex_row=observation['tetrahedral_complex']
        need(surface['oriented_source_owner_rows']==outer, 'all oriented boundary owner/corner rows')
        faces=[r['global_node_tags'] for r in outer]
        need(complex_row['oriented_boundary']==[list(f) for f in sorted(cycle(f) for f in faces)], 'complex boundary orientations')
        need(complex_row['cell_count']==len(selected) and complex_row['internal_face_pairs']==internal, 'complex counts')
        edges=defaultdict(list); adjacency=defaultdict(set); links=defaultdict(list)
        for face in faces:
            for i,a in enumerate(face):
                b=face[(i+1)%3]; edges[tuple(sorted((a,b)))].append((a,b)); adjacency[a].add(b); adjacency[b].add(a)
                links[a].append((face[(i+1)%3],face[(i+2)%3]))
        need(all(len(v)==2 and v[0]==v[1][::-1] for v in edges.values()) and connected(adjacency), 'closed connected shell edges')
        need(len(adjacency)-len(edges)+len(faces)==2, 'Euler sphere')
        for pairs in links.values():
            graph=defaultdict(set); degree=Counter()
            for a,b in pairs: graph[a].add(b);graph[b].add(a);degree.update((a,b))
            need(all(n==2 for n in degree.values()) and connected(graph), 'single cycle vertex links')
        need({k:surface[k] for k in ['vertices','edges','oriented_triangles','components','Euler','all_vertex_links_single_cycles']}==dict(vertices=len(adjacency),edges=len(edges),oriented_triangles=len(faces),components=1,Euler=2,all_vertex_links_single_cycles=True), 'surface counts')
        fixed=sorted(adjacency); need(set(fixed)==set(vertices)-{apex}, 'all nonapex shell vertices')
        inverse={t:i+1 for i,t in enumerate(fixed)}
        need(shell['local_to_global_node_tags']==fixed and shell['global_to_local_node_tags']=={str(t):i for t,i in inverse.items()}, 'local/global bijection')
        need(shell['vertices']==len(fixed) and shell['oriented_triangles']==len(faces) and shell['excluded_source_apex_tag']==apex and shell['apex_not_in_shell_input'] is True, 'shell sizes/apex')
        boundary=[t for t in fixed if nodes[t]['source_boundary_tag']]; interior=[t for t in fixed if not nodes[t]['source_boundary_tag']]
        classes=dict(boundary_global_node_tags=boundary,other_interior_global_node_tags=interior)
        need(observation['original_source_classifications']==classes, 'original class partitions')
        need(shell['original_source_classifications']==dict(classes,boundary_local_node_tags=[inverse[t] for t in boundary],other_interior_local_node_tags=[inverse[t] for t in interior]), 'shell classes versus temporary fixing')
        expected_v=[]
        for t in fixed:
            n=nodes[t]
            need(n['source_boundary_tag'] is (t<=871731), 'source boundary tag convention')
            expected_v.append(dict(local_node_tag=inverse[t],source_global_node_tag=t,coordinates_mm=n['coordinates_mm'],binary64_hex=n['binary64_hex'],binary64_little_endian_bytes_hex=words(n['coordinates_mm']).hex(),original_source_boundary_node=n['source_boundary_tag'],original_source_classification=n['freshly_proved_classification_scope'],prospective_cavity_fixed=True))
        need(shell['vertex_rows']==expected_v, 'complete shell vertex rows')
        for a,b in zip(shell['vertex_rows'],expected_v):need(words(a['coordinates_mm'])==words(b['coordinates_mm']), 'shell bit identity')
        need(len(complex_row['quality_rows'])==len(selected) and complex_row['all_exact_positive'] is True, 'all saved old qualities')
        stored_volume=Fraction(0)
        for q,cell in zip(complex_row['quality_rows'],selected):
            det=ratio(q['exact_determinant_mm3']); q2=ratio(q['exact_SICN_squared'])
            need(q['tetrahedron_tag']==cell['tetrahedron_tag'] and q['ordered_node_tags']==cell['node_tags'], 'quality association')
            need(det>0 and q2>0 and q['exact_point1_gate_passed'] is (det>0 and q2>=Fraction(1,100)), 'saved old quality flags')
            stored_volume+=det/6
        need(stored_volume==ratio(complex_row['exact_signed_volume_mm3'])==ratio(observation['exact_volume_mm3'])==ratio(shell['exact_enclosed_volume_mm3']), 'stored exact volume identities')
        need(len(shell['oriented_triangle_rows'])==len(screen['all_rows'])==len(faces)==screen['complete_face_count'], 'every face retained')
        counts=Counter(strictly_above=0,equal=0,below=0); failed=[]
        indices={r['tetrahedron_tag']:r['native_array_index'] for r in selected}
        for i,(face,row,tri) in enumerate(zip(outer,screen['all_rows'],shell['oriented_triangle_rows']),1):
            tags=face['global_node_tags']; xyz=[nodes[t]['coordinates_mm'] for t in tags]; hexes=[nodes[t]['binary64_hex'] for t in tags]
            expected_tri=dict(local_face_id=i,local_node_tags=[inverse[t] for t in tags],source_global_node_tags=tags,source_owner_tetrahedron_tag=face['source_owner_tetrahedron_tag'],source_native_array_index=indices[face['source_owner_tetrahedron_tag']],native_corner_indices=face['native_corner_indices'])
            need(tri==expected_tri and row['local_face_id']==i and row['source_global_node_tags']==tags and row['binary64_hex']==hexes, 'face native/local/hex associations')
            need([words(p) for p in row['coordinates_mm']]==[words(p) for p in xyz], 'face coordinate word identity')
            cert=row['exact_fixed_face_certificate']; cross2=ratio(cert['cross_squared_mm4']); length=ratio(cert['sum_squared_edge_lengths_mm2']); q2=ratio(row['exact_triangle_SICN_squared'])
            need(cross2>0 and length>0 and q2==ratio(cert['exact_triangle_SICN_squared'])==12*cross2/length**2, 'stored triangle rational arithmetic')
            need(ratio(cert['exact_loose_tetra_SICN_squared_upper_bound'])==27*cross2/length**2 and ratio(cert['inequality_left_2700_cross_squared'])==2700*cross2 and ratio(cert['inequality_right_edge_sum_squared'])==length**2, 'stored loose rational arithmetic')
            loose=2700*cross2<length**2
            need(cert['exact_strict_inequality_2700_cross_squared_lt_edge_sum_squared'] is loose and cert['no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1'] is loose, 'loose flag consistency')
            threshold=Fraction(4,841)
            need(ratio(row['exact_threshold_squared'])==threshold, 'tight threshold')
            flags=dict(strictly_above=q2>threshold,equal=q2==threshold,below=q2<threshold)
            need(all(row[k] is v for k,v in flags.items()) and row['necessary_point1_face_bound_passed'] is (q2>=threshold), 'tight exact decision')
            counts.update({k:int(v) for k,v in flags.items()})
            if q2<threshold: failed.append(dict(local_face_id=i,global_node_tags=tags,exact_triangle_SICN_squared=row['exact_triangle_SICN_squared']))
        passed=counts['below']==0
        need(dict(counts)==screen['counts'] and screen['all_necessary_point1_face_bounds_passed'] is passed and ratio(screen['exact_threshold_triangle_SICN_squared'])==Fraction(4,841), 'complete face counts')
        need(screen['tight_decision_uses_q_squared_not_the_included_loose_certificate_flag'] is True and record['eligible'] is passed, 'tight not loose eligibility')
        need(record['eligibility_status']==('all_exact_shell_and_necessary_face_gates_pass' if passed else 'necessary_face_quality_refused'), 'eligibility label')
        need(shell['status']==('DATA_ONLY_HELD' if passed else 'DATA_ONLY_REJECTED_FIXED_SHELL_FACE_QUALITY') and shell['necessary_face_quality_passed'] is passed and shell['generation_input_rejected_by_necessary_face_quality'] is (not passed), 'complete negative retention')
        for key in ['execution_authorized','native_application_authorized','engineering_accepted','physics_qualified','manufacturing_authorized']: need(shell[key] is False,'held shell authority')
        need(shell['next_candidate'] is None and shell['native_output'] is None and shell['prospective_fixed_shell_only'] is True and observation['embedding_domain_and_external_owner_checks_performed'] is False, 'prospective scope')
        totals.update(cell_rows=len(selected),node_rows=len(vertices),shell_faces=len(faces),internal_face_pairs=internal)
        summaries.append(dict(apex=apex,cells=len(selected),vertices=len(vertices),shell_faces=len(faces),poor_coverage=len(thispoor),eligible=passed,failed_faces=failed))
        if failed:negative.append(summaries[-1])

    picked=[]; expected_decisions=[]
    for rank,record in enumerate(sorted(records,key=lambda r:(-r['poor_coverage'],r['apex'])),1):
        overlap=[]
        for old in picked:
            shared=sorted(set(record['all_vertex_tags']).intersection(old['all_vertex_tags']))
            if shared:overlap.append(dict(selected_apex=old['apex'],shared_vertex_tags=shared))
        take=record['eligible'] and not overlap
        expected_decisions.append(dict(rank=rank,apex=record['apex'],poor_coverage=record['poor_coverage'],eligible=record['eligible'],selected=take,status='selected' if take else ('ineligible' if not record['eligible'] else 'vertex_conflict'),conflicts_with_already_selected=overlap))
        if take:picked.append(record)
    need(report['all_ranked_selection_decisions']==expected_decisions, 'complete deterministic decisions/conflicts')
    flat_vertices=[t for r in picked for t in r['all_vertex_tags']]
    flat_cells=[t for r in picked for t in r['source_tetrahedron_tags']]
    covered=sorted({t for r in picked for t in r['poor_tetrahedron_tags']})
    need(len(flat_vertices)==len(set(flat_vertices)) and len(flat_cells)==len(set(flat_cells)), 'entire vertex and cell disjointness')
    need(report['selected_apex_tags']==[r['apex'] for r in picked] and report['selected_star_count']==len(picked)==116, 'selected ranking')
    need(report['selected_unique_vertex_count']==len(flat_vertices)==2430 and report['selected_complete_cell_count']==len(flat_cells)==4164, 'selected counts')
    need(report['current_poor_tetrahedron_tags_covered']==covered and report['current_poor_cell_coverage']==len(covered)==172 and report['remaining_current_poor_tetrahedron_tags']==sorted(poor-set(covered)), 'coverage union/remaining')
    need(len(poor-set(covered))==32 and report['eligibility_count']==sum(r['eligible'] for r in records)==152 and report['ineligible_count']==len(negative)==2 and report['candidate_star_count']==154, 'all counts')
    after={name:digest(ROOT/name) for name in pins}
    need(after==before, 'all explicit saved inputs stable')
    result=dict(schema='962-current204-batch-independent-saved-association-check/v1',status='PASS',
      input_sha256=before,input_sha256_after=after,all_inputs_unchanged=True,
      full_output_inventory=closed['output_files'],all_154_star_summaries=summaries,negative_records=negative,
      total_repeated_saved_rows=dict(totals),all_154_decisions_conflicts_equal=True,
      selected_apex_tags=report['selected_apex_tags'],selected_stars=116,eligible=152,ineligible=2,
      selected_unique_vertices=2430,selected_complete_cells=4164,current_poor_coverage=172,remaining_poor=32,
      all_six_census_typed_hashes_equal=star['ordered_tagged_array_sha256s'],
      root_lifecycle_attribution=dict(returncode=0,reaped=True,individual_leader_absent=True,stop_reason=None,
        wall_seconds=closed['wall_seconds'],sampled_RSS_count=len(rss),maximum_sampled_owned_leader_RSS_bytes=173670400,true_peak=False),
      independent_scope='Complete saved row/bit/index/class/inverse/face-incidence/topology associations, rational arithmetic on saved determinant/certificate fields, threshold flags, ranking/conflicts/disjointness/coverage and byte closure. No prepared helper, query or geometry predicate executed.',
      source_attribution='Coordinate-to-determinant/cross/length/Q2 derivations and exact geometric certificates remain producer/source-reviewed calculations. Full-global incidence/classification/native metrics remain executed census observations, not a new MSH read or geometry replay.',
      limits=['Tag disjointness is not geometric nonoverlap. Necessary face screens do not prove embedding/domain/containment/meshing feasibility. Coverage is a combinatorial observation, not repaired cells. Whole head remains quality-rejected with 204 positive poor cells.'],
      engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False)
    destination=HERE/'independent-saved-check.json'
    need(not destination.exists(), 'fresh saved check output')
    destination.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='PASS',candidates=154,eligible=152,selected=116,poor_covered=172,remaining_poor=32,checked_inputs=len(pins))))

if __name__=='__main__':
    main()
