"""Independent STEP replay of the unchanged first millimetre and journal binding."""
import json
from pathlib import Path
import sys
import cadquery as cq

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'twins/m64-cylinder-head/source/fourvalve')]
import g11_cad as g11
import g13_cad as g13

folder=ROOT/'work/m64-g14/cad-v1'
report=json.loads((folder/'receipt.json').read_text())
if not report['complete'] or report['error'] is not None:raise ValueError('CAD audit incomplete')
if g11.sha256(folder/'g14_cad_private.py')!=report['source_sha256']:raise ValueError('executed CAD source changed')
g11path=g13.g12.G11_CAD
old11=json.loads(g11path.read_text())
old13path=ROOT/'twins/m64-cylinder-head/evidence/g13-support-reference-20260926/cad.json'
old13=json.loads(old13path.read_text())
p=json.loads(g11.BASELINE.read_text())['values']
if g11.sha256(g11.BASELINE)!=report['G7_receipt_sha256']:raise ValueError('G7 receipt changed')
central=next(r for r in old11['variants'] if r['id']=='centre_w11')
baselines={'central_diaphragm':(ROOT/'work/m64-g11/cad-v2'/central['step'],central['step_sha256'],central['journal_width_mm'])}
for tag in ('p','m'):
    info=old13['outer_mirror_audit']['files'][tag]
    baselines['carrier_base_'+tag]=(ROOT/'work/m64-g13/cad'/info['step'],info['step_sha256'],old13['outer_reference']['journal_width_mm'])
slab=cq.Solid.makeBox(400,200,1,cq.Vector(-200,-100,p['carrier_face_height']))
rows=[]
for row in report['variants']:
    base,want,width=baselines[row['component']]
    step=folder/row['step']
    if g11.sha256(base)!=want or g11.sha256(step)!=row['step_sha256']:raise ValueError('STEP fingerprint mismatch')
    a=cq.importers.importStep(str(step)).val();b=cq.importers.importStep(str(base)).val()
    delta=g13.difference(a.intersect(slab),b.intersect(slab))
    unchanged=all(v<=g11.TOL for v in delta.values())
    if not unchanged:raise ValueError('first millimetre changed')
    rows.append(dict(id=row['id'],step_sha256=row['step_sha256'],baseline_step_sha256=want,
        journal_width_mm=width,journal_diameter_mm=2*(p['rocker_pivot_radius']+p['carrier_journal_radial_clearance']),
        journal_width_evidence='Published baseline width, bound by unchanged full through-axis BRep neighbourhood in CAD receipt; no bore resizing',
        first_1mm_difference_mm3=delta,first_1mm_unchanged=unchanged,cad_accepted=row['cad_accepted']))
proof=dict(classification='G14_private_interface_replay_not_FE_or_build_release',
    source_sha256=g11.sha256(Path(__file__)),cad_receipt_sha256=g11.sha256(folder/'receipt.json'),
    G11_receipt_sha256=g11.sha256(g11path),G13_receipt_sha256=g11.sha256(old13path),values=p,variants=rows,
    complete=True,manufacturing_authorized=False,engine_start_authorized=False)
with (folder/'interface-proof.json').open('x') as f:json.dump(proof,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps({'accepted_ids':[r['id'] for r in rows if r['cad_accepted']],'first_1mm_unchanged':True}))
