"""Authored, bounded engineering tasks; public papers inform method, not training text."""
import ast
import itertools
import json
import operator
import random

SYSTEM = 'Return only the requested code or JSON. All fixtures are synthetic. Never infer Porsche dimensions, material qualification or physical validation.'
FAMILIES = {'train': ('duct', 'plenum', 'coupon', 'spacer'),
            'valid': ('diffuser', 'enclosure'), 'test': ('heat_exchanger', 'guide')}


def cases(usd, pico):
    rows = []
    for split, count, seed in [('train', 96, 260021), ('valid', 8, 260022), ('test', 8, 260023)]:
        rng = random.Random(seed)
        for i in range(count):
            family = FAMILIES[split][i % len(FAMILIES[split])]
            label = f'{family}_{seed}_{i}'
            kinds = [
                ('reynolds', 'speed * length / viscosity',
                 {'speed': rng.randint(1, 20), 'length': rng.randint(1, 9) / 100, 'viscosity': rng.choice([1e-5, 2e-5, 5e-5])},
                 'Calculate Reynolds number. speed is m/s, length is m, viscosity is kinematic m^2/s.'),
                ('courant', 'target * cell / speed',
                 {'target': 0.5, 'cell': rng.randint(1, 8) / 1000, 'speed': rng.randint(1, 12)},
                 'Calculate dt in seconds from the one-dimensional advective Courant limit. target is dimensionless, cell is m and speed is positive m/s. This does not bound diffusion or multidimensional fluxes.'),
                ('conversion', 'length / 1000', {'length': rng.randint(1, 1500)}, 'Convert length from millimetres to metres.'),
                ('torque', 'power * 1000 / (2 * pi * rpm / 60)',
                 {'power': rng.randint(10, 500), 'pi': 3.141592653589793, 'rpm': rng.randint(10, 70) * 100},
                 'Calculate shaft torque in N m from power in kW and speed in rpm. Do not use horsepower or infer mount loads.')]
            task, expression, values, instruction = kinds[i % 4]
            rows.append(row(split, family, 'python', label,
                instruction + ' Synthetic fixture ' + label + '. Inputs: ' + json.dumps(values) + '. Return only result = <expression> using the supplied variable names; no numeric substitution.',
                'result = ' + expression, {'values': values, 'expression': expression}, task))

            # Ground the version and output schema. No untrusted shell or OpenFOAM code directives.
            dt = rng.choice([0.001, 0.002, 0.005]); end = dt * rng.choice([10, 20, 40])
            control = {'application': 'icoFoam', 'deltaT': dt, 'endTime': round(end, 6), 'writeInterval': 10}
            if i % 4 == 3:
                expected = {'run_solver': False, 'reason': 'mesh_failed', 'physically_validated': False}
                prompt = 'OpenFOAM ESI v2312. checkMesh failed with illegal cells. The solver has not run. Return exactly run_solver, reason and physically_validated. Mesh failure blocks execution; reason must be mesh_failed.'
                task = 'mesh_gate'
            else:
                expected = control
                prompt = ('Use the reviewed laminar incompressible cavity on OpenFOAM ESI v2312; its installed application is icoFoam. '
                    f'Set deltaT={dt} s, endTime={end:g} s, and writeInterval=10 time steps. Return exactly application, deltaT, endTime, writeInterval. '
                    'These are controlDict values, not a complete case or proof of convergence.')
                task = 'control'
            rows.append(row(split, family, 'openfoam', label, prompt + ' Synthetic fixture ' + label + '.',
                json.dumps(expected, sort_keys=True), expected, task))

            points = [list(p) for p in rng.sample(list(itertools.product(range(-18, 19, 6), repeat=3)), 4)]
            edges = rng.sample(list(itertools.combinations(range(4), 2)), 1 + i % 6)
            radii = [rng.choice([1, 1.5, 2, 2.5]) for _ in range(4)]
            rounded = bool(i % 2)
            beams = [points[a] + [radii[a]] + points[b] + [radii[b]] + [rounded] for a, b in edges]
            spec = {'nodes': {str(n): {'xyz_mm': xyz, 'radius_mm': r} for n, (xyz, r) in enumerate(zip(points, radii))},
                    'edges': edges, 'rounded_caps': rounded}
            prompt = ('PicoGK contract: AddBeam takes endpoint radii, not diameters. Given this dependency graph, '
                      'emit one AddBeam statement per edge, preserving the radius attached to each node. Synthetic fixture ' + label + '.\n' + json.dumps(spec))
            rows.append(row(split, family, 'picogk', label, prompt, pico.code(beams), beams, 'graph', pico.SYSTEM))

            size, shift = rng.randint(3, 40), rng.randint(-12, 12)
            path = '/World/' + label
            header = ('root = UsdGeom.Xform.Define(stage, "/World")\nstage.SetDefaultPrim(root.GetPrim())\n'
                      'UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)\nUsdGeom.SetStageMetersPerUnit(stage, 0.001)\n')
            shape, attr = ('Cube', 'Size') if i % 2 == 0 else ('Sphere', 'Radius')
            code = header + f'part = UsdGeom.{shape}.Define(stage, "{path}")\npart.Create{attr}Attr({size})\npart.AddTranslateOp().Set(Gf.Vec3d({shift}, 0, 0))\n'
            if i % 4 >= 2:
                code += 'part.CreatePurposeAttr(UsdGeom.Tokens.guide)\n'
            prompt = (f'Create {shape.lower()} {path}, {attr.lower()} {size} mm, translation ({shift},0,0) mm. '
                      'Author millimetre units, Z-up and /World default prim.' + (' Set purpose guide.' if i % 4 >= 2 else ''))
            rows.append(row(split, family, 'openusd', label, prompt, code, None, 'scene', usd.SYSTEM))
    validate(rows)
    return rows


def row(split, family, domain, label, prompt, answer, expected, task, system=SYSTEM):
    return {'id': domain + '-' + label, 'split': split, 'family': family, 'domain': domain,
            'task': task, 'expected': expected, 'synthetic': True,
            'provenance': 'New owner-authorised examples; repository licence. No third-party dataset rows or paper text.',
            'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt},
                         {'role': 'assistant', 'content': answer}]}


def validate(rows):
    if len({r['id'] for r in rows}) != len(rows) or len({r['messages'][1]['content'] for r in rows}) != len(rows):
        raise ValueError('duplicate case or prompt')
    for r in rows:
        if r['family'] not in FAMILIES[r['split']] or not r['synthetic']:
            raise ValueError('family leakage or non-synthetic data')
    return {s: sum(r['split'] == s for r in rows) for s in FAMILIES}


def calculate(source, values):
    """Interpret arithmetic only; no Python exec, imports, calls, attributes or loops."""
    tree = ast.parse(source.strip())
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
        raise ValueError('one assignment required')
    statement = tree.body[0]
    if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name) or statement.targets[0].id != 'result':
        raise ValueError('result assignment required')
    operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
    def value(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and abs(node.value) <= 1e6:
            return node.value
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](value(node.left), value(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -value(node.operand)
        raise ValueError('outside arithmetic contract')
    if len(list(ast.walk(tree))) > 80:
        raise ValueError('expression too large')
    return value(statement.value)
