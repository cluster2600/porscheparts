#!/usr/bin/env python3
"""Validate published 935 input requirements; no solver or claim admission."""
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
VARIANTS={'factory_935_1976','factory_935_1977','factory_935_1978_moby_dick','kremer_k3','kremer_k4','replica_declared_build'}


def require(condition,message):
    if not condition:raise ValueError(message)


def check(root=ROOT):
    data=json.loads((root/'data/input-matrix.json').read_text())
    rows=data['rows'];by_id={r['id']:r for r in rows}
    require(len(by_id)==len(rows)==50,'Matrix ID/count coverage differs')
    variants={v['id'] for v in data['variants']}
    require(variants==VARIANTS,'Separate 935 variant identities required')
    for variant in data['variants']:
        require(variant['accepted_source_claim_ids']==[] and variant['cooling_architecture'] is None,
                'Unreviewed cooling architecture or physical variant claim')
        require(not variant['horizontal_configuration_verified'],'Unverified horizontal arrangement')
        require(variant['transfer_from_other_variants']=='forbidden_without_explicit_applicability_evidence','Cross-variant transfer guard missing')
    sources={s['id']:s for s in data['source_evidence']}
    require(len(sources)==9,'Existing evidence coverage differs')
    require(list(sources.values())==json.loads((root/'data/existing-evidence.json').read_text()),'Evidence register copies disagree')
    for source in sources.values():
        path=source['repository_relative_path'];commit=source['reference_commit']
        require(not path.startswith('/') and '..' not in Path(path).parts,'Unsafe/private source path')
        require(bool(re.fullmatch('[0-9a-f]{40}',commit)) and bool(re.fullmatch('[0-9a-f]{64}',source['sha256'])),'Immutable source identity required')
        require(source['url']==f'https://github.com/cluster2600/porscheparts/blob/{commit}/{path}','Evidence URL must identify exact public source commit')
        require(source['admitted_935_physical_claims']==[],'Source integrity cannot admit a physical 935 value')
    levels={x['id'] for x in data['levels']}
    contract=json.loads((REPO/'twins/993-engine-cooling-fan-system-f0/program/research/corpus/geometry/parameter-contract.json').read_text())
    known={r['id'] for r in contract['parameter_dictionary']}
    for row in rows:
        require(row['minimum_level'] in levels and bool(row['canonical_units']),'Level/unit definition missing')
        require(set(row['variant_ids_require_separate_claims'])==VARIANTS,'Parameter variant applicability differs')
        require(set(row['depends_on'])<=by_id.keys(),'Unknown parameter dependency')
        require(set(row['current_evidence_ids'])<=sources.keys(),'Unknown evidence ID')
        require(set(row['legacy_contract_ids'])<=known,'Unknown legacy parameter ID')
        require(row['accepted_value'] is None and row['accepted_claim_ids']==[],
                'Numeric 935 value requires reviewed provenance; admission is empty in this publication')
        require(row['admission_status']=='not_admitted_for_named_935_variant','Unreviewed parameter admission')
        require(all(row[k] for k in ['gap','conditions_and_definition','required_evidence']),'Parameter gap/conditions/evidence missing')
    visiting=set();visited=set()
    def visit(key):
        require(key not in visiting,'Dependency cycle')
        if key in visited:return
        visiting.add(key)
        for dep in by_id[key]['depends_on']:visit(dep)
        visiting.remove(key);visited.add(key)
    for key in by_id:visit(key)
    with (root/'data/input-matrix.csv').open(newline='') as stream:csv_rows=list(csv.DictReader(stream))
    require(len(csv_rows)==len(rows),'CSV/JSON coverage differs')
    for csv_row,row in zip(csv_rows,rows):
        for key,value in csv_row.items():
            expected=row[key];expected='; '.join(expected) if isinstance(expected,list) else '' if expected is None else str(expected)
            require(value==expected,f'CSV/JSON value differs: {row["id"]}/{key}')
    require(not any(data[k] for k in ['scan_identity_established','scan_scale_established','scan_935_993_equivalence_established','manufacturing_authorized']),
            'Planning package cannot validate a specimen or authorize manufacture')
    require(data['accepted_935_numeric_physical_claims']==data['new_solver_runs']==0,'Unexpected numeric admission or solver result')
    require(data['publication_authorized_for_this_package'],'Publication authorization metadata missing')
    coverage=json.loads((root/'research/coverage.json').read_text())
    require(coverage['status']=='partial_awaiting_original_bundle','Current incomplete coverage must remain explicit')
    require(coverage['received_original_report_files']==coverage['received_verified_bundle_manifests']==0,'Unreceived bundle cannot be claimed imported')
    require(not any(coverage[k] for k in ['complete_language_coverage_verified','complete_engine_dataset_claimed','partial_briefs_ingested']),
            'Incomplete corpus cannot become complete/admitted')
    require(coverage['received_language_codes']==[],'Received languages require a verified inventory')
    manifest=json.loads((root/'data/publication-manifest.json').read_text())
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.suffix in {'.json','.csv','.md','.py'} and p.name!='publication-manifest.json'}
    require(set(manifest['files_sha256'])==actual,'Published file inventory differs')
    for name,expected in manifest['files_sha256'].items():
        raw=(root/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==expected,'Published artifact digest differs: '+name)
        if name.endswith(('.json','.csv','.md')):
            require(not re.search(r'/Users/|/private/tmp/|libfile_|sediment://|[?&](?:token|sig|signature)=',raw.decode()),'Private transport/local metadata in publication')
    return {'status':'passed_static_consistency','matrix_rows':50,'separate_variants':6,'existing_evidence_references':9,
            'accepted_935_numeric_physical_claims':0,'new_solver_runs':0,'research_coverage':'partial_awaiting_original_bundle'}


if __name__=='__main__':print(json.dumps(check(),indent=2))
