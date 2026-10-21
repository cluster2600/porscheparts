"""One fixed saved-data prediction; no solver, assessment, or field acceptance."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types

E = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering')
OUT = E / 'native005-exodus-averaging-reconstruction-001'
SOURCE = E / 'cp1-oneway-cooling-release-richardson2-assessor-prep-001/assess.py'
RUNTIME = E / 'native005-raw-displacement-decoder-runtime-root-001/acceptance.json'
SAVED = E / 'cp1-oneway-cooling-release-richardson2-observer004-native005-raw-displacement-diagnostic-execution-002/report.json'
CDF = E / 'cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic.e-s002'
PINS = {
    str(SOURCE): ('aa7ee403a0a3078df58410815f2b613aaeb9634bd14bc9c90517ce00cec7f2d5', 46645),
    str(RUNTIME): ('5dbf28e11b6fcd7c4770bb40a042a58735ab98485a592b857e3293eb5dab8376', 9673),
    str(SAVED): ('7f11a0976f15d90d05f26c388e3d5b5196916dfcc2d401f88a6b8e627fcc0d8a', 1021950),
    str(CDF): ('b6147b3e9c8fe447f85676c7d10b0f8bf7f33e69a3147569c06d1f0f486228d4', 3189268),
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def record(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def check(records):
    observed = {}
    for path, (digest, size) in records.items():
        item = record(path)
        need((item['sha256'], item['bytes']) == (digest, size), 'Changed fixed input: ' + path)
        observed[path] = item
    return observed


def word(value):
    return struct.pack('<d', value).hex()


def main():
    need(sys.version_info[:3] == (3, 12, 11) and sys.flags.isolated == 1
         and sys.dont_write_bytecode, 'Fixed selected Python3.12.11 -B -I required')
    before = check(PINS)
    source_bytes = SOURCE.read_bytes()
    need(hashlib.sha256(source_bytes).hexdigest() == PINS[str(SOURCE)][0], 'Source buffer changed')
    runtime = json.loads(RUNTIME.read_bytes())
    modules = {r['path']: (r['sha256'], r['bytes']) for r in runtime['selected_module_records']}
    need(len(modules) == 22 and sum(s for _, s in modules.values()) == 11299366,
         'Exact selected22 runtime closure required')
    runtime_before = check(modules)
    import numpy
    import scipy
    from scipy.io import _netcdf
    need(numpy.__version__ == '2.2.6' and scipy.__version__ == '1.17.1', 'Runtime version changed')
    need(all(str(Path(m.__file__).resolve()) in modules for m in (numpy, scipy, _netcdf)),
         'Observed decoder origins must match selected module pins')
    assessor = types.ModuleType('fixed_averaging_assessor')
    assessor.__file__ = str(SOURCE)
    exec(compile(source_bytes, str(SOURCE), 'exec'), assessor.__dict__)
    saved = json.loads(SAVED.read_bytes())
    data = assessor.read_exodus(CDF)
    geometry = saved['geometry']
    need(geometry['END181_member'] == CDF.name, 'END181 must join this same-run family member')
    ti = geometry['END181_index']
    need(type(ti) is int and 0 <= ti < len(data['times'])
         and word(data['times'][ti]) == geometry['END181_time_word_LE'], 'Exact END181 time-word join failed')
    need(len(data['nodes']) == 425 and len(data['cells']) == 256
         and set(data['nodes']) == set(range(425)) and len(data['blocks']) == 256,
         'Complete425-node/256-cell source-ID census required')
    status = dict(zip(data['block_ids'], data['block_status']))
    need(set(data['blocks'].values()) == {2, 3}
         and all(status[b] == 1 for b in data['blocks'].values()), 'All256 END181 old/born cells must be active')
    counts = dict.fromkeys(data['nodes'], 0)
    incidents = {tag: [] for tag in data['nodes']}
    cell_rows = []
    for tag, nodes in data['cells'].items():
        need(len(nodes) == len(set(nodes)) == 8 and set(nodes) <= set(counts), 'Complete distinct HEX8 incidence required')
        cell_rows.append(dict(source_element_ID=tag, block_ID=data['blocks'][tag], source_node_IDs=nodes))
        for node in nodes:
            counts[node] += 1
            incidents[node].append(tag)
    need(all(n > 0 for n in counts.values()) and sum(counts.values()) == 2048, 'Full active HEX8 incidence closure failed')
    old = saved['comparison_rows']
    need(len(old) == 1275 and {(r['source_node_ID'], r['slot']) for r in old}
         == {(n, s) for n in counts for s in range(3)}, 'Complete saved1275 node/component rows required')
    need(len({r['global_DOF'] for r in old}) == 1275
         and {r['global_DOF'] for r in old} == set(range(1275)), 'Complete physical DOF associations required')
    node_index = {tag - 1: k for k, tag in enumerate(data['node_map'])}
    result = []
    histogram = {}
    for row in old:
        node, slot = row['source_node_ID'], row['slot']
        name = ('disp_x', 'disp_y', 'disp_z')[slot]
        need(row['component'] == name and row['X1_word_LE'] == row['END181_CSV_word_LE'], 'Saved X1/CSV association changed')
        actual = word(data['fields'][name][ti][node_index[node]])
        need(actual == row['END181_Exodus_word_LE'], 'Same-run CDF field does not join saved row')
        value = struct.unpack('<d', bytes.fromhex(row['X1_word_LE']))[0]
        need(math.isfinite(value), 'Finite original X1 word required')
        total = 0.0
        for _ in range(counts[node]):
            total = total + value
        predicted = word(total / counts[node])
        matched = predicted == actual
        prior_match = row['X1_Exodus_exact_word_match']
        need(type(prior_match) is bool and prior_match == (row['X1_word_LE'] == actual), 'Saved prior disposition changed')
        group = ('previous_match' if prior_match else 'previous_mismatch') + ('_predicted_match' if matched else '_predicted_mismatch')
        histogram[group] = histogram.get(group, 0) + 1
        result.append(dict(original_saved_row=row, active_incident_cell_count=counts[node],
                           active_source_element_IDs=incidents[node], repeated_sum_word_LE=word(total),
                           predicted_Exodus_word_LE=predicted, decoded_Exodus_word_LE=actual,
                           predicted_exact_word_match=matched))
    after = check(PINS)
    runtime_after = check(modules)
    need(before == after and runtime_before == runtime_after, 'Final source/input/runtime identity changed')
    report = dict(schema='962-native005-exodus-averaging-reconstruction/v1',
                  status='COMPLETE_CONDITIONAL_EXPORTER_PREDICTION', source=record(__file__),
                  input_records_before=before, input_records_after=after,
                  selected22_runtime_before=runtime_before, selected22_runtime_after=runtime_after,
                  runtime_versions=dict(python=list(sys.version_info[:3]), numpy=numpy.__version__, scipy=scipy.__version__),
                  exact_assessor_source_buffer_loaded=True, assessor_entrypoint='read_exodus only; its validation dependencies retained',
                  model='binary64 accumulator initially +0; add saved X1 once per active incident HEX8; divide by integer repeat count',
                  public_libmesh_commit='90766057ef390adc9968b529e8ded2a87b0a77c7',
                  installed_libmesh_source_equivalence_proved=False, cause_uniquely_established=False,
                  END181=dict(member=CDF.name, index=ti, time_word_LE=geometry['END181_time_word_LE']),
                  block_ids=data['block_ids'], block_status=data['block_status'], active_cell_rows=cell_rows,
                  node_incidence_rows=[dict(source_node_ID=n, active_cell_count=counts[n], source_element_IDs=incidents[n]) for n in counts],
                  source_node_count=425, active_HEX8_count=256, incidence_count=2048,
                  comparison_count=len(result), disposition_counts=histogram,
                  predicted_exact_match_count=sum(r['predicted_exact_word_match'] for r in result), rows=result,
                  no_tolerance_or_word_repair=True, original_fields_modified=False,
                  physics_force_reaction_material_LPBF_manufacturing_acceptance=False,
                  strict_collector_or_assessment_called=False, solver_or_native_called=False,
                  full_ABI_or_true_RSS_peak_proved=False, automatic_retry=False)
    payload = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
    need(len(payload) < 8 * 1024**2, 'Complete report exceeds finite planned output sub-budget')
    with (OUT / 'report.json').open('xb') as stream:
        stream.write(payload)
    print(json.dumps(dict(comparison_count=len(result), disposition_counts=histogram,
                          predicted_exact_match_count=report['predicted_exact_match_count'],
                          report=record(OUT / 'report.json')), allow_nan=False))


if __name__ == '__main__':
    main()
