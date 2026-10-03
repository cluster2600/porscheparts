#!/usr/bin/env python3
"""Prepare new fixed-interface rotating-mode and uncalibrated eigenstrain studies.

Only existing original parametric decks are supported. No private scan,
process-qualified material card, physical attachment or release is inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_mesh(text):
    nodes, elements, mode = {}, {}, None
    for line in text.splitlines():
        upper = line.upper().strip()
        if upper.startswith('*'):
            compact = upper.replace(' ', '')
            element_type = next((field.split('=',1)[1] for field in compact.split(',')[1:] if field.startswith('TYPE=')),None)
            if compact.startswith('*ELEMENT,') and element_type != 'C3D10':
                raise ValueError('Only full-integration C3D10 tetrahedra are supported')
            mode = 'node' if upper == '*NODE' else 'element' if compact.startswith('*ELEMENT,') else None
        elif mode and line.strip():
            fields = [v.strip() for v in line.split(',')]
            if mode == 'node':
                nodes[int(fields[0])] = np.array(list(map(float, fields[1:4])))
            elif mode == 'element':
                if len(fields) != 11:
                    raise ValueError('Only one-line ten-node tetrahedra are supported')
                elements[int(fields[0])] = list(map(int, fields[1:]))
    if not nodes or not elements or any(n not in nodes for e in elements.values() for n in e):
        raise ValueError('Complete C3D10 mesh required')
    return nodes, elements


def prepare_modes(source, output, speeds, modes=12):
    text = source.read_text()
    nodes, elements = parse_mesh(text)
    head = text[:text.upper().index('*STEP')]
    if '*BOUNDARY' not in head or '*DENSITY' not in head:
        raise ValueError('Restrained elastic deck with density required')
    if not 1 <= modes <= 30 or any(not math.isfinite(v) or v < 0 for v in speeds):
        raise ValueError('Finite nonnegative speeds and 1..30 modes required')
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for rpm in speeds:
        case = output / f'rpm-{rpm:g}'
        case.mkdir()
        body = head
        if rpm:
            body += ('*STEP,NLGEOM,INC=100\n*STATIC\n0.25,1.,1e-5,0.25\n'
                     f'*DLOAD\nROTOR,CENTRIF,{(rpm*math.pi/30)**2:.16g},0,0,0,0,0,1\n'
                     '*NODE FILE\nU\n*EL FILE\nS\n*END STEP\n')
        body += ('*STEP' + (',PERTURBATION' if rpm else '') + '\n'
                 f'*FREQUENCY,STORAGE=YES\n{modes}\n*NODE FILE\nU\n*END STEP\n')
        if rpm:
            body += (f'*STEP,PERTURBATION\n*COMPLEX FREQUENCY,CORIOLIS\n{modes}\n'
                     '*NODE FILE\nPU\n*END STEP\n')
        deck = case / 'rotor.inp'
        deck.write_text(body)
        cases.append({'case':case.name,'rpm_assumed':rpm,'deck_sha256':sha(deck),
                      'centrifugal_prestress':bool(rpm),'coriolis_requested':bool(rpm),
                      'requested_modes':modes})
    result = {'status':'prepared_not_solved','source_deck_sha256':sha(source),
              'nodes':len(nodes),'tetrahedra':len(elements),'units':'mm,N,s,tonne',
              'cases':cases,'boundary':'inherited hypothetical fully fixed bore',
              'material':'inherited assumed isotropic elastic card, not qualified AlSi10Mg',
              'bearing_belt_contact_damping_included':False,'mesh_independence':False,
              'validated_campbell_diagram':False,'safe_speed_rpm':None,
              'manufacturing_authorized':False,
              'contract_ids':['drive.rotor_speed','dynamics.prestressed_modes','dynamics.excitation_orders',
                              'material.elastic_properties','material.density','hub.bore_profile']}
    (output/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def support_nodes(nodes, elements, direction, pitch=5.):
    # Surface corners/midside nodes only. Pick the lowest surface node in each
    # projected 5 mm raster cell as a vertical-column attachment proxy.
    faces = {}
    for e in elements.values():
        for inds in ((0,1,2,4,5,6),(0,3,1,7,8,4),(1,3,2,8,9,5),(2,3,0,9,7,6)):
            face = [e[i] for i in inds]
            key = tuple(sorted(face[:3]))
            if key in faces:
                del faces[key]
            else:
                faces[key] = face
    surface = set(n for f in faces.values() for n in f)
    n = np.asarray(direction,dtype=float)
    first = np.array([1.,0.,0.]) if abs(n[0]) < .9 else np.array([0.,1.,0.])
    first -= np.dot(first,n)*n
    first /= np.linalg.norm(first)
    second = np.cross(n,first)
    cells = {}
    for tag in sorted(surface):
        xyz = nodes[tag]
        key = (math.floor(np.dot(xyz,first)/pitch),math.floor(np.dot(xyz,second)/pitch))
        if key not in cells or np.dot(xyz,n) < np.dot(nodes[cells[key]],n):
            cells[key] = tag
    return sorted(cells.values())


def prepare_eigenstrain(source, output, amplitude, direction):
    if not math.isfinite(amplitude) or not 0 <= amplitude <= .005:
        raise ValueError('Assumed strain amplitude must be 0..0.005')
    direction = np.asarray(direction,dtype=float)
    if not np.isfinite(direction).all() or np.linalg.norm(direction) == 0:
        raise ValueError('Finite nonzero build direction required')
    direction /= np.linalg.norm(direction)
    text = source.read_text()
    nodes, elements = parse_mesh(text)
    head = text[:text.upper().index('*BOUNDARY')]
    coordinates = np.array(list(nodes.values()))
    projected = coordinates @ direction
    zmin, height = projected.min(), float(np.ptp(projected))
    attached = support_nodes(nodes,elements,direction)
    if len(attached)<20 or height <= 0:
        raise ValueError('Insufficient support proxy or collapsed geometry')
    # Stable 3-2-1 gauge constraints in global coordinates. Selection is recorded;
    # they remove rigid motion only and do not represent installed attachments.
    a = min(nodes,key=lambda i:np.linalg.norm(nodes[i]))
    b = max(nodes,key=lambda i:abs(nodes[i][0]-nodes[a][0]))
    c = max(nodes,key=lambda i:abs(nodes[i][1]-nodes[a][1]))
    if len({a,b,c}) != 3:
        raise ValueError('Cannot select distinct gauge nodes')
    output.mkdir(parents=True,exist_ok=False)
    deck = output/'rotor.inp'
    # Initial strains are prescribed at the four C3D10 integration points in
    # global coordinates, using the documented CalculiX initial-strain API.
    # This is not thermal, plasticity, deposition activation or a scan-path solve.
    tensor_base = np.eye(3) - .7*np.outer(direction,direction)
    gauss = np.array([[.5854101966249685,.1381966011250105,.1381966011250105,.1381966011250105],
                      [.1381966011250105,.5854101966249685,.1381966011250105,.1381966011250105],
                      [.1381966011250105,.1381966011250105,.5854101966249685,.1381966011250105],
                      [.1381966011250105,.1381966011250105,.1381966011250105,.5854101966249685]])
    with deck.open('w') as f:
        f.write(head+'*NSET,NSET=BUILD_ATTACH\n')
        for start in range(0,len(attached),12):
            f.write(','.join(map(str,attached[start:start+12]))+'\n')
        f.write('*INITIAL CONDITIONS,TYPE=PLASTIC STRAIN\n')
        for e in sorted(elements):
            for ip in range(1,5):
                f.write(f'{e},{ip},0,0,0,0,0,0\n')
        f.write('*BOUNDARY\nBUILD_ATTACH,1,3\n*STEP\n*STATIC\n*INITIAL STRAIN INCREASE\n')
        for e, connectivity in sorted(elements.items()):
            corners = np.array([nodes[i] for i in connectivity[:4]])
            for ip, weights in enumerate(gauss,1):
                position = weights@corners
                height_fraction = np.clip((np.dot(position,direction)-zmin)/height,0.,1.)
                strain = -amplitude*(.5+.5*height_fraction**2)*tensor_base
                values = [strain[0,0],strain[1,1],strain[2,2],strain[0,1],strain[0,2],strain[1,2]]
                f.write(f'{e},{ip},'+','.join(f'{v:.14g}' for v in values)+'\n')
        f.write('*NODE FILE\nU\n*EL FILE\nS\n*EL PRINT,ELSET=ROTOR\nS\n*END STEP\n')
        f.write(f'*STEP\n*STATIC\n*BOUNDARY,OP=NEW\n{a},1,3\n{b},2,3\n{c},3,3\n')
        f.write('*NODE FILE\nU\n*EL FILE\nS\n*EL PRINT,ELSET=ROTOR\nS\n*END STEP\n')
    report = {'status':'prepared_not_solved','source_deck_sha256':sha(source),
              'deck_sha256':sha(deck),'nodes':len(nodes),'tetrahedra':len(elements),
              'units':'mm,N,s,tonne','strain_amplitude_assumed':amplitude,
              'strain_is_not_a_measured_process_property':True,'build_direction':direction.tolist(),
              'formula':'epsilon_star = -amplitude*(0.5+0.5*s^2)*(I-0.7*n*nT), s=normalized build height',
              'support_proxy':'fully fixed lowest surface node per projected 5 mm raster cell; rigid column bound, no supplier topology',
              'support_attachment_nodes':len(attached),'gauge_nodes':[a,b,c],
              'gauge_node_coordinates_mm':[nodes[i].tolist() for i in [a,b,c]],
              'support_release_included':True,'layer_activation_included':False,
              'scan_path_temperature_plasticity_recoater_included':False,
              'process_calibrated':False,'distortion_prediction_qualified':False,
              'material':'inherited assumed isotropic elastic card, not a route-qualified material',
              'mesh_independence':False,'manufacturing_authorized':False,
              'contract_ids':['lpbf.build_orientation','lpbf.support_strategy','lpbf.machine_parameters',
                              'lpbf.heat_treatment','material.elastic_properties','material.defect_population']}
    (output/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('study',choices=['modes','eigenstrain'])
    p.add_argument('source',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--rpm',type=float,nargs='+',default=[0,3000,6000,10000])
    p.add_argument('--modes',type=int,default=12)
    p.add_argument('--strain',type=float,default=.001)
    p.add_argument('--direction',type=float,nargs=3,default=[0,0,1])
    a=p.parse_args()
    result=prepare_modes(a.source,a.output,a.rpm,a.modes) if a.study=='modes' else prepare_eigenstrain(a.source,a.output,a.strain,a.direction)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
