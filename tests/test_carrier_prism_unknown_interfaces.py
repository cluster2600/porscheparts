"""A repaired face cannot index −1 and borrow an original or floor anchor."""
from pathlib import Path
import importlib.util
import json
import hashlib
import sys
import tempfile
import unittest
if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional coverage runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):raise unittest.SkipTest('Coverage runtime required')
import numpy as np
import trimesh
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
from interface_sources_prisms_v2 import attach

class UnknownPrismInterfaces(unittest.TestCase):
 def test_unknown_face_at_plate_does_not_borrow_last_parent_or_floor_anchor(self):
  with tempfile.TemporaryDirectory() as directory:
   directory=Path(directory);paths=[]
   v=np.array([[0.,0.,1.],[1.,0.,1.],[0.,1.,1.],[0,0,0],[1,0,0],[0,1,0]])
   f=np.array([[0,1,2]],dtype=np.int64)
   for name in ['roofs','mask','part']:
    path=directory/(name+'.npz');np.savez(path,vertices=v[:3],faces=f);paths.append(path)
   audit=dict(leaf_role_order=['positive_roof_prisms','mask','part','clip_bbox'],leaf_face_counts=[8,1,1,12],
    input_sha256=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
   raw=dict(vertices=v[:3],faces=f,source_face=np.array([1]),source=np.array([0]),
    all_parent_offsets=np.array([0,1]),all_parent_faces=np.array([1]))
   final=dict(source_face=np.array([1,-1]),source=np.array([0,-1]))
   volume=trimesh.Trimesh(v,[[0,1,2],[3,4,5]],process=False)
   schema=SOURCE.parent/'native-cgal-prism-free-20261016/prism-face-schema.json'
   receipt=attach(volume,final,raw,audit,*paths,schema,np.array([0,-1],dtype=np.int64))
   self.assertEqual(volume.face_attributes['interface_kind'].tolist(),[1,0])
   self.assertEqual(receipt['unknown_final_face_ids'],[1])
   with self.assertRaisesRegex(ValueError,'map is invalid'):
    attach(volume,final,raw,audit,*paths,schema,np.array([0,-2],dtype=np.int64))
