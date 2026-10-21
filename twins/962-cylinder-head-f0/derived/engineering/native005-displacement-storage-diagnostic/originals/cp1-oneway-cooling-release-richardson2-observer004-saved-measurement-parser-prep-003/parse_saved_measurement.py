"""HELD pure byte/association parsers. No file IO, CLI, imports of PETSc or authority.

Unrun on synthetic or real inputs. Presence/storage/index association is separate
from field mechanics, force units, scaling, reaction and physical qualification.
"""
import hashlib
import json
import math
import re
import struct

VEC_CLASS=1211214
MAX_OBJECTS=364
MAX_ENTRIES=1700
MAX_STREAM_BYTES=MAX_OBJECTS*(16+8*MAX_ENTRIES)
NAMES=("disp_x","disp_y","disp_z","inactive_placeholder")


def need(value,message):
    if not value:raise ValueError(message)


def strict_json(data):
    def pairs(rows):
        out={}
        for k,v in rows:
            need(k not in out,"Duplicate JSON member");out[k]=v
        return out
    def bad(value):raise ValueError("Nonfinite JSON number")
    need(type(data) is bytes and len(data)<=1048576,"Bounded complete map bytes required")
    return json.loads(data,object_pairs_hook=pairs,parse_constant=bad)


def word_is_finite(word):
    need(type(word) is str and re.fullmatch('[0-9a-f]{16}',word),"Binary64 LE word required")
    bits=int.from_bytes(bytes.fromhex(word),'little')
    return (bits>>52)&2047!=2047


def scan_vectors(data,integer_bytes,info):
    """Exact standard big-endian Vec framing; width is explicit, never guessed from N.

    Real binary64 is a separate admitted observer/runtime precondition. This
    header alone cannot distinguish all complex/precision builds. Every raw
    stream and .info body must remain retained externally without rewriting.
    Nonfinite words are counted, never normalized or rejected here (notably Y0).
    """
    need(type(data) is bytes and 0<len(data)<=MAX_STREAM_BYTES,"Complete bounded Vec stream required")
    need(type(info) is bytes and len(info)<=1048576,"Complete .info bytes required, even if empty")
    need(type(integer_bytes) is int and integer_bytes in (4,8),"Explicit PetscInt4/8 required")
    offset=0;rows=[];code='>ii' if integer_bytes==4 else '>qq'
    while offset<len(data):
        need(len(rows)<MAX_OBJECTS,"Too many vector objects")
        start=offset;header=2*integer_bytes
        need(len(data)-offset>=header,"Truncated vector header/trailing bytes")
        kind,n=struct.unpack_from(code,data,offset);offset+=header
        need(kind==VEC_CLASS,"Expected standard vector class header")
        need(0<=n<=MAX_ENTRIES,"Unsupported/negative vector N")
        end=offset+8*n;need(end<=len(data),"Truncated real8 vector payload")
        nonfinite=0
        for i in range(offset,end,8):
            nonfinite+=((int.from_bytes(data[i:i+8],'big')>>52)&2047)==2047
        rows.append(dict(object_ordinal=len(rows),header_offset=start,payload_offset=offset,
            end_offset=end,N=n,integer_bytes=integer_bytes,scalar_bytes=8,endian='big',
            nonfinite_word_count=nonfinite,payload_sha256=hashlib.sha256(data[offset:end]).hexdigest()))
        offset=end
    need(offset==len(data),"Complete EOF required")
    return dict(stream_sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),objects=rows,
        object_count=len(rows),EOF_exact=True,info_sha256=hashlib.sha256(info).hexdigest(),
        info_bytes=len(info),info_interpreted_as_field_or_ABI_authority=False,
        real8_is_external_observer_runtime_precondition=True)


def vector_words(data,row,indices):
    """Raw LE words at explicit indices from a separately bound scanned object."""
    need(type(data) is bytes and type(row['payload_offset']) is int and 0<=row['payload_offset']<=row['end_offset']<=len(data),"Bound complete scanned bytes first")
    need(type(row['N']) is int and row['end_offset']-row['payload_offset']==8*row['N'],"Exact scanned extent required")
    need(hashlib.sha256(data[row['payload_offset']:row['end_offset']]).hexdigest()==row['payload_sha256'],"Scanned payload identity changed")
    need(all(type(i) is int and 0<=i<row['N'] for i in indices),"Actual global index outside this object's own N")
    return [data[row['payload_offset']+8*i:row['payload_offset']+8*i+8][::-1].hex() for i in indices]


def validate_map(mapping,expected):
    """Full real observer schema; external expected words must come from THIS capture.

    expected holds425 coordinate triples,4 scaling words,time/dt words. Its
    provenance and complete current END181 node/CSV ID relation remain separate
    admission requirements; this pure function cannot establish their origin.
    """
    need(mapping['schema']=='962-RICH2-END181-node-global-DOF-map/v1',"Observer schema changed")
    need(mapping['scope']=='integer_associations_only_no_field_acceptance' and
         mapping['constraint_mask_scope']=='original_case_expected_labels_not_live_BC_or_DofMap_observation',"Map scope changed")
    for k,v in dict(step=181,event='TIMESTEP_END',nonlinear_system_name='nl0',physical_displacement_DOF_count=1275,
                    source_node_count=425,MPI_ranks=1,threads=1,Real_bytes=8,PetscScalar_bytes=8).items():
        need(type(mapping[k]) is type(v) and mapping[k]==v,"Fixed observer metadata changed: "+k)
    need(type(mapping['PetscInt_bytes']) is int and mapping['PetscInt_bytes'] in (4,8),"Unsupported observed integer width")
    need(mapping['PETSc_version']==[3,25,4] and all(type(x) is int for x in mapping['PETSc_version']),"Pinned PETSc version required")
    need(type(mapping['nonlinear_system_number']) is int and mapping['nonlinear_system_number']>=0,"Observed system number required")
    ndof=mapping['global_DOF_count'];need(type(ndof) is int and 1275<=ndof<=1700,"Observed full global size outside source contract")
    for key in ['time_binary64_LE_hex','dt_binary64_LE_hex']:
        need(word_is_finite(mapping[key]) and mapping[key]==expected[key],"Current event word mismatch: "+key)
    coords=expected['coordinate_words'];scaling=expected['scaling_words']
    need(len(coords)==425 and all(len(p)==3 and all(word_is_finite(w) for w in p) for p in coords),"Complete425 current coordinate word triples required")
    need(len(scaling)==4 and all(word_is_finite(w) for w in scaling),"Complete4 observed scaling words required")
    variables=mapping['variables'];need(len(variables)==4,"Four variable rows required")
    numbers=[]
    for slot,row in enumerate(variables):
        need(type(row['slot']) is int and row['slot']==slot and row['name']==NAMES[slot],"Variable slot/name changed")
        need(type(row['number']) is int and 0<=row['number']<4,"Variable number outside four-variable permutation")
        need(row['family']=='LAGRANGE' and row['order']=='FIRST' and row['physical_displacement'] is (slot<3),"FE/physical variable contract changed")
        need(row['existing_scaling_binary64_LE_hex']==scaling[slot],"Existing scaling word mismatch; no unscaling inferred")
        numbers.append(row['number'])
    need(set(numbers)==set(range(4)),"Complete variable-number permutation required")
    rows=mapping['rows'];need(len(rows)==1700,"All425x4 map rows required")
    dofs=set();physical=[];mask=[]
    for ordinal,row in enumerate(rows):
        node,slot=divmod(ordinal,4)
        need(type(row['source_node_ID']) is int and row['source_node_ID']==node and
             type(row['variable_slot']) is int and row['variable_slot']==slot and
             type(row['variable_number']) is int and row['variable_number']==numbers[slot],"Ordered node/slot/number association changed")
        need(row['coordinate_binary64_LE_hex']==coords[node],"Node coordinate word mismatch across slots/current capture")
        present=row['dof_present'];need(type(present) is bool and row['DOF_state']==('present' if present else 'absent'),"DOF presence/state mismatch")
        constrained=(node==0 and slot<3) or (node==32 and slot in (1,2)) or (node==137 and slot==2)
        need(type(row['constrained']) is bool and row['constrained']==constrained,"Original expected six-mask labels changed")
        if constrained:mask.append([node,slot])
        index=row['global_DOF']
        if present:
            need(type(index) is int and 0<=index<ndof and index not in dofs,"Duplicate/out-of-range global index")
            dofs.add(index)
        else:need(slot==3 and index is None,"Only placeholder may be absent with null index")
        if slot<3:
            need(present,"All1275 physical DOFs must be present");physical.append(dict(source_node_ID=node,slot=slot,global_DOF=index))
    need(dofs==set(range(ndof)) and len(physical)==1275 and len(mask)==6,"Complete actual global range/physical/mask closure required")
    for k in ['assembly_invoked','solution_or_physical_state_written','field_acceptance']:
        need(mapping[k] is False,"Observer read-only/field scope changed")
    reaction=mapping['reaction_convention']
    need(reaction['system']=='auxiliary_save_in' and reaction['save_in']==['rx','ry','rz'] and
         reaction['DOF_presence_is_not_kernel_activation'] is True and reaction['reaction_values_recorded_by_this_observer'] is False and
         reaction['unchanged_END181_collector_required'] is True and reaction['solver_F_has_nodal_BC_rows'] is True and
         reaction['constrained_F_is_not_reaction'] is True and reaction['scaling_changed_or_removed'] is False,"Reaction/scaling caveat changed")
    return dict(ndof=ndof,integer_bytes=mapping['PetscInt_bytes'],physical_rows=physical,expected_mask_labels=mask,
        source_coordinate_time_scaling_words_compared=True,external_word_provenance_verified=False,
        live_BC_observed=False,field_or_SI_force_or_reaction_accepted=False)


def parse_monitor_trace(text):
    """Strict finite serial grammar; printed time tokens are not exact solver words."""
    need(type(text) is str and len(text.encode('utf-8'))<=32*1024**2,"Bounded complete raw log text required")
    blocks=[];current=None
    for line_number,line in enumerate(text.splitlines(),1):
        if line=='Time Step 0, time = 0':
            current=dict(step=0,time_token='0',dt_token=None,line=line_number,monitors=[])
            blocks.append(current);continue
        step=re.fullmatch(r'\s*Time Step ([0-9]+), time = ([^,\s]+), dt = (\S+)\s*',line)
        if step:
            current=dict(step=int(step[1]),time_token=step[2],dt_token=step[3],line=line_number,monitors=[])
            need(all(math.isfinite(float(x)) for x in (step[2],step[3])),"Nonfinite printed step metadata")
            blocks.append(current);continue
        monitor=re.fullmatch(r'\s*([0-9]+) SNES Function norm (\S+)\s*',line)
        if monitor:
            need(current is not None and int(monitor[1]) in (0,1),"Unbound/unexpected SNES monitor")
            float(monitor[2]) # Lexical numeric check only; nonfinite norm is retained, not accepted as accuracy.
            current['monitors'].append(dict(iteration=int(monitor[1]),norm_token=monitor[2],line=line_number));continue
        need('SNES Function norm' not in line and not re.search(r'\bTime\s+Step\b',line),"Unsupported monitor/time grammar; preserve, do not guess")
    startup=[b for b in blocks if b['step']==0]
    solves=[b for b in blocks if b['step']!=0]
    need(len(startup)<=1 and all(not b['monitors'] for b in startup),"Initial step is not an invented solve")
    need([b['step'] for b in blocks]==([0] if startup else [])+list(range(1,183)),"Complete ordered time-step trace required")
    need(len(solves)==182 and all([m['iteration'] for m in b['monitors']]==[0,1] for b in solves),"Exactly182 solves with one monitor0/1 pair each required")
    events=[]
    for block in solves:
        for monitor in block['monitors']:
            events.append(dict(object_ordinal=len(events),step=block['step'],monitor_iteration=monitor['iteration'],
                printed_time_token=block['time_token'],printed_dt_token=block['dt_token'],monitor_line=monitor['line']))
    return dict(blocks=blocks,events=events,solves=182,objects_per_stream=364,
        printed_tokens_are_not_binary64_solver_time_words=True)


def bind_stream_headers(scans,trace,ndof,integer_bytes):
    """Header/count association only; never use END181 map to invent earlier layouts."""
    need(set(scans)=={'X','F','Y'},"All three complete streams required")
    need(len(trace['events'])==364,"Full current0/1 time trace required first")
    for scan in scans.values():
        need(scan['object_count']==364 and scan['EOF_exact'] is True,"Complete364objects/EOF per stream required")
        need(all(r['integer_bytes']==integer_bytes and r['scalar_bytes']==8 and r['endian']=='big' for r in scan['objects']),"Observed width/real8/big-endian framing changed")
    rows=[]
    for event in trace['events']:
        ordinal=event['object_ordinal'];sizes={s:scans[s]['objects'][ordinal]['N'] for s in ('X','F','Y')}
        need(len(set(sizes.values()))==1 and next(iter(sizes.values()))>0,"Current X/F/Y header sizes disagree or empty")
        if event['step']==181:need(sizes['X']==ndof,"END181 own header/map range mismatch")
        rows.append(dict(**event,N_by_stream=sizes,earlier_node_layout_inferred=False))
    for i in range(0,364,2):need(rows[i]['N_by_stream']==rows[i+1]['N_by_stream'],"Monitor0/1 layout changed within one solve")
    return dict(rows=rows,complete_storage_trace_association=True,
        field_SI_force_reaction_unscaling_or_cause_accepted=False)
