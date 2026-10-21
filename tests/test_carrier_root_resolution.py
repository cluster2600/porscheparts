"""Exact generating-entity capture and a measured section of a known cylinder."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

try:
    import gmsh
    import numpy as np
    from build123d import Cylinder,export_step
except (ImportError,OSError):
    gmsh=None

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/design-20261016'


def load(name):
    spec=importlib.util.spec_from_file_location('carrier_'+name,SOURCE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


@unittest.skipIf(gmsh is None,'Optional native CAD/Gmsh runtime is unavailable')
class CarrierRootResolutionTests(unittest.TestCase):
    def test_capture_and_readback_of_known_cylinder_section(self):
        capture=load('mesh_root_entities');reader=load('audit_root_resolution')
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);mesh=folder/'mesh-7';mesh.mkdir();output=folder/'resolution.json'
            export_step(Cylinder(1,2,rotation=(0,90,0)),folder/'carrier.step')
            selection={'sections':[{'label':'known-R1','plane_X_mm':0.,'point_on_blend_face_mm':[0.,2**-.5,2**-.5],
                                    'reference_section_radius_mm':1.,'reference_IP_xyz_mm':[0.,.5,.5]}]}
            gmsh.initialize()
            try:
                for key,value in [('General.Terminal',0),('General.NumThreads',1),('Mesh.MeshSizeMin',.2),
                                  ('Mesh.MeshSizeMax',.25),('Mesh.ElementOrder',2),('Mesh.SecondOrderLinear',1),('Mesh.SaveAll',0)]:
                    gmsh.option.setNumber(key,value)
                gmsh.model.occ.importShapes(str(folder/'carrier.step'));gmsh.model.occ.synchronize()
                volumes=gmsh.model.getEntities(3);gmsh.model.addPhysicalGroup(3,[volumes[0][1]],name='BODY')
                gmsh.model.mesh.generate(3);capture.capture(mesh,selection)
                tags,xyz,_=gmsh.model.mesh.getNodes();order=np.argsort(tags);tags=tags[order];xyz=xyz.reshape(-1,3)[order]
                with np.load(mesh/'surface-entities.npz') as surfaces:facets=surfaces['faces'].copy()
                np.savez_compressed(mesh/'mesh.npz',tags=tags,xyz=xyz,faces=facets)
                gmsh.write(str(mesh/'mesh.inp'))
            finally:gmsh.finalize()
            (mesh/'mesh.json').write_text(json.dumps({'straight_midsides':True,'element_order':2,'global_mesh_size_factor':7/8}))
            receipt={'STEP_sha256':capture.sha(folder/'carrier.step'),
                     **{key:capture.sha(mesh/name) for key,name in [('mesh_inp_sha256','mesh.inp'),
                       ('surface_entities_npz_sha256','surface-entities.npz'),('surface_entities_json_sha256','surface-entities.json')]}}
            (mesh/'surface-capture-receipt.json').write_text(json.dumps(receipt))
            report=reader.audit(folder,mesh,output);section=report['sections'][0]
            self.assertAlmostEqual(section['exact_CAD_section_length_mm'],2*np.pi,places=10)
            self.assertGreater(section['boundary_facet_section_segments'],20)
            self.assertLess(section['section_polyline_length_mm'],2*np.pi)
            self.assertLess(section['maximum_sampled_chord_midpoint_distance_to_CAD_section_mm'],.06)
            self.assertLess(section['nearest_Gauss_to_reference_IP']['distance_to_reference_IP_mm'],.25)


if __name__=='__main__':unittest.main()
