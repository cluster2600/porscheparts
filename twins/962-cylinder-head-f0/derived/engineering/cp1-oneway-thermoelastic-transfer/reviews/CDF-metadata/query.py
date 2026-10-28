"""Inspect saved CDF text metadata only; never assess or rewrite fields."""
from pathlib import Path
import hashlib, json
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[3]
NATIVE = ROOT / 'work/962-engineering/cp1-oneway-thermoelastic-transfer-002'
reports = []
for name in ['thermoelastic.e', 'thermoelastic.e-s002']:
    path = NATIVE / name
    raw = path.read_bytes()
    with netcdf_file(path, mode='r', mmap=False) as file:
        rows = []
        for key, variable in file.variables.items():
            if variable.typecode() != 'c':
                continue
            payload = variable.data.tobytes()
            matches = []
            start = 0
            while (start := raw.find(payload, start)) >= 0:
                matches.append(start)
                start += 1
            hits = [i for i in range(len(payload)) if payload.startswith(b'private-home-prefix-role:///', i)]
            rows.append(dict(name=key, dimensions=list(variable.dimensions), shape=list(variable.data.shape), bytes=len(payload), whole_payload_sha256=hashlib.sha256(payload).hexdigest(), exact_file_offsets=matches, private_prefix_offsets_in_payload=hits))
        info = file.variables.get('info_records')
        info_bytes = info.data.tobytes() if info is not None else b''
        private_positions = [i for i in range(len(raw)) if raw.startswith(b'private-home-prefix-role:///', i)]
        expected = [row for row in rows if row['name'] == 'info_records']
        assert not private_positions or len(expected) == 1 and len(expected[0]['exact_file_offsets']) == 1
        assert private_positions == ([] if not expected else [expected[0]['exact_file_offsets'][0]+i for i in expected[0]['private_prefix_offsets_in_payload']])
        assert raw.count(b'workspace:____') == len(private_positions)
        assert raw.lower().count(b'private-user-role') == len(private_positions)
        reports.append(dict(filename=name, original_sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), character_variables=rows, all_private_prefixes_confined_to_info_records=True, private_file_offsets=private_positions, exact_prefix='workspace:____', exact_prefix_bytes=len(b'workspace:____'), global_attribute_names=list(file._attributes), no_original_or_selected_CDF_written=True, numerical_fields_assessed=False))
    assert path.read_bytes() == raw
print(json.dumps(dict(schema='962-CDF2-private-path-text-metadata-query/v1', decoder_scope='Existing selected scipy netcdf_file loads arrays; only character-variable bytes and metadata are inspected. No numerical field evaluation, native solver or assessor.', files=reports), indent=2))
