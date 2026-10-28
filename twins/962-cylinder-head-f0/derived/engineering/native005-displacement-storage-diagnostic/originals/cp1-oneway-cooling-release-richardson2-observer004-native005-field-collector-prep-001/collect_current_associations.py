"""HELD/UNRUN fixed native005 saved association collector; no CLI or output writes.

Only a separately reviewed root-issued saved-intake binding can authorize a
future call. Source/AST preparation is not a data operation. Parser and assessor
dependencies must be the exact externally loaded frozen modules; no module is
imported here. The existing geometry/CSV entrypoints are reused; the full
mechanical assessment and POLICY are not invoked or replaced.
"""
import hashlib
import json
import math
import re
import struct
from pathlib import Path

ROOT=Path("/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993")
NATIVE=ROOT/'work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004'
FILES={
  "map": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/rich2-END181-dof-map.json",
    "sha256": "581f359f22b93b87e74c23f5ef991d0971ff574c285c169579eb9e2b4c5ca4ec",
    "bytes": 387694
  },
  "X": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/physical-X.petsc",
    "sha256": "b5dadf59281095b56c5f7cfb1f8fdbb7287d1075d757fa7877386f7d856b8f86",
    "bytes": 3244624
  },
  "F": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/physical-F.petsc",
    "sha256": "b7dee38b7cdb0c37c887fd82fbf579025fb679987bf802a581da62d6f79d3704",
    "bytes": 3244624
  },
  "Y": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/physical-Y.petsc",
    "sha256": "f750dbe34d66c337acadf1b4378fda743019e8e668edef92bfd18e1c8b731701",
    "bytes": 3244624
  },
  "X_info": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/physical-X.petsc.info",
    "sha256": "fc71ba3e4e62b9fff1069fb11e71005561d34757f6764ed05da879b469c6fb79",
    "bytes": 8008
  },
  "F_info": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/physical-F.petsc.info",
    "sha256": "fc71ba3e4e62b9fff1069fb11e71005561d34757f6764ed05da879b469c6fb79",
    "bytes": 8008
  },
  "Y_info": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/physical-Y.petsc.info",
    "sha256": "fc71ba3e4e62b9fff1069fb11e71005561d34757f6764ed05da879b469c6fb79",
    "bytes": 8008
  },
  "native_log": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/native.log",
    "sha256": "f53294d71d4f67a73c5af5d47b8ead7307a61e30c003bbe2eb77c997079b0d1d",
    "bytes": 272166
  },
  "END181_nodal": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic_end_0181.csv",
    "sha256": "9970cbfd2e3d11f584e5b38615f9d92e02e00ce240b1c3f88c59716bed899f8e",
    "bytes": 71995
  },
  "BEGIN80_nodal": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic_begin_0080.csv",
    "sha256": "22609b849303638a30e49276f9171371eef5bc639f70528aa2ab210358830035",
    "bytes": 28080
  },
  "BEGIN80_reference": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic_reference_begin_0080.csv",
    "sha256": "ea69e318eca4878c7f857a18864cc5ec96206dfc60bdea99cde25b98e0624ea5",
    "bytes": 4816
  },
  "exodus_1": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic.e",
    "sha256": "6d3fc2319b5030667456883b199b326df1b6e0502e9b3011edefd491f96401fb",
    "bytes": 2684460
  },
  "exodus_2": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/thermoelastic.e-s002",
    "sha256": "b6147b3e9c8fe447f85676c7d10b0f8bf7f33e69a3147569c06d1f0f486228d4",
    "bytes": 3189268
  },
  "transfer_manifest": {
    "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-004/transfer-manifest.json",
    "sha256": "c774e62c67e16c29dc024b8cc8e6641570e316265960e58cd7170827f8cecd06",
    "bytes": 130095
  }
}
PARSER={
  "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-saved-measurement-parser-prep-002/parse_saved_measurement.py",
  "sha256": "dfce01d6cd8d7618e0dee794d35a7bb0a56e34ae998facf2dd3f7b9335d4bede",
  "bytes": 13042
}
ASSESSOR={
  "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-assessor-prep-001/assess.py",
  "sha256": "aa7ee403a0a3078df58410815f2b613aaeb9634bd14bc9c90517ce00cec7f2d5",
  "bytes": 46645
}
OPERATIONAL_ROOT={
  "path": "work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native005-native-root-result-review-001/review.json",
  "sha256": "37104fe3014ab81327c487ecbd7fbd268efb6c827bb571235232cf9a2c93401b",
  "bytes": 5803
}
CAP=33554432
META_CAP=1048576


def need(ok,message):
    if not ok:
        raise ValueError(message)


def strict_json(raw,limit=META_CAP):
    need(type(raw) is bytes and 0<len(raw)<=limit,'Complete bounded metadata bytes required')
    def pairs(items):
        out={}
        for k,v in items:
            need(k not in out,'Duplicate JSON key')
            out[k]=v
        return out
    def invalid(value):
        raise ValueError('Nonfinite JSON constant')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def read_pin(pin,limit):
    need(type(pin) is dict and set(pin)=={'path','sha256','bytes'},'Exact descriptor required')
    name=Path(pin['path'])
    need(type(pin['path']) is str and not name.is_absolute() and '..' not in name.parts,'Fixed relative source/input path required')
    need(type(pin['bytes']) is int and 0<=pin['bytes']<=limit and re.fullmatch('[0-9a-f]{64}',pin['sha256']),'Bounded exact byte identity required')
    path=ROOT/name
    need(path.is_file() and not path.is_symlink() and path.resolve(strict=True)==path,'Canonical regular selected file required')
    with path.open('rb') as stream:
        raw=stream.read(pin['bytes']+1)
    need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'Complete source/input identity changed')
    return raw


def word(value):
    need(type(value) in (float,int) and math.isfinite(value),'Finite scalar word required')
    return struct.pack('<d',value).hex()


def module_identity(module,pin,functions):
    need(Path(module.__file__).resolve(strict=True)==ROOT/pin['path'],'Exact frozen dependency path required')
    read_pin(pin,META_CAP)
    need(all(callable(getattr(module,name,None)) for name in functions),'Missing frozen dependency entrypoint')


def provenance_words(raw,pin,review_pin,parser):
    need(type(raw) is bytes and type(pin) is dict and set(pin)=={'path','sha256','bytes'} and type(pin['bytes']) is int and pin['bytes']==len(raw)<=META_CAP and hashlib.sha256(raw).hexdigest()==pin['sha256'],'Externally bound independent-word bundle required')
    bundle=strict_json(raw)
    need(bundle['schema']=='962-native005-independent-expected-words/v1' and bundle['capture_closed']=={"path":"work/962-engineering/cp1-oneway-cooling-release-richardson2-observer004-native-measurement-root-execution-004/closed-result.json","sha256":"23b5561f68fad16893cf8dbc3931cadbd94a6bfc06612f0813ff975048b9586d","bytes":1578239},'Current capture word provenance required')
    expected=bundle['expected'];origins=bundle['provenance']
    need(set(expected)=={'coordinate_words','time_binary64_LE_hex','dt_binary64_LE_hex','scaling_words'} and set(origins)=={'coordinate','time','dt','scaling'},'Complete four-part independent expected-word contract required')
    review_raw=read_pin(review_pin,META_CAP)
    review=strict_json(review_raw)
    need(review['schema']=='962-native005-independent-word-provenance-root-review/v1' and review['root_reviewed'] is True and review['expected_words']==pin and review['capture_closed']==bundle['capture_closed'] and review['independently_reviewed_fields']==['coordinate','time','dt','scaling'],'Separate exact provenance semantic review required')
    forbidden={p['path'] for k,p in FILES.items() if k in ('map','X','F','Y','X_info','F_info','Y_info','native_log')}
    for key,origin in origins.items():
        need(type(origin['method']) is str and origin['method'] and origin['independent_of_map_and_solver_vectors'] is True,'Explicit independent source method required')
        need(type(origin['source_records']) is list and origin['source_records'],'Explicit finite provenance records required')
        need(origin==review['provenance'][key],'Root review must bind every exact provenance association')
        for record in origin['source_records']:
            need(type(record) is dict and set(record)=={'path','sha256','bytes'} and record['path'] not in forbidden,'Map/vector/printed-log self-certification is forbidden')
            need(record in review['admitted_source_records'],'Each provenance record requires separate finite root source authorization')
    need(FILES['transfer_manifest'] in origins['coordinate']['source_records'],'Coordinate source must include frozen transfer manifest')
    need(any(FILES[k] in origins['time']['source_records'] for k in ('exodus_1','exodus_2')),'Exact same-run Exodus time source required')
    need(len(expected['coordinate_words'])==425 and all(len(row)==3 and all(parser.word_is_finite(w) for w in row) for row in expected['coordinate_words']),'Complete425 independent coordinate triples required')
    need(len(expected['scaling_words'])==4 and all(parser.word_is_finite(w) for w in expected['scaling_words']),'Four independent finite scaling words required')
    need(all(parser.word_is_finite(expected[k]) for k in ('time_binary64_LE_hex','dt_binary64_LE_hex')),'Independent finite time/dt words required')
    return expected,bundle,review_raw


def collect_current(binding_bytes,binding_sha256,provenance_bytes,parser,assessor):
    """One fixed future saved-data call; any exception is INCOMPLETE, never empty success.

    The future external caller owns current-runtime/source admission, lifecycle,
    complete exception/stream preservation and an independently hashed binding.
    It must not call this function under operational-native authority alone.
    """
    need(type(binding_sha256) is str and re.fullmatch('[0-9a-f]{64}',binding_sha256) and hashlib.sha256(binding_bytes).hexdigest()==binding_sha256,'Sole external saved-intake binding digest required')
    binding=strict_json(binding_bytes)
    need(binding['schema']=='962-native005-current-field-intake-binding/v1' and binding['root_issued'] is True and binding['scientific_saved_intake_authorized'] is True and type(binding['invocations']) is int and binding['invocations']==1,'Separate fixed once-only saved-intake authority required')
    need(binding['independent_source_review_complete'] is True and binding['root_source_review_complete'] is True and binding['selected_decoder_runtime_review_complete'] is True,'Independent source/decoder runtime gates pending')
    need(all(binding[k] is False for k in ('native_execution_authorized','runtime_query_authorized','full_mechanical_assessment_authorized','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry')),'No new native/mechanical/qualification authority')
    need(binding['source_dependencies']=={'parser':PARSER,'assessor':ASSESSOR} and binding['captured_input_records']==FILES and binding['operational_root']==OPERATIONAL_ROOT,'Exact current source/capture selection required')
    need('binding_sha256' not in binding,'No self-hash in binding')
    root_raw=read_pin(OPERATIONAL_ROOT,META_CAP)
    root=strict_json(root_raw)
    need(root['decision']=='ACCEPT_ONE_FIXED_NATIVE_COUPON_OPERATIONAL_CAPTURE_ONLY' and root['authority']['scientific_body_intake_authorized'] is False,'Operational acceptance is separate from this future intake')
    module_identity(parser,PARSER,['strict_json','word_is_finite','scan_vectors','vector_words','validate_map','parse_monitor_trace','bind_stream_headers'])
    module_identity(assessor,ASSESSOR,['geometry_family','node_sample'])
    expected,bundle,review_raw=provenance_words(provenance_bytes,binding['independent_words'],binding['provenance_root_review'],parser)
    # Fixed, complete bytes only. Existing scientific files are never rewritten.
    payloads={name:read_pin(pin,pin['bytes']) for name,pin in FILES.items()}
    transfer=strict_json(payloads['transfer_manifest'])
    geometry,cells,frames,family=assessor.geometry_family(NATIVE,['thermoelastic.e','thermoelastic.e-s002'],transfer)
    need(set(geometry)==set(range(425)) and len(cells)==256 and set(frames)==set(range(183)),'Complete native source-ID/cell/frame association required')
    derived_coordinates=[[word(x) for x in geometry[node]] for node in range(425)]
    need(derived_coordinates==expected['coordinate_words'],'Independent coordinate words must join both transfer and native Exodus')
    frame=frames[181]
    member=next(row for row in family if row['filename']==frame['member'])
    time_word=word(member['times'][frame['index']])
    need(time_word==expected['time_binary64_LE_hex'],'Exact same-run native END181 time word changed')
    mapping=parser.strict_json(payloads['map'])
    map_result=parser.validate_map(mapping,expected)
    scans={name:parser.scan_vectors(payloads[name],map_result['integer_bytes'],payloads[name+'_info']) for name in ('X','F','Y')}
    trace=parser.parse_monitor_trace(payloads['native_log'].decode('utf-8','strict'))
    headers=parser.bind_stream_headers(scans,trace,map_result['ndof'],map_result['integer_bytes'])
    indices=[row['global_DOF'] for row in map_result['physical_rows']]
    need(len(indices)==1275 and len(set(indices))==1275,'Complete physical source/global-index rows required')
    events=[row for row in headers['rows'] if row['step']==181]
    need([row['monitor_iteration'] for row in events]==[0,1],'Validated own END181 monitor pair required')
    selected={}
    for stream,iteration,name in [('X',0,'X0'),('X',1,'X1'),('F',0,'F0'),('F',1,'F1'),('Y',0,'Y0'),('Y',1,'Y1')]:
        ordinal=events[iteration]['object_ordinal']
        selected[name]=dict(stream=stream,object_ordinal=ordinal,words_LE=parser.vector_words(payloads[stream],scans[stream]['objects'][ordinal],indices))
    old={n for n,p in geometry.items() if p[0]<=1.};born={n for n,p in geometry.items() if p[0]>=1.};shared=old&born
    need(len(old)==len(born)==225 and len(shared)==25,'Complete old/born/shared reference partition required')
    end,end_storage=assessor.node_sample(NATIVE/'thermoelastic_end_0181.csv',geometry,set(geometry),(*assessor.DISP,'temperature',*assessor.FORCE),shared)
    begin80,begin80_storage=assessor.node_sample(NATIVE/'thermoelastic_begin_0080.csv',geometry,set(geometry),(*assessor.DISP,'temperature'),shared)
    reference,reference_storage=assessor.node_sample(NATIVE/'thermoelastic_reference_begin_0080.csv',geometry,born,('born_reference_temperature',))
    cdf_comparisons=[]
    for node in sorted(geometry):
        for name in (*assessor.DISP,'temperature',*assessor.FORCE):
            csv_word=word(end[node][name]);cdf_word=word(frame['fields'][name][node])
            cdf_comparisons.append(dict(source_node_ID=node,field=name,END181_CSV_word_LE=csv_word,END181_Exodus_word_LE=cdf_word,exact_word_match=csv_word==cdf_word))
    comparisons=[]
    for i,row in enumerate(map_result['physical_rows']):
        expected_word=word(end[row['source_node_ID']][assessor.DISP[row['slot']]])
        actual_word=selected['X1']['words_LE'][i]
        comparisons.append(dict(**row,END181_CSV_word_LE=expected_word,X1_word_LE=actual_word,exact_word_match=actual_word==expected_word))
    birth_reference=[]
    for node in sorted(born):
        temperature_word=word(begin80[node]['temperature']);reference_word=word(reference[node]['born_reference_temperature'])
        birth_reference.append(dict(source_node_ID=node,BEGIN80_displacement_words_LE=[word(begin80[node][name]) for name in assessor.DISP],BEGIN80_temperature_word_LE=temperature_word,reference_temperature_word_LE=reference_word,exact_temperature_word_match=temperature_word==reference_word))
    # Retain every comparison, including failures. No tolerance/rounding/mechanics is added.
    all_X1=all(row['exact_word_match'] for row in comparisons)
    all_reference=all(row['exact_temperature_word_match'] for row in birth_reference)
    all_cdf=all(row['exact_word_match'] for row in cdf_comparisons)
    report=dict(schema='962-native005-current-field-association-collection/v1',status='COMPLETE_WORD_ASSOCIATION_CANDIDATE' if all_X1 and all_reference and all_cdf else 'COMPLETE_COLLECTION_WITH_WORD_ASSOCIATION_REFUSALS',binding_sha256=binding_sha256,source_dependencies=binding['source_dependencies'],captured_input_records=FILES,operational_root=OPERATIONAL_ROOT,independent_words=binding['independent_words'],provenance_root_review=binding['provenance_root_review'],external_provenance_semantics_root_attributed=True,external_semantic_origin_proved_by_this_collector=False,geometry=dict(source_nodes=425,cells=256,frames=183,family=family,END181_frame=frame['member'],END181_index=frame['index'],END181_time_word_LE=time_word),map_association=map_result,stream_scans=scans,trace=trace,header_associations=headers,selected_END181_words=selected,X1_comparisons=comparisons,X1_word_comparison_count=len(comparisons),all1275_X1_words_match=all_X1,END181_CSV_Exodus_comparisons=cdf_comparisons,END181_CSV_Exodus_comparison_count=len(cdf_comparisons),all2975_END181_CSV_Exodus_words_match=all_cdf,birth_reference_rows=birth_reference,birth_reference_count=len(birth_reference),all225_reference_temperature_words_match=all_reference,nodal_storage=dict(END181=end_storage,BEGIN80=begin80_storage,BEGIN80_reference=reference_storage),source_CSV_bytes_retained_read_only=True,Y0_uninterpreted_nonfinite_bits_retained=True,Y1_is_observed_not_rounded_X1_minus_X0=True,F1_SI_force_reaction_unscaling_accepted=False,live_BC_observed=False,POLICY_loaded_or_changed=False,full_mechanical_assessment_performed=False,field_association_accepted=False,physics_material_LPBF_manufacturing_qualified=False,automatic_retry=False)
    need(len(comparisons)==1275 and len(birth_reference)==225 and len(cdf_comparisons)==2975,'No partial comparison set')
    for name,pin in FILES.items():
        need(read_pin(pin,pin['bytes'])==payloads[name],'Current raw artifact changed during collection')
    module_identity(parser,PARSER,['scan_vectors','validate_map'])
    module_identity(assessor,ASSESSOR,['geometry_family','node_sample'])
    need(read_pin(OPERATIONAL_ROOT,META_CAP)==root_raw and read_pin(binding['provenance_root_review'],META_CAP)==review_raw,'Root provenance/control evidence changed during collection')
    need(len((json.dumps(report,allow_nan=False)+'\n').encode())<=CAP,'Full association report exceeds32MiB; refuse without truncation')
    return report
