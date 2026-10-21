"""HELD one-phase END181 equilibrium localization; never launches or reruns the assessor/solver."""
import csv
from decimal import Decimal, localcontext
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import re
import struct
import sys

ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993')
BASE = ROOT / 'work/962-engineering'
HERE = Path(__file__).resolve().parent
HELD = HERE / 'held-preparation.json'
NATIVE = BASE / 'cp1-oneway-cooling-release-richardson2-001'
OUTPUT = BASE / 'cp1-oneway-cooling-release-richardson2-END181-equilibrium-diagnostic-001'
AUTHORIZATION = BASE / 'cp1-oneway-cooling-release-richardson2-END181-equilibrium-diagnostic-root-execution-001/authorization.json'
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

def support_masks(geometry, active_nodes, step, phase):
    need(type(step) is int and 0 <= step <= 182 and phase in ('begin', 'end'), 'Fixed183-step phase required')
    point = {(0, 0), (0, 1), (0, 2), (32, 1), (32, 2), (137, 2)}
    need(geometry.get(0) == (0., 0., 0.) and geometry.get(32) == (1., 0., 0.)
         and geometry.get(137) == (0., 1., 0.), 'Exact original six support IDs/positions required')
    clamp = {(tag, component) for tag in active_nodes if geometry[tag][2] == 0. for component in range(3)}
    need(len(clamp) == (135 if step < 80 else 255) and point <= clamp,
         'Exact45/85 active z=0 plane nodes and six remaining components required')
    constrained = clamp if step < 181 else point
    universe = {(tag, component) for tag in active_nodes for component in range(3)}
    free = universe - constrained
    need(constrained <= universe and not constrained & free and constrained | free == universe,
         'One complete disjoint constrained/free mask; no simultaneous clamp/point BCs')
    released = clamp - point if step == 181 and phase == 'begin' else set()
    # BEGIN181 is inherited END180 state, before the new free rows have equilibrated.
    # Only newly released components are exempt then; every END row is checked.
    need(not released or (len(released) == 249 and released <= free), 'Only249 newly released BEGIN181 components may be unequilibrated')
    return constrained, free, released

def read_geometry_phase(path):
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
        matches = [index for index, value in enumerate(times) if round(value * 400) == 181 and abs(value - 181 / 400) <= 5e-13]
        need(len(matches) == 1, 'Exactly one END181 time association in the selected family member required')
        return dict(nodes=nodes, cells=cells, blocks=blocks, times=times, node_map=node_map,
                    element_map=element_map, dimensions=dict(dims), block_ids=block_ids,
                    block_status=statuses, END181_time_index=matches[0], END181_native_time=times[matches[0]])


class DiagnosticAudit:
    """Record unchanged scalar gates; exceeding one never means field acceptance."""
    def __init__(self, policy):
        self.policy = policy
        self.counts = {}
        self.maximum = {}
        self.exceedances = []
        self.context = None

    def close(self, a, b, unit):
        a, b = number(a), number(b)
        error = abs(a - b)
        self.counts[unit] = self.counts.get(unit, 0) + 1
        observation = dict(unit=unit, value=a, reference=b, absolute_error=error,
                           unchanged_limit=self.policy[unit], context=self.context)
        if unit not in self.maximum or error > self.maximum[unit]['absolute_error']:
            self.maximum[unit] = observation
        if not error <= self.policy[unit]:
            self.exceedances.append(observation)


def vector_rows(values, active, constraints, rowset):
    return [[values[tag][j] if rowset == 'all' or ((tag, j) in constraints) == (rowset == 'constrained') else 0.
             for j in range(3)] for tag in sorted(active)]


def resultants(values, geometry, active, constraints):
    out = {}
    for rowset in ('constrained', 'free', 'all'):
        force_rows = vector_rows(values, active, constraints, rowset)
        components = []
        for j in range(3):
            force_sum = math.fsum(v[j] for v in force_rows)
            moment_sum = math.fsum(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3] for n, v in zip(sorted(active), force_rows))
            components.append(dict(component=j, force_N=force_sum, force_binary64_hex=force_sum.hex(),
                moment_Nm=moment_sum, moment_binary64_hex=moment_sum.hex(),
                force_L1_N=math.fsum(abs(v[j]) for v in force_rows),
                force_max_abs_term_N=max(abs(v[j]) for v in force_rows),
                moment_L1_Nm=math.fsum(abs(geometry[n][(j+1)%3]*v[(j+2)%3] - geometry[n][(j+2)%3]*v[(j+1)%3]) for n, v in zip(sorted(active), force_rows)),
                original_force_limit_N=1e-7, original_moment_limit_Nm=1e-7,
                force_exceeds_original_gate=not (abs(force_sum - 0.) <= 1e-7),
                moment_exceeds_original_gate=not (abs(moment_sum - 0.) <= 1e-7)))
        out[rowset] = components
    return out


def main(authorization_sha256=None):
    # An absent external authorization refuses before metadata, runtime, CSV or CDF body access.
    need(isinstance(authorization_sha256, str) and re.fullmatch('[0-9a-f]{64}', authorization_sha256),
         'HELD: exact separate root authorization digest required')
    need(AUTHORIZATION.is_file() and not AUTHORIZATION.is_symlink() and sha(AUTHORIZATION) == authorization_sha256,
         'Exact separate root authorization required')
    held = json.loads(HELD.read_text()); authorization = json.loads(AUTHORIZATION.read_text())
    need(authorization.get('schema') == '962-richardson2-cooling-END181-equilibrium-diagnostic-authorization/v1'
         and authorization.get('diagnostic_execution_authorized') is True
         and authorization.get('root_and_independent_source_review_complete') is True
         and authorization.get('source') == held['source']
         and authorization.get('held') == dict(path=str(HELD.relative_to(ROOT)), sha256=sha(HELD), bytes=HELD.stat().st_size)
         and all(authorization.get(key) is False for key in ('native_execution_authorized', 'assessment_execution_authorized',
             'automatic_retry', 'head_execution_authorized', 'engineering_accepted', 'physics_qualified',
             'material_qualified', 'process_calibrated', 'manufacturing_authorized')),
         'Only reviewed fixed-phase diagnostics are authorized')
    need(authorization.get('ordinary_seconds') == 60 and authorization.get('TERM_grace_seconds') == 8
         and authorization.get('sampled_RSS_stop_bytes') == 2147483648
         and authorization.get('sampled_output_stop_bytes') == 33554432
         and authorization.get('new_owned_session') is True and authorization.get('verified_owned_KILL_wait') is True,
         'Separate ordinary60s/T8/2GiB/32MiB owned lifecycle required')
    need(not OUTPUT.exists() and not OUTPUT.is_symlink(), 'Fresh fixed diagnostic output required')
    for name, record in held['metadata_records'].items():
        path = ROOT / name
        need(path.is_file() and not path.is_symlink() and path.resolve() == path
             and path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], 'Direct metadata drift')
    for name, record in held['raw_input_records'].items():
        path = NATIVE / name
        need(path.is_file() and not path.is_symlink() and path.resolve() == path
             and str(path.relative_to(ROOT)) == record['path'] and path.stat().st_size == record['bytes']
             and sha(path) == record['sha256'], 'One of five fixed raw input identities changed')
    cap = json.loads((ROOT / held['native_root_closed']['path']).read_text())
    for name, record in held['raw_input_records'].items():
        need(cap['outputs'][name] == record, 'Every selected raw input must join the exact capture inventory')
    storage = json.loads((ROOT / held['complete_storage_result']['path']).read_text())
    storage_admission = json.loads((ROOT / held['storage_root_acceptance']['path']).read_text())
    need(storage['status'] == 'PASS_OBSERVED_MULTIPLICITY_AND_LEXICAL_ASSOCIATIONS_ONLY'
         and storage['negatives'] == [] and storage['scanned_CSVs'] == 732
         and storage_admission['decision'] == 'ACCEPT_COMPLETE732_LEXICAL_STORAGE_ONLY_FULL_FIELD_ASSESSMENT_STILL_PENDING',
         'Accepted complete original lexical storage required')
    for name in ('thermoelastic_end_0181.csv', 'thermoelastic_begin_0080.csv', 'thermoelastic_reference_begin_0080.csv'):
        need(storage['files'][name]['sha256'] == held['raw_input_records'][name]['sha256'], 'Prior full lexical proof must bind the exact original CSV')
    selection = json.loads((ROOT / held['decoder_selection']['path']).read_text())
    need(held['decoder_selection']['sha256'] == '2b3b2ac0f52ecef6f349d45524f26011da94c257fc0ede5067a9f236681e9713'
         and sha(Path(sys.executable).resolve()) == selection['Python_sha256'] and len(selection['files']) == 258,
         'Exact selected1699/258 decoder required')
    for name, record in selection['files'].items():
        need(sha(Path(selection['site_packages']) / name) == record['sha256'], 'Selected decoder drift')
    import numpy, scipy
    from scipy.io import netcdf_file
    need(numpy.__version__ == '2.2.6' and scipy.__version__ == '1.17.1'
         and Path(numpy.__file__).resolve() == (Path(selection['site_packages']) / 'numpy/__init__.py').resolve()
         and Path(scipy.__file__).resolve() == (Path(selection['site_packages']) / 'scipy/__init__.py').resolve()
         and netcdf_file.__module__ == 'scipy.io._netcdf'
         and Path(sys.modules[netcdf_file.__module__].__file__).resolve() == (Path(selection['site_packages']) / 'scipy/io/_netcdf.py').resolve(),
         'Exact decoder versions and origins required')
    transfer = json.loads((ROOT / held['accepted_transfer_manifest']['path']).read_text())
    geometry = {row['source_node_id']: tuple(row['coordinates_m']) for row in transfer['node_rows']}
    need(len(geometry) == len(transfer['node_rows']) == 425 and len(set(map(bits, geometry.values()))) == 425,
         'Complete accepted425 source node map required')
    mesh = read_geometry_phase(NATIVE / 'thermoelastic.e-s002')
    need(set(mesh['nodes']) == set(geometry)
         and all(bits(mesh['nodes'][tag]) == bits(geometry[tag]) for tag in geometry),
         'Complete external node_num_map minus1/coordinate-word association required')
    cells = mesh['cells']; boxes = set()
    for tag, conn in cells.items():
        ordered_hex([geometry[n] for n in conn]); hex_rule([geometry[n] for n in conn])
        box = tuple(min(geometry[n][j] for n in conn) for j in range(3))
        need(box not in boxes, 'No duplicate HEX8 grid cell'); boxes.add(box)
    need(boxes == set(product((i / 8 for i in range(16)), (i / 4 for i in range(4)), (i / 4 for i in range(4)))),
         'Complete original256 HEX8 grid bijection required')
    old_nodes = {tag for tag, point in geometry.items() if point[0] <= 1.}
    born_nodes = {tag for tag, point in geometry.items() if point[0] >= 1.}
    shared = old_nodes & born_nodes
    old_cells = {tag for tag, conn in cells.items() if max(geometry[n][0] for n in conn) <= 1.}
    need((len(old_nodes), len(born_nodes), len(shared), len(old_cells), len(cells)) == (225,225,25,128,256),
         'Exact old/born/shared/cell partition required')
    need(all(mesh['blocks'][tag] == (2 if tag in old_cells else 3) for tag in cells),
         'END181 native old2/born3 per-element blocks required')
    policy = json.loads((ROOT / held['POLICY']['path']).read_text())['absolute_SI_limits']
    need(policy == held['unchanged_seven_absolute_SI_limits'], 'No SI threshold change')
    audit = DiagnosticAudit(policy)
    born_begin, born_storage = node_sample(NATIVE / 'thermoelastic_begin_0080.csv', geometry, set(geometry), (*DISP, 'temperature'), shared)
    reference, reference_storage = node_sample(NATIVE / 'thermoelastic_reference_begin_0080.csv', geometry, born_nodes, ('born_reference_temperature',))
    born_u = {tag: [born_begin[tag][key] for key in DISP] for tag in born_nodes}
    birth_T = {tag: reference[tag]['born_reference_temperature'] for tag in born_nodes}
    audit.context = 'own_BEGIN80_born_reference_temperature_vs_own_nodal_temperature'
    for tag in born_nodes: audit.close(birth_T[tag], born_begin[tag]['temperature'], 'temperature_K')
    audit.context = 'own_BEGIN80_newborn_displacement_reference'
    for tag in born_nodes - old_nodes:
        for value in born_u[tag]: audit.close(value, 0., 'displacement_m')
    nodal, nodal_storage = node_sample(NATIVE / 'thermoelastic_end_0181.csv', geometry, set(geometry), (*DISP, 'temperature', *FORCE), shared)
    constraints, free, released = support_masks(geometry, set(geometry), 181, 'end')
    need(len(constraints) == 6 and len(free) == 1269 and not released, 'Original released END181 six-point constraints only')
    audit.context = 'END181_prescribed300K_and_six_constrained_displacements'
    for tag, row in nodal.items():
        audit.close(row['temperature'], 300., 'temperature_K')
        for j in range(3):
            if (tag,j) in constraints: audit.close(row[DISP[j]], 0., 'displacement_m')
    qp = quadrature_sample(NATIVE / 'thermoelastic_end_fields_0181.csv', geometry, cells, set(cells), {}, policy['QP_coordinate_m'])
    forces = {tag: [0.] * 3 for tag in set(geometry)}; energy = 0.; computed = {}
    assembly_order = []
    for label, subset, ru, rt in [('old2', old_cells, {n: ZERO[0] for n in old_nodes}, {n:400. for n in old_nodes}),
                                  ('born3', set(cells)-old_cells, born_u, birth_T)]:
        subset_nodes = {n for tag in subset for n in cells[tag]}; ns = {n:nodal[n] for n in subset_nodes}
        all_constrained = {(n,k) for n in subset_nodes for k in range(3)}
        audit.context = 'END181_' + label + '_exact_field_phase'
        f, en, state = field_phase(audit, geometry, cells, subset, ns, ru, rt, qp, all_constrained)
        for n, values in f.items():
            for k in range(3): forces[n][k] += values[k]
        energy += en; computed.update(state)
        assembly_order.append(dict(region=label, cell_iteration_order=list(subset), node_iteration_order=list(subset_nodes)))
    components = []; maxima = {}; native = {tag:[nodal[tag][name] for name in FORCE] for tag in geometry}
    for tag in sorted(geometry):
        for j in range(3):
            error = abs(native[tag][j] - forces[tag][j]); constrained = (tag,j) in constraints
            row = dict(source_ID=tag, component=j, constrained=constrained,
                coordinate_binary64_LE_hex=bits(geometry[tag]).hex(),
                native_force_N=native[tag][j], native_binary64_hex=native[tag][j].hex(),
                assembled_force_N=forces[tag][j], assembled_binary64_hex=forces[tag][j].hex(),
                native_minus_assembled_N=native[tag][j]-forces[tag][j], absolute_error_N=error,
                original_force_limit_N=policy['force_N'], exceeds_original_force_limit=not error<=policy['force_N'],
                native_original_CSV_lines=[line for line, source_ID in enumerate(storage['files']['thermoelastic_end_0181.csv']['raw_ordered_source_IDs'],2) if source_ID==tag])
            components.append(row)
            for metric, value in [('native_vs_assembled_'+('constrained' if constrained else 'free'),error),
                                  ('native_'+('constrained' if constrained else 'free')+'_absolute_residual',abs(native[tag][j])),
                                  ('assembled_'+('constrained' if constrained else 'free')+'_absolute_residual',abs(forces[tag][j]))]:
                key = metric + '_component' + str(j)
                if key not in maxima or value > maxima[key]['magnitude_N']:
                    maxima[key] = dict(magnitude_N=value, witness=row)
            audit.context = 'END181_native_vs_assembled_force'; audit.close(native[tag][j], forces[tag][j], 'force_N')
            if not constrained:
                audit.context = 'END181_independent_free_DOF_residual'; audit.close(forces[tag][j], 0., 'force_N')
    native_sums = resultants(native, geometry, set(geometry), constraints)
    assembled_sums = resultants(forces, geometry, set(geometry), constraints)
    for name, record in held['raw_input_records'].items(): need(sha(NATIVE/name)==record['sha256'], 'Fixed raw input changed')
    for name, record in held['metadata_records'].items(): need(sha(ROOT/name)==record['sha256'], 'Fixed metadata changed')
    for name, record in selection['files'].items(): need(sha(Path(selection['site_packages'])/name)==record['sha256'], 'Selected decoder changed')
    need(sha(AUTHORIZATION)==authorization_sha256, 'External authorization changed')
    result = dict(schema='962-richardson2-cooling-END181-one-phase-independent-equilibrium-localization/v1',
        status='COMPLETED_SINGLE_PHASE_DIAGNOSTIC_ONLY', step=181, phase='end',
        source=held['source'], input_metadata=held['metadata_records'], raw_inputs=held['raw_input_records'],
        selected_geometry_member='thermoelastic.e-s002', selected_END181_time=mesh['END181_native_time'],
        selected_END181_time_index=mesh['END181_time_index'],
        geometry_scope='One selected member geometry/block/external-ID/time only; no nodal frame variables requested, no complete family assessment.',
        complete_source_ID_coordinate_binary64_LE_hex={str(tag):bits(geometry[tag]).hex() for tag in sorted(geometry)},
        complete_ordered_HEX8_cells=[dict(source_cell_ID=tag,nodes=conn,block=mesh['blocks'][tag]) for tag,conn in sorted(cells.items())],
        QP_map_count=len(qp), QP_coordinate_tolerance_m=policy['QP_coordinate_m'],
        own_BEGIN80_reference=dict(node_storage=born_storage,reference_storage=reference_storage,
            born_u_and_Tref=[dict(source_ID=tag,u=born_u[tag],u_hex=[x.hex() for x in born_u[tag]],Tref_K=birth_T[tag],Tref_hex=birth_T[tag].hex()) for tag in sorted(born_nodes)]),
        END181_nodal_storage=nodal_storage, constrained_DOFs=sorted(map(list,constraints)),free_DOF_count=len(free),
        native_resultants=native_sums,independently_assembled_resultants=assembled_sums,
        all1275_native_vs_assembled_component_observations=components,per_component_maxima_and_witnesses=maxima,
        exact_region_assembly_iteration_order=assembly_order,elastic_strain_energy_J=energy,
        unchanged_scalar_gate_observations=dict(counts=audit.counts,maximum=audit.maximum,exceedances=audit.exceedances),
        accepted_original_thermal_values_metadata_only_root_attributed=True,
        source_math_and_limits_unchanged=True,original_full_assessment_refusal_retained=True,
        mathematical_or_solver_cause=None,IEEE_floor_or_roundoff_cause=None,feasibility_claim=None,
        full_trajectory_or_assessor_reexecuted=False,native_solver_replayed=False,
        seven_SI_or_full_fields_accepted=False,engineering_accepted=False,physics_qualified=False,
        material_qualified=False,process_calibrated=False,head_execution_authorized=False,manufacturing_authorized=False)
    encoded=(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n').encode()
    need(len(encoded)<=33554432 and not OUTPUT.exists(), 'Fresh bounded diagnostic JSON required')
    OUTPUT.mkdir()
    with (OUTPUT/'diagnostic.json').open('xb') as stream: stream.write(encoded)
    print(json.dumps(dict(status=result['status'],step=181,phase='end',native_resultants=native_sums,
        assembled_resultants=assembled_sums,scalar_gate_exceedances=len(audit.exceedances))))


if __name__ == '__main__':
    need(len(sys.argv) in (1,2), 'Exactly one external root authorization digest, or held invocation required')
    main(sys.argv[1] if len(sys.argv)==2 else None)
