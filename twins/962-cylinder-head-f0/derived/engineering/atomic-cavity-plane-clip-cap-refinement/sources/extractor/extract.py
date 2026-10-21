"""Copy the frozen cap bytes and separately serialize the saved mixed keeper map."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
MAGIC = b'962SURF1'


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def ids(values, message):
    need(isinstance(values, list) and all(type(v) is int and v >= 0 for v in values), message)
    need(values == sorted(set(values)), message)
    return values


def mapped_cycle(loop, mapping):
    result = []
    for vertex in loop:
        value = mapping.get(vertex, vertex)
        if not result or result[-1] != value:
            result.append(value)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def payloads(source, face_ids, cycles, choices, fixed_faces):
    """Only integer reindexing; coordinate rows are copied as opaque 24-byte strings."""
    ids(face_ids, 'Sorted unique source face IDs required')
    ids(fixed_faces, 'Sorted unique fixed source face IDs required')
    with Path(source).open('rb') as stream:
        header = stream.read(24)
        need(len(header) == 24 and header[:8] == MAGIC, 'Exact SURF1 header required')
        nv, nf = struct.unpack('<QQ', header[8:])
        need(Path(source).stat().st_size == 24 + 24 * (nv + nf), 'Exact SURF1 byte length required')
        need(face_ids and face_ids[-1] < nf, 'Source face association outside input')
        rows = []
        for fid in face_ids:
            stream.seek(24 + 24 * nv + 24 * fid)
            row = struct.unpack('<QQQ', stream.read(24))
            need(len(set(row)) == 3 and max(row) < nv, 'Invalid source triangle indices')
            rows.append(row)
        vertices = sorted({v for row in rows for v in row})
        local = {v: i for i, v in enumerate(vertices)}
        points = []
        for vertex in vertices:
            stream.seek(24 + 24 * vertex)
            bits = stream.read(24)
            xyz = struct.unpack('<ddd', bits)
            need(all(math.isfinite(v) for v in xyz) and xyz[2] == 0, 'Finite source cap coordinates at z0 required')
            points.append(bits)
    need(len(cycles) == 2 and all(isinstance(c, list) and len(c) >= 3 for c in cycles), 'Two source cycles required')
    need(all(type(v) is int and v in local for c in cycles for v in c), 'Source cycle vertex association')
    need(len({v for c in cycles for v in c}) == sum(map(len, cycles)) == len(vertices), 'Complete all-boundary cap vertex identity')
    mapping = {}
    for group in choices:
        members = ids(group['members'], 'Sorted unique group members required')
        keeper = group['selected_keeper']
        need(members and type(keeper) is int and keeper in members and set(members) <= set(local), 'Keeper/member cap association')
        need(not set(members).intersection(mapping), 'Disjoint saved groups required')
        for vertex in members:
            mapping[vertex] = keeper
    face_local = {v: i for i, v in enumerate(face_ids)}
    need(set(fixed_faces) <= set(face_local), 'Fixed face is not in complete cap')
    fixed_vertices = {v for fid in fixed_faces for v in rows[face_local[fid]]}
    need(all(mapping.get(v, v) == v for v in fixed_vertices), 'Fixed cap vertex mapping must be identity')
    pairs = sorted((local[a], local[b]) for a, b in mapping.items())
    pack = lambda values: b''.join(struct.pack('<Q', v) for v in values)
    data = {
        'cap.bin': MAGIC + struct.pack('<QQ', len(vertices), len(rows)) + b''.join(points) +
            b''.join(struct.pack('<QQQ', *(local[v] for v in row)) for row in rows),
        'local-to-global-vertices.u64': pack(vertices),
        'local-to-global-faces.u64': pack(face_ids),
        'old-to-keeper.u64': b''.join(struct.pack('<QQ', a, b) for a, b in pairs),
        'fixed-face-ids.u64': pack(sorted(face_local[v] for v in fixed_faces)),
    }
    mapped = [mapped_cycle(c, mapping) for c in cycles]
    need(mapped[1] == cycles[1], 'Outer cycle must remain unchanged')
    need(len({v for c in mapped for v in c}) == sum(map(len, mapped)), 'Mapped cycle IDs must be unique and disjoint')
    meta = dict(source_vertices=nv, source_faces=nf, cap_vertices=len(vertices), cap_faces=len(rows),
        keeper_groups=len(choices), map_rows=len(pairs), identity_map_rows=sum(a == b for a, b in pairs),
        nonidentity_map_rows=sum(a != b for a, b in pairs), fixed_faces=len(fixed_faces),
        fixed_vertex_maps_identity=True, source_cycles_global=cycles, mapped_cycles_global=mapped,
        source_cycles_local=[[local[v] for v in c] for c in cycles],
        mapped_cycles_local=[[local[v] for v in c] for c in mapped])
    return data, meta


def readback(output, source, data, meta):
    """Full emitted-file comparisons, then an independently decoded integer/source-row check."""
    for name, expected in data.items():
        need((output / name).read_bytes() == expected, 'Output byte readback differs: ' + name)
    cap = (output / 'cap.bin').read_bytes()
    nv, nf = struct.unpack_from('<QQ', cap, 8)
    vertices = list(struct.unpack('<' + 'Q' * nv, (output / 'local-to-global-vertices.u64').read_bytes()))
    faces = list(struct.unpack('<' + 'Q' * nf, (output / 'local-to-global-faces.u64').read_bytes()))
    with Path(source).open('rb') as stream:
        for i, global_id in enumerate(vertices):
            stream.seek(24 + 24 * global_id)
            need(cap[24 + 24*i:48 + 24*i] == stream.read(24), 'Source coordinate bits changed')
        for i, global_id in enumerate(faces):
            row = struct.unpack_from('<QQQ', cap, 24 + 24*nv + 24*i)
            stream.seek(24 + 24*meta['source_vertices'] + 24*global_id)
            need(struct.pack('<QQQ', *(vertices[v] for v in row)) == stream.read(24), 'Source oriented face row changed')
    return True


def main(contract_path, contract_sha):
    need(sha(contract_path) == contract_sha, 'Exact frozen contract required')
    c = json.loads(contract_path.read_text())
    need(c['extraction_launch_authorized'] is True and c['root_and_peer_review_complete'] is True, 'Separate reviewed extraction launch required')
    need(sha(__file__) == c['extractor_sha256'] and sha(sys.executable) == c['runtime']['python_sha256'], 'Source/interpreter identity')
    output = ROOT / c['expected_output']
    need(output.resolve().parent == ROOT / 'work/962-engineering' and not output.exists() and not output.is_symlink(), 'Fresh task-owned output required')
    for name, digest in c['input_sha256'].items():
        need(sha(ROOT / name) == digest, 'Before input drift: ' + name)
    reference = json.loads((ROOT / c['repair_reference']).read_text())
    report = json.loads((ROOT / c['mixed_report']).read_text())
    cap, = reference['cap']['components']
    need(report['status'] == 'complete_independent_choices_and_simultaneous_side_census' and not report['groups_without_eligible_nonempty_star'], 'Complete saved mixed map required')
    cycles = cap['topology']['oriented_boundary_cycles']
    need(cap['face_ids'] == reference['cap']['all_face_ids'] and cycles == report['cap_cycle_observations']['original_cycles'], 'Complete original cap/reference association')
    data, meta = payloads(ROOT / c['source_geometry'], cap['face_ids'], cycles,
        report['groups_and_all_keeper_candidates'], cap['exterior_face_ids'])
    expected = c['expected_counts']
    need(all(meta[k] == v for k, v in expected.items()), 'Exact frozen extraction counts')
    need(meta['mapped_cycles_global'] == report['cap_cycle_observations']['mapped_cycles'], 'Complete saved mapped cycle IDs differ')
    need([len(v) for v in cycles] == [1482, 2026] and [len(v) for v in meta['mapped_cycles_global']] == [766, 2026], 'Frozen loop lengths')
    output.mkdir()
    for name, content in data.items():
        with (output / name).open('xb') as stream:
            stream.write(content)
    need(readback(output, ROOT / c['source_geometry'], data, meta), 'Full byte readback')
    for name, digest in c['input_sha256'].items():
        need(sha(ROOT / name) == digest, 'After input drift: ' + name)
    need(sha(contract_path) == contract_sha and sha(sys.executable) == c['runtime']['python_sha256'], 'After contract/runtime drift')
    result = dict(schema='962-cap-source-byte-extraction/v1', status='complete_source_subset_and_separate_map_only',
        contract_sha256=contract_sha, extractor_sha256=sha(__file__), input_sha256=c['input_sha256'], metadata=meta,
        output_sha256={name: sha(output / name) for name in data}, output_bytes={name: len(value) for name, value in data.items()},
        full_coordinate_byte_and_ordered_oriented_face_readback=True, all_inputs_unchanged=True,
        keeper_map_applied_to_cap=False, geometry_modified_or_quality_recalculated=False,
        CDT_or_native_geometry_call=False, head_or_solver_or_physical_or_manufacturing_admitted=False)
    with (output / 'manifest.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    args = parser.parse_args()
    main(args.contract, args.contract_sha256)
