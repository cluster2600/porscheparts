"""One owned saved-only structural decode. No worker/helper, SymPy, Fraction or native replay."""
from pathlib import Path
import gzip,hashlib,io,json,sys
R=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
E=R/'work/962-engineering'
Q=E/'head-star-current24-exact-segment-feasibility-saved-structure-002'
O=E/'head-star-current24-exact-segment-feasibility-002'
D=E/'head-star-current24-exact-segment-feasibility-root-execution-002'
def rec(p):
 b=p.read_bytes();return dict(path=str(p.relative_to(R)),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def check(condition,message):
 if not condition:raise ValueError(message)
def load(p):return json.loads(p.read_text())
m=load(O/'manifest.json');closed=load(D/'closed-result.json')
check(rec(O/'manifest.json')==closed['outputs']['manifest.json'],'Manifest/root inventory join')
check(rec(D/'closed-result.json')['sha256']=='6bbbc243a87106a213e0b0e3813a638b4e43be7aae878ce17f65d8daf7d59b6e','Fixed root closure')
check(m['logical_payload']['bytes']==35016403 and m['logical_payload']['sha256']=='3e5d8c2d788e8510b8894e1a5811ef89c3a42716e1c1c2ba0debe4c20aed8c33','Exact logical bound')
compressed=(O/'real-segment-feasibility.json.gz').read_bytes()
check(len(compressed)==5750611 and hashlib.sha256(compressed).hexdigest()=='74773078ca9ccccf02a9e3e7530b6fe753d7af065723ab70f0778976b8943226','Exact compressed hash/count')
check(rec(O/'real-segment-feasibility.json.gz')==closed['outputs']['real-segment-feasibility.json.gz'],'Compressed/root inventory join')
chunks=[];count=0;digest=hashlib.sha256()
with gzip.GzipFile(fileobj=io.BytesIO(compressed),mode='rb')as stream:
 while True:
  block=stream.read1(min(io.DEFAULT_BUFFER_SIZE,35016403-count+1))
  if not block:break
  count+=len(block);check(count<=35016403,'Declared exact input exceeded')
  digest.update(block);chunks.append(block)
check(count==35016403 and digest.hexdigest()==m['logical_payload']['sha256'],'Full logical SHA/count/EOF/CRC')
logical=b''.join(chunks);del chunks
body=json.loads(logical);del logical
check('sympy'not in sys.modules and 'fractions'not in sys.modules,'No mathematical replay module')
check(body['schema']==m['logical_schema']and body['status']==m['logical_status'],'Inner schema/status')
for key in ('source','held_preparation','own_actual','tuple_list'):
 check(body[key]==m[key]and rec(R/body[key]['path'])==body[key],'Complete source/held/actual/tuple identity:'+key)
held=load(R/body['held_preparation']['path']);actual=load(R/body['own_actual']['path'])
tuples=load(R/body['tuple_list']['path'])
check(body['own_actual']==closed['actual_before']==closed['actual_after'],'Root actual join')
check(body['input_records']==held['input_records']==actual['input_records']and len(body['input_records'])==55,'All55 input map joins')
check(body['source']==actual['worker']==held['source']and body['held_preparation']==actual['held_preparation'],'Source and held caller joins')
check(body['tuple_list']==actual['tuple_list']==held['tuple_list'],'Tuple caller joins')
check(body['segment_count']==19 and body['complete_cell_dispositions']==916 and body['complete_constraint_associations']==1832,'Top counts')
paths=body['complete19_segments'];check(len(paths)==len(tuples['tuples'])==19,'All19 path order')
rows=[];cells=0;constraints=0;unique_cells=set();seeds=set();seen_tuples=set();component_IDs=set()
totals=dict(paths=0,real_path_feasible_saved_true=0,real_path_feasible_saved_false=0,global_real_roots_saved=0,
 ordered_boundaries_including0and1=0,interior_boundary_count=0,sign_atoms=0,feasible_sign_atoms=0,
 connected_real_feasible_components=0,positive_width_components=0,isolated_components=0,rational_witnesses=0)
for descriptor,path in zip(tuples['tuples'],paths):
 check({k:path[k]for k in descriptor}==descriptor,'Exact complete tuple descriptor join')
 check(path['tuple_ID']not in seen_tuples,'Unique tuple_ID')
 seen_tuples.add(path['tuple_ID']);component_IDs.add(path['component_ID'])
 tags=[x['tetrahedron_tag']for x in path['complete_cell_polynomials']]
 check(tags==descriptor['full_tetrahedron_tags']and len(tags)==descriptor['full_cell_count'],'Every original full-cell association')
 unique_cells.update(tags);cells+=len(tags)
 for choice in path['seed_choices']:seeds.add(choice['seed_node_tag'])
 real=path['real_feasibility'];cs=real['constraints'];constraints+=len(cs)
 check(len(cs)==path['complete_constraint_count']==2*len(tags),'All D/P row counts')
 check([x['constraint_ID']for x in cs]==list(range(len(cs))),'Complete sequential constraint IDs')
 check([(x['cell_tag'],x['kind'])for x in cs]==[(tag,kind)for tag in tags for kind in ('D','P')],'Every D/P cell association')
 components=real['connected_feasible_components'];atoms=real['complete_sign_atoms'];boundaries=real['ordered_boundaries']
 check(real['real_path_classification_complete']is True and real['all_cell_constraint_associations_retained']is True,'Saved completeness flags')
 check(real['real_path_feasible']is bool(components),'Saved boolean/component consistency')
 check([x['atom_ID']for x in atoms]==list(range(len(atoms))),'All sign atoms sequential')
 check(all(len(x['signs'])==len(cs)for x in atoms),'Complete saved sign-vector lengths')
 check(path['word_construction_status']=='UNSUPPORTED_NOT_ATTEMPTED'and path['rounded_word_proposals']==[]and path['word_rechecks']==[],'Word phase unresolved')
 component_rows=[]
 for c in components:
  sample=c['canonical_exact_sample'];isolated=sample['kind']=='exact_singleton'
  rational_sample=sample.get('value')if sample['kind']=='minimum_denominator_then_numerator_rational'else None
  check(c['correctly_rounded_binary64_proposal']is None and c['actual_word_recheck']is None and c['binary64_existence_claim']is False,'No word witness')
  component_rows.append(dict(component_index=c['component_index'],kind='isolated'if isolated else'positive_width',
   atom_IDs=c['atom_IDs'],left_boundary=c['left_boundary'],right_boundary=c['right_boundary'],
   left_closed=c['left_closed'],right_closed=c['right_closed'],
   canonical_exact_sample=sample,rational_witness_saved_exact=rational_sample))
  totals['isolated_components']+=int(isolated);totals['positive_width_components']+=int(not isolated)
  totals['rational_witnesses']+=int(rational_sample is not None)
 global_roots=sum(f['total_real_roots']for f in real['irreducible_factors'])
 row=dict(component_ID=path['component_ID'],tuple_ID=path['tuple_ID'],
  seed_choices=path['seed_choices'],full_cells=len(tags),constraint_associations=len(cs),
  irreducible_factor_count=len(real['irreducible_factors']),global_real_roots_saved=global_roots,
  ordered_boundaries_including0and1=len(boundaries),interior_boundary_count=len(boundaries)-2,
  sign_atom_count=len(atoms),feasible_sign_atom_count=sum(x['feasible']is True for x in atoms),
  real_path_feasible_saved=real['real_path_feasible'],real_feasible_component_count=len(components),
  real_feasible_components=component_rows)
 rows.append(row);totals['paths']+=1
 totals['real_path_feasible_saved_true']+=int(real['real_path_feasible'])
 totals['real_path_feasible_saved_false']+=int(not real['real_path_feasible'])
 totals['global_real_roots_saved']+=global_roots;totals['ordered_boundaries_including0and1']+=len(boundaries)
 totals['interior_boundary_count']+=len(boundaries)-2;totals['sign_atoms']+=len(atoms)
 totals['feasible_sign_atoms']+=row['feasible_sign_atom_count'];totals['connected_real_feasible_components']+=len(components)
check(cells==916 and constraints==1832 and len(unique_cells)==499 and len(seeds)==16 and len(component_IDs)==11,'Complete finite structural scope')
check(all(v is False for v in body['qualification'].values()),'False physical/native/optimizer/qualification flags')
summary=dict(schema='962-current24-exact-segment-source-author-saved-structure-summary/v1',
 status='BYTE_AND_STRUCTURAL_JOINS_ONLY_INDEPENDENT_SCIENTIFIC_REVIEW_PENDING',
 author_lineage='Source/controller author structural read; not the independent Fraction/Sturm result peer.',
 inputs=dict(root_closed=rec(D/'closed-result.json'),manifest=rec(O/'manifest.json'),
  compressed=rec(O/'real-segment-feasibility.json.gz'),logical_payload=m['logical_payload'],
  source=body['source'],held=body['held_preparation'],actual=body['own_actual'],tuples=body['tuple_list']),
 byte_identity=dict(compressed_hash_count=True,logical_hash_count=True,complete_gzip_EOF_CRC=True,logical_bytes=count),
 structural_coverage=dict(paths=19,component_IDs=sorted(component_IDs),unique_components=11,
  full_cell_dispositions=cells,unique_cells=len(unique_cells),constraint_associations=constraints,
  input_record_joins=55,unique_seed_nodes=len(seeds),all19_tuple_descriptors_exact=True,
  all916_cell_tag_associations_exact=True,all1832_D_P_constraint_associations_exact=True),
 aggregate_saved_summary=totals,complete19_paths=rows,
 native_run_lifecycle_and_106_metadata_1667_packages_runtime_freshness='Attributed to root closure6bbbc243; not re-executed or independently body-hashed here.',
 no_root_or_polynomial_or_Fraction_quality_or_candidate_arithmetic_replay=True,
 scientific_result_accepted=False,empty_or_nonempty_real_paths='Saved declarations summarized only; exact scientific acceptance pending independent peer.',
 binary64_word_construction=False,geometry_application=False,all_prior_failures_preserved=True)
out=Q/'summary.json'
with out.open('x')as f:json.dump(summary,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(summary=rec(out),structural_coverage=summary['structural_coverage'],aggregate_saved_summary=totals,
 paths=[dict(component_ID=x['component_ID'],tuple_ID=x['tuple_ID'],roots=x['interior_boundary_count'],
  atoms=x['sign_atom_count'],feasible_components=x['real_feasible_component_count'],
  exact_rational_witnesses=[c['rational_witness_saved_exact']for c in x['real_feasible_components']])for x in rows])),flush=True)
