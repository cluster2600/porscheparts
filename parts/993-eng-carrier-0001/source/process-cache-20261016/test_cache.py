"""Focused identity, completeness and exact-array reuse tests for part-only cache."""
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
    import trimesh
    import pyslm
    import part_cache as cache
except ImportError:
    cache=None


@unittest.skipIf(cache is None,'Optional native PySLM runtime is unavailable')
class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.directory=self.root/'cache';self.directory.mkdir();(self.directory/'layers').mkdir()
        self.source=self.root/'part.stl';trimesh.creation.box(extents=[2,2,.06]).export(self.source)
        self.parameters=cache.parameters_only(cache.core_module().PARAMETERS)
        self.parameters.update(rotation_degrees_xyz=[0,0,0],support_gap_mm=0)
        self.part=cache.make_part(self.source,self.parameters)
        raw=[np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.],[-1.,-1.]])]
        self.result=(raw,[raw[0]*.8],np.array([[[-.5,0.],[.5,0.]]]),4.)
        row=cache.write_layer(self.directory,0,.03,self.result)
        with (self.directory/'layers.csv').open('w') as stream:
            writer=csv.DictWriter(stream,fieldnames=row);writer.writeheader();writer.writerow(row)
        self.report={'status':'part_layers_completed','source_and_runtime_unchanged_at_completion':True,
            'input_sha256':cache.sha(self.source),'part_parameters':self.parameters,
            'part_pose_and_arrays':cache.part_identity(self.part),'runtime':cache.runtime_identity(),
            'n_layers':1,'outputs_sha256':{str(p.relative_to(self.directory)):cache.sha(p) for p in self.directory.rglob('*') if p.is_file()}}
        self.save()

    def save(self):(self.directory/'report.json').write_text(json.dumps(self.report))
    def reader(self):return cache.CachedLayers(self.directory,self.source,self.parameters)

    def test_complete_cache_returns_exact_arrays_and_no_support_fields(self):
        result=self.reader()(self.part,.03)
        for a,b in zip(result[:2],self.result[:2]):
            for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
        np.testing.assert_array_equal(result[2],self.result[2]);self.assertEqual(result[3],4.)
        with np.load(self.directory/'layers/layer-00000.npz') as data:self.assertEqual(set(data.files),cache.FIELDS)

    def test_partial_cache_status_is_rejected(self):
        self.report['status']='partial';self.save()
        with self.assertRaises(ValueError):self.reader()

    def test_missing_layer_is_rejected(self):
        (self.directory/'layers/layer-00000.npz').unlink()
        with self.assertRaises(ValueError):self.reader()

    def test_corrupt_npz_is_rejected(self):
        with (self.directory/'layers/layer-00000.npz').open('ab') as stream:stream.write(b'corrupt')
        with self.assertRaises(ValueError):self.reader()

    def test_modified_source_and_part_parameters_are_rejected(self):
        self.parameters['hatch_distance_mm']*=2
        with self.assertRaises(ValueError):self.reader()
        self.parameters['hatch_distance_mm']/=2
        self.source.write_bytes(b'changed')
        with self.assertRaises(ValueError):self.reader()

    def test_pose_and_vertex_array_changes_are_rejected(self):
        reader=self.reader();self.part.geometry.vertices[0,0]+=.001
        with self.assertRaises(ValueError):reader(self.part,.03)

    def test_runtime_or_noncontiguous_coverage_are_rejected(self):
        self.report['runtime']['packages']['numpy']='other';self.save()
        with self.assertRaises(ValueError):self.reader()
        self.report['runtime']=cache.runtime_identity();self.report['n_layers']=2;self.save()
        with self.assertRaises(ValueError):self.reader()

    def test_npz_changed_after_initial_validation_is_rejected(self):
        reader=self.reader()
        with (self.directory/'layers/layer-00000.npz').open('ab') as stream:stream.write(b'changed')
        with self.assertRaises(ValueError):reader(self.part,.03)

    def test_wrong_midplane_is_rejected(self):
        with self.assertRaises(ValueError):self.reader()(self.part,.031)


if __name__=='__main__':unittest.main()
