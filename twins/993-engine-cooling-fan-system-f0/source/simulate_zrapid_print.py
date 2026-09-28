#!/usr/bin/env python3
"""Full-layer slicing and energy-balanced bulk LPBF thermal screening, not qualification."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import runpy

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import cg
import trimesh

ROOT = Path(__file__).resolve().parents[3]
GEOMETRY = runpy.run_path(str(ROOT / 'scripts/run_metal_am_geometry_screen.py'))
MACRO = runpy.run_path(str(ROOT / 'twins/reference-917-engine/source/simulate_lpbf_macro_f41.py'))
sha = GEOMETRY['sha256']


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def load_card(path):
    card = json.loads(path.read_text())
    GEOMETRY['validate_machine'](card)
    p, a, m = [card[k] for k in ['published_research_recipe', 'study_assumptions', 'published_machine']]
    values = [p[k] for k in ['power_w', 'scan_speed_mm_s', 'hatch_spacing_mm', 'layer_thickness_mm', 'plate_temperature_k']]
    values += [a[k] for k in ['standoff_mm', 'recoat_seconds_per_layer', 'absorptivity', 'thermal_support_solid_fraction', 'convection_w_m2_k']]
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError('Nonfinite or nonpositive process parameters')
    if a['active_lasers'] != 1 or a['orientation'] != 'build_z':
        raise ValueError('Only the documented single-laser flat build is supported')
    if not 0 < a['absorptivity'] <= 1 or not 0 < a['thermal_support_solid_fraction'] <= 1:
        raise ValueError('Fractions outside (0,1]')
    for value, bounds in [(p['layer_thickness_mm'],m['precision_layer_range_mm']),
                          (p['scan_speed_mm_s'],m['recommended_scan_speed_mm_s']),
                          (p['spot_diameter_mm'],m['beam_diameter_1_e2_range_mm'])]:
        if not bounds[0] <= value <= bounds[1]:
            raise ValueError('Research recipe outside published machine range')
    if p['power_w'] > m['maximum_power_per_laser_w']:
        raise ValueError('Power exceeds machine rating')
    return card


def slice_part(card_path, geometry, analysis, output):
    card = load_card(card_path)
    reduction = json.loads((analysis/'surface-reduction.json').read_text())
    source, surface = geometry/'organic-fan-mm.stl', analysis/'analysis-mm.stl'
    if sha(source) != reduction['source_sha256'] or sha(surface) != reduction['analysis_sha256']:
        raise ValueError('Analysis geometry provenance mismatch')
    mesh = trimesh.load_mesh(surface, process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.body_count != 1:
        raise ValueError('Closed oriented single-body mesh required')
    output.mkdir(parents=True, exist_ok=False)
    k = GEOMETRY['load_kernel']()
    k.LAYER_MM = card['published_research_recipe']['layer_thickness_mm']
    k.MACHINE = card
    k.machine_fit = lambda extents: GEOMETRY['machine_fit'](card, extents)
    rows, result = k.slice_build(mesh, 'build_z')
    GEOMETRY['write_rows'](output/'layers.csv', rows)
    a = card['study_assumptions']
    fit = all(mesh.extents[i] + 2*a['xy_edge_margin_mm'] <= card[key]
              for i,key in enumerate(['build_width_mm','build_depth_mm']))
    fit &= mesh.extents[2]+a['standoff_mm']+a['base_plate_thickness_mm'] <= card['build_height_mm']
    if not fit:
        raise ValueError('Part and assumed allowances exceed machine envelope')
    report = {'scope':'full_layer_geometric_screen_not_machine_code', 'source_sha256':sha(source),
        'surface_sha256':sha(surface),'card_sha256':sha(card_path),'surface_path':str(surface.resolve()),
        'part_volume_mm3':float(mesh.volume),'slicing':result,'allowance_fit':bool(fit),
        'assumed_xy_edge_margin_mm':a['xy_edge_margin_mm'], 'physical_print_executed':False}
    save(output/'slicing.json',report)
    print(json.dumps(result),flush=True)


def implicit_step(t, capacity, laplacian, sink, bath, power, dt):
    """Backward Euler; all terms SI, with an explicit energy residual check."""
    diagonal = capacity/dt + sink
    matrix = laplacian + sparse.diags(diagonal)
    # Solve temperature increments to avoid cancellation against the ~300 K bath.
    reference = float(t.mean())
    rhs = capacity/dt*(t-reference) + bath-sink*reference + power
    result, info = cg(matrix, rhs, x0=t-reference, M=sparse.diags(1/matrix.diagonal()), rtol=1e-12, atol=1e-12, maxiter=3000)
    result += reference
    if info or not np.isfinite(result).all():
        raise RuntimeError(f'Thermal solve failed: {info}')
    stored = float(np.dot(capacity,result-t))
    rejected = float(np.sum(sink*result-bath)*dt)
    injected = float(np.sum(power)*dt)
    error = abs(stored+rejected-injected)/max(abs(stored),abs(rejected),abs(injected),1.)
    if error > 1e-6:
        raise RuntimeError(f'Energy balance residual too large: {error}')
    return result,error,stored,rejected,injected


def interior_voxels(mesh, pitch):
    """Classify cell centres by paired vertical intersections with a closed mesh."""
    shape=np.ceil(mesh.extents/pitch).astype(int)
    x,y=np.meshgrid((np.arange(shape[0])+.5)*pitch,(np.arange(shape[1])+.5)*pitch,indexing='ij')
    origins=np.column_stack([x.ravel(),y.ravel(),np.full(x.size,-pitch)])
    z=(np.arange(shape[2])+.5)*pitch
    occupied=np.zeros(tuple(shape),dtype=bool)
    for start in range(0,len(origins),2048):
        batch=origins[start:start+2048]
        hits,rays,_=mesh.ray.intersects_location(batch,np.tile([0.,0.,1.],(len(batch),1)),multiple_hits=True)
        if not len(hits):continue
        order=np.lexsort((hits[:,2],rays));rays=rays[order];heights=hits[order,2]
        unique,first,counts=np.unique(rays,return_index=True,return_counts=True)
        if np.any(counts%2):raise ValueError('Odd ray intersection count; grid classification ambiguous')
        for ray,begin,count in zip(unique,first,counts):
            i,j=divmod(start+int(ray),shape[1])
            occupied[i,j]=np.searchsorted(heights[begin:begin+count],z,side='right')%2==1
    if not occupied.any():raise ValueError('No solid cell centres')
    last=int(np.nonzero(occupied.any(axis=(0,1)))[0][-1])+1
    return occupied[:,:,:last]


def thermal(card_path, sliced, output, pitch, absorption, substeps=None):
    card=load_card(card_path);p=card['published_research_recipe'];a=card['study_assumptions']
    if not 0 < absorption <= 1 or not math.isfinite(absorption) or pitch not in [1.,1.5,2.]:
        raise ValueError('Invalid thermal sensitivity inputs')
    substeps = substeps or a['substeps_per_macro_layer']
    if not isinstance(substeps,int) or not 1 <= substeps <= 32:
        raise ValueError('Invalid temporal resolution')
    upstream=json.loads((sliced/'slicing.json').read_text());surface=Path(upstream['surface_path'])
    if sha(surface)!=upstream['surface_sha256'] or sha(card_path)!=upstream['card_sha256']:
        raise ValueError('Slicing inputs changed')
    with (sliced/'layers.csv').open() as stream: rows=list(csv.DictReader(stream))
    mesh=trimesh.load_mesh(surface,process=True);mesh.apply_translation(-mesh.bounds[0])
    part0=interior_voxels(mesh,pitch)
    base=int(round(a['standoff_mm']/pitch))
    if abs(base*pitch-a['standoff_mm'])>1e-9: raise ValueError('Standoff must align with thermal grid')
    part=np.pad(part0,((0,0),(0,0),(base,0)))
    first=np.argmax(part,axis=2);present=part.any(axis=2)
    support=present[:,:,None] & (np.arange(part.shape[2])[None,None,:] < first[:,:,None])
    occupied=part|support
    cells=np.argwhere(occupied);cells=cells[np.argsort(cells[:,2],kind='stable')]
    grid=np.full(part.shape,-1,dtype=np.int32);grid[tuple(cells.T)]=np.arange(len(cells))
    is_part=part[tuple(cells.T)];fraction=np.where(is_part,1.,a['thermal_support_solid_fraction'])
    dx=pitch/1000;volume=dx**3;rho=2670.
    conductivity,cp=MACRO['material_fields'](np.array([p['plate_temperature_k']]))
    conductivity=float(conductivity[0]);cp=float(cp[0])
    capacity=rho*cp*volume*fraction
    left=[];right=[]
    for axis in range(3):
        s1=[slice(None)]*3;s2=s1.copy();s1[axis]=slice(None,-1);s2[axis]=slice(1,None)
        x,y=grid[tuple(s1)],grid[tuple(s2)];valid=(x>=0)&(y>=0)
        left.extend(x[valid]);right.extend(y[valid])
    left=np.array(left);right=np.array(right)
    conductance=conductivity*dx*2*fraction[left]*fraction[right]/(fraction[left]+fraction[right])
    temperature=np.full(len(cells),p['plate_temperature_k']);peak=temperature.copy()
    height=float(mesh.extents[2]);total_layers=math.ceil((height+a['standoff_mm'])/p['layer_thickness_mm'])
    physical_z=(np.arange(total_layers)+.5)*p['layer_thickness_mm']
    physical_bins=np.minimum(np.floor(physical_z/pitch).astype(int),part.shape[2]-1)
    counts=np.bincount(physical_bins,minlength=part.shape[2])
    energies=np.zeros(part.shape[2]);part_scan_volume=0.
    for row in rows:
        z=float(row['z_mm']);idx=min(int((z+a['standoff_mm'])/pitch),part.shape[2]-1)
        thickness=min(p['layer_thickness_mm'],height-int(row['layer_index'])*p['layer_thickness_mm'])
        v=float(row['part_area_mm2'])*thickness;part_scan_volume+=v
        energies[idx]+=p['power_w']*v/(p['scan_speed_mm_s']*p['hatch_spacing_mm']*p['layer_thickness_mm'])
    support_volume_by_layer=np.bincount(cells[~is_part,2],minlength=part.shape[2])*pitch**3*a['thermal_support_solid_fraction']
    energies+=p['power_w']*support_volume_by_layer/(p['scan_speed_mm_s']*p['hatch_spacing_mm']*p['layer_thickness_mm'])
    output.mkdir(parents=True,exist_ok=False)
    history=[];time=0.;max_error=0.;total_heat=0.;total_rejected=0.;total_stored=0.
    # ponytail: macro-layer averaged heat, not a moving beam; use calibrated local LPBF physics for melt pools.
    for layer in range(part.shape[2]):
        n=int(np.searchsorted(cells[:,2],layer,side='right'))
        if n==0:continue
        links=(left<n)&(right<n);i,j,g=left[links],right[links],conductance[links]
        degree=np.bincount(np.r_[i,j],minlength=n)
        diagonal=np.bincount(np.r_[i,j],weights=np.r_[g,g],minlength=n)
        lap=sparse.csr_matrix((np.r_[diagonal,-g,-g],(np.r_[np.arange(n),i,j],np.r_[np.arange(n),j,i])),shape=(n,n))
        plate=cells[:n,2]==0;exposed=6-degree-plate.astype(int)
        plate_sink=np.where(plate,2*conductivity*dx*fraction[:n],0.)
        duration=energies[layer]/p['power_w']+counts[layer]*a['recoat_seconds_per_layer']
        if duration<=0:raise ValueError('Empty macro-layer schedule')
        fresh=cells[:n,2]==layer;weights=fraction[:n]*fresh
        power=absorption*energies[layer]/duration*weights/weights.sum()
        for step in range(substeps):
            t=temperature[:n];ambient=a['ambient_temperature_k']
            h=a['convection_w_m2_k']+a['emissivity']*5.670374419e-8*(t+ambient)*(t*t+ambient*ambient)
            gas_sink=h*exposed*dx*dx
            sink=plate_sink+gas_sink;bath=plate_sink*p['plate_temperature_k']+gas_sink*ambient
            t,error,stored,rejected,injected=implicit_step(t,capacity[:n],lap,sink,bath,power,duration/substeps)
            temperature[:n]=t;peak[:n]=np.maximum(peak[:n],t)
            max_error=max(max_error,error);total_heat+=injected;total_rejected+=rejected;total_stored+=stored
            time+=duration/substeps
        active_part=is_part[:n]
        history.append({'macro_layer':layer,'physical_layers':int(counts[layer]),'elapsed_s':time,
            'mean_part_temperature_k':float(temperature[:n][active_part].mean()) if active_part.any() else None,
            'max_active_temperature_k':float(temperature[:n].max()),'scan_seconds':float(energies[layer]/p['power_w']),
            'recoat_seconds':float(counts[layer]*a['recoat_seconds_per_layer'])})
        print(f'Layer {layer+1}/{part.shape[2]}: bulk max {temperature[:n].max():.2f} K',flush=True)
    build_temperature=temperature.copy();build_time=time
    for step in range(12):
        t=temperature;ambient=a['ambient_temperature_k']
        h=a['convection_w_m2_k']+a['emissivity']*5.670374419e-8*(t+ambient)*(t*t+ambient*ambient)
        gas_sink=h*exposed*dx*dx;sink=plate_sink+gas_sink;bath=plate_sink*p['plate_temperature_k']+gas_sink*ambient
        temperature,error,stored,rejected,injected=implicit_step(t,capacity,lap,sink,bath,np.zeros(n),a['cooldown_seconds']/12)
        max_error=max(max_error,error);total_rejected+=rejected;total_stored+=stored
    np.savez_compressed(output/'thermal-fields.npz',centres_mm=(cells+.5)*pitch,is_part=is_part,
        peak_temperature_k=peak,build_temperature_k=build_temperature,cooled_temperature_k=temperature)
    save(output/'history.json',history)
    report={'scope':'machine_bound_homogenized_bulk_thermal_screen_not_calibrated_process_prediction',
        'card_sha256':sha(card_path),'surface_sha256':sha(surface),'slice_sha256':sha(sliced/'layers.csv'),
        'script_sha256':sha(Path(__file__)),'pitch_mm':pitch,'substeps_per_macro_layer':substeps,
        'absorptivity':absorption,'nodes':len(cells),'part_voxels':int(is_part.sum()),'voxel_classification':'closed_mesh_vertical_ray_parity_at_cell_centres',
        'voxel_part_volume_mm3':float(is_part.sum()*pitch**3),'mesh_part_volume_mm3':float(mesh.volume),
        'voxel_relative_volume_error':float(is_part.sum()*pitch**3/mesh.volume-1),
        'geometry_volume_error_below_2_percent':bool(abs(is_part.sum()*pitch**3/mesh.volume-1)<.02),
        'slice_integrated_volume_mm3':part_scan_volume,'thermal_support_solid_volume_mm3':float(support_volume_by_layer.sum()),
        'physical_layer_count_with_standoff':total_layers,'build_time_estimate_h':build_time/3600,
        'laser_on_estimate_h':float(energies.sum()/p['power_w']/3600),
        'recoat_estimate_h':float(counts.sum()*a['recoat_seconds_per_layer']/3600),
        'peak_macro_part_temperature_k':float(peak[is_part].max()),
        'end_build_mean_part_temperature_k':float(build_temperature[is_part].mean()),
        'end_build_max_part_temperature_k':float(build_temperature[is_part].max()),
        'after_cooldown_mean_part_temperature_k':float(temperature[is_part].mean()),
        'maximum_relative_step_energy_residual':max_error,'absorbed_laser_energy_j':total_heat,
        'net_heat_rejected_j':total_rejected,'stored_energy_change_j':total_stored,
        'solid_properties':{'rho_kg_m3':rho,'cp_j_kg_k':cp,'conductivity_w_m_k':conductivity},
        'constant_solid_model_below_solidus':bool(peak[is_part].max()<850),
        'melt_pool_simulated':False,'residual_stress_or_warpage_predicted':False,
        'machine_calibrated':False,'manufacturing_authorized':False,'physical_print_executed':False}
    save(output/'thermal-summary.json',report);print(json.dumps(report),flush=True)


def self_test():
    box=trimesh.creation.box(extents=[4,4,4]);box.apply_translation([2,2,2])
    assert interior_voxels(box,1.).sum()==64
    t=np.array([300.]);c=np.array([2.]);lap=sparse.csr_matrix((1,1));sink=np.array([4.]);bath=np.array([1200.]);q=np.array([10.])
    result,error,*_=implicit_step(t,c,lap,sink,bath,q,.5)
    assert np.allclose(result,[301.25]) and error<1e-9
    lap=sparse.csr_matrix([[3.,-3.],[-3.,3.]])
    result,error,*_=implicit_step(np.array([400.,300.]),np.ones(2),lap,np.zeros(2),np.zeros(2),np.zeros(2),.1)
    assert np.isclose(result.sum(),700) and 300<result[1]<result[0]<400 and error<1e-9
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp:
        card_path=Path(tmp)/'card.json'
        card=json.loads((Path(__file__).parents[1]/'zrapid-print-process.json').read_text())
        save(card_path,card);load_card(card_path)
        card['published_research_recipe']['power_w']=501
        save(card_path,card)
        try:load_card(card_path)
        except ValueError:pass
        else:raise AssertionError('Out-of-range machine power accepted')
    print('Voxel volume, implicit analytic, energy conservation and machine-boundary checks passed')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['slice','thermal','self-test'])
    parser.add_argument('--card',type=Path,default=Path(__file__).parents[1]/'zrapid-print-process.json')
    parser.add_argument('--geometry',type=Path);parser.add_argument('--analysis',type=Path);parser.add_argument('--sliced',type=Path)
    parser.add_argument('--output',type=Path);parser.add_argument('--pitch',type=float,default=2.)
    parser.add_argument('--absorptivity',type=float,default=.35);parser.add_argument('--substeps',type=int)
    args=parser.parse_args()
    if args.action=='self-test':self_test()
    elif args.action=='slice':slice_part(args.card,args.geometry,args.analysis,args.output)
    else:thermal(args.card,args.sliced,args.output,args.pitch,args.absorptivity,args.substeps)
