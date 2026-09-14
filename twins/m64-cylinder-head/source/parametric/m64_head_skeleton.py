"""Squelette paramétrique G1 d'une culasse M64 4V (un cylindre).

Géométrie fonctionnelle de travail : jamais maître, jamais autorisée en fabrication.
Chaque paramètre est soit lu et vérifié dans le contrat d'interfaces, soit un
placeholder explicitement marqué ``unsourced``. Fail-closed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DEFAULT_PARAMETERS = HERE / 'parameters.json'
DEFAULT_CONTRACT = REPO / 'twins/m64-cylinder-head/interface-contract.json'
PROVENANCES = ('sourced', 'unsourced')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _resolve(contract, dotted):
    node = contract
    for key in dotted.split('.'):
        if not isinstance(node, dict) or key not in node:
            raise ValueError(f'contract path not found: {dotted}')
        node = node[key]
    return node


def resolve_parameters(spec, contract):
    """Retourne (valeurs, non_sourcés, sourcés) ou lève ValueError."""
    values, unsourced, sourced = {}, [], {}
    interfaces = contract.get('critical_interfaces', {})
    for name, item in spec['parameters'].items():
        prov = item.get('provenance')
        if prov not in PROVENANCES:
            raise ValueError(f'{name}: provenance must be sourced or unsourced')
        value = item.get('value')
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f'{name}: numeric value required')
        if prov == 'sourced':
            path = item.get('contract_path')
            if not path:
                raise ValueError(f'{name}: sourced parameter without contract_path')
            if path.startswith('critical_interfaces.'):
                iface = interfaces.get(path.split('.')[1], {})
                if iface.get('status') != 'found':
                    raise ValueError(f'{name}: critical interface is not found in contract')
            parent = _resolve(contract, path.rsplit('.', 1)[0])
            reference = _resolve(contract, path)
            if reference is None:
                raise ValueError(f'{name}: contract value is null, cannot be sourced')
            if not parent.get('source') or parent.get('source') not in contract.get('sources', {}):
                raise ValueError(f'{name}: contract entry has no registered source')
            if not parent.get('source_locator'):
                raise ValueError(f'{name}: contract entry has no source_locator')
            if parent.get('unit') and parent['unit'] != item.get('unit'):
                raise ValueError(f'{name}: unit differs from contract')
            if not math.isclose(float(value), float(reference), rel_tol=0, abs_tol=1e-9):
                raise ValueError(f'{name}: sourced value {value} differs from contract {reference}')
            sourced[name] = {'value': value, 'contract_path': path,
                             'source': parent['source'], 'source_locator': parent['source_locator']}
        else:
            if item.get('contract_path'):
                raise ValueError(f'{name}: unsourced parameter cannot cite a contract_path')
            iface_name = item.get('contract_interface')
            if iface_name and interfaces.get(iface_name, {}).get('status') == 'found':
                raise ValueError(f'{name}: contract now sources {iface_name}; placeholder refused')
            unsourced.append(name)
        values[name] = float(value)
    return values, sorted(unsourced), sourced


def build(p):
    import cadquery as cq

    V = cq.Vector
    h = p['head_block_height_z']
    block = cq.Solid.makeBox(p['head_block_length_x'], p['head_block_width_y'], h,
                             V(-p['head_block_length_x'] / 2, -p['head_block_width_y'] / 2, 0))
    # Centrage cylindre (épaulement sous le plan d'étanchéité) et portée annulaire.
    register = cq.Solid.makeCylinder(p['cylinder_register_diameter'] / 2, p['cylinder_register_depth'],
                                     V(0, 0, -p['cylinder_register_depth']))
    body = block.fuse(register)
    relief = cq.Solid.makeCylinder(p['head_block_length_x'], 0.5, V(0, 0, 0)).cut(
        cq.Solid.makeCylinder(p['sealing_face_outer_diameter'] / 2, 0.5, V(0, 0, 0)))
    body = body.cut(relief)
    # Chambre de combustion (volume simplifié) ouverte vers le cylindre.
    chamber = cq.Solid.makeCylinder(p['chamber_reference_diameter'] / 2,
                                    p['chamber_depth'] + p['cylinder_register_depth'],
                                    V(0, 0, -p['cylinder_register_depth']))
    body = body.cut(chamber)
    roof = p['chamber_depth']
    # Quatre sièges et guides : 2 admission (x<0), 2 échappement (x>0).
    for side, dia_key in ((-1, 'intake_valve_head_diameter'), (1, 'exhaust_valve_head_diameter')):
        tilt = math.radians(p['valve_inclination_deg']) * side
        axis = V(math.sin(tilt), 0, math.cos(tilt))
        for sy in (-1, 1):
            base = V(side * p['valve_x_offset'], sy * p['valve_y_offset'], roof - 1.0)
            seat = cq.Solid.makeCylinder(p[dia_key] / 2, p['seat_counterbore_depth'] + 1.0, base, axis)
            guide = cq.Solid.makeCylinder(p['guide_bore_diameter'] / 2, 3 * h, base, axis)
            body = body.cut(seat).cut(guide)
    # Puits de bougie central.
    body = body.cut(cq.Solid.makeCylinder(p['spark_plug_bore_diameter'] / 2, 2 * h, V(0, 0, roof - 1.0)))
    # Goujons principaux (quatre trous traversants).
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = body.cut(cq.Solid.makeCylinder(p['main_stud_hole_diameter'] / 2, h + 20,
                                                  V(sx * p['main_stud_circle_x'], sy * p['main_stud_circle_y'], -10)))
    # Axes porte-arbres (deux alésages longitudinaux).
    for side in (-1, 1):
        body = body.cut(cq.Solid.makeCylinder(p['cam_bore_diameter'] / 2, p['head_block_width_y'] + 20,
                                              V(side * p['cam_axis_x_offset'], -p['head_block_width_y'] / 2 - 10,
                                                p['cam_axis_height_z']), V(0, 1, 0)))
    return body.clean()


def brep_valid(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    return bool(BRepCheck_Analyzer(shape.wrapped).IsValid())


def generate(out_dir, parameters_path=DEFAULT_PARAMETERS, contract_path=DEFAULT_CONTRACT):
    import cadquery as cq

    spec = json.loads(Path(parameters_path).read_text())
    contract = json.loads(Path(contract_path).read_text())
    if contract.get('manufacturing_authorized') is not False:
        raise ValueError('contract must keep manufacturing_authorized false')
    values, unsourced, sourced = resolve_parameters(spec, contract)
    solid = build(values)
    valid = brep_valid(solid)
    if not valid:
        raise ValueError('BRepCheck rejected the skeleton')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    step = out / 'm64-head-skeleton.step'
    section = out / 'm64-head-skeleton-section-xz.svg'
    cq.exporters.export(cq.Workplane().add(solid), str(step))
    keep = cq.Solid.makeBox(1000, 1000, 1000, cq.Vector(-500, values['valve_y_offset'], -500))
    cut = solid.cut(keep)
    cq.exporters.export(cq.Workplane().add(cut), str(section),
                        opt={'projectionDir': (0, 1, 0), 'showHidden': False})
    manifest = {
        'schema_version': 1,
        'artifact': 'm64_g1_parametric_skeleton',
        'master_geometry': False,
        'manufacturing_authorized': False,
        'brep_check_valid': valid,
        'volume_mm3': round(solid.Volume(), 3),
        'section': f'plan XZ à y = valve_y_offset, vue depuis +Y',
        'unsourced_parameters': unsourced,
        'unsourced_count': len(unsourced),
        'sourced_parameters': sourced,
        'sha256': {
            'step': sha256(step), 'section_svg': sha256(section),
            'parameters': sha256(parameters_path), 'contract': sha256(contract_path),
            'generator': sha256(__file__),
        },
        'limits': 'Volumes fonctionnels schématiques ; toutes les positions de goujons, registre, '
                  'axes et sièges sont des placeholders non sourcés.',
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('out_dir')
    args = parser.parse_args()
    result = generate(args.out_dir)
    print(json.dumps({k: result[k] for k in ('brep_check_valid', 'volume_mm3', 'unsourced_count',
                                              'master_geometry', 'manufacturing_authorized')}))
