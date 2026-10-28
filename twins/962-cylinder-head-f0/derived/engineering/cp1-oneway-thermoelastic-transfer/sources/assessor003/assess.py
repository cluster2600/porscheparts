"""HELD fixed SI coupon saved-field assessor; never launches a native process."""
import argparse
import csv
from decimal import Decimal
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import re
import struct
import sys

PREP = Path(__file__).resolve().parent
ROOT = PREP.parents[2]
CASE = ROOT / 'work/962-engineering/cp1-oneway-thermoelastic-transfer-prep-002'
OUTPUT = 'work/962-engineering/cp1-oneway-thermoelastic-assessment-002'
DISP = ('disp_x', 'disp_y', 'disp_z')
FORCE = ('rx', 'ry', 'rz')
TENSORS = ('stress', 'elastic_strain', 'mechanical_strain', 'total_strain', 'thermal_eigenstrain')
COMP = ((0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2))
SUFFIX = ('xx', 'yy', 'zz', 'xy', 'xz', 'yz')
QP_FIELDS = tuple(t + '_' + s for t in TENSORS for s in SUFFIX)
E = 71e9
NU = .33
ALPHA = 1e-5
MU = E / (2 * (1 + NU))
LAM = E * NU / ((1 + NU) * (1 - 2 * NU))
ZERO = ((0., 0., 0.),) * 3


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024**2), b''):
            h.update(part)
    return h.hexdigest()


def bits(xyz):
    return struct.pack('<3d', *xyz)


def number(value):
    need(type(value) in (str, float, int), 'Explicit finite numeric scalar required')
    out = float(value)
    need(math.isfinite(out), 'Nonfinite scalar refused')
    return out


def integer(value):
    need(type(value) in (str, float, int), 'Explicit ID scalar required')
    x = Decimal(str(value))
    need(x.is_finite() and x >= 0 and x == x.to_integral_value(), 'Nonnegative integral ID required')
    return int(x)


def rows(path, columns, allow_empty=False):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames))
             and set(reader.fieldnames) == set(columns), 'Exact unique CSV field set required: ' + str(path))
        data = list(reader)
    need((data or allow_empty) and all(set(r) == set(columns) and all(v is not None and v != '' for v in r.values()) for r in data),
         'Complete CSV row required: ' + str(path))
    return data


def tensor(row, name):
    a = [[0.] * 3 for _ in range(3)]
    for (i, j), suffix in zip(COMP, SUFFIX):
        a[i][j] = a[j][i] = number(row[name + '_' + suffix])
    return a


def symgrad(displacements, gradients):
    g = [[math.fsum(u[i] * d[j] for u, d in zip(displacements, gradients)) for j in range(3)] for i in range(3)]
    return [[(g[i][j] + g[j][i]) / 2 for j in range(3)] for i in range(3)]


def hooke(elastic):
    trace = math.fsum(elastic[i][i] for i in range(3))
    return [[2 * MU * elastic[i][j] + (LAM * trace if i == j else 0.) for j in range(3)] for i in range(3)]


def hex_rule(points):
    """Q1 bases attached to observed Cartesian corners; no element-row/DOF guess."""
    need(len(points) == 8 and len(set(map(tuple, points))) == 8, 'Eight distinct HEX8 corners required')
    lo = [min(p[j] for p in points) for j in range(3)]
    hi = [max(p[j] for p in points) for j in range(3)]
    width = [hi[j] - lo[j] for j in range(3)]
    need(width == [.125, .25, .25] and set(map(tuple, points)) == set(product(*zip(lo, hi))), 'Fixed Cartesian HEX8 grid cell required')
    signs = [tuple(-1 if p[j] == lo[j] else 1 for j in range(3)) for p in points]
    result = []
    for ref in product((-1 / math.sqrt(3), 1 / math.sqrt(3)), repeat=3):
        shape = [math.prod(1 + sign[j] * ref[j] for j in range(3)) / 8 for sign in signs]
        gradients = [tuple(sign[j] * math.prod(1 + sign[k] * ref[k] for k in range(3) if k != j) / (4 * width[j]) for j in range(3)) for sign in signs]
        xyz = tuple((lo[j] + hi[j]) / 2 + width[j] * ref[j] / 2 for j in range(3))
        result.append((xyz, shape, gradients, math.prod(width) / 8))
    return result


def ordered_hex(points):
    """Validate observed HEX8 reference-corner order, allowing positive Cartesian rotations."""
    need(len(points) == 8, 'Eight ordered native HEX8 corners required')
    edges = [tuple(points[k][j] - points[0][j] for j in range(3)) for k in (1, 3, 4)]
    axes = [{j for j, value in enumerate(edge) if value != 0} for edge in edges]
    need(all(len(axis) == 1 for axis in axes) and len(set.union(*axes)) == 3, 'Native reference edges must be three distinct Cartesian axes')
    determinant = math.fsum(edges[0][j] * (edges[1][(j+1)%3] * edges[2][(j+2)%3] - edges[1][(j+2)%3] * edges[2][(j+1)%3]) for j in range(3))
    need(determinant > 0, 'Positive observed native HEX8 reference orientation required')
    corners = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))
    need(all(tuple(p) == tuple(points[0][j] + sum(ref[k] * edges[k][j] for k in range(3)) for j in range(3)) for p, ref in zip(points, corners)), 'Twisted/misordered native HEX8 connectivity refused')


def mechanical_state(points, u, temperature, reference_u, reference_temperature):
    result = []
    du = [[x - y for x, y in zip(a, b)] for a, b in zip(u, reference_u)]
    for xyz, shape, grad, weight in hex_rule(points):
        total = symgrad(du, grad)
        delta = math.fsum(n * (t - r) for n, t, r in zip(shape, temperature, reference_temperature))
        eigen = [[ALPHA * delta if i == j else 0. for j in range(3)] for i in range(3)]
        elastic = [[total[i][j] - eigen[i][j] for j in range(3)] for i in range(3)]
        result.append((xyz, grad, weight, dict(total_strain=total, thermal_eigenstrain=eigen,
                                             elastic_strain=elastic, mechanical_strain=elastic, stress=hooke(elastic))))
    return result


def accumulate(forces, tags, gradients, weight, stress):
    for tag, grad in zip(tags, gradients):
        for i in range(3):
            forces[tag][i] += weight * math.fsum(stress[i][j] * grad[j] for j in range(3))


class Audit:
    def __init__(self, policy):
        self.policy = policy
        self.maximum = {}
        self.counts = {}

    def close(self, a, b, unit):
        a, b = number(a), number(b)
        error = abs(a - b)
        self.maximum[unit] = max(self.maximum.get(unit, 0.), error)
        self.counts[unit] = self.counts.get(unit, 0) + 1
        need(error <= self.policy[unit], unit + ' fixed absolute SI gate failed: ' + repr(error))


def node_sample(path, geometry, active, columns, shared_doublets=()):
    # Only the native postbirth caller supplies the exact frozen shared25 IDs.
    expected = set(shared_doublets)
    need(len(expected) == len(shared_doublets) and expected <= set(active)
         and (not expected or len(expected) == 25)
         and all(type(tag) is int and geometry[tag][0] == 1. for tag in expected),
         'Only the explicit shared25 native doublet set is supported')
    fields = ('id', 'x', 'y', 'z', *columns)
    saved = rows(path, fields)
    data = {}; tokens = {}; positions = {}
    for line, row in enumerate(saved, 2):
        tag = integer(row['id'])
        xyz = tuple(number(row[k]) for k in 'xyz')
        need(tag in active and bits(xyz) == bits(geometry[tag]), 'Observed source ID/coordinate words must join native Exodus map')
        original = tuple(row[name] for name in fields)
        values = {name: number(row[name]) for name in columns}
        if tag in data:
            need(tag in expected and len(positions[tag]) == 1 and original == tokens[tag],
                 'Only two complete lexically identical rows per expected shared source ID are supported')
        else:
            data[tag] = values; tokens[tag] = original; positions[tag] = []
        positions[tag].append(line)
    need(set(data) == set(active), 'Complete active nodal sample required')
    need(len(saved) == len(active) + len(expected)
         and all(len(positions[tag]) == (2 if tag in expected else 1) for tag in active),
         'Exact expected shared doublets and all other singletons required')
    storage = dict(filename=Path(path).name, raw_csv_sha256=sha(path), comparison_field_order=list(fields),
                   raw_row_count=len(saved), unique_source_ID_count=len(data), expected_shared_doublet_IDs=sorted(expected),
                   verified_doublets=[dict(source_node_id=tag, csv_line_numbers_1_based=positions[tag],
                       complete_field_token_sha256=hashlib.sha256(json.dumps(tokens[tag], separators=(',', ':')).encode('utf-8')).hexdigest())
                       for tag in sorted(expected)],
                   token_hash_encoding='UTF8 compact JSON array of original CSV string tokens in comparison_field_order',
                   all_duplicate_complete_field_tokens_identical=True, all_other_multiplicities_one=True,
                   raw_rows_rewritten_or_averaged=False)
    return data, storage


def cdf_magic(path):
    with Path(path).open('rb') as stream:
        value = stream.read(4)
    need(value in (b'CDF\x01', b'CDF\x02'), 'Only complete CDF1/CDF2 Exodus files are supported')
    return value.hex()


def read_exodus(path):
    # The e382 decoder's read-only/mmap=False structure is reused, not its TET4/15-node case.
    from scipy.io import netcdf_file
    cdf_magic(path)
    with netcdf_file(str(path), mode='r', mmap=False, maskandscale=False) as dataset:
        dims = dataset.dimensions
        need(all(dims.get(k) == v for k, v in {'num_dim': 3, 'num_nodes': 425, 'num_elem': 256}.items()), 'Full fixed425/256 native mesh required in every family member')
        def array(name, shape=None):
            need(name in dataset.variables, 'Missing explicit Exodus variable: ' + name)
            a = dataset.variables[name].data.copy()
            need(shape is None or a.shape == shape, 'Exodus shape mismatch: ' + name)
            return a.tolist()
        def text(value):
            return b''.join(value).split(b'\0', 1)[0].decode('ascii').strip()
        node_map = list(map(integer, array('node_num_map', (425,))))
        element_map = list(map(integer, array('elem_num_map', (256,))))
        need(min(node_map) > 0 and min(element_map) > 0 and len(set(node_map)) == 425 and len(set(element_map)) == 256, 'Complete positive external Exodus ID maps required')
        coords = list(zip(*(array('coord' + k, (425,)) for k in 'xyz')))
        nodes = {tag - 1: tuple(map(number, xyz)) for tag, xyz in zip(node_map, coords)}
        block_ids = list(map(integer, array('eb_prop1')))
        statuses = list(map(integer, array('eb_status', (len(block_ids),))))
        need(len(set(block_ids)) == len(block_ids) and set(block_ids) <= {1, 2, 3}, 'Only fixed inactive/old/born native blocks permitted')
        cells = {}; blocks = {}; offset = 0
        for k, (block, status) in enumerate(zip(block_ids, statuses), 1):
            need(status in (0, 1), 'Explicit Exodus block status required')
            if not status:
                continue
            name = 'connect' + str(k)
            raw = array(name)
            kind = getattr(dataset.variables[name], 'elem_type', b'').decode().strip().upper()
            need(kind in ('HEX8', 'HEX') and raw and all(len(r) == 8 for r in raw), 'Only explicit complete HEX8 connectivity permitted')
            for row in raw:
                indices = list(map(integer, row)); need(min(indices) > 0 and max(indices) <= 425 and len(set(indices)) == 8, 'One-based local Exodus connectivity must be valid')
                tag = element_map[offset] - 1; offset += 1
                cells[tag] = [node_map[t - 1] - 1 for t in indices]; blocks[tag] = block
        need(offset == 256 and len(cells) == 256, 'Complete block-ordered external element map required')
        times = list(map(number, array('time_whole')))
        need(times and all(a < b for a, b in zip(times, times[1:])), 'Finite strictly ordered Exodus family times required')
        names = [text(r) for r in array('name_nod_var')]
        required = {*DISP, *FORCE, 'temperature'}
        if any(time >= .2 - 5e-13 for time in times):
            required.add('born_reference_temperature')
        allowed = {*DISP, *FORCE, 'temperature', 'born_reference_temperature', 'inactive_placeholder'}
        need(len(set(names)) == len(names) and required <= set(names) <= allowed, 'Named active coupon nodal fields required; empty-block reference/placeholder fields may be absent')
        fields = {name: array('vals_nod_var' + str(k), (len(times), 425)) for k, name in enumerate(names, 1)}
        return dict(nodes=nodes, cells=cells, blocks=blocks, times=times, node_map=node_map,
                    element_map=element_map, fields=fields, dimensions=dict(dims), block_ids=block_ids, block_status=statuses)


def geometry_family(directory, filenames, transfer):
    need(filenames == sorted(set(filenames)), 'Explicit unique ordered Exodus family required')
    observed = sorted(p.name for p in directory.iterdir() if re.fullmatch(r'thermoelastic(?:_out)?\.e(?:-s\d+)?', p.name))
    possible = sorted(p.name for p in directory.iterdir() if p.name.startswith('thermoelastic') and re.search(r'\.e(?:$|[-.])', p.name))
    need(possible == observed, 'Unknown Exodus-family naming/parallel format is unsupported, never silently omitted')
    need(observed == sorted(filenames) and observed, 'Exact full frozen Exodus family, including transition members, required')
    geometry = {r['source_node_id']: tuple(r['coordinates_m']) for r in transfer['node_rows']}
    need(len(transfer['node_rows']) == len(geometry) == 425 and len(set(map(bits, geometry.values()))) == 425
         and all(type(tag) is int and tag >= 0 and len(p) == 3 and all(type(x) is float and math.isfinite(x) for x in p) for tag, p in geometry.items()), 'Complete finite typed transfer source-node map required')
    mesh = None; frames = {}; member_rows = []
    for name in filenames:
        data = read_exodus(directory / name)
        need(set(data['nodes']) == set(geometry) and all(bits(xyz) == bits(geometry[tag]) for tag, xyz in data['nodes'].items()), 'External node_num_map minus1 and exact coordinate words must join every original source ID')
        if mesh is None:
            mesh = data['cells']
        need(data['cells'] == mesh, 'Every family must retain all native element IDs and ordered connectivity')
        boxes = set()
        for tag, conn in mesh.items():
            ordered_hex([geometry[n] for n in conn])
            hex_rule([geometry[n] for n in conn])
            box = tuple(min(geometry[n][j] for n in conn) for j in range(3)); need(box not in boxes, 'Duplicate native Cartesian cell refused'); boxes.add(box)
        need(boxes == set(product((i / 8 for i in range(16)), (i / 4 for i in range(4)), (i / 4 for i in range(4)))), 'Complete256 native HEX8 grid bijection required')
        for ti, time in enumerate(data['times']):
            step = round(time * 400)
            need(0 <= step <= 160 and abs(time - step / 400) <= 5e-13 and step not in frames, 'One unambiguous native END frame per exact fixed time required')
            for tag, conn in mesh.items():
                old = max(geometry[n][0] for n in conn) <= 1.
                need(data['blocks'][tag] == (2 if old else 1 if step < 80 else 3), 'Native per-element block transition must match old/inactive/born geometry')
            frames[step] = dict(member=name, index=ti, fields={field: {tag - 1: values[ti][k] for k, tag in enumerate(data['node_map'])} for field, values in data['fields'].items()})
        member_rows.append(dict(filename=name, sha256=sha(directory / name), magic=cdf_magic(directory / name), times=data['times'],
                                node_map=data['node_map'], element_map=data['element_map'], block_ids=data['block_ids'], block_status=data['block_status']))
    need(set(frames) == set(range(161)), 'Complete161 END Exodus frames required')
    return geometry, mesh, frames, member_rows


def quadrature_sample(path, geometry, cells, active, native_qp_coordinates, coordinate_tolerance):
    data = {}; covered = {}; targets = {tag: hex_rule([geometry[n] for n in cells[tag]]) for tag in active}
    for row in rows(path, ('elem_id', 'qp_id', 'x', 'y', 'z', *QP_FIELDS)):
        tag, qp = integer(row['elem_id']), integer(row['qp_id'])
        need(tag in active and 0 <= qp < 8 and (tag, qp) not in data, 'Sampler element ID must join observed elem_num_map minus1; unique QP0..7 required')
        xyz = tuple(number(row[k]) for k in 'xyz')
        matches = [k for k, (p, _, _, _) in enumerate(targets[tag]) if max(abs(a - b) for a, b in zip(xyz, p)) <= coordinate_tolerance]
        need(len(matches) == 1 and matches[0] not in covered.setdefault(tag, set()), 'Unique observed physical8-GP association required, without assumed QP ordering')
        covered[tag].add(matches[0]); key = (tag, qp)
        if key in native_qp_coordinates:
            need(bits(native_qp_coordinates[key]) == bits(xyz), 'Observed native QP ID/coordinate association changed')
        else:
            native_qp_coordinates[key] = xyz
        data[key] = (matches[0], {name: tensor(row, name) for name in TENSORS})
    need(set(covered) == set(active) and all(v == set(range(8)) for v in covered.values()), 'All eight physical Gauss points of every active cell required')
    return data


def field_phase(audit, geometry, cells, active, nodes, reference_u, reference_T, qp, constraints):
    forces = {tag: [0.] * 3 for tag in nodes}; observed_forces = {tag: [0.] * 3 for tag in nodes}
    independent = {}; strain_energy = 0.
    for tag in active:
        conn = cells[tag]; points = [geometry[n] for n in conn]
        expected = mechanical_state(points, [[nodes[n][k] for k in DISP] for n in conn],
                                    [nodes[n]['temperature'] for n in conn], [reference_u[n] for n in conn], [reference_T[n] for n in conn])
        for q in range(8):
            index, stored = qp[(tag, q)]; xyz, grad, weight, fields = expected[index]
            independent[(tag, q)] = fields
            for name in TENSORS:
                for i, j in COMP:
                    audit.close(stored[name][i][j], fields[name][i][j], 'stress_Pa' if name == 'stress' else 'strain')
            accumulate(forces, conn, grad, weight, fields['stress'])
            accumulate(observed_forces, conn, grad, weight, stored['stress'])
            strain_energy += .5 * weight * math.fsum(fields['stress'][i][j] * fields['elastic_strain'][i][j] for i in range(3) for j in range(3))
    need(math.isfinite(strain_energy) and strain_energy >= 0, 'Finite nonnegative elastic strain energy diagnostic required')
    for tag in nodes:
        for component in range(3):
            audit.close(forces[tag][component], observed_forces[tag][component], 'force_N')
            if (tag, component) not in constraints:
                audit.close(forces[tag][component], 0., 'force_N')
    return forces, strain_energy, independent


def assess_data(directory, transfer, source_directory, source_index, filenames, policy):
    audit = Audit(policy)
    geometry, cells, frames, family = geometry_family(directory, filenames, transfer)
    old_nodes = {tag for tag, p in geometry.items() if p[0] <= 1.}; born_nodes = {tag for tag, p in geometry.items() if p[0] >= 1.}
    old_cells = {t for t, conn in cells.items() if max(geometry[n][0] for n in conn) <= 1.}
    need((len(old_nodes), len(born_nodes), len(old_cells)) == (225, 225, 128), 'Fixed native old/born partition required')
    shared_nodes = old_nodes & born_nodes
    need(len(shared_nodes) == 25 and shared_nodes == {r['source_node_id'] for r in transfer['node_rows'] if r['shared'] is True},
         'Exact frozen source shared25 IDs must join the native old/born partition')
    constraints = {(0, 0), (0, 1), (0, 2), (32, 1), (32, 2), (137, 2)}
    need(geometry[0] == (0., 0., 0.) and geometry[32] == (1., 0., 0.) and geometry[137] == (0., 1., 0.), 'Observed exact support IDs and positions required')
    source = {(r['step'], r['phase']): r for r in source_index['selected']}
    need(len(source) == 321, 'Complete original321 thermal source associations required')
    def thermal(step, phase, active):
        item = source[(step, phase) if step else (0, 'end')]
        path = source_directory / item['filename']; need(sha(path) == item['sha256'], 'Original thermal source drift')
        return node_sample(path, geometry, active, ('temperature',))[0]  # Original thermal rows remain strictly unique.
    birth_T = {tag: value['temperature'] for tag, value in thermal(80, 'begin', set(geometry)).items() if tag in born_nodes}
    born_u = None; previous_end = None; previous_qp = None; qcoords = {}; summaries = []; total_qp = dict(begin=0, end=0)
    for step in range(161):
        active_nodes = old_nodes if step < 80 else set(geometry); active_cells = old_cells if step < 80 else set(cells)
        phase_state = {}
        for phase in ('begin', 'end'):
            cols = (*DISP, 'temperature') if phase == 'begin' else (*DISP, 'temperature', *FORCE)
            nodal, nodal_storage = node_sample(directory / f'thermoelastic_{phase}_{step:04d}.csv', geometry, active_nodes, cols,
                                               shared_nodes if step >= 80 else ())
            source_T = thermal(step, phase, active_nodes)
            for tag, row in nodal.items():
                audit.close(row['temperature'], source_T[tag]['temperature'], 'temperature_K')
                for component in range(3):
                    if (tag, component) in constraints:
                        audit.close(row[DISP[component]], 0., 'displacement_m')
            if phase == 'begin' and previous_end is not None:
                for tag, previous in previous_end.items():
                    for name in (*DISP, 'temperature'):
                        audit.close(nodal[tag][name], previous[name], 'temperature_K' if name == 'temperature' else 'displacement_m')
            if phase == 'begin' and step == 80:
                born_u = {tag: [nodal[tag][k] for k in DISP] for tag in born_nodes}
                for tag in born_nodes - old_nodes:
                    for value in born_u[tag]:
                        audit.close(value, 0., 'displacement_m')
            reference_path = directory / f'thermoelastic_reference_{phase}_{step:04d}.csv'
            reference_storage = None
            if step >= 80:
                ref, reference_storage = node_sample(reference_path, geometry, born_nodes, ('born_reference_temperature',))
                for tag in born_nodes:
                    audit.close(ref[tag]['born_reference_temperature'], birth_T[tag], 'temperature_K')
            elif reference_path.exists():
                need(not rows(reference_path, ('id', 'x', 'y', 'z', 'born_reference_temperature'), True), 'Prebirth reference sampler must have no active rows')
                reference_storage = dict(filename=reference_path.name, raw_csv_sha256=sha(reference_path),
                                         comparison_field_order=['id', 'x', 'y', 'z', 'born_reference_temperature'],
                                         raw_row_count=0, unique_source_ID_count=0, expected_shared_doublet_IDs=[], verified_doublets=[],
                                         raw_rows_rewritten_or_averaged=False)
            # Shared nodes have old and born material references; override per cell below.
            qp = quadrature_sample(directory / f'thermoelastic_{phase}_fields_{step:04d}.csv', geometry, cells, active_cells, qcoords, policy['QP_coordinate_m'])
            forces = {tag: [0.] * 3 for tag in active_nodes}; energy = 0.; computed = {}
            for subset, ru, rt in [(old_cells, {n: ZERO[0] for n in old_nodes}, {n: 400. for n in old_nodes})] + ([(set(cells) - old_cells, born_u, birth_T)] if step >= 80 else []):
                subset_nodes = {n for t in subset for n in cells[t]}; ns = {n: nodal[n] for n in subset_nodes}
                # A subdomain's interface nodal forces are not individually free equilibrium rows.
                all_constrained = {(n, k) for n in subset_nodes for k in range(3)}
                f, en, state = field_phase(audit, geometry, cells, subset, ns, ru, rt, qp, all_constrained)
                for n, values in f.items():
                    for k in range(3): forces[n][k] += values[k]
                energy += en; computed.update(state)
            for tag in active_nodes:
                for k in range(3):
                    if (tag, k) not in constraints: audit.close(forces[tag][k], 0., 'force_N')
            if phase == 'begin' and previous_qp is not None:
                for key, (_, tensors) in qp.items():
                    if key in previous_qp:
                        before = previous_qp[key][1]
                        for name in TENSORS:
                            for i, j in COMP: audit.close(tensors[name][i][j], before[name][i][j], 'stress_Pa' if name == 'stress' else 'strain')
                    else:
                        need(step == 80 and key[0] not in old_cells, 'Only newborn material rows may appear')
                        for name in TENSORS:
                            for i, j in COMP: audit.close(tensors[name][i][j], 0., 'stress_Pa' if name == 'stress' else 'strain')
            if phase == 'end':
                for tag in active_nodes:
                    for k, name in enumerate(FORCE): audit.close(nodal[tag][name], forces[tag][k], 'force_N')
                reaction = [[nodal[n][k] if (n, j) in constraints else 0. for j, k in enumerate(FORCE)] for n in sorted(active_nodes)]
                all_forces = [[nodal[n][k] for k in FORCE] for n in sorted(active_nodes)]
                for force_rows in (reaction, all_forces):
                    for j in range(3):
                        audit.close(math.fsum(v[j] for v in force_rows), 0., 'force_N')
                        audit.close(math.fsum(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3] for n, v in zip(sorted(active_nodes), force_rows)), 0., 'moment_Nm')
                frame = frames[step]['fields']
                for tag in active_nodes:
                    for name in cols: audit.close(frame[name][tag], nodal[tag][name], 'temperature_K' if name == 'temperature' else 'displacement_m' if name in DISP else 'force_N')
                if step >= 80:
                    for tag in born_nodes: audit.close(frame['born_reference_temperature'][tag], birth_T[tag], 'temperature_K')
                begin_qp = phase_state['begin'][1]
                for key, (_, tensors) in qp.items():
                    for name in TENSORS:
                        for i, j in COMP:
                            observed = tensors[name][i][j] - begin_qp[key][1][name][i][j]
                            expected = computed[key][name][i][j] - phase_state['begin'][2][key][name][i][j]
                            audit.close(observed, expected, 'stress_Pa' if name == 'stress' else 'strain')
                previous_end = nodal; previous_qp = qp
            phase_state[phase] = (nodal, qp, computed); total_qp[phase] += len(qp)
            summaries.append(dict(step=step, phase=phase, active_nodes=len(nodal), active_cells=len(active_cells), quadrature_rows=len(qp), elastic_strain_energy_J_diagnostic=energy,
                                  native_nodal_storage=nodal_storage, born_reference_storage=reference_storage))
    need(total_qp == dict(begin=247808, end=247808) and len(qcoords) == 2048, 'Complete fixed161-phase/8-GP coverage required')
    return dict(passed=True, maximum_SI_errors=audit.maximum, scalar_comparisons=audit.counts, phase_summaries=summaries,
                native_nodes=[dict(id=t, coordinates_m=list(p)) for t, p in sorted(geometry.items())],
                native_ordered_cells=[dict(id=t, nodes=row) for t, row in sorted(cells.items())], exodus_family=family,
                observed_QP_ID_coordinate_map=[dict(elem_id=t, qp_id=q, coordinates_m=list(x)) for (t, q), x in sorted(qcoords.items())],
                quadrature_rows=total_qp, PETSc_order_assumed=False, work_equals_2U_used=False,
                material_process_head_or_manufacturing_qualified=False)


def assess(contract_path, digest):
    contract_path = Path(contract_path)
    need(contract_path.is_file() and not contract_path.is_symlink() and sha(contract_path) == digest, 'Exact external assessment actual required')
    c = json.loads(contract_path.read_text()); held = json.loads((PREP / 'held-preparation.json').read_text())
    need(c.get('schema') == '962-cp1-oneway-thermoelastic-assessment-actual/v1' and c.get('assessment_authorized') is True
         and c.get('root_and_independent_source_review_complete') is True and c.get('native_completed_and_peer_reviewed') is True
         and all(c.get(k) is False for k in ('native_execution_authorized', 'automatic_retry', 'head_execution_authorized', 'engineering_accepted', 'physics_qualified', 'material_qualified', 'process_calibrated', 'manufacturing_authorized')),
         'Only separately reviewed saved-data assessment is authorized')
    output = ROOT / OUTPUT
    need(c.get('output_directory') == OUTPUT and not output.exists() and not output.is_symlink(), 'Fresh fixed assessment output required before reading saved fields')
    pins = c['input_sha256']
    need(all(pins.get(k) == v for k, v in held['input_sha256'].items()) and pins.get(str((PREP / 'held-preparation.json').relative_to(ROOT))) == sha(PREP / 'held-preparation.json'), 'All held sources require direct pins')
    def checked():
        for name, expected in pins.items():
            p = ROOT / name
            need(not Path(name).is_absolute() and '..' not in Path(name).parts and p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT) and sha(p) == expected, 'Direct saved input drift: ' + name)
        need(sha(contract_path) == digest, 'Assessment actual drift')
    checked()
    policy = json.loads((PREP / 'POLICY.json').read_text())['absolute_SI_limits']
    need(c.get('native_directory') == 'work/962-engineering/cp1-oneway-thermoelastic-transfer-002', 'Only the fixed future native coupon may be assessed')
    native = ROOT / c['native_directory']; receipt = json.loads((native / 'native-execution.json').read_text())
    need(receipt.get('native_execution_completed') is True and receipt.get('returncode') == 0 and receipt.get('inputs_unchanged') is True and receipt.get('binary_and_runtime_unchanged') is True, 'Stopped completed immutable native receipt required')
    need(receipt.get('process_reaped') is True and receipt.get('physics_contract_sha256') == sha(CASE / 'case-contract.json')
         and (native / 'frozen-contract.json').read_bytes() == (CASE / 'case-contract.json').read_bytes(), 'Exact source physics and stopped native lifecycle required')
    native_actual = json.loads((native / 'actual-contract.json').read_text())
    need(sha(native / 'actual-contract.json') == receipt['actual_contract_sha256']
         and native_actual.get('schema') == '962-macos-oneway-thermoelastic-case-actual/v1'
         and all(native_actual['input_sha256'].get(k) == v for k, v in json.loads((CASE / 'held-preparation.json').read_text())['input_sha256'].items()), 'Same separately authorized source-bound native actual required')
    inventory = c['native_output_inventory']
    entries = list(native.rglob('*'))
    need(not any(p.is_symlink() for p in entries)
         and {str(p.relative_to(native)) for p in entries if p.is_file()} == set(inventory), 'Complete recursive native output inventory, including source snapshots; no omissions or symlinks')
    for name, record in inventory.items():
        path = native / name; need(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'] and pins.get(str(path.relative_to(ROOT))) == record['sha256'], 'Every original native artifact requires exact inventory and direct pin')
    need(receipt['complete_artifact_sha256'] == {name: record['sha256'] for name, record in inventory.items() if name != 'native-execution.json'}
         and receipt['artifact_sha256'] == {name: record['sha256'] for name, record in inventory.items() if name != 'native-execution.json' and Path(name).name == name}, 'Separate complete recursive and flat native receipt closures required')
    selection = json.loads((ROOT / c['runtime_selection']).read_text())
    need(sha(ROOT / c['runtime_selection']) == '2b3b2ac0f52ecef6f349d45524f26011da94c257fc0ede5067a9f236681e9713'
         and sha(Path(sys.executable).resolve()) == selection['Python_sha256'], 'Exact selected decoder metadata and interpreter required')
    for name, record in selection['files'].items(): need(sha(Path(selection['site_packages']) / name) == record['sha256'], 'Selected decoder runtime drift')
    import numpy, scipy
    need(numpy.__version__ == '2.2.6' and scipy.__version__ == '1.17.1', 'Exact reviewed decoder runtime versions required')
    from scipy.io import netcdf_file
    need(Path(numpy.__file__).resolve() == (Path(selection['site_packages']) / 'numpy/__init__.py').resolve()
         and Path(scipy.__file__).resolve() == (Path(selection['site_packages']) / 'scipy/__init__.py').resolve()
         and netcdf_file.__module__ == 'scipy.io._netcdf'
         and Path(sys.modules[netcdf_file.__module__].__file__).resolve() == (Path(selection['site_packages']) / 'scipy/io/_netcdf.py').resolve(), 'Actual decoder import origins must equal selected files')
    transfer = json.loads((ROOT / c['transfer_manifest']).read_text()); need(transfer.get('schema') == '962-oneway-thermoelastic-prepared-transfer/v1' and transfer.get('birth_reference_phase') == 'BEGIN80_all225_born_DOFs_including25shared', 'Exact completed original transfer associations required')
    need(pins.get(c['transfer_manifest']) == receipt['transfer_manifest_sha256'] == sha(ROOT / c['transfer_manifest']), 'Native and assessor must use the same completed transfer manifest')
    result = assess_data(native, transfer, ROOT / 'work/962-engineering/cp1-assumed-thermal-birth-linear-001', json.loads((CASE / 'thermal-input-index.json').read_text()), c['exodus_family'], policy)
    checked()
    for name, record in inventory.items(): need(sha(native / name) == record['sha256'], 'Native output drift during assessment')
    for name, record in selection['files'].items(): need(sha(Path(selection['site_packages']) / name) == record['sha256'], 'Selected decoder runtime changed')
    need(c.get('output_directory') == OUTPUT and not output.exists() and not output.is_symlink(), 'Fresh fixed assessment output required')
    result.update(schema='962-cp1-oneway-thermoelastic-saved-field-assessment/v1', actual_sha256=digest, input_sha256=pins,
                  source_physics_contract_sha256=sha(CASE / 'case-contract.json'), policy_sha256=sha(PREP / 'POLICY.json'),
                  native_original_receipt_passed_field=receipt.get('passed'), native_receipt_is_not_assessment_authority=True,
                  decoder_runtime_selection_sha256='2b3b2ac0f52ecef6f349d45524f26011da94c257fc0ede5067a9f236681e9713',
                  decoder_selected_file_count=len(selection['files']), decoder_complete_ABI_or_OS_closure_claimed=False,
                  source_and_runtime_inputs_unchanged=True, mechanical_space_time_convergence=False,
                  head_execution_authorized=False, engineering_accepted=False, physics_qualified=False,
                  material_qualified=False, process_calibrated=False, manufacturing_authorized=False)
    output.mkdir()
    with (output / 'assessment.json').open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path); parser.add_argument('contract_sha256')
    args = parser.parse_args(); assess(args.contract, args.contract_sha256)
