"""UNRUN pure format/association fixtures; no native data or runtime is opened."""
import copy
import importlib.util
from pathlib import Path
import struct
import unittest

spec=importlib.util.spec_from_file_location('held_measurement_parser',Path(__file__).with_name('parse_saved_measurement.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def stream(width,objects):
    code='>ii' if width==4 else '>qq'
    return b''.join(struct.pack(code,1211214,len(words))+b''.join(words) for words in objects)


def word(value):return struct.pack('<d',value).hex()


def toy_map():
    coords=[[word(float(i)),word(-0.0),word(0.0)] for i in range(425)]
    expected=dict(coordinate_words=coords,scaling_words=[word(1.0)]*4,
        time_binary64_LE_hex=word(.4525),dt_binary64_LE_hex=word(.0025))
    numbers=[2,0,3,1];rows=[]
    for node in range(425):
        for slot in range(4):
            present=slot<3
            rows.append(dict(source_node_ID=node,variable_slot=slot,variable_number=numbers[slot],
                dof_present=present,DOF_state='present' if present else 'absent',
                global_DOF=((3*node+slot)*7)%1275 if present else None,
                coordinate_binary64_LE_hex=coords[node],
                constrained=(node==0 and slot<3) or (node==32 and slot in (1,2)) or (node==137 and slot==2)))
    mapping=dict(schema='962-RICH2-END181-node-global-DOF-map/v1',scope='integer_associations_only_no_field_acceptance',
        constraint_mask_scope='original_case_expected_labels_not_live_BC_or_DofMap_observation',step=181,event='TIMESTEP_END',
        time_binary64_LE_hex=expected['time_binary64_LE_hex'],dt_binary64_LE_hex=expected['dt_binary64_LE_hex'],
        nonlinear_system_name='nl0',nonlinear_system_number=0,global_DOF_count=1275,physical_displacement_DOF_count=1275,
        source_node_count=425,MPI_ranks=1,threads=1,Real_bytes=8,PetscScalar_bytes=8,PetscInt_bytes=4,PETSc_version=[3,25,4],
        variables=[dict(slot=i,name=name,number=numbers[i],family='LAGRANGE',order='FIRST',physical_displacement=i<3,
                        existing_scaling_binary64_LE_hex=word(1.0)) for i,name in enumerate(p.NAMES)],rows=rows,
        reaction_convention=dict(system='auxiliary_save_in',save_in=['rx','ry','rz'],DOF_presence_is_not_kernel_activation=True,
            reaction_values_recorded_by_this_observer=False,unchanged_END181_collector_required=True,solver_F_has_nodal_BC_rows=True,
            constrained_F_is_not_reaction=True,scaling_changed_or_removed=False),
        assembly_invoked=False,solution_or_physical_state_written=False,field_acceptance=False)
    return mapping,expected


def log_text():
    return '\n'.join('Time Step %d, time = %s, dt = 0.0025\n  0 SNES Function norm 1.0e-8\n  1 SNES Function norm 1.0e-16' % (i,str(i/400)) for i in range(1,183))+'\n'


class SavedMeasurementFormatFixtures(unittest.TestCase):
    def test_both_integer_widths_variable_N_full_EOF_and_info(self):
        for width in (4,8):
            raw=stream(width,[[struct.pack('>d',1.25)],[struct.pack('>d',-0.0),struct.pack('>d',3.5)]])
            scan=p.scan_vectors(raw,width,b'-vecload_block_size 1\n')
            self.assertEqual([r['N'] for r in scan['objects']],[1,2]);self.assertTrue(scan['EOF_exact'])
            self.assertEqual(scan['objects'][-1]['end_offset'],len(raw))
            self.assertEqual(p.vector_words(raw,scan['objects'][1],[0,1]),[word(-0.0),word(3.5)])
            self.assertEqual(scan['info_bytes'],22)

    def test_class_signed_length_payload_and_trailing_bytes_refused(self):
        for raw in [struct.pack('>ii',1211213,0),struct.pack('>ii',1211214,-1),
                    struct.pack('>ii',1211214,2)+b'\0'*8,stream(4,[[]])+b'\0']:
            with self.assertRaises(ValueError):p.scan_vectors(raw,4,b'')

    def test_duplicate_and_nonfinite_JSON_tokens_refused(self):
        for raw in [b'{"x":1,"x":2}',b'{"x":NaN}']:
            with self.assertRaises(ValueError):p.strict_json(raw)

    def test_wrong_width_endian_oversize_or_missing_info_refused(self):
        for raw,width,info in [(stream(8,[[]]),4,b''),(struct.pack('<ii',1211214,0),4,b''),
                               (struct.pack('>ii',1211214,1701),4,b''),(stream(4,[[]]),4,None)]:
            with self.assertRaises(ValueError):p.scan_vectors(raw,width,info)

    def test_nonfinite_Y0_payload_and_signed_zero_are_preserved_uninterpreted(self):
        words=[bytes.fromhex('7ff8000000000042'),bytes.fromhex('fff0000000000000'),struct.pack('>d',-0.0)]
        raw=stream(4,[words]);scan=p.scan_vectors(raw,4,b'')
        self.assertEqual(scan['objects'][0]['nonfinite_word_count'],2)
        self.assertEqual(p.vector_words(raw,scan['objects'][0],[0,1,2]),[w[::-1].hex() for w in words])
        self.assertFalse(p.word_is_finite(words[0][::-1].hex()))

    def test_map_has_actual_permuted_full_global_range_and_expected_six_labels(self):
        mapping,expected=toy_map();r=p.validate_map(mapping,expected)
        self.assertEqual(len(r['physical_rows']),1275)
        self.assertEqual(r['physical_rows'][1]['global_DOF'],7)
        self.assertEqual(r['expected_mask_labels'],[[0,0],[0,1],[0,2],[32,1],[32,2],[137,2]])
        self.assertFalse(r['live_BC_observed']);self.assertFalse(r['field_or_SI_force_or_reaction_accepted'])

    def test_map_missing_range_mask_coordinates_scaling_and_time_refused(self):
        for change in ('range','mask','coordinate','scaling','time'):
            m,e=toy_map()
            if change=='range':m['global_DOF_count']=1276
            if change=='mask':m['rows'][0]['constrained']=False
            if change=='coordinate':m['rows'][2]['coordinate_binary64_LE_hex']=[word(1.0)]*3
            if change=='scaling':m['variables'][1]['existing_scaling_binary64_LE_hex']=word(2.0)
            if change=='time':m['time_binary64_LE_hex']=word(.45)
            with self.assertRaises(ValueError):p.validate_map(m,e)

    def test_map_duplicate_index_and_absent_physical_DOF_refused(self):
        for change in ('duplicate','absent'):
            m,e=toy_map()
            if change=='duplicate':m['rows'][1]['global_DOF']=m['rows'][0]['global_DOF']
            else:m['rows'][0].update(dof_present=False,DOF_state='absent',global_DOF=None)
            with self.assertRaises(ValueError):p.validate_map(m,e)

    def test_full_trace_gives_conditional_ordinals_not_times(self):
        trace=p.parse_monitor_trace(log_text())
        self.assertEqual(len(trace['events']),364)
        self.assertEqual([(r['object_ordinal'],r['monitor_iteration']) for r in trace['events'] if r['step']==181],[(360,0),(361,1)])
        self.assertTrue(trace['printed_tokens_are_not_binary64_solver_time_words'])

    def test_missing_extra_or_unrecognized_trace_monitor_refused(self):
        text=log_text()
        for bad in [text.replace('  1 SNES Function norm 1.0e-16\n','',1),
                    text+'  1 SNES Function norm 1.0e-16\n',text.replace('0 SNES Function norm','2 SNES Function norm',1),
                    text+'Time Step -1, time = 0, dt = 0.0025\n',
                    text+'Time Step 1.5, time = 0, dt = 0.0025\n',
                    text+'Time Step unknown, time = 0, dt = 0.0025\n',
                    text+'Time Step, time = 0, dt = 0.0025\n']:
            with self.assertRaises(ValueError):p.parse_monitor_trace(bad)

    def test_header_join_keeps_earlier_N_independent_of_END181(self):
        trace=p.parse_monitor_trace(log_text())
        rows=[dict(N=9 if e['step']<81 else 1275,integer_bytes=4,scalar_bytes=8,endian='big') for e in trace['events']]
        scans={s:dict(object_count=364,EOF_exact=True,objects=copy.deepcopy(rows)) for s in ('X','F','Y')}
        joined=p.bind_stream_headers(scans,trace,1275,4)
        self.assertEqual(joined['rows'][0]['N_by_stream']['X'],9)
        self.assertFalse(joined['field_SI_force_reaction_unscaling_or_cause_accepted'])
        scans['Y']['objects'][361]['N']=1274
        with self.assertRaises(ValueError):p.bind_stream_headers(scans,trace,1275,4)


if __name__=='__main__':unittest.main(verbosity=2)
