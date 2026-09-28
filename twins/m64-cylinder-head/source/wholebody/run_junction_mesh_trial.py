#!/usr/bin/env python3
"""Spatially bounded mesh-size experiment on the unchanged, pinned full body.

Reuse the original 155-face MeshAdapt trial and all its acceptance gates.
The extra receipt records the nested sizing hook; no installed code is edited.
"""
import argparse
import json
import math
from pathlib import Path
import signal

import run_local_surface_trial as previous
from audit_pinched_junction import REGION_SHA


def local_size(distance, previous_size, minimum):
    if (not math.isfinite(distance) or distance < 0 or not math.isfinite(previous_size)
            or previous_size <= 0 or minimum not in (.02, .005)):
        raise ValueError('finite_bounded_size_input_required')
    # Preserve the previous 1-unit floor away from this 0.1-unit core.
    return min(max(1., previous_size), minimum + .4 * max(0., distance - .1))


def run(args):
    import gmsh
    diagnostic = json.loads(args.diagnostic.read_text())
    producer = Path(__file__).with_name('audit_pinched_junction.py')
    if (args.output.exists() or args.diagnostic.is_symlink()
            or diagnostic.get('input_sha256') != previous.BODY_SHA
            or diagnostic.get('region_sha256') != REGION_SHA
            or diagnostic.get('source_sha256') != previous.native.sha256(producer)
            or diagnostic.get('inputs_unchanged') is not True):
        raise ValueError('fresh_output_and_bound_junction_diagnostic_required')
    centre = diagnostic['centre_private']
    if len(centre) != 3 or not all(math.isfinite(v) for v in centre):
        raise ValueError('finite_junction_centre_required')
    pins = {args.diagnostic: previous.native.sha256(args.diagnostic),
            producer: previous.native.sha256(producer), Path(__file__): previous.native.sha256(__file__),
            Path(previous.__file__): previous.native.sha256(previous.__file__)}
    args.output.mkdir(mode=0o700)
    receipt = dict(schema='m64-spatial-junction-mesh-trial/v1', status='incomplete',
        source_sha256=pins[Path(__file__)], diagnostic_sha256=pins[args.diagnostic],
        inherited_trial_source_sha256=pins[Path(previous.__file__)],
        centre_private=centre, core_radius=.1, radial_size_gradient=.4, minimum=args.minimum,
        geometry_modified=False, physical_millimetres_certified=False, manufacturing_authorized=False,
        previous_quality_gates_unchanged=True, calls=[])
    path = args.output/'junction-trial.json'
    previous.native.save(path, receipt)
    generate = gmsh.model.mesh.generate
    def spatial_generate(dimension=3):
        receipt['calls'].append(dimension)
        if dimension == 1:
            gmsh.option.setNumber('Mesh.MeshSizeMin', args.minimum)
            gmsh.model.mesh.setSizeCallback(lambda dim, tag, x, y, z, lc:
                local_size(math.dist((x,y,z), centre), lc, args.minimum))
        result = generate(dimension)
        if dimension == 2:
            surface = args.output/'surface-before-volume-private.msh'
            gmsh.option.setNumber('Mesh.Binary', 1)
            gmsh.option.setNumber('Mesh.SaveAll', 1)
            gmsh.write(str(surface))
            receipt['surface_sha256'] = previous.native.sha256(surface)
        previous.native.save(path, receipt)
        return result
    gmsh.model.mesh.generate = spatial_generate
    inherited = argparse.Namespace(input=args.input, baseline=args.baseline, quality=args.quality,
                                   output=args.output/'native-trial')
    try:
        code = previous.main(inherited)
        report_path = inherited.output/'mesh/mesh-report.json'
        report = json.loads(report_path.read_text())
        receipt.update(status='completed' if receipt['calls'] == [1,2,3] and report['status'] != 'failed' else 'failed',
            inherited_exit_code=code, mesh_report_sha256=previous.native.sha256(report_path),
            mesh_status=report['status'])
        return code
    finally:
        gmsh.model.mesh.generate = generate
        receipt['inputs_and_sources_unchanged'] = all(previous.native.sha256(p) == h for p,h in pins.items())
        previous.native.save(path, receipt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'baseline', 'quality', 'diagnostic', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--minimum', type=float, choices=(.02, .005), default=.02)
    signal.alarm(600)
    raise SystemExit(run(parser.parse_args()))
