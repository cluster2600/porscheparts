"""Analytic controls for composed surface maps with retained vertex ancestry."""
from fractions import Fraction as F
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/vertex_map_certificate.py'
SPEC=importlib.util.spec_from_file_location('carrier_vertex_map',P);M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class VertexMapCertificateTests(unittest.TestCase):
 def test_disjoint_contractions_use_maximum_displacement_not_sum(self):
  points=[(0,0,0),(1/32,0,0),(10,0,0),(10+1/32,0,0)];mapping=M.VertexMap(points)
  self.assertEqual(mapping.apply(0,1),F(1,32));self.assertEqual(mapping.apply(2,3),F(1,32))
  self.assertEqual(F(mapping.certificate()['actual_final_vertex_maximum_L1_mm']),F(1,32));self.assertEqual(points,[(0,0,0),(1/32,0,0),(10,0,0),(10+1/32,0,0)])

 def test_composed_map_checks_original_ancestors_not_only_last_edge(self):
  mapping=M.VertexMap([(0,0,0),(1/32,0,0),(1/16,0,0)])
  mapping.apply(1,0);self.assertEqual(mapping.proposal(2,1),F(1,16));mapping.apply(2,1)
  certificate=mapping.certificate();self.assertEqual(F(certificate['actual_final_vertex_maximum_L1_mm']),F(1,16));self.assertEqual(set(certificate['nontrivial_clusters'][0]['original_vertices']),{0,1,2})
