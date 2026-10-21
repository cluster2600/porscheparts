"""Check the published binary volume/boundary chain and analytic native controls."""
from fractions import Fraction as F
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'parts/993-eng-carrier-0001/source/design-20261016/resume-20261020'
REPORT=ROOT/'docs/reports/carrier-resume-20261020'


class VolumeCheckpointTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('numpy'),'optional NumPy dataset verification')
    def test_published_skin_is_the_complete_boundary_of_the_published_volume(self):
        import numpy as np
        archive=SOURCE/'volume-checkpoint.npz'
        audit=json.loads((REPORT/'evidence/wildmeshing-volume-audit-001/assessment.json').read_text())
        expected=next(value for path,value in audit['source_sha256'].items()if path.endswith('/mesh.npz'))
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),expected)
        with np.load(archive,allow_pickle=False)as data:vertices=data['vertices'];cells=data['tetrahedra']
        self.assertEqual(len(cells),audit['exact_orientation']['tetrahedra'])
        self.assertGreater(F(audit['exact_orientation']['minimum_signed_determinant_mm3']),0)
        self.assertEqual(audit['exact_orientation']['negative'],0);self.assertEqual(audit['exact_orientation']['zero'],0)
        raw=gzip.decompress((SOURCE/'volume-checkpoint-boundary.mesh64.gz').read_bytes())
        with io.StringIO(raw.decode())as stream:nv,nf=map(int,stream.readline().split());points=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.int64)
        identity={tuple(v):i for i,v in enumerate(vertices)}
        self.assertEqual(len(identity),len(vertices));remap=np.array([identity[tuple(p)]for p in points])
        stored=np.unique(np.sort(remap[faces],axis=1),axis=0)
        full=np.concatenate([cells[:,[0,2,1]],cells[:,[0,1,3]],cells[:,[0,3,2]],cells[:,[1,2,3]]])
        unique,counts=np.unique(np.sort(full,axis=1),axis=0,return_counts=True)
        self.assertTrue(np.array_equal(unique[counts==1],stored));self.assertEqual(len(stored),nf)
        boundary=json.loads((REPORT/'evidence/wildmeshing-boundary-audit-001/assessment.json').read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),boundary['source_mesh_sha256'])
        self.assertEqual(boundary['status'],'complete_surface_screen_passed')

    def test_native_predicate_controls_use_exact_translations_and_a_stricter_guard(self):
        def read(path):
            lines=path.read_text().splitlines();nv,nf=map(int,lines[0].split())
            return [[F(x)for x in line.split()]for line in lines[1:1+nv]],lines[1+nv:]
        ref,faces=read(REPORT/'evidence/hausdorff-cgal56-control-001/inputs/reference.mesh64')
        for label,case,name,shift,larger in [('inside','hausdorff-cgal56-control-001','translated.mesh64',F(1,64),False),('outside','envelope-predicate-control-001','outside.mesh64',F(1,8),True)]:
            moved,moved_faces=read(REPORT/f'evidence/{case}/inputs/{name}');self.assertEqual(faces,moved_faces)
            for before,after in zip(ref,moved):self.assertEqual([b-a for a,b in zip(before,after)],[shift,0,0])
            result=json.loads((REPORT/f'evidence/envelope-predicate-control-001/{label}/assessment.json').read_text())
            self.assertEqual(result['public_predicate_distance_larger'],larger)
            self.assertLessEqual(F(result['stricter_predicate_threshold_mm'])+F(result['API_additive_error_mm']),F(result['fixed_limit_mm']))
            self.assertTrue(result['symmetric'])
