"""Collect small, hash-bound receipts; private meshes never enter Git."""
from pathlib import Path
import hashlib,json,shutil
work=Path(__file__).resolve().parent.parent;repo=work.parent;out=repo/'docs/reports/carrier-interface-20261028/evidence/complete-void-conditioning-001';assert not out.exists();out.mkdir(parents=True)
cases={'r0-negative':work/'canonical-eight-voids-001/r0-negative-001','r0-positive':work/'cgal-checkpoint-coarsen-001/r0-positive-001','r1-negative':work/'dihedral-optimization-001/r1-negative-001','r1-positive':work/'bounded-local-fairing-001/r1-positive-001','r2-negative':work/'bounded-local-fairing-001/r2-negative-001','r2-positive':work/'dihedral-optimization-001/r2-positive-001','r3-negative':work/'bounded-local-fairing-001/r3-negative-001','r3-positive':work/'dihedral-optimization-001/r3-positive-001'}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
rows=[]
for label,case in cases.items():
 binary=case/'decoded-001/candidate.meshbin';npz=case/'decoded-001/candidate.npz';bh=digest(binary);nh=digest(npz);proof=json.loads((case/'proof-terminal.json').read_text());domain=json.loads((case/'decoded-001/independent-domain.json').read_text());feature=json.loads((case/'material-feature-audit.json').read_text());source=work/f'all-voids-upstream-audit-001/source-{label}/decoded-001/candidate.meshbin'
 assert proof['returncode']==0 and proof['candidate_sha256']==bh and proof['source_sha256']==digest(source)
 assert domain['status']=='complete_strict_domain_containment_passed'and domain['whole_bounded_solid_containment_proved']and not domain['candidate_self_intersection']
 assert feature['input_sha256']==nh and feature['reentrant_edges_above_degrees']['45']==0
 dest=out/label;dest.mkdir()
 for name,src in [('domain.json',case/'decoded-001/independent-domain.json'),('proof-terminal.json',case/'proof-terminal.json'),('material-feature-audit.json',case/'material-feature-audit.json'),('material-feature-audit-terminal.json',case/'material-feature-audit-terminal.json')]:shutil.copyfile(src,dest/name)
 method='Exact local edge flip' if label=='r0-negative'else 'Exact planar reduction and bounded CGAL coarsening'if label=='r0-positive'else 'JAX direct dihedral optimization'if 'dihedral' in str(case)else 'Bounded four-pass local fairing'
 if (case/'assessment.json').exists():shutil.copyfile(case/'assessment.json',dest/'assessment.json')
 if label=='r0-negative':shutil.copyfile(case/'fidelity.json',dest/'fidelity.json')
 rows.append(dict(void=label,method=method,private_case_path=str(case.relative_to(work)),binary_sha256=bh,npz_sha256=nh,original_void_binary_sha256=proof['source_sha256'],faces=domain['candidate_faces'],maximum_material_turn_degrees=-feature['most_reentrant_edges'][0]['normal_turn_degrees'],edges_above45=0,independent_domain_status=domain['status']))
for folder,names in [('dihedral-optimization-001',['optimize.py','run.py','controls.py','controls.json','requirements.txt','runtime.json','image.json','render-r1.py']),('bounded-local-fairing-001',['fair.py','run.py','controls.py','controls.json']),('bounded-world-translation-001',['translation.py','controls.py','controls.json','decode.py'])]:
 dest=out/folder;dest.mkdir()
 for name in names:shutil.copyfile(work/folder/name,dest/name)
for folder,name in [('l2-local-fairing-001','terminal.json'),('l2-local-fairing-001','flip-terminal.json'),('refined-local-fairing-001','terminal.json')]:shutil.copyfile(work/folder/name,out/(folder+'-'+name))
ledger=dict(status='eight_void_boundaries_pass_geometry_conditioning_stage',scope='Intermediate individual cavity boundaries. No new complete carrier assembly, mass or mechanical convergence established.',complete_carrier_reference_mass_kg=1.2933916038651307,mass_limit_kg=1.30,rows=rows,manufacturing_authorized=False)
(out/'assessment.json').write_text(json.dumps(ledger,indent=2)+'\n')
shutil.copyfile(Path(__file__),out/'collect.py')
files={str(p.relative_to(out)):dict(sha256=digest(p),bytes=p.stat().st_size)for p in sorted(out.rglob('*'))if p.is_file()};(out/'manifest.json').write_text(json.dumps(dict(status='receipt_and_method_source_manifest',files=files),indent=2)+'\n');print(json.dumps(ledger,indent=2))
