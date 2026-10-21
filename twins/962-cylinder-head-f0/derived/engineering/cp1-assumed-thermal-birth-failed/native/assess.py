"""Independent field, Gaussian power and nonlinear-enthalpy birth verification."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_value(card, point, time):
    radii = card['radii_m']
    center = [x + time*v for x, v in zip(card['source_start_m'], card['velocity_m_s'])]
    exponent = sum(3*((x-c)/r)**2 for x,c,r in zip(point, center, radii))
    amplitude = 6*math.sqrt(3)*card['laser_power_W']*card['efficiency']*card['factor']/(math.prod(radii)*math.pi**1.5)
    return amplitude*math.exp(-exponent)


def box_power(card, time, xmax):
    center = [x + time*v for x, v in zip(card['source_start_m'], card['velocity_m_s'])]
    bounds = [card['bounds_m'][0], [xmax, *card['bounds_m'][1][1:]]]
    fractions = [0.5*(math.erf(math.sqrt(3)*(b-c)/r)-math.erf(math.sqrt(3)*(a-c)/r))
                 for a,b,c,r in zip(*bounds, center, card['radii_m'])]
    return 2*card['factor']*card['efficiency']*card['laser_power_W']*math.prod(fractions)


def incoming_energy(card, time):
    def simpson(a, b, xmax):
        if b <= a:
            return 0.0
        n = 1024
        h = (b-a)/n
        return h/3*sum((1 if i in (0,n) else 4 if i%2 else 2)*box_power(card,a+i*h,xmax)
                       for i in range(n+1))
    birth = card['birth_time_s']
    return simpson(0,min(time,birth),card['old_region_xmax_m']) + simpson(birth,time,card['bounds_m'][1][0])


def enthalpy_density(card, temperature):
    delta = temperature-card['enthalpy_reference_K']
    return card['density_kg_m3']*(card['cp_at_300K_J_kgK']*delta + 0.5*card['cp_slope_J_kgK2']*delta**2)


def csv_rows(path):
    with Path(path).open(newline='') as stream:
        rows = [{key:float(value) for key,value in row.items()} for row in csv.DictReader(stream)]
    if not rows or any(not math.isfinite(value) for row in rows for value in row.values()):
        raise ValueError('Missing or nonfinite native field')
    return rows


def nodal_field(path):
    rows = csv_rows(path)
    field = {tuple(round(row[k],9) for k in ('x','y','z')):row['temperature'] for row in rows}
    if len(field) != len(rows):
        raise ValueError('Duplicate nodal coordinate')
    return field


def grid(card, xmax):
    upper=card['bounds_m'][1]
    h=[length/n for length,n in zip(upper,card['mesh_intervals'])]
    nx=round(xmax/h[0])
    offsets=list(itertools.product((0,1), repeat=3))
    for index in itertools.product(range(nx),range(card['mesh_intervals'][1]),range(card['mesh_intervals'][2])):
        lo=[i*d for i,d in zip(index,h)]
        corners=[tuple(round(x+o*d,9) for x,o,d in zip(lo,offset,h)) for offset in offsets]
        yield lo,h,corners


def cell_values(values):
    offsets=list(itertools.product((0,1),repeat=3))
    for point in itertools.product((-1/math.sqrt(3),1/math.sqrt(3)), repeat=3):
        weights=[math.prod((1+(2*o-1)*p)/2 for o,p in zip(offset,point)) for offset in offsets]
        yield sum(t*w for t,w in zip(values,weights))


def integrals(card, field, xmax, previous=None):
    energy=0.0
    square_increment=0.0
    for lo,h,corners in grid(card,xmax):
        values=[field[c] for c in corners]
        weight=math.prod(h)/8
        if previous is None:
            for temperature in cell_values(values):
                energy += weight*enthalpy_density(card,temperature)
        else:
            changes=[field[c]-previous[c] for c in corners]
            for delta in cell_values(changes):
                square_increment += weight*delta**2
    return square_increment if previous is not None else energy


def gaussian_cell_average(card, lo, h, time):
    total=0.0
    for point in itertools.product((-1/math.sqrt(3),1/math.sqrt(3)),repeat=3):
        physical=[x+d*(1+p)/2 for x,d,p in zip(lo,h,point)]
        total += source_value(card,physical,time)/8
    return total


def centered_enthalpy_increment(card, end, begin, xmax):
    """Exact HEX8 integral form for constant cp; avoid subtracting inventories."""
    if card['cp_slope_J_kgK2'] != 0:
        raise ValueError('This centered successor requires constant cp')
    capacity = card['density_kg_m3']*card['cp_at_300K_J_kgK']
    return capacity*math.fsum(math.prod(h)/8*math.fsum(end[p]-begin[p] for p in corners)
                              for lo,h,corners in grid(card,xmax))


def assess(directory, contract_path):
    directory=Path(directory)
    contract=json.loads(Path(contract_path).read_text())
    card=json.loads((directory/'card.json').read_text())
    receipt=json.loads((directory/'native-execution.json').read_text())
    if (card.get('id')!='cp1-assumed-thermal-birth-sensitivity-001' or card['cp_slope_J_kgK2']!=0
            or card['density_kg_m3']!=2700 or card['cp_at_300K_J_kgK']!=900
            or card['k_at_300K_W_mK']!=187 or card['k_slope_W_mK2']!=0):
        raise ValueError('Only the separately frozen assumed constant thermal card is supported')
    if card['classification']!='HYPOTHETICAL_SOFTWARE_VERIFICATION_ONLY':
        raise ValueError('Physical material claims are prohibited for this witness')
    if sha(contract_path)!=receipt['input_sha256']['frozen-contract.json'] or sha(directory/'card.json')!=contract['card_sha256']:
        raise ValueError('Native execution is not bound to this predeclared contract')
    for name,digest in receipt['artifact_sha256'].items():
        if Path(name).name!=name or sha(directory/name)!=digest:
            raise ValueError('Changed native artifact: '+name)
    for name,digest in receipt['input_sha256'].items():
        if sha(directory/name)!=digest:
            raise ValueError('Changed native input: '+name)
    if not (receipt['returncode']==0 and receipt['binary_unchanged'] and receipt['inputs_unchanged'] and
            receipt['binary_sha256']==card['native_binary_sha256'] and receipt['wall_seconds']<=100):
        raise ValueError('Native execution rejected')
    if receipt['input_sha256']['thermal-birth.i']!=contract['input_sha256']['thermal-birth.i']:
        raise ValueError('Native input differs from the predeclared source')
    level=receipt['level']
    if receipt['input_sha256']['time-level.i']!=contract['level_input_sha256'][str(level)]:
        raise ValueError('Time refinement differs from the predeclared level')
    dt=card['time_steps_s'][level]
    count=round(card['end_time_s']/dt)
    log=(directory/'native.log').read_bytes()
    if log.count(b'Solve Converged!')!=count:
        raise ValueError('Incomplete equilibrium history')
    tol=card['predeclared_tolerances']
    checks=[]
    def check(name,error,limit,step):
        checks.append({'step':step,'name':name,'error':error,'absolute_tolerance':limit,
                       'pass':math.isfinite(error) and abs(error)<=limit})
    required={'thermal_end_0000.csv'}
    for step in range(1,count+1):
        required.update({f'thermal_{name}_{step:04d}.csv' for name in ('begin','end','properties')})
    if not required.issubset(receipt['artifact_sha256']):
        raise ValueError('An assessed field is not bound to native capture')
    initial=nodal_field(directory/'thermal_end_0000.csv')
    check('initial_temperature',max(abs(t-card['initial_temperature_K']) for t in initial.values()),tol['node_history_K'],0)
    oldmax=card['old_region_xmax_m']
    e0=integrals(card,initial,oldmax)
    previous=initial
    birth_energy=0.0
    continuous=[]
    thermal_increments=[]
    traces=[]
    birth_step=round(card['birth_time_s']/dt)
    for step in range(1,count+1):
        time=step*dt
        xmax=oldmax if step<birth_step else card['bounds_m'][1][0]
        begin=nodal_field(directory/f'thermal_begin_{step:04d}.csv')
        end=nodal_field(directory/f'thermal_end_{step:04d}.csv')
        expected_nodes=(round(xmax/(card['bounds_m'][1][0]/card['mesh_intervals'][0]))+1)*(card['mesh_intervals'][1]+1)*(card['mesh_intervals'][2]+1)
        check('active_node_count',len(end)-expected_nodes,0,step)
        if set(begin)!=set(end) or not set(previous).issubset(begin):
            raise ValueError('Activation coordinate/DOF mapping changed unexpectedly')
        check('existing_nodal_history',max(abs(begin[p]-value) for p,value in previous.items()),tol['node_history_K'],step)
        added=set(begin)-set(previous)
        if step==birth_step:
            check('new_node_count',len(added)-(expected_nodes-len(previous)),0,step)
            check('new_node_birth_temperature',max(abs(begin[p]-card['birth_temperature_K']) for p in added),tol['node_history_K'],step)
            # Extend only new nodes; shared interface values remain the old field.
            declared=dict(previous)
            declared.update({p:card['birth_temperature_K'] for p in added})
            birth_energy=integrals(card,declared,xmax)-integrals(card,previous,oldmax)
        elif added:
            raise ValueError('Unexpected node birth')
        if min(end.values())<tol['temperature_lower_K'] or max(end.values())>tol['temperature_upper_K']:
            raise ValueError('Temperature left the predeclared synthetic domain')
        properties=csv_rows(directory/f'thermal_properties_{step:04d}.csv')
        observed={tuple(round(row[k],9) for k in ('x','y','z')):row for row in properties}
        qh=0.0
        for lo,h,corners in grid(card,xmax):
            center=tuple(round(x+d/2,9) for x,d in zip(lo,h))
            row=observed[center]
            mean=sum(end[p] for p in corners)/8
            check('k_T_element_average',row['k_seen']-(card['k_at_300K_W_mK']+card['k_slope_W_mK2']*(mean-300)),tol['material_property_absolute'],step)
            check('cp_T_element_average',row['cp_seen']-(card['cp_at_300K_J_kgK']+card['cp_slope_J_kgK2']*(mean-300)),tol['material_property_absolute'],step)
            q=gaussian_cell_average(card,lo,h,time)
            check('moving_source_element_average',(row['q_seen']-q)/max(q,1e-12),tol['source_cell_average_relative'],step)
            qh += q*math.prod(h)
        power=box_power(card,time,xmax)
        check('finite_box_gaussian_power',(qh-power)/power,tol['finite_box_power_relative'],step)
        delta_h=centered_enthalpy_increment(card,end,begin,xmax)
        thermal_increments.append(delta_h)
        cumulative_heat=math.fsum(thermal_increments)
        ee=e0+birth_energy+cumulative_heat  # reported inventory only; not subtracted in acceptance
        correction=0.5*card['density_kg_m3']*card['cp_slope_J_kgK2']*integrals(card,end,xmax,begin)
        check('nonlinear_BE_enthalpy_identity',delta_h-dt*qh+correction,tol['corrected_step_energy_absolute_J'],step)
        incoming=incoming_energy(card,time)
        defect=cumulative_heat-incoming
        relative=defect/max(abs(incoming),1e-12)
        continuous.append(abs(relative))
        traces.append({'step':step,'time_s':time,'active_volume_m3':xmax,'enthalpy_J':ee,'birth_enthalpy_J':birth_energy,
                       'centered_step_enthalpy_increment_J':delta_h,'cumulative_centered_heat_response_J':cumulative_heat,
                       'continuous_source_energy_J':incoming,'continuous_energy_error_J':defect,'relative_continuous_energy_error':relative,
                       'finite_box_power_W':power,'quadrature_power_W':qh,'BE_capacity_correction_J':correction,
                       'temperature_min_K':min(end.values()),'temperature_max_K':max(end.values())})
        previous=end
    check('nonuniform_final_temperature',min(0,max(previous.values())-min(previous.values())-tol['minimum_final_temperature_range_K']),0,count)
    if level==len(card['time_steps_s'])-1:
        check('finest_continuous_energy_error',max(continuous),tol['finest_continuous_energy_relative'],count)
    failed=[c for c in checks if not c['pass']]
    return {'passed':not failed,'classification':card['classification'],'level':level,'dt_s':dt,'native_steps':count,
            'checks_count':len(checks),'failed_checks':failed,'max_error_by_check':{name:max(abs(c['error']) for c in checks if c['name']==name) for name in {c['name'] for c in checks}},
            'max_continuous_relative_energy_error':max(continuous),'traces':traces,
            'native_receipt_sha256':sha(directory/'native-execution.json'),'frozen_contract_sha256':sha(contract_path),
            'assessor_sha256':sha(__file__),'energy_normalization':'Centered constant-cp increments; continuous error relative to integrated source energy, excluding initial/birth inventory.',
            'scope':'Assumed CP1-like synthetic thermal/source/activation sensitivity only; no matched material/process, head, mechanics, LPBF or manufacturing qualification.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Assessment output must be new')
    result=assess(args.directory,args.contract)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('passed','level','dt_s','checks_count','failed_checks','max_continuous_relative_energy_error')}))
    raise SystemExit(0 if result['passed'] else 1)
