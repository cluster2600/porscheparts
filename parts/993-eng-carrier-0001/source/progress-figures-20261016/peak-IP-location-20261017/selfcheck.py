"""Small stdlib checks of retained four-case data and direct coordinate display."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_peak_figure_stdlib_only',HERE/'render.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
load=lambda name:json.loads((HERE/'data'/name).read_text())


class Contracts(unittest.TestCase):
    def setUp(self):
        self.data=load('figure-data.json')
        self.sources=[load(name)for name in self.data['case_source_files']]
        self.args=[self.sources,load('peak-assessment.json'),load('peak-root-terminal.json'),
                   load('geometry.json'),load('study.json'),load('mesh-7.json')]
    def validate(self):m.validate_data(self.data,*self.args)
    def test_all_four_actual_complete_cases_pass(self):self.validate()
    def test_missing_reordered_or_changed_peak_refused(self):
        for kind in ('missing','order','stress','position'):
            with self.subTest(kind=kind):
                original=deepcopy(self.data)
                if kind=='missing':self.data['cases'].pop()
                elif kind=='order':self.data['cases'].reverse()
                elif kind=='stress':self.data['cases'][0]['maximum_VM_MPa']+=1
                else:self.data['cases'][0]['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm'][0]+=1
                with self.assertRaises(ValueError):self.validate()
                self.data=original
    def test_coincident_two_cases_are_not_deduplicated(self):
        groups=m.coincident_groups(self.data['cases'],self.data['labels'],[0,1])
        self.assertIn(['A','B'],list(groups.values()))
        self.assertEqual(sorted(label for values in groups.values()for label in values),['A','B','C','D'])
        self.assertEqual(len(self.data['cases']),4)
    def test_projection_selects_original_coordinates_without_pose_or_jitter(self):
        for case in self.data['cases']:
            point=case['all_global_maximum_ties'][0]['reference_undeformed_IP_xyz_mm']
            self.assertEqual(m.project_point(point,[0,1]),(point[0],point[1]))
            self.assertEqual(m.project_point(point,[0,2]),(point[0],point[2]))
    def test_actual_stress_and_h_values_preserved(self):
        self.assertEqual([c['maximum_VM_MPa']for c in self.data['cases']],
            [700.7608420501294,1857.9107572863848,617.7164972717483,1676.5460429720838])
        self.assertEqual([c['all_global_maximum_ties'][0]['corner_measure']['measured_h_mm']for c in self.data['cases']],
            [2.6038677635386436,2.6038677635386436,2.7688832354912423,2.5172357815814346])
    def test_load_stiffness_and_CAD_mass_changes_refused(self):
        for key,value in [('force_N',[0,0,4000]),('spring_stiffness_N_per_mm_per_eye_and_axis',10000.),('CAD_mass_kg',1.1),('CAD_mass_ceiling_kg',1.5)]:
            original=self.data[key];self.data[key]=value
            with self.assertRaises(ValueError):self.validate()
            self.data[key]=original
    def test_terminal_failure_refused(self):
        self.args[2]['actual_tool_returncode']=1
        with self.assertRaises(ValueError):self.validate()
    def test_continuous_map_amplification_or_jitter_refused(self):
        for key in ['no_continuous_stress_map','no_geometry_amplification','no_point_jitter']:
            self.data[key]=False
            with self.assertRaises(ValueError):self.validate()
            self.data[key]=True
    def test_discrete_distances_remain_in_exact_source_records(self):
        for actual,source in zip(self.data['cases'],self.sources):
            peak=actual['all_global_maximum_ties'][0];original=source['all_global_maximum_ties'][0]
            for key in ['nearest_prescribed_displacement_node','nearest_grounded_spring_node','nearest_applied_load_node']:
                self.assertEqual(peak[key],original[key])
                if peak[key]is not None:self.assertIn('discrete node set only',peak[key]['scope'])
    def test_stdlib_checks_import_no_plotting_or_FEA(self):
        self.assertFalse({'numpy','matplotlib','shapely','pyslm','gmsh','OCP'}&set(sys.modules))


if __name__=='__main__':unittest.main()
