"""Provenance typée des jumeaux 4 soupapes (numpy inutile ici). Fail-closed."""
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PARAMS_DIR = HERE / 'params'
DESIGN_SPACE = PARAMS_DIR / 'design_space.json'
SOURCES = {
    'contract': 'twins/m64-cylinder-head/interface-contract.json',
    'scan935': 'twins/m64-cylinder-head/evidence/scan935-interfaces-20260914.json',
    'manual993': 'catalog/manual/page-checked/993-workshop-manual-group15-cylinder-head.json',
    'swindon': 'catalog/sources/src-swindon-m64-24v-head-kit.json',
    'gsc5092': 'twins/m64-cylinder-head/source/valvetrain/spring_candidates.json',
}
FILE_PROVENANCES = ('sourced_m64', 'candidate_935_scan_C', 'stock_993_2v_manual', 'supplier_swindon',
                    'supplier_gsc5092', 'derived', 'unsourced')
PROVENANCES = FILE_PROVENANCES + ('derived_by_iteration',)
SOURCED = ('sourced_m64', 'candidate_935_scan_C', 'stock_993_2v_manual', 'supplier_swindon', 'supplier_gsc5092')
SCAN_STATUS = 'measured_on_935_scan_evidence_C'
TOL = 1e-6


def _walk(node, dotted):
    for key in dotted.split('.') if dotted else []:
        if isinstance(node, list):
            node = node[int(key)]
        elif isinstance(node, dict) and key in node:
            node = node[key]
        else:
            raise ValueError(f'path not found: {dotted}')
    return node


def _first_number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    match = re.search(r'-?\d+(?:\.\d+)?', str(value))
    if not match:
        raise ValueError(f'no number in {value!r}')
    return float(match.group())


def _num(item, name):
    value = item.get('value')
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f'{name}: numeric value required')
    return float(value)


def load_spec(params_dir=PARAMS_DIR):
    components, parameters = {}, {}
    for path in sorted(Path(params_dir).glob('*.json')):
        if path.name == DESIGN_SPACE.name:
            continue
        data = json.loads(path.read_text())
        names = []
        for name, item in data['parameters'].items():
            if name in parameters:
                raise ValueError(f'{name}: defined in two component files')
            parameters[name] = item
            names.append(name)
        components[data['component']] = names
    return {'components': components, 'parameters': parameters}


def load_sources():
    return {k: json.loads((REPO / v).read_text()) for k, v in SOURCES.items()}


def _check_contract(name, item, contract):
    path = item.get('contract_path')
    if not path:
        raise ValueError(f'{name}: contract_path required')
    parent = _walk(contract, path.rsplit('.', 1)[0])
    reference = _walk(contract, path)
    if reference is None:
        raise ValueError(f'{name}: contract value is null')
    if parent.get('source') not in contract.get('sources', {}) or not parent.get('source_locator'):
        raise ValueError(f'{name}: contract entry has no registered source')
    if parent.get('unit') and parent['unit'] != item.get('unit'):
        raise ValueError(f'{name}: unit differs from contract')
    if abs(_num(item, name) - float(reference)) > TOL:
        raise ValueError(f'{name}: value differs from contract {reference}')
    return {'contract_path': path, 'source': parent['source'], 'source_locator': parent['source_locator']}


def verify_provenance(name, item, src):
    prov = item.get('provenance')
    if prov not in FILE_PROVENANCES:
        raise ValueError(f'{name}: provenance {prov!r} not allowed in a parameter file')
    if prov == 'derived':
        raise ValueError(f'{name}: derived handled separately')
    value = _num(item, name)
    if prov == 'sourced_m64':
        return _check_contract(name, item, src['contract'])
    if prov == 'candidate_935_scan_C':
        paths = item.get('scan_paths') or []
        if not paths:
            raise ValueError(f'{name}: scan_paths required')
        values = []
        for p in paths:
            raw = _walk(src['scan935'], p)
            if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                raise ValueError(f'{name}: scan value at {p} is not numeric')
            values.append(float(raw))
            head = p.split('.')
            for cut in range(len(head) - 1, 0, -1):
                owner = _walk(src['scan935'], '.'.join(head[:cut]))
                if isinstance(owner, dict) and 'status' in owner:
                    if owner['status'] != SCAN_STATUS:
                        raise ValueError(f'{name}: scan status is not {SCAN_STATUS}')
                    break
        reduce = item.get('reduce')
        if reduce == 'single' and len(values) == 1:
            ref = values[0]
        elif reduce == 'mean':
            ref = sum(values) / len(values)
        elif reduce == 'max':
            ref = max(values)
        else:
            raise ValueError(f'{name}: invalid reduce {reduce!r}')
        transform = item.get('transform', 'identity')
        if transform not in ('identity', 'negate'):
            raise ValueError(f'{name}: unknown transform')
        ref = -ref if transform == 'negate' else ref
        if abs(value - ref) > 5e-4:
            raise ValueError(f'{name}: value {value} differs from scan {ref:.4f}')
        return {'scan_paths': paths, 'reduce': reduce, 'transform': transform, 'status': SCAN_STATUS}
    if prov == 'stock_993_2v_manual':
        records = {r['id']: r for r in src['manual993']['records']}
        record = records.get(item.get('record'))
        if not record or record.get('status') != 'page_checked':
            raise ValueError(f'{name}: manual record missing or not page_checked')
        ref = _first_number(_walk(record['value'], item.get('key', '')))
        if abs(value - ref) > TOL:
            raise ValueError(f'{name}: value differs from manual {ref}')
        return {'record': record['id'], 'pdf_page': record.get('pdf_page'), 'applicability': '993 Carrera 2V, témoin'}
    if prov == 'supplier_swindon':
        quote = item.get('quote') or ''
        text = f'{value:g}'.replace('.', ',')
        if not quote or quote not in src['swindon'].get('notes', '') or text not in quote:
            raise ValueError(f'{name}: quote absent from Swindon record or value not in quote')
        trace = {'source_id': src['swindon']['source_id'], 'quote': quote}
        if item.get('contract_path'):
            trace.update(_check_contract(name, item, src['contract']))
        return trace
    if prov == 'supplier_gsc5092':
        cands = [c for c in src['gsc5092']['candidates'] if c.get('id') == 'GSC5092']
        ref = cands[0].get(item.get('field', '')) if len(cands) == 1 else None
        if ref is None or abs(value - float(ref)) > TOL:
            raise ValueError(f'{name}: value differs from GSC5092 record')
        return {'field': item['field'], 'url': cands[0].get('url')}
    for forbidden in ('contract_path', 'scan_paths', 'record', 'quote', 'field'):
        if item.get(forbidden):
            raise ValueError(f'{name}: unsourced parameter cannot cite {forbidden}')
    if not item.get('hypothesis'):
        raise ValueError(f'{name}: unsourced parameter needs a documented hypothesis')
    return {'hypothesis': item['hypothesis']}


def resolve_base(spec, src=None):
    """Valeurs non dérivées vérifiées + traces ; les dérivés sont calculés par layout.derive."""
    src = src or load_sources()
    if src['contract'].get('manufacturing_authorized') is not False:
        raise ValueError('contract must keep manufacturing_authorized false')
    values, traces = {}, {}
    params = spec['parameters']
    for name, item in params.items():
        if item.get('provenance') == 'derived':
            if 'value' in item:
                raise ValueError(f'{name}: derived parameter must not store a value')
            if not item.get('formula') or not item.get('inputs'):
                raise ValueError(f'{name}: derived parameter needs formula and inputs')
            for inp in item['inputs']:
                if inp not in params:
                    raise ValueError(f'{name}: unknown input {inp}')
            continue
        traces[name] = dict(verify_provenance(name, item, src), provenance=item['provenance'])
        values[name] = _num(item, name)
    return values, traces


def load_design_space(path=DESIGN_SPACE):
    return json.loads(Path(path).read_text())


def validate_design(spec, space, design, stage):
    variables = {v['name']: v for v in space['variables']}
    for name, value in design.items():
        if name.startswith('plug_2_') and space.get('plug_mode') == 'mirror_y':
            continue
        var = variables.get(name)
        if var is None:
            raise ValueError(f'{name}: not an admissible design variable')
        if var['stage'] > stage:
            raise ValueError(f'{name}: requires stage {var["stage"]}')
        if not var['lower'] - 1e-9 <= value <= var['upper'] + 1e-9:
            raise ValueError(f'{name}: {value} outside [{var["lower"]}, {var["upper"]}]')
        prov = spec['parameters'][name]['provenance']
        # Les candidats 935 sont des points de départ admissibles (bougies) ; les valeurs M64,
        # manuel et fournisseurs ne sont jamais modifiées à l'étape 1.
        if prov in SOURCED and prov != 'candidate_935_scan_C' and var['stage'] == 1:
            raise ValueError(f'{name}: stage 1 cannot override a sourced value')


def counts(spec, iteration_names=()):
    out = {k: 0 for k in PROVENANCES}
    for name, item in spec['parameters'].items():
        out['derived_by_iteration' if name in iteration_names else item['provenance']] += 1
    return out
