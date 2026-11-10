"""Canonical curved lofts for an independently authored assumed structural cell.

Each loft is a tensor Catmull-Rom surface, equivalently a joined bicubic Bezier
patch network. Preview tessellation thickens those same surfaces along their
normals. No F1 geometry or source scan is consumed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import numpy as np

HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def catmull(points, value, closed=False):
    p=np.asarray(points,dtype=float);segments=len(p) if closed else len(p)-1
    value=float(value)
    if closed:value%=segments
    else:value=min(max(value,0),segments)
    i=min(int(value),segments-1);t=value-i
    get=lambda k:p[k%len(p)] if closed else p[min(max(k,0),len(p)-1)]
    a,b,c,d=get(i-1),get(i),get(i+1),get(i+2)
    return .5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)

def evaluate(component,u,v):
    rows=np.array([catmull(row,v,component['closed_profile']) for row in component['sections_mm']])
    return catmull(rows,u)

def tangent(component,u,v,axis):
    eps=1e-5;limits=[len(component['sections_mm'])-1,len(component['sections_mm'][0])-int(not component['closed_profile'])]
    a=[u,v];b=[u,v];a[axis]-=eps;b[axis]+=eps
    if axis==0 or not component['closed_profile']:
        a[axis]=max(0,a[axis]);b[axis]=min(limits[axis],b[axis])
    return (evaluate(component,*b)-evaluate(component,*a))/(b[axis]-a[axis])

def normal(component,u,v):
    n=np.cross(tangent(component,u,v,0),tangent(component,u,v,1));size=np.linalg.norm(n)
    if size<1e-9:raise ValueError('Degenerate canonical loft normal: '+component['name'])
    return n/size

def loft(name,component,sections,thickness,closed=False,fibre='projected_global_X'):
    return {'name':name,'component':component,'scope':'structural_cell','type':'tensor_catmull_rom_loft','sections_mm':np.asarray(sections).tolist(),'closed_profile':closed,'thickness_mm':thickness,'fibre_reference_method':fibre}

def tube(name,centres,half_axes,thickness,reference):
    centres=np.asarray(centres,float);a=np.asarray(reference,float);sections=[]
    for i,c in enumerate(centres):
        t=centres[min(i+1,len(centres)-1)]-centres[max(i-1,0)];t/=np.linalg.norm(t);e1=a-t*np.dot(a,t);e1/=np.linalg.norm(e1);e2=np.cross(t,e1)
        sections.append([c+half_axes[0]*math.cos(2*math.pi*j/12)*e1+half_axes[1]*math.sin(2*math.pi*j/12)*e2 for j in range(12)])
    d=loft(name,'upper_structure',sections,thickness,True,'canonical_longitudinal_tangent');d['centreline_mm']=centres.tolist();return d

def rounded_box(name, category, centres, half_axes, thickness, reference):
    centres = np.asarray(centres, float)
    reference = np.asarray(reference, float)
    sections = []
    a, b = half_axes
    r = min(a, b) * .32
    profile = [(-a, -b+r), (-a+r, -b), (a-r, -b), (a, -b+r),
               (a, b-r), (a-r, b), (-a+r, b), (-a, b-r)]
    for i, centre in enumerate(centres):
        direction = centres[min(i+1, len(centres)-1)] - centres[max(i-1, 0)]
        direction /= np.linalg.norm(direction)
        e1 = reference - direction*np.dot(reference, direction)
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(direction, e1)
        sections.append([centre+x*e1+y*e2 for x, y in profile])
    result = loft(name, category, sections, thickness, True, 'canonical_longitudinal_tangent')
    result['centreline_mm'] = centres.tolist()
    return result


def cap(parent, end, name=None):
    index = 0 if end == 'start' else -1
    profile = np.asarray(parent['sections_mm'][index], float)
    neighbour = np.asarray(parent['sections_mm'][1 if end == 'start' else -2], float)
    outward = profile.mean(axis=0) - neighbour.mean(axis=0)
    candidates = [np.cross(profile[k]-profile[0], profile[k+1]-profile[0])
                  for k in range(1, len(profile)-1)]
    direction = max(candidates, key=np.linalg.norm)
    direction /= np.linalg.norm(direction)
    if np.dot(direction, outward) < 0:
        direction = -direction
    return {'name': name or parent['name']+'_'+end+'_closure',
            'component': 'integral_end_closures', 'scope': 'structural_cell',
            'type': 'planar_profile_cap', 'profile_mm': profile.tolist(),
            'normal_direction': direction.tolist(), 'thickness_mm': parent['thickness_mm'],
            'boundary_loft_name': parent['name'], 'boundary_end': end,
            'fibre_reference_method': 'projected_global_X'}


def parameter_at_x(component, x):
    low, high = 0., float(len(component['sections_mm'])-1)
    for _ in range(48):
        middle = (low+high)/2
        if evaluate(component, middle, 0)[0] < x:
            low = middle
        else:
            high = middle
    return (low+high)/2


def centreline_at_x(centres, x):
    low, high = 0., float(len(centres)-1)
    for _ in range(48):
        middle = (low+high)/2
        if catmull(centres, middle)[0] < x:
            low = middle
        else:
            high = middle
    return catmull(centres, (low+high)/2)


def build(parameters):
    d = parameters
    if d['status'] != 'assumed' or d['units'] != 'mm':
        raise ValueError('Require explicit hypothetical millimetre design inputs')
    xs, f, width = d['stations_x_mm'], d['floor_base_z_mm'], d['inner_half_width_mm']
    tops, roof, wall = d['sill_top_z_mm'], d['tunnel_roof_z_mm'], d['wall_mm']
    if not all(len(d[key]) == len(xs) for key in
               ('floor_base_z_mm', 'inner_half_width_mm', 'sill_top_z_mm',
                'tunnel_roof_z_mm', 'sill_outer_width_mm', 'sill_bottom_z_mm')):
        raise ValueError('Station profiles must share their authored X stations')
    components, joins = [], []
    def add(component):
        components.append(component)
        return component
    def join(a, b, label=None):
        joins.append({'id': label or a+'__'+b, 'component_a': a,
                      'component_b': b, 'minimum_shared_edges': 1})
    ys = [-1, -.9, -.6, -.32, -.24, -.19, -.12, 0, .12, .19, .24, .32, .6, .9, 1]
    floor = []
    for i, x in enumerate(xs):
        z = [f[i]+25, f[i]-5, f[i]-20, f[i]+10, f[i]+35,
             roof[i]-45, roof[i]-10, roof[i], roof[i]-10,
             roof[i]-45, f[i]+35, f[i]+10, f[i]-20, f[i]-5, f[i]+25]
        floor.append([[x, y*width[i], zz] for y, zz in zip(ys, z)])
    # Cropped intervals retain the complete interpolation context. Their exact
    # shared boundary curves and tangents are the same as the full floor loft.
    full_floor = loft('floor_interpolation_context', 'floor', floor, wall)
    for name, interval in [('floor_bay_right', [0, 3]),
                           ('integrated_tunnel', [3, 11]),
                           ('floor_bay_left', [11, 14])]:
        surface = loft(name, 'floor_bays' if 'bay' in name else 'tunnel', floor, wall)
        surface['v_range'] = interval
        add(surface)
    join('floor_bay_right', 'integrated_tunnel')
    join('floor_bay_left', 'integrated_tunnel')
    closure = [[row[3], [x, -.32*width[i], f[i]-55],
                [x, .32*width[i], f[i]-55], row[11]]
               for i, (x, row) in enumerate(zip(xs, floor))]
    add(loft('tunnel_lower_return', 'tunnel', closure, wall))
    join('tunnel_lower_return', 'integrated_tunnel')
    for side, suffix in [(-1, 'right'), (1, 'left')]:
        sections = []
        for i, x in enumerate(xs):
            y, t, outer, bottom = width[i], tops[i], d['sill_outer_width_mm'][i], d['sill_bottom_z_mm'][i]
            profile = [[y, f[i]+25], [y-25, t-100], [y-25, t-70],
                       [y+10, t-70], [y+28, t-35], [y+55, t-8],
                       [y+outer-35, t], [y+outer, t-25],
                       [y+outer, bottom+35], [y+outer-35, bottom],
                       [y+25, bottom], [y, bottom+30]]
            sections.append([[x, side*yy, zz] for yy, zz in profile])
        sill = add(loft('sill_'+suffix, 'sills_with_integral_door_returns', sections, wall, True))
        join(sill['name'], 'floor_bay_'+suffix)
        for end in ('start', 'end'):
            closure_part = add(cap(sill, end))
            join(closure_part['name'], sill['name'])
    boundaries = {}
    for rear, name in [(False, 'sculpted_scuttle'), (True, 'rear_shoulders_bulkhead')]:
        bottom = np.asarray(floor[-1 if rear else 0])
        upper = []
        for j, (_, y, z) in enumerate(bottom):
            fraction = abs(ys[j])
            height = (640+75*math.exp(-((fraction-.68)/.24)**2) if rear
                      else 675-45*fraction*fraction+20*math.exp(-(fraction/.3)**2))
            upper.append([2210+70*(1-fraction*fraction) if rear else -145+40*fraction*fraction,
                          ys[j]*d['rear_upper_half_width_mm' if rear else 'scuttle_upper_half_width_mm'], height])
        upper = np.asarray(upper)
        middle = .5*(bottom+upper)
        middle[:, 0] += -25 if rear else 45
        panel = add(loft(name, 'rear_structure' if rear else 'scuttle', [bottom, middle, upper], wall))
        boundaries['rear' if rear else 'front'] = panel
        for floor_name in ('floor_bay_right', 'integrated_tunnel', 'floor_bay_left'):
            join(name, floor_name)
        # A real finite-depth hollow crossbeam follows the shaped panel's
        # upper boundary. Its upper-front edge is that exact same curve.
        depth = -d['bulkhead_return_depth_mm'] if rear else d['bulkhead_return_depth_mm']
        height = d['bulkhead_return_height_mm']
        offsets = [(0, 0), (depth*.25, 0), (depth*.80, 0), (depth, -height*.20),
                   (depth, -height*.80), (depth*.80, -height),
                   (depth*.20, -height), (0, -height*.80), (0, -height*.20)]
        sections = [[[p[0]+dx, p[1], p[2]+dz] for dx, dz in offsets] for p in upper]
        beam = add(loft('rear_shoulder_return' if rear else 'scuttle_return',
                        'bulkhead_closed_returns', sections, wall, True,
                        'canonical_longitudinal_tangent'))
        join(beam['name'], name)
        for end in ('start', 'end'):
            end_part = add(cap(beam, end))
            join(end_part['name'], beam['name'])
        for side, suffix, v in [(-1, 'right', 0), (1, 'left', 14)]:
            # Columns run along the actual side of the bulkhead into the
            # closed sill and crossbeam. These are structure, not bolt seats.
            points = [evaluate(panel, u, v) for u in (0, .5, 1, 1.5, 2)]
            points = [p + np.array([-30 if rear else 30, 0, -25]) for p in points]
            points[-1] = upper[v] + np.array([depth*.5, 0, -height*.5])
            foot = add(rounded_box(('rear_pillar_foot_' if rear else 'A_pillar_foot_')+suffix,
                                   'integral_pillar_feet', points, [48, 48 if rear else 34], wall, [1, 0, 0]))
            join(foot['name'], name)
            join(foot['name'], beam['name'])
            join(foot['name'], 'sill_'+suffix+'_'+('end' if rear else 'start')+'_closure')
    # Four closed support regions bridge each seat bay between sill and tunnel.
    # Their lower walls cross the literal floor; no seat or belt bolt is inferred.
    for x in d['seat_support_stations_mm']:
        u = xs.index(x)
        for suffix, interval in [('right', (0, 3)), ('left', (11, 14))]:
            centres = [evaluate(full_floor, u, v)+np.array([0, 0, 25])
                       for v in np.linspace(interval[0], interval[1], 5)]
            beam = add(rounded_box('seat_support_'+suffix+'_'+str(x), 'seat_support_regions',
                                   centres, [35, d['seat_support_height_mm']/2], wall, [1, 0, 0]))
            join(beam['name'], 'floor_bay_'+suffix)
            join(beam['name'], 'sill_'+suffix)
            join(beam['name'], 'integrated_tunnel')
    sides = {}
    for side, suffix in [(-1, 'right'), (1, 'left')]:
        front = evaluate(boundaries['front'], 2, 13.7 if side > 0 else .3)
        rear = evaluate(boundaries['rear'], 2, 13 if side > 0 else 1)
        front += [d['bulkhead_return_depth_mm']*.5, 0, -55]
        rear += [-d['bulkhead_return_depth_mm']*.35, 0, -55]
        middle = np.asarray(d['upper_side_intermediate_mm'], float)
        middle[:, 1] *= side
        centres = np.vstack([front, middle, rear])
        sides[suffix] = centres
        rib = add(tube('upper_side_'+suffix, centres, d['upper_rib_half_axes_mm'],
                       d['upper_rib_wall_mm'], [0, 1, 0]))
        join(rib['name'], 'scuttle_return')
        join(rib['name'], 'rear_shoulder_return')
    # Header ends at the side-rib centres, without extending an outer stub.
    left, right = centreline_at_x(sides['left'], 540), centreline_at_x(sides['right'], 540)
    header = [right, [540, -.5*left[1], left[2]+6],
              [540, 0, left[2]+8], [540, .5*left[1], left[2]+6], left]
    add(tube('windscreen_header', header, [20, 21], d['upper_rib_wall_mm'], [1, 0, 0]))
    join('windscreen_header', 'upper_side_left')
    join('windscreen_header', 'upper_side_right')
    xb = 1500
    roof_point = centreline_at_x(sides['left'], xb)
    sill_left = next(c for c in components if c['name'] == 'sill_left')
    sill_u = parameter_at_x(sill_left, xb)
    sill_top = evaluate(sill_left, sill_u, 5)
    foot_y, foot_z = sill_top[1], sill_top[2]-35
    ry, rz = roof_point[1], roof_point[2]
    hoop = [[xb, -foot_y, foot_z], [xb, -ry-10, rz-180],
            [xb, -ry, rz-25], [xb, -.75*ry, rz-10], [xb, -.35*ry, rz-5],
            [xb, 0, rz-5], [xb, .35*ry, rz-5], [xb, .75*ry, rz-10],
            [xb, ry, rz-25], [xb, ry+10, rz-180], [xb, foot_y, foot_z]]
    add(tube('B_roof_hoop', hoop, [26, 30], d['upper_rib_wall_mm'], [1, 0, 0]))
    for suffix in ('left', 'right'):
        join('B_roof_hoop', 'sill_'+suffix)
        join('B_roof_hoop', 'upper_side_'+suffix)
    for side, suffix in [(-1, 'right'), (1, 'left')]:
        start = centreline_at_x(sides[suffix], 1710)
        end = evaluate(boundaries['rear'], 2, 12 if side > 0 else 2)
        end += [-35, 0, -55]
        centre = .5*(start+end)+np.array([20, 0, 0])
        add(tube('rear_brace_'+suffix, [start, centre, end], [21, 25],
                 d['upper_rib_wall_mm'], [0, 1, 0]))
        join('rear_brace_'+suffix, 'upper_side_'+suffix)
        join('rear_brace_'+suffix, 'rear_shoulder_return')
    return {'study_id': d['study_id'], 'units': 'mm', 'status': 'assumed',
            'parameter_sha256': digest(HERE/'parameters.json'),
            'source_builder_sha256': digest(Path(__file__)), 'components': components,
            'upper_structure_components': [c['name'] for c in components if c['component'] == 'upper_structure'],
            'join_contract': joins,
            'fixture_contract': {'clamp_component_ends': [
                {'component': name, 'end': 'start'} for name in
                ('floor_bay_right', 'integrated_tunnel', 'floor_bay_left', 'sill_left', 'sill_right')],
                'torsion_component_ends': {'TORSION_LEFT': [{'component': 'sill_left', 'end': 'end'}],
                                           'TORSION_RIGHT': [{'component': 'sill_right', 'end': 'end'}]},
                'bending_components': ['floor_bay_left', 'floor_bay_right']},
            'admission': 'Unadmitted authored shape proposal until raw views, packaging, physical wall and complete-edge junction audits pass.',
            'physical_interfaces_admitted': False, 'manufacturing_authorized': False}


def sample_cap(component, per_segment):
    direction = np.asarray(component['normal_direction'], float)
    direction /= np.linalg.norm(direction)
    profile = component['profile_mm']
    points = np.array([catmull(profile, v, True) for v in
                       np.linspace(0, len(profile), len(profile)*per_segment, endpoint=False)])
    origin = points[0]
    e1 = points[1]-origin
    e1 -= np.dot(e1, direction)*direction
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(direction, e1)
    if np.max(np.abs((points-origin)@direction)) > 1e-5:
        raise ValueError('Nonplanar closure profile: '+component['name'])
    xy = np.column_stack([(points-origin)@e1, (points-origin)@e2])
    area = sum(np.cross(a, b) for a, b in zip(xy, np.roll(xy, -1, axis=0)))
    if area < 0:
        points, xy = points[::-1].copy(), xy[::-1].copy()
    remaining, faces = list(range(len(points))), []
    cross2 = lambda a, b: a[0]*b[1]-a[1]*b[0]
    while len(remaining) > 3:
        for k, b in enumerate(remaining):
            a, c = remaining[k-1], remaining[(k+1) % len(remaining)]
            if cross2(xy[b]-xy[a], xy[c]-xy[b]) <= 1e-10:
                continue
            interior = False
            for q in remaining:
                if q in (a, b, c):
                    continue
                tests = [cross2(xy[j]-xy[i], xy[q]-xy[i]) for i, j in ((a, b), (b, c), (c, a))]
                if min(tests) >= -1e-10:
                    interior = True
                    break
            if not interior:
                faces.append([a, b, c])
                remaining.pop(k)
                break
        else:
            raise ValueError('Closure polygon cannot be triangulated without repair: '+component['name'])
    faces.append(remaining)
    return points, np.asarray(faces, int), np.tile(direction, (len(points), 1))


def sample_surface(component, per_segment=5):
    if component['type'] == 'planar_profile_cap':
        return sample_cap(component, per_segment)
    nu = len(component['sections_mm'])-1
    nv = len(component['sections_mm'][0])-int(not component['closed_profile'])
    low, high = component.get('v_range', [0, nv])
    closed = component['closed_profile']
    us = np.linspace(0, nu, nu*per_segment+1)
    vs = np.linspace(low, high, int((high-low)*per_segment)+(0 if closed else 1), endpoint=not closed)
    vertices, normals = [], []
    for u in us:
        for v in vs:
            vertices.append(evaluate(component, u, v))
            normals.append(normal(component, u, v))
    faces, count = [], len(vs)
    for i in range(len(us)-1):
        for j in range(count if closed else count-1):
            k = (j+1) % count
            a, b, c, d = i*count+j, (i+1)*count+j, (i+1)*count+k, i*count+k
            faces.extend([[a, b, c], [a, c, d]])
    return np.asarray(vertices), np.asarray(faces, int), np.asarray(normals)


def thickened_preview(component,resolution):
    v,f,n=sample_surface(component,resolution);count=len(v);points=np.vstack([v+component['thickness_mm']/2*n,v-component['thickness_mm']/2*n]);faces=f.tolist()+[(row[::-1]+count).tolist() for row in f];edges={}
    for row in f:
        for a,b in zip(row,np.roll(row,-1)):
            key=tuple(sorted([int(a),int(b)]));edges.setdefault(key,[]).append([int(a),int(b)])
    for incidents in edges.values():
        if len(incidents)==1:
            a,b=incidents[0];faces.extend([[b,a,a+count],[b,a+count,b+count]])
    return {'name':component['name'],'scope':component['scope'],'vertices_mm':points.tolist(),'triangles':faces,'physical_thickness_mm':component['thickness_mm']}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--preview-segments',type=int,default=4);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);d=build(json.loads((HERE/'parameters.json').read_text()));(a.output/'model.json').write_text(json.dumps(d,indent=2)+'\n');display={'geometry_source_kind':'analytic_loft_preview_not_BRep_or_Pico_yet','components':[thickened_preview(c,a.preview_segments) for c in d['components']],'canonical_model_sha256':digest(a.output/'model.json'),'parameter_sha256':d['parameter_sha256'],'scope':'Physical-thickness analytic loft/cap preview; component overlaps retained before native Boolean/fragment audit. No FEA admission.'};(a.output/'display-preview.json').write_text(json.dumps(display,separators=(',',':'))+'\n');print(json.dumps({'components':len(d['components']),'triangles':sum(len(c['triangles']) for c in display['components']),'output':str(a.output)}))
if __name__=='__main__':main()
