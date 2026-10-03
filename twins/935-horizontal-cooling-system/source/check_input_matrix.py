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


def check_research(root,rows):
    """Check public synthesis integrity and navigation without admitting values."""
    research=root/'research'
    coverage=json.loads((research/'coverage.json').read_text())
    qa=json.loads((research/'QA_SUMMARY.json').read_text())
    families=json.loads((research/'SOURCE_FAMILIES.json').read_text())
    ledger=json.loads((research/'ENGINE_FAN_PARAMETER_LEDGER.json').read_text())
    intake=json.loads((research/'import-manifest.json').read_text())
    require(coverage['status']=='completed_40_lane_public_synthesis_engine_data_partial',
            'Completed bounded passes must retain incomplete engine-data coverage')
    require(coverage['received_original_report_files']==0,'Unpublished original reports cannot be claimed imported into the public branch')
    require(coverage['published_public_synthesis_files']==4 and coverage['received_private_original_files']==97,
            'Public views and private originals must remain distinct')
    require(not any(coverage[k] for k in ['complete_language_coverage_verified','complete_engine_dataset_claimed','partial_briefs_ingested']),
            'Bounded corpus cannot become exhaustive/admitted')
    lanes=qa['coverage']['lanes']
    require(len(lanes)==len({v['lane'] for v in lanes})==40 and all(v['status']=='completed' for v in lanes),'Language inventory differs')
    require(coverage['received_language_codes']==[v['lane'] for v in lanes] and coverage['completed_language_lanes']==40,'Received language inventory differs')
    require(sum(v['source_records'] for v in lanes)==coverage['source_access_records']==families['source_record_count']==535,'Source/access accounting differs')
    require(sum(v['claim_records'] for v in lanes)==coverage['claim_observations_including_exclusions_and_gaps']==ledger['original_claim_record_count']==418,'Claim observation accounting differs')
    origins=qa['input_manifest']+qa['supplemental_input_manifest']
    origin_hashes={v['sha256'] for v in origins}
    source_origin_hashes={v['path'].split('/')[0]:v['sha256'] for v in qa['input_manifest'] if v['path'].endswith('/sources.json')}
    claim_origin_hashes={v['path'].split('/')[0]:v['sha256'] for v in qa['input_manifest'] if v['path'].endswith('/claims.json')}
    require(len(qa['input_manifest'])==160 and len(qa['supplemental_input_manifest'])==3,'Original manifest coverage differs')
    for origin in origins:
        name=origin.get('path',origin.get('artifact_id'))
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and bool(re.fullmatch('[0-9a-f]{64}',origin['sha256'])) and origin['bytes']>0,'Unsafe original artifact identity')
    all_sources=[v for family in families['families'] for v in family['members']]+families['supplemental_source_records']
    source_refs={v['source_ref'] for v in all_sources}
    family_ids={v['family_id'] for v in families['families']}
    require(len(source_refs)==len(all_sources)==542 and len(family_ids)==len(families['families'])==families['family_count']==461,'Source family/ref identity differs')
    require(len(families['supplemental_source_records'])==families['supplemental_record_count']==coverage['supplemental_source_records']==7,'Supplement accounting differs')
    for source in all_sources:
        require(source['original_artifact_sha256'] in origin_hashes,'Original artifact provenance missing for source')
        lane=source['source_ref'].split(':')[0]
        if lane!='supplement':
            require(source['original_artifact_sha256']==source_origin_hashes.get(lane),'Original artifact provenance differs from source lane')
        require(source['url'].startswith(('https://','http://')),'Public source URL missing')
    records=ledger['parameter_records'];observations=ledger['original_claim_index']
    parameter_ids={v['id'] for v in records};claim_refs={v['claim_ref'] for v in observations}
    require(len(parameter_ids)==len(records)==coverage['curated_parameter_gap_entries']==143,'Parameter/gap inventory differs')
    require(len(claim_refs)==len(observations)==418,'Original claim identity differs')
    require(sum(v['classification']=='missing' for v in records)==coverage['explicit_null_gaps']==66,'Explicit gap accounting differs')
    for record in records+observations:
        require(record.get('automatic_model_admission') is False,'Research record cannot automatically admit a model input')
        require(set(record['source_refs'])<=source_refs and set(record['source_family_ids'])<=family_ids,'Unknown research source/family reference')
    for record in records:
        require(record.get('physical_validation_established') is False,'Research cannot establish physical validation')
        require(set(record['source_claim_refs'])<=claim_refs,'Unknown original claim reference')
        if record['classification']=='missing':
            require(record['reported_value'] is None and record['normalized_value'] is None,'Missing quantity must remain null, not zero')
    for record in observations:
        require(record['original_artifact_sha256'] in origin_hashes,'Original artifact provenance missing for claim')
        require(record['original_artifact_sha256']==claim_origin_hashes.get(record['claim_ref'].split(':')[0]),'Original artifact provenance differs from claim lane')
    def no_source_payload(value):
        if isinstance(value,dict):
            require(not any(re.search(r'quote|excerpt|private_cache|local_evidence',k,re.I) for k in value),'Source excerpt/cache payload prohibited in public views')
            for child in value.values():no_source_payload(child)
        elif isinstance(value,list):
            for child in value:no_source_payload(child)
    no_source_payload(families);no_source_payload(ledger)
    crosswalk=json.loads((research/'matrix-crosswalk.json').read_text())
    require(crosswalk['matrix_variant_templates']==[v['id'] for v in json.loads((root/'data/input-matrix.json').read_text())['variants']], 'Crosswalk variant templates differ')
    require([v['matrix_id'] for v in crosswalk['rows']]==[v['id'] for v in rows],'Crosswalk must cover all 50 matrix rows')
    for link,row in zip(crosswalk['rows'],rows):
        require(link['quantity']==row['quantity'] and link['minimum_level']==row['minimum_level'],'Crosswalk requirement differs')
        require(link['accepted_input_value'] is None and link['automatic_model_admission'] is False,'Navigation cannot admit a matrix value')
        expected=[v['id'] for v in records if v['parameter'] in link['ledger_parameter_names']]
        require(link['ledger_record_ids']==expected,'Crosswalk ledger references differ')
    expected_files={'CONSOLIDATED_REPORT.md','SOURCE_FAMILIES.json','ENGINE_FAN_PARAMETER_LEDGER.json','QA_SUMMARY.json'}
    require(set(intake['files'])==expected_files and intake['bundle']['integrity_verified'],'Four verified public views required')
    require(not intake['raw_scan_or_source_caches_published'] and not intake['persistent_security_changes'],'Intake privacy/context boundary differs')
    for name,identity in intake['files'].items():
        raw=(research/name).read_bytes()
        require(len(raw)==identity['bytes'] and hashlib.sha256(raw).hexdigest()==identity['sha256'],'Original public view digest differs: '+name)
        require(identity['transformation']=='none; byte-identical public synthesis','Public synthesis transformation requires separate documented derivative')
    for identity in qa['checks']['public_output_checksums_excluding_self']:
        require(identity['sha256']==intake['files'][identity['filename']]['sha256'],'QA/output provenance differs')
    require(coverage['admitted_935_numeric_physical_claims']==0,'Research coverage cannot admit physical inputs')
    return coverage['status']


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
    research_status=check_research(root,rows)
    manifest=json.loads((root/'data/publication-manifest.json').read_text())
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.suffix in {'.json','.csv','.md','.py'} and p.name!='publication-manifest.json'}
    require(set(manifest['files_sha256'])==actual,'Published file inventory differs')
    for name,expected in manifest['files_sha256'].items():
        raw=(root/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==expected,'Published artifact digest differs: '+name)
        if name.endswith(('.json','.csv','.md')):
            require(not re.search(r'/Users/|/private/tmp/|libfile_|sediment://|[?&](?:token|sig|signature)=',raw.decode()),'Private transport/local metadata in publication')
    return {'status':'passed_static_consistency','matrix_rows':50,'separate_variants':6,'existing_evidence_references':9,
            'accepted_935_numeric_physical_claims':0,'new_solver_runs':0,'research_coverage':research_status,
            'bounded_language_lanes':40,'public_synthesis_views':4,'curated_parameter_gap_entries':143,'explicit_null_gaps':66}


if __name__=='__main__':print(json.dumps(check(),indent=2))
