"""Prepared/unrun stdlib guards: AST-extract only seed policy and integer incidence."""
import ast
import copy
import hashlib
import math
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
READER_SHA256='7ba14f2d91bbdfc4d7b2e26529238f212cc82c107507d92c96fca80cc832fd46'


def load_helpers():
    data=(HERE/'reader.py').read_bytes()
    if hashlib.sha256(data).hexdigest()!=READER_SHA256:raise ValueError('Frozen source mismatch')
    names={'expanded_from_prior','movable_from_poor_rows','incident_positions'}
    body=[n for n in ast.parse(data).body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in body}!=names:raise ValueError('Exact three pure helpers required')
    namespace={'math':math}
    exec(compile(ast.Module(body=body,type_ignores=[]),'actual-three-pure-helpers','exec'),namespace)
    return namespace


def literal():
    seeds=[10,11]
    # Second cell is initially good/shared; third is outside the first star but touches new12.
    cells=[(101,[1,2,10,11],.05),(103,[3,10,11,12],.5)]
    nodes=[(t,[float(t),-0. if t==1 else 0.,1.]) for t in [1,2,3,10,11,12]]
    prior=dict(status='direct_saved_file_readback_completed',bound_inputs_unchanged=True,
        complete_seed_star_census=dict(schema='962-complete-current-poor-seed-stars/v1',
            all_seed_stars_complete_including_initially_good_and_shared_cells=True,movable_node_tags=seeds,
            complete_incident_tetrahedra=[dict(tetrahedron_tag=t,node_tags=row,initial_native_SICN=q) for t,row,q in cells],
            unique_incident_nodes=[dict(node_tag=t,coordinates_mm=xyz,binary64_hex=[x.hex() for x in xyz],
                in_movable_seed_set=t in seeds,source_boundary_tag=t<=3,
                freshly_proved_classification_scope='below_dim3' if t<=3 else 'dim3') for t,xyz in nodes]))
    return prior,seeds,cells,nodes,[10,11,12,13,14],3


class Guards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.helpers=load_helpers()

    def test_one_expansion_keeps_boundary_and_second_context_fixed(self):
        args=literal()
        self.assertEqual(self.helpers['expanded_from_prior'](*args),[10,11,12])
        self.assertNotIn(13,self.helpers['expanded_from_prior'](*args))
        self.assertEqual(self.helpers['movable_from_poor_rows']([[1,2,10,11]],args[4],3),[10,11])

    def test_full_good_shared_and_new_seed_incidence_without_duplicates(self):
        args=literal();expanded=self.helpers['expanded_from_prior'](*args)
        full=[[1,2,10,11],[3,10,11,12],[1,2,12,13],[1,2,3,14]]
        first=self.helpers['incident_positions'](full,[10,11])
        new=self.helpers['incident_positions'](full,expanded)
        self.assertEqual(first,[0,1]);self.assertEqual(new,[0,1,2])
        self.assertTrue(set(first)<=set(new));self.assertEqual(len(new),len(set(new)))

    def test_missing_good_cell_extra_cell_and_corner_reversal_refuse(self):
        for change in ['missing','extra','reversed','quality']:
            args=list(copy.deepcopy(literal()))
            if change=='missing':args[2]=args[2][:1]
            elif change=='extra':args[2].append((105,[1,2,11,12],.6))
            elif change=='reversed':args[2][0]=(101,[2,1,10,11],.05)
            else:args[2][0]=(101,[1,2,10,11],.06)
            with self.assertRaises(ValueError):self.helpers['expanded_from_prior'](*args)

    def test_missing_coordinate_signed_zero_and_unclassified_interior_refuse(self):
        for change in ['missing','signedzero','unclassified','dimension']:
            args=list(copy.deepcopy(literal()))
            if change=='missing':args[3]=args[3][:-1]
            elif change=='signedzero':args[3][0][1][1]=0.
            elif change=='unclassified':args[4]=[10,11,13,14]
            else:args[0]['complete_seed_star_census']['unique_incident_nodes'][-1]['freshly_proved_classification_scope']='below_dim3'
            with self.assertRaises(ValueError):self.helpers['expanded_from_prior'](*args)

    def test_prior_proof_seed_and_selected_row_refusals(self):
        for change in ['status','bound','complete','seed','row']:
            args=list(copy.deepcopy(literal()))
            if change=='status':args[0]['status']='reading_saved_mesh'
            elif change=='bound':args[0]['bound_inputs_unchanged']=False
            elif change=='complete':args[0]['complete_seed_star_census']['all_seed_stars_complete_including_initially_good_and_shared_cells']=False
            elif change=='seed':args[1]=[11,10]
            else:args[2][0]=(101,[1,2,10,10],.05)
            with self.assertRaises(ValueError):self.helpers['expanded_from_prior'](*args)


if __name__=='__main__':unittest.main()
