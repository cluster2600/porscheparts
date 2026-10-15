"""Check the baseline open profile against both actual CFD surface bounds."""
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path('twins/bionic-turbo-f1/cfd').resolve()))
from prepare_case import sha
base=Path(__file__).resolve().parent
reports={name:json.loads((base/(name+'-profile-023.json')).read_text()) for name in ('baseline','candidate')}
a,b=(reports[name] for name in ('baseline','candidate'))
assert len(a['bands'])==len(b['bands'])==359
assert a['corridor']['unresolved_band_indices']==b['corridor']['unresolved_band_indices']==[0,1,2]
profile=a['corridor']['open_profiles'][0];nodes=profile['nodes_z_radius_mm'];cosine=math.cos(math.pi/32)
values={}
for name,report in reports.items():
    margins=[]
    for j,i in enumerate(profile['band_indices']):
        row=report['bands'][i]
        assert row['z_low_mm']==nodes[j][0] and row['z_high_mm']==nodes[j+1][0]
        margins.append(min(min(nodes[j][1],nodes[j+1][1])*cosine-row['rotor_upper_mm'],row['stator_lower_mm']-max(nodes[j][1],nodes[j+1][1])))
    assert min(margins)>0
    values[name]=dict(surface_sha256=report['surface_sha256'],report_sha256=sha(base/(name+'-profile-023.json')),minimum_shared_profile_radial_separation_bound_mm=min(margins))
result=dict(source_sha256=sha(Path(__file__)),shared_profile='baseline open profile, z -3.5 to 32.1 mm, 32 undivided angular sectors',
            resolved_bands=356,total_bands=359,variants=values,closed_interface_verified=False,
            performance_ranking_authorized=False,interpretation='Both complete CFD patch sets admit this same OPEN side profile. End closures, volume containment, smoothness and manufacturability are not established. Abrupt midpoint-profile changes must not be passed blindly to a volume mesher.')
with (base/'shared-corridor.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
