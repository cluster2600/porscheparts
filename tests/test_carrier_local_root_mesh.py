"""Verify the local callback against a known circle and an unchanged remote line."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import gmsh
    import numpy as np
except (ImportError,OSError):
    gmsh=None

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016/mesh_local_root.py'
spec=importlib.util.spec_from_file_location('carrier_local_mesh',SOURCE)
local=importlib.util.module_from_spec(spec);spec.loader.exec_module(local)


class CarrierLocalMeshTests(unittest.TestCase):
    def test_remote_callback_preserves_the_original_clamp(self):
        regions=[{'bounds_mm':[[-1,-1,-1],[2,2,1]],'target_h_mm':.25}]
        self.assertEqual(local.local_size(20,0,0,.1,regions,7/8),2.)
        self.assertEqual(local.local_size(20,0,0,3.,regions,7/8),3.)
        self.assertEqual(local.local_size(20,0,0,20.,regions,7/8),8.)

    @unittest.skipIf(gmsh is None,'Optional native Gmsh runtime is unavailable')
    def test_actual_circle_refines_while_remote_line_coordinates_are_unchanged(self):
        def generate(target=None):
            gmsh.initialize()
            try:
                for name,value in [('General.Terminal',0),('General.NumThreads',1),('Mesh.MeshSizeMin',2 if target is None else 0),
                                   ('Mesh.MeshSizeMax',8),('Mesh.MeshSizeFactor',7/8),('Mesh.MeshSizeFromCurvature',18)]:
                    gmsh.option.setNumber(name,value)
                centre=gmsh.model.geo.addPoint(0,0,0,8)
                a=gmsh.model.geo.addPoint(1,0,0,8);b=gmsh.model.geo.addPoint(0,1,0,8)
                arc=gmsh.model.geo.addCircleArc(a,centre,b)
                c=gmsh.model.geo.addPoint(20,0,0,8);d=gmsh.model.geo.addPoint(30,0,0,8)
                line=gmsh.model.geo.addLine(c,d);gmsh.model.geo.synchronize()
                if target is not None:
                    regions=[{'bounds_mm':[[-1,-1,-1],[2,2,1]],'target_h_mm':target}]
                    gmsh.model.mesh.setSizeCallback(lambda dim,tag,x,y,z,lc:local.local_size(x,y,z,lc,regions,7/8))
                gmsh.model.mesh.generate(1)
                tags,points,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=tags[order];points=points.reshape(-1,3)[order]
                kind,ids,connectivity=gmsh.model.mesh.getElements(1,arc);self.assertEqual(list(kind),[1])
                coordinates=points[np.searchsorted(tags,connectivity[0].reshape(-1,2))]
                chords=np.linalg.norm(coordinates[:,1]-coordinates[:,0],axis=1)
                line_tags=gmsh.model.mesh.getNodes(1,line,includeBoundary=True)[0]
                remote=points[np.searchsorted(tags,line_tags)];remote=remote[np.argsort(remote[:,0])]
                return chords,remote
            finally:gmsh.finalize()
        coarse,remote_before=generate();fine,remote_after=generate(float(coarse.max())/2)
        self.assertGreater(len(fine),len(coarse))
        self.assertLessEqual(float(fine.max()),float(coarse.max())*.6)
        np.testing.assert_allclose(remote_after,remote_before,rtol=0,atol=1e-12)

    @unittest.skipIf(gmsh is None,'Optional native Gmsh runtime is unavailable')
    def test_surface_capture_identifies_actual_cylinder_facets(self):
        spec=importlib.util.spec_from_file_location('carrier_mesh_entities',SOURCE.with_name('mesh_root_entities.py'))
        capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory);gmsh.initialize()
            try:
                gmsh.option.setNumber('General.Terminal',0)
                gmsh.option.setNumber('General.NumThreads',1)
                gmsh.option.setNumber('Mesh.ElementOrder',2)
                gmsh.model.occ.addCylinder(-1,0,0,2,0,0,1)
                gmsh.model.occ.synchronize();gmsh.model.mesh.generate(2)
                point=[0,2**-.5,2**-.5]
                capture.capture(output,{'sections':[{'label':'known-cylinder','plane_X_mm':0,'point_on_blend_face_mm':point}]})
                report=json.loads((output/'surface-entities.json').read_text())
                entity=report['sections'][0]['entity_tag']
                self.assertEqual(next(r['type'] for r in report['entities'] if r['entity_tag']==entity),'Cylinder')
                with np.load(output/'surface-entities.npz',allow_pickle=False) as data:
                    selected=data['faces'][data['entity_tags']==entity]
                    self.assertGreater(len(selected),0)
                    self.assertEqual(selected.shape[1],3)
            finally:gmsh.finalize()


if __name__=='__main__':unittest.main()
