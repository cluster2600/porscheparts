"""Three Boolean pairs for caps/extended candidates, with before/after fingerprints."""
import itertools
import json
from pathlib import Path
import time

import g14_cad_private as helpers

ROOT=helpers.REPO
OUTPUT=ROOT/'work/m64-g14/combined-caps-extended-clearance-v1.json'
INPUTS=(('cad-central-caps-v1','088a05feeb88d73e10b84708be6eb0d524d42b7b387eb79c08b95b4e2628e6df',
         'g14_central_caps_private.py',('centre_spine68_t40_root2_upper_caps',)),
        ('cad-extended-v1','f495427952c68eefd8b31c1a0b43a32a83515fbb8acf334ad70674d093ea97e6',
         'g14_extended_haunch_private.py',('outer_high_cheeks_extended_haunch_p','outer_high_cheeks_extended_haunch_m')))


def run():
    if OUTPUT.exists():raise FileExistsError('immutable output already exists')
    shapes={};bound=[];g7sha=None;frozen=None;before={}
    def require(path,want):
        actual=helpers.g11.sha256(path)
        if actual!=want:raise ValueError('fingerprint changed: '+str(path.relative_to(ROOT)))
        before[str(path.relative_to(ROOT))]=actual
    for folder,want,source,ids in INPUTS:
        directory=ROOT/'work/m64-g14'/folder;receipt=directory/'receipt.json';require(receipt,want)
        report=json.loads(receipt.read_text())
        if not report['complete'] or report['error'] is not None:raise ValueError('CAD incomplete')
        if report['crank_samples_deg']!=list(range(0,720,5)):raise ValueError('different pose coverage')
        for sourcepath in (ROOT/'work/m64-g14'/source,directory/source):require(sourcepath,report['source_sha256'])
        if g7sha is None:g7sha=report['G7_receipt_sha256'];frozen=report['frozen_sources_sha256']
        if g7sha!=report['G7_receipt_sha256'] or frozen!=report['frozen_sources_sha256']:raise ValueError('individual audits use different baselines')
        for ident in ids:
            row=next(r for r in report['variants'] if r['id']==ident)
            if not row['cad_accepted'] or row['rejections'] or row['motion_samples_checked']!=144 or row['static_interferences'] or row['sampled_motion_interferences']:raise ValueError('individual audit did not pass')
            step=directory/row['step'];require(step,row['step_sha256'])
            shapes[ident]=helpers.cq.importers.importStep(str(step)).val()
            if not helpers.assembly.brep_valid(shapes[ident]) or len(shapes[ident].Solids())!=1:raise ValueError('invalid imported BRep')
            bound.append(dict(id=ident,step=str(step.relative_to(ROOT)),step_sha256=row['step_sha256'],CAD_receipt_sha256=want,source_sha256=report['source_sha256'],individual_sampled_poses=144))
    require(helpers.g11.BASELINE,g7sha)
    for name,want in frozen.items():require(ROOT/name,want)
    require(Path(__file__),helpers.g11.sha256(Path(__file__)))
    pairs=[dict(first=a,second=b,intersection_volume_mm3=helpers.audit.overlap(shapes[a],shapes[b])) for a,b in itertools.combinations(shapes,2)]
    after={name:helpers.g11.sha256(ROOT/name) for name in before}
    if after!=before:raise ValueError('inputs or sources changed during native pair audit')
    report=dict(classification='G14_caps_extended_unselected_candidates_geometric_coexistence_only',source_sha256=helpers.g11.sha256(Path(__file__)),created_epoch=time.time(),
        components=bound,G7_receipt_sha256=g7sha,hashes_before=before,hashes_after=after,all_fingerprints_unchanged=True,
        pairs=pairs,intersection_tolerance_mm3=helpers.g11.TOL,pairwise_no_intersection=all(p['intersection_volume_mm3']<=helpers.g11.TOL for p in pairs),
        individual_motion_reuse='Each stationary support independently passed the identical144 sampled poses of the same G7 moving shapes. No support is fused, moved, or deformed; new checks cover only the three support-support pairs.',
        scope='Intersection volumes, not minimum clearances, continuous motion, or tool approach. Does not select a design or qualify real interfaces.',
        combined_structural_FEA_executed=False,deformed_or_thermal_clearance_qualified=False,manufacturing_authorized=False,engine_start_authorized=False)
    with OUTPUT.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'output':str(OUTPUT.relative_to(ROOT)),'sha256':helpers.g11.sha256(OUTPUT),'pairs':pairs,'passed':report['pairwise_no_intersection']}))
    return 0 if report['pairwise_no_intersection'] else 2


if __name__=='__main__':
    raise SystemExit(run())
