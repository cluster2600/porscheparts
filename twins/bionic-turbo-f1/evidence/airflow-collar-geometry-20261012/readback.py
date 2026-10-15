"""Reread the collar report and independently verify its published bounds."""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
from audit_collar import BASE, BANDS, PROFILE, self_check
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
self_check()
p=BASE/'collar-062.json';r=json.loads(p.read_text())
assert sha(BASE/'audit_collar.py')==r['source_sha256']
assert sha(PROFILE)==r['profile_manifest_sha256']
assert [sha(p) for p in BANDS]==r['band_report_sha256']
nodes=np.asarray(r['nodes_z_radius_mm']);c=math.cos(math.pi/128)
eta=r['central_required_clearance_mm']/(2*max(nodes[:,1]))
assert eta==r['eta'] and r['inner_ratio']==1-eta and r['outer_ratio']==1+eta
assert (1-eta)<c and (1+eta)*c>1
results={}
for (name,v),path in zip(r['variants'].items(),BANDS):
    source=json.loads(path.read_text());minimum=float('inf')
    assert [b['index'] for b in v['bands']]==list(range(3,359))
    for row in v['bands']:
        b=source['bands'][row['index']];lo,hi=row['z_mm']
        # Separate segment traversal, including an interior knot even when endpoints are feasible.
        radii=[]
        for (z0,r0),(z1,r1) in zip(nodes[:-1],nodes[1:]):
            if z0<=hi and z1>=lo:
                for z in (max(z0,lo),min(z1,hi)):
                    radii.append(r0+(r1-r0)*(z-z0)/(z1-z0))
        expected=[(1-eta)*min(radii)*c-b['rotor_upper_mm'],b['stator_lower_mm']-(1+eta)*max(radii)]
        assert np.max(np.abs(np.array(expected)-row['rotor_stator_separations_mm']))<2e-14
        assert min(expected)>=r['minimum_required_lateral_collar_separation_mm']
        minimum=min(minimum,min(expected))
    rotor=v['rotor'];assert rotor['facets']==516216 and rotor['minimum_radial_bound_mm']>0
    assert rotor['all_facets_inside_inner_boundary']
    for patch,counts in v['terminal_candidates'].items():
        assert all(value==0 for key,value in counts.items() if key!='rear_candidates')
        assert patch=='stator' or not counts['rear_candidates']
    assert all(abs(w['value']-w['expected'])<1e-6 for w in v['closed_boundary_winding'].values())
    results[name]=dict(bands_checked=len(v['bands']),minimum_radial_separation_mm=minimum,
                       rotor_facets=rotor['facets'],rotor_minimum_bound_mm=rotor['minimum_radial_bound_mm'])
assert r['variants']['baseline']['rotor']['float64_mm_sha256']==r['variants']['candidate']['rotor']['float64_mm_sha256']
assert r['mesh_admission'] is False and r['performance_ranking_authorized'] is False
out=dict(source_sha256=sha(Path(__file__)),report_sha256=sha(p),all_published_bounds_reread=True,
         source_facets_reread_by='audit_collar.py, exact STL SHA-256 and complete patch counts checked',
         variants=results,solver_launched=False,performance_ranking_authorized=False)
with (BASE/'readback.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out,indent=2))
