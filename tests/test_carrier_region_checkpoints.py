"""A native generated region can be reused only with its exact identities."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest

if importlib.util.find_spec('pyslm') is None:raise unittest.SkipTest('Optional patched PySLM runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):raise unittest.SkipTest('Coverage runtime required')
import numpy as np
import pyslm.support
import trimesh

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
import region_checkpoints as checkpoint
from peripheral_skins import geometry
from interface_sources import fixture
from layer_schedule import calendar


class RegionCheckpoints(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)
        volume=trimesh.creation.box([10,10,1]);volume.apply_translation([5,5,.5])
        self.block=pyslm.support.GridBlockSupport(supportVolume=volume)
        self.block.interfaceSourceReceipt=fixture(volume)
        self.block.gridSpacing=[5,5];self.block.generateTrussGrid=False;self.block.continuousFragmentedInterfaces=True
        self.block.exposureCalendar=calendar(1.2,.06)
        self.before=checkpoint.block_identity(self.block);self.runtime=checkpoint.runtime_identity()
        surface=geometry(self.block);self.graph=self.block.skinCoverage['material_connection_graph']
        np.savez_compressed(self.output/'support.npz',vertices=surface.vertices,faces=surface.faces,
            order=surface.face_attributes['order'],type=surface.face_attributes['type'])
        meta=dict(surface_sha256=checkpoint.sha(self.output/'support.npz'),
            peripheral_skin=self.block.skinCoverage,grid_coverage=self.block.gridCoverage)
        (self.output/'geometry-assessment.json').write_text(json.dumps(meta))
        (self.output/'material-connections.json').write_text(json.dumps(self.graph))
        self.sources={str(p):checkpoint.sha(p) for p in checkpoint.geometry_sources()}

    def write(self):
        return checkpoint.write_checkpoint(self.output,self.block,self.graph,self.before,
            self.runtime,checkpoint.runtime_identity(),self.sources,8)

    def test_native_region_replay_preserves_arrays_and_refuses_new_parameters_or_attestation(self):
        self.write();reader=checkpoint.PreparedRegion(self.output);loaded=reader.geometry(self.block)
        with np.load(self.output/'support.npz') as original:
            self.assertTrue(np.array_equal(loaded.vertices,original['vertices']))
            self.assertTrue(np.array_equal(loaded.faces,original['faces']))
        self.block.gridSpacing=[4,5]
        with self.assertRaisesRegex(ValueError,'requested geometry'):reader.geometry(self.block)
        self.block.gridSpacing=[5,5];self.block.interfaceSourceReceipt['algorithm']='different ancestry'
        with self.assertRaisesRegex(ValueError,'requested geometry'):reader.geometry(self.block)

    def test_reader_refuses_missing_output_hash_and_later_file_mutation(self):
        self.write();path=self.output/'region-checkpoint.json';receipt=json.loads(path.read_text())
        receipt['files_sha256']={};path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError,'all three outputs'):checkpoint.PreparedRegion(self.output)
        self.write();reader=checkpoint.PreparedRegion(self.output)
        with (self.output/'geometry-assessment.json').open('a') as target:target.write(' ')
        with self.assertRaisesRegex(ValueError,'output identity'):reader.geometry(self.block)

    def test_seal_refuses_changed_runtime_and_empty_graph(self):
        changed=dict(self.runtime,python_version='changed')
        with self.assertRaisesRegex(ValueError,'runtime changed'):
            checkpoint.write_checkpoint(self.output,self.block,self.graph,self.before,self.runtime,changed,self.sources,8)
        self.graph=dict(status='passed')
        with self.assertRaisesRegex(ValueError,'complete material graph'):self.write()
