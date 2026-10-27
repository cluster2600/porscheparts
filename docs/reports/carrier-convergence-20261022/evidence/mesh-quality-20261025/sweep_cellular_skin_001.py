from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];S=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022';sys.path.insert(0,str(S));from select_cellular_budget import eligible_core;from assess_native_P2 import stress_energy
W=Path(__file__).resolve().parent;P=W/'linear-cellular-collected-015';metadata=json.loads((P/'prepared/oracle-report.json').read_text());baseline=json.loads((W/'linear-cellular-budget-015/assessment.json').read_text());a=json.loads((W/'fine-P2-015-assessment/assessment.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();sources=[P/'prepared/oracle-report.json',P/'prepared/screen-fields.npz',P/'results/cpu/report.json',P/'results/cuda/report.json',P/'results/cuda/distances.npz',W/'linear-cellular-budget-015/assessment.json',W/'linear-cellular-budget-015/selected-cells.npz',W/'fine-P2-015-assessment/assessment.json',W/'fine-P2-015-assessment/results.npz',W/'remeshed-red8-matched-traction-001/P2/transport.npz',W/'fine-P2-core-energy-015/assessment.json',Path(__file__),S/'select_cellular_budget.py',S/'assess_native_P2.py'];OUT=W/'cellular-skin-sweep-001';assert not OUT.exists();OUT.mkdir();skins=[.75,1.,1.25,1.5,2.,3.];(OUT/'contract.json').write_text(json.dumps(dict(skin_scenarios_mm=skins,bore_keepout_mm=10,end_inboard_limit_abs_X_mm=260,relative_density=.4,maximum_volume_fraction=.1,distance_limit_mm=.0001,original_skin_mm=1.5,selection_ranking='unchanged T4 baseline energy density; independently evaluate selected T10 energy',geometry_changed=False,source_sha256={str(p):sha(p)for p in sources}),indent=2))
for device in ['cpu','cuda']:
 r=json.loads((P/f'results/{device}/report.json').read_text());assert r['status']=='passed' and r['fixed_absolute_error_limit_mm']==.0001 and r['queries']==3052512
assert sha(P/'prepared/screen-fields.npz')==metadata['screen_fields_sha256'];assert sha(P/'results/cuda/distances.npz')==r['output_distances_sha256'];assert r['gpu_validated']and r['actual_device']=='cuda:0';assert sha(W/'fine-P2-015-assessment/results.npz')==a['output_sha256']
with np.load(P/'prepared/screen-fields.npz')as d:f={k:d[k].copy()for k in d.files}
with np.load(P/'results/cuda/distances.npz')as d:distance=d['distances_mm'].astype(float);assert np.all(d['hits']==1)
with np.load(W/'remeshed-red8-matched-traction-001/P2/transport.npz')as d:v=d['vertices'].copy();c=d['tetrahedra'].copy()
with np.load(W/'fine-P2-015-assessment/results.npz')as d:stress=d['stress'].copy()
with np.load(W/'linear-cellular-budget-015/selected-cells.npz')as d:original=d['indices'].copy()
assert c.shape==(3052512,10)and stress.shape==(3052512,4,6);material=metadata['material'];volume=f['volumes_mm3'];energy=f['energy_Nmm'];rows=[]
for skin in skins:
 eligible=eligible_core(distance,f['radii'],f['probe_transport_L1_mm'],metadata['surface_float32_transport_L1_bound_mm'],f['interface_allowed'],skin);ids=np.flatnonzero(eligible);ids=ids[np.argsort(energy[ids]/volume[ids],kind='stable')];ids=ids[np.cumsum(volume[ids])<=.1*volume.sum()]
 if skin==1.5:assert np.array_equal(ids,original)
 if len(ids):u,vol=stress_energy(v,c[ids],stress[ids],material['E_MPa'],material['nu'],np)
 else:u=vol=0.
 assert np.isclose(vol,volume[ids].sum(),rtol=1e-10,atol=1e-8);saving=.6*vol*material['density_tonne_mm3']*1000;rows.append(dict(skin_mm=skin,selected_cells=len(ids),volume_mm3=vol,conditional_saving_kg=saving,T10_baseline_energy_fraction=u/a['independent_stress_compliance_energy_Nmm']));np.savez_compressed(OUT/('skin-'+str(skin)+'.npz'),indices=ids);print(rows[-1],flush=True)
(OUT/'assessment.json').write_text(json.dumps(dict(status='conditional_skin_sensitivity_screen_completed',rows=rows,original_skin_mm=1.5,bore_keepout_changed=False,geometry_changed=False,changed_geometry_stiffness_predicted=False,printability_qualified=False,contract_sha256=sha(OUT/'contract.json')),indent=2))
