"""Combined selection, immutable global trial history and current-round refusal gates."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

import numpy as np


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/research/935-pairing-continuation-20261106/source'


def module(name,path=None):
    spec=importlib.util.spec_from_file_location(name,path or SOURCE/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


census=module('census_continuation_pairs')
checker=module('verify_continuation_pairs')
record=module('record_selected_pairs')
registry_check=module('verify_pair_registry')
filtering=module('filter_continuation_strips')
terminal=module('verify_terminal_stop')
scalar=module('fixed_scalar_pairs',ROOT/'docs/research/935-frontier-pairing-20261106/source/verify_frontier_pairs_v2.py')


class PairingContinuation(unittest.TestCase):
    def test_cross_class_competition_and_ties_have_literal_controls(self):
        self.assertEqual(checker.combined_selection_controls(scalar),4)

    def test_combined_sort_keeps_class_flags_and_score_attached(self):
        pairs,classes,flags,scores=census.combine(np.array([[2,3]]),np.array([[True,True]]),np.array([.09]),
            np.array([[0,2]]),np.array([[True,False]]),np.array([.04]))
        self.assertEqual(pairs.tolist(),[[0,2],[2,3]])
        self.assertEqual(classes.tolist(),[1,0]);self.assertEqual(flags.tolist(),[[True,False],[True,True]])
        self.assertTrue(np.array_equal(scores,[.04,.09]))

    def test_empty_combined_graph_is_a_real_stop_without_phantom_pair(self):
        empty=np.empty((0,2),dtype=int);flags=np.empty((0,2),dtype=bool)
        result=census.combine(empty,flags,np.empty(0),empty,flags,np.empty(0))
        self.assertEqual([len(value) for value in result],[0,0,0,0])

    def test_duplicate_pair_in_both_geometry_classes_fails_closed(self):
        with self.assertRaises(AssertionError):
            census.combine(np.array([[0,1]]),np.array([[True,True]]),np.array([.1]),
                np.array([[0,1]]),np.array([[True,False]]),np.array([.1]))

    def registry_fixture(self):
        history=np.arange(1705*6,dtype=np.int64).reshape(-1,6)+10000
        keys=np.array([[1,2,3,4,5,6],[7,8,9,10,11,12]]);classes=np.array([0,1])
        first=record.append(None,keys,classes,1,'a'*64,'b'*64,'c'*64)
        return history,keys,classes,first

    def test_append_and_independent_registry_inspection_preserve_prior_fields(self):
        history,keys,classes,first=self.registry_fixture();next_history=np.r_[history,keys]
        self.assertEqual(registry_check.inspect(None,first,keys,classes,1,'a'*64,'b'*64,'c'*64,history,next_history),(0,2))
        new=np.array([[13,14,15,16,17,18]]);cls=np.array([1])
        second=record.append(first,new,cls,2,'d'*64,'e'*64,'f'*64)
        self.assertEqual(registry_check.inspect(first,second,new,cls,2,'d'*64,'e'*64,'f'*64,next_history,np.r_[next_history,new]),(2,3))
        for key in first:self.assertTrue(np.array_equal(second[key][:2],first[key]))
        self.assertEqual(second['global_pair_ids'].tolist(),[0,1,2])

    def test_registry_rejects_changed_identity_class_birth_or_noncontiguous_id(self):
        history,keys,classes,first=self.registry_fixture();next_history=np.r_[history,keys]
        for field,value in [('global_pair_ids',8),('raw_pair_keys',99),('geometry_classes',2),('birth_rounds',2),('birth_parent_mesh_sha256','d'*64)]:
            changed={key:array.copy() for key,array in first.items()}
            if field=='raw_pair_keys':changed[field][0,0]=value
            else:changed[field][0]=value
            with self.assertRaises(AssertionError,msg=field):
                registry_check.inspect(None,changed,keys,classes,1,'a'*64,'b'*64,'c'*64,history,next_history)

    def test_previous_registry_prefix_cannot_be_rewritten_by_new_round(self):
        history,keys,_,first=self.registry_fixture();new=np.array([[13,14,15,16,17,18]]);cls=np.array([0])
        second=record.append(first,new,cls,2,'d'*64,'e'*64,'f'*64);second['birth_rounds'][0]=9
        with self.assertRaises(AssertionError):
            registry_check.inspect(first,second,new,cls,2,'d'*64,'e'*64,'f'*64,np.r_[history,keys],np.r_[history,keys,new])

    def test_attempt_history_retains_every_prior_outcome_and_refuses_duplicates(self):
        history,keys,classes,first=self.registry_fixture();combined=np.r_[history,keys]
        wrong=combined.copy();wrong[0,0]+=1
        with self.assertRaises(AssertionError):registry_check.inspect(None,first,keys,classes,1,'a'*64,'b'*64,'c'*64,history,wrong)
        with self.assertRaises(AssertionError):registry_check.inspect(None,first,keys,classes,1,'a'*64,'b'*64,'c'*64,np.r_[history[:1703],keys],combined)

    def test_current_round_filter_cannot_remove_earlier_accepted_global_pair(self):
        data=dict(points=np.zeros((4,3)),global_node_ids=np.arange(4),triangles=np.array([[0,1,2],[0,2,3],[1,0,3],[1,3,2]]),
                  source_continuation_pair_ids=np.array([2,2,5,5]),inferred_surface_kind=np.array([9,9,9,9]),continuation_birth_parent_face_rows=np.array([-1,-1,-1,-1]))
        filtered=filtering.compose(data,{5},first_current=5)
        self.assertTrue(np.array_equal(filtered['triangles'],data['triangles'][:2]))
        self.assertEqual(filtered['source_continuation_pair_ids'].tolist(),[2,2])
        with self.assertRaises(AssertionError):filtering.compose(data,{2},first_current=5)

    def test_terminal_set_subtraction_uses_original_directed_raw_pair_identity(self):
        keys=np.array([[0,1,2],[3,4,5],[6,7,8]])
        pairs=np.array([[0,1],[0,2]])
        history=np.array([[0,1,2,3,4,5]])
        self.assertEqual(terminal.remaining_keys(keys,pairs,history).tolist(),[[0,1,2,6,7,8]])
        complete=np.r_[history,[[0,1,2,6,7,8]]]
        self.assertEqual(terminal.remaining_keys(keys,pairs,complete).shape,(0,6))
        self.assertEqual(terminal.remaining_keys(keys,pairs[:,::-1],complete).shape,(0,6))

    def test_executed_sources_helpers_and_ancestors_remain_hash_bound(self):
        result=json.loads((SOURCE.parent/'results.json').read_text())
        for row in result['executed_sources']:self.assertEqual(hashlib.sha256((SOURCE/row['name']).read_bytes()).hexdigest(),row['sha256'])
        for row in result['reused_helpers']:self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
        for row in result['derivative_source_ancestry']:self.assertEqual(hashlib.sha256((ROOT/row['parent_path']).read_bytes()).hexdigest(),row['parent_sha256'])
        self.assertNotIn('/Users/',json.dumps(result))

    def test_bounded_continuation_does_not_complete_or_release_the_head(self):
        result=json.loads((SOURCE.parent/'results.json').read_text())
        self.assertLessEqual(result['completed_construction_rounds'],4)
        self.assertFalse(result['goal_complete']);self.assertFalse(result['physical_acceptance']);self.assertFalse(result['manufacturing_authorized'])
        self.assertTrue(result['final_audit']['surface_study_checks_passed'])
        self.assertFalse(result['final_audit']['closed_volume'])


if __name__=='__main__':unittest.main()
