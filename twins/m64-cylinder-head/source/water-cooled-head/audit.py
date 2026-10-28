"""Independent raw surface inspection of a private coolant routing proposal."""
import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('retained_raw_surface_audit', HERE.parent/'bionic-fin-integration/audit.py')
surface = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(surface)


def validate_report(report, contract):
    if (report['schema'] != 'm64-water-head-generation/v1'
            or report['status'] != 'routing_only_integration_blocked'
            or report['units'] != contract['units']
            or report['voxel_scan_units'] not in (.6, .3)
            or report['head_stl_sha256'] != contract['head_stl_sha256']
            or report['input_manifest_sha256'] != contract['input_manifest_sha256']
            or report['diagnostic_wall_margin'] != contract['layout']['diagnostic_wall_margin']):
        raise ValueError('Different or qualified producer report')
    for key in ('source_master_modified', 'material_removed', 'manufacturing_authorized',
                'gas_oil_stud_spark_plug_domains_complete', 'pressure_boundary_qualified',
                'thermal_simulation', 'structural_simulation'):
        if report[key] is not False:
            raise ValueError('Unsupported qualification: '+key)
    expected = ['coolant-routing.stl', 'routing-plus-wall-margin.stl', 'outside-eroded-head.stl']
    if [f['filename'] for f in report['files']] != expected:
        raise ValueError('Exact diagnostic exports required')
    if len(report['reference_wall_margin_conflicts']) != 12:
        raise ValueError('All retained references required')
    return report['files']


def run(directory, inputs, output):
    if output.exists():
        raise FileExistsError(output)
    contract = json.loads((HERE/'contract.json').read_text())
    report = json.loads((directory/'generation.json').read_text())
    rows = validate_report(report, contract)
    pins = {HERE/'contract.json': report['contract_sha256'],
            inputs/'inputs.json': contract['input_manifest_sha256'],
            directory/'generation.json': surface.mesh.sha256(directory/'generation.json')}
    manifest = json.loads((inputs/'inputs.json').read_text())
    if len(manifest['parts']) != 13:
        raise ValueError('Retained thirteen-part module required')
    for part in manifest['parts']:
        if part['filename'] != part['name']+'.stl' or Path(part['filename']).name != part['filename']:
            raise ValueError('Local filename required')
        pins[inputs/part['filename']] = part['sha256']
    for row in rows:
        if row['triangles']:
            pins[directory/row['filename']] = row['sha256']
        elif (directory/row['filename']).exists() or row['sha256'] is not None:
            raise ValueError('Inconsistent empty diagnostic')
    for path, pin in pins.items():
        if path.is_symlink() or surface.mesh.sha256(path) != pin:
            raise ValueError('Retained input/output hash mismatch')
    inspections = {}
    for row in rows:
        if not row['triangles']:
            continue
        triangles = surface.mesh.load_binary_stl(directory/row['filename'])
        check = surface.raw_surface_summary(triangles)
        if len(triangles) != row['triangles']:
            raise ValueError('Triangle count mismatch')
        # Diagnostic fragments may be disconnected; the coolant proposal must be one closed surface.
        check['basic_surface_pass'] = (check['edge_manifold_closed']
            and check['winding_consistent_on_two_face_edges'] and check['zero_area_triangles'] == 0
            and check['duplicate_triangles_ignoring_winding'] == 0 and check['signed_volume_scan_units_cubed'] > 0)
        inspections[row['filename']] = check
    routing = inspections['coolant-routing.stl']
    passed = routing['basic_surface_pass'] and routing['connected_vertex_components'] == 1
    for path, pin in pins.items():
        if surface.mesh.sha256(path) != pin:
            raise ValueError('Input changed during inspection')
    result = dict(schema='m64-water-head-inspection/v1',
                  status='routing_surface_passed_integration_blocked' if passed else 'routing_surface_failed',
                  inspector_sha256=surface.mesh.sha256(Path(__file__)),
                  reused_inspector_sha256=surface.mesh.sha256(HERE.parent/'bionic-fin-integration/audit.py'),
                  contract_sha256=report['contract_sha256'], generation_sha256=pins[directory/'generation.json'],
                  surfaces=inspections, source_master_modified=False, material_removed=False,
                  pressure_boundary_qualified=False, manufacturing_authorized=False,
                  required_next_inputs=['calibrated_interfaces', 'complete_protected_domains',
                      'sealed_metal_jacket', 'heat_flux_map', 'material_process', 'pump_radiator_curves'])
    with output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    if not passed:
        raise ValueError('Coolant routing raw surface failed; diagnostics retained')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('directory', 'inputs', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args(); print(run(args.directory, args.inputs, args.output)['status'])
