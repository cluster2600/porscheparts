"""Known-area/volume tests for exact support sheets and free-interval admission."""
from pathlib import Path
import sys
import hashlib
import importlib.util
import json
import tempfile
import unittest
if importlib.util.find_spec('pyslm') is None:
    raise unittest.SkipTest('Optional patched PySLM runtime required')
from pyslm.support import support as native_support
if not hasattr(native_support,'_triangulate_exact_projected_domain'):
    raise unittest.SkipTest('The distinct coverage runtime is required')
import numpy as np
from shapely.geometry import Polygon
import trimesh

SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
sys.path.insert(0,str(SOURCE))
from grid_intervals import free_section,trim_and_admit,contacts
from prismatic_envelopes import prism_boundary_chain,reduce_exact_horizontal_patches
from admitted_regions import EnvelopeStore
from peripheral_skins import geometry as support_geometry,vertical_components,unfold,remap
from quantized_contacts import restore_short_horizontal_interfaces
from layer_schedule import calendar,no_exposure


class ExactSupportGeometry(unittest.TestCase):
    def test_continuous_interval_restores_real_core_and_refuses_to_join_separate_gaps(self):
        import shapely
        from continuous_interfaces import repair
        free=shapely.box(0,0,10,1)
        native=shapely.union_all([shapely.box(0,0,2,.4),shapely.box(6,.6,7,1.2)])
        interface=dict(upper=[[[0,1],[10,1]]],lower=[[[0,0],[10,0]]])
        result,receipt=repair(native,free,interface,.2)
        self.assertEqual(receipt['selected_intervals'],1)
        self.assertEqual(free.difference(result).area,0)
        self.assertEqual(result.bounds,(0.,0.,10.,1.2))
        self.assertGreater(receipt['intervals'][0]['added_material_area_mm2'],0)
        second=shapely.box(0,1.1,10,2)
        domain=shapely.union_all([free,second])
        both=dict(upper=[[[0,1],[10,1]],[[0,2],[10,2]]],
                  lower=[[[0,0],[10,0]],[[0,1.1],[10,1.1]]])
        with self.assertRaisesRegex(ValueError,'join distinct free intervals'):
            repair(shapely.GeometryCollection(),domain,both,.2)

    def test_native_continuous_horizontal_roof_has_exposed_contacts_at_60um(self):
        import pyslm.support,shapely
        volume=trimesh.creation.box([30,20,1]);volume.apply_translation([15,10,.5])
        block=pyslm.support.GridBlockSupport(supportVolume=volume);block.gridSpacing=[5,5]
        block.supportWallThickness=1;block.supportTeethBaseInterval=1.5
        block.useLowerSupportTeeth=True;block.useUpperSupportTeeth=True;block.generateTrussGrid=False
        block.continuousFragmentedInterfaces=True
        surface=support_geometry(block)
        self.assertEqual(block.skinCoverage['material_connection_graph']['status'],'passed')
        self.assertGreaterEqual(surface.bounds[0,2],0.)
        self.assertGreater(surface.bounds[1,2],1.05)
        source=SOURCE.parent/'process-scanpath-audit-20261016/exact_support_section.py'
        spec=importlib.util.spec_from_file_location('continuous_roof_exact_sections',source)
        hook=importlib.util.module_from_spec(spec);spec.loader.exec_module(hook)
        z_bounds=np.c_[surface.triangles[:,:,2].min(axis=1),surface.triangles[:,:,2].max(axis=1)]
        sections={float(z):hook.support_section(surface,float(z),z_bounds) for z in calendar(1.2,.06)}
        self.assertGreater(len(sections[.03]),0)
        # The first actual part exposure above the horizontal roof is z=1.05.
        # A continuous sheet ending at z=1 would miss it; explicit penetration
        # must produce a positive line inside the real box section [0,30]x[0,20].
        exposed=sections[1.05];part_section=shapely.box(0,0,30,20)
        self.assertTrue(any(shapely.LineString(segment[:,:2]).intersection(part_section).length>0 for segment in exposed))

    def test_positive_prism_ancestry_checks_every_parent_and_rejects_artificial_anchors(self):
        from interface_sources_prisms import attach
        schema=SOURCE.parent/'native-cgal-prism-free-20261016/prism-face-schema.json'
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory);paths=[]
            vertices=np.array([[0.,0.,1.],[1.,0.,1.],[0.,1.,1.]])
            faces=np.array([[0,1,2]],dtype=np.int64)
            for name in ['roofs','mask','part']:
                path=directory/(name+'.npz');np.savez(path,vertices=vertices,faces=faces);paths.append(path)
            audit=dict(leaf_role_order=['positive_roof_prisms','mask','part','clip_bbox'],
                leaf_face_counts=[8,1,1,12],input_sha256=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
            mesh=trimesh.Trimesh(vertices,faces,process=False)
            child=dict(autorefine_input_face=np.array([0]),source_face=np.array([1]),source=np.array([0]))
            raw=dict(vertices=vertices,faces=faces,source_face=np.array([1]),source=np.array([0]),
                all_parent_offsets=np.array([0,1]),all_parent_faces=np.array([1]))
            receipt=attach(mesh,child,raw,audit,*paths,schema)
            self.assertEqual(mesh.face_attributes['interface_kind'].tolist(),[1])
            self.assertEqual(receipt['clip_bbox_parents'],0)
            # The primary top face alone is insufficient: the complete parent
            # list also contains a part face whose reversed orientation is lower.
            conflicting=dict(raw,all_parent_offsets=np.array([0,2]),all_parent_faces=np.array([1,9]))
            with self.assertRaisesRegex(ValueError,'parents disagree'):
                attach(mesh,child,conflicting,audit,*paths,schema)
            artificial=dict(raw,all_parent_offsets=np.array([0,2]),all_parent_faces=np.array([1,10]))
            with self.assertRaisesRegex(ValueError,'clipping-box parent'):
                attach(mesh,child,artificial,audit,*paths,schema)
            with self.assertRaisesRegex(ValueError,'primary ancestry'):
                attach(mesh,dict(child,source_face=np.array([2])),raw,audit,*paths,schema)

    def test_native_full_sheet_mode_preserves_connected_contacts_without_truss_islands(self):
        import pyslm.support
        volume=trimesh.creation.box([30,20,10]);volume.apply_translation([15,10,5])
        block=pyslm.support.GridBlockSupport(supportVolume=volume);block.gridSpacing=[5,5]
        block.supportWallThickness=1;block.supportTeethBaseInterval=1.5
        block.useLowerSupportTeeth=True;block.useUpperSupportTeeth=True;block.generateTrussGrid=False
        surface=support_geometry(block)
        self.assertEqual(block.skinCoverage['support_strategy'],'native_full_sheet_no_truss_perforation')
        self.assertEqual(block.skinCoverage['material_connection_graph']['status'],'passed')
        self.assertEqual(len(block.skinCoverage['support_surface_face_groups']),11)
        segments=trimesh.intersections.mesh_plane(surface,[0,0,1],[0,0,5.])
        self.assertGreater(len(segments),0)
        self.assertTrue(all(row['passed'] for axis in block.gridCoverage['axes'] for plane in axis['planes'] for row in plane['contacts']))

    def test_interface_ownership_cannot_bridge_a_hole_between_valid_endpoints(self):
        domain=Polygon([(0,0),(10,0),(10,10),(0,10)],holes=[[(4,4),(6,4),(6,6),(4,6)]])
        receipt=contacts(domain,domain,dict(upper=[[[1,5],[9,5]]],lower=[[[0,0],[10,0]]]))
        component=next(row for row in receipt if row['kind']=='generated_material_component')
        self.assertEqual(component['upper_contact_traces_2d_mm'],[[[1.,5.],[4.,5.]],[[6.,5.],[9.,5.]]])
        self.assertEqual(component['upper_contact_trace_mm'],6.)
        self.assertEqual(component['free_domain_geometry_sha256'],hashlib.sha256(domain.wkb).hexdigest())

    def test_tilted_air_sides_are_not_part_or_plate_anchors(self):
        q=4*np.spacing(10.)
        domain=Polygon([(0,0),(10,0),(10+q,10),(q,10)])
        material=Polygon([(q/4,2.5),(10+q/4,2.5),(10+3*q/4,7.5),(3*q/4,7.5)])
        for interfaces in [None,dict(upper=[[[q,10],[10+q,10]]],lower=[[[0,0],[10,0]]])]:
            rows=contacts(material,domain,interfaces)
            self.assertTrue(all(not r['passed'] for r in rows))
            self.assertTrue(all(r['upper_contact_trace_mm']==r['lower_contact_trace_mm']==0 for r in rows))

    def test_schedule_exclusion_uses_actual_planes_not_a_height_threshold(self):
        planes=calendar(.2,.06)
        sheet=trimesh.Trimesh([[0,0,.031],[1,0,.031],[1,0,.089]],[[0,1,2]],process=False)
        proof=no_exposure(sheet,[0],planes)
        self.assertIsNotNone(proof)
        self.assertEqual(proof['preceding_plane']['z_mm'],.03)
        self.assertEqual(proof['following_plane']['z_mm'],.09)
        # A shorter sheet that actually crosses z=.03 must be retained.
        short=trimesh.Trimesh([[0,0,.0299],[1,0,.0299],[1,0,.0301]],[[0,1,2]],process=False)
        self.assertIsNone(no_exposure(short,[0],planes))
        # A vertex alone at the plane has zero section length; an edge does not.
        touch=trimesh.Trimesh([[0,0,.03],[1,0,.031],[1,0,.04]],[[0,1,2]],process=False)
        self.assertIsNotNone(no_exposure(touch,[0],planes))
        edge=trimesh.Trimesh([[0,0,.03],[1,0,.03],[1,0,.04]],[[0,1,2]],process=False)
        self.assertIsNone(no_exposure(edge,[0],planes))

    def test_short_tooth_free_interface_is_restored_from_its_identified_quantization(self):
        import shapely
        z=35.99000000953674
        domain=shapely.box(0,25.11,1.33,z);native=shapely.box(0,25.11,1.33,35.99)
        before=contacts(native,domain)
        self.assertFalse(before[0]['passed'])
        restored,receipt=restore_short_horizontal_interfaces(native,domain,1.5)
        self.assertEqual(restored.bounds[3],z)
        self.assertTrue(all(row['passed'] for row in contacts(restored,domain)))
        self.assertEqual(receipt['maximum_displacement_mm'],z-35.99)
        self.assertLess(receipt['maximum_displacement_mm'],receipt['maximum_allowed_displacement_mm'])
        # A long interface that receives a native tooth pattern is untouched.
        original=shapely.box(0,25.11,10,35.99)
        untouched,proof=restore_short_horizontal_interfaces(original,shapely.box(0,25.11,10,z),1.5)
        self.assertTrue(untouched.equals(original));self.assertEqual(proof['restored_edges'],[])

    def test_vertical_charts_partition_a_real_stepped_branch_without_area_stretch(self):
        lower=trimesh.creation.box([30,20,10]);lower.apply_translation([15,10,5])
        upper=trimesh.creation.box([10,30,10]);upper.apply_translation([5,15,15])
        volume=trimesh.boolean.union([lower,upper],engine='manifold')
        self.assertTrue(volume.is_watertight)
        components,_=vertical_components(volume)
        ids=np.concatenate(components)
        self.assertEqual(len(ids),len(np.unique(ids)))
        for component in components:
            domain,mapping,receipt=unfold(volume,component)
            mesh,back=remap(domain,mapping)
            self.assertAlmostEqual(domain.area,mesh.area,places=9)
            self.assertAlmostEqual(receipt['source_vertical_area_mm2'],mesh.area,places=9)

    def test_thin_horizontal_face_is_not_a_skin_and_tiny_vertical_face_is_retained(self):
        horizontal=trimesh.Trimesh([[0,0,2],[10,10,2],[20,np.nextafter(20.,np.inf),2]],[[0,1,2]],process=False)
        self.assertGreater(horizontal.area,0)
        self.assertEqual(len(vertical_components(horizontal)[0]),0)
        vertical=trimesh.Trimesh([[0,0,0],[1e-14,0,0],[1e-14,0,10]],[[0,1,2]],process=False)
        self.assertGreater(vertical.area,0)
        self.assertEqual(len(vertical_components(vertical)[0]),1)

    def test_generated_face_groups_bind_real_contacts_and_material(self):
        import pyslm.support
        volume=trimesh.creation.box([30,20,10]);volume.apply_translation([15,10,5])
        block=pyslm.support.GridBlockSupport(supportVolume=volume);block.gridSpacing=[5,5]
        block.supportWallThickness=1;block.supportTeethBaseInterval=1.5
        block.useLowerSupportTeeth=True;block.useUpperSupportTeeth=True
        mesh=support_geometry(block);groups=block.skinCoverage['support_surface_face_groups']
        self.assertEqual(len(groups),11)
        self.assertEqual(sum(g['face_range'][1]-g['face_range'][0] for g in groups),len(mesh.faces))
        self.assertEqual([g['face_range'][0] for g in groups],[0]+[g['face_range'][1] for g in groups[:-1]])
        report={'grid_coverage':block.gridCoverage,'peripheral_skin':block.skinCoverage}
        for group in groups:
            begin,end=group['face_range'];self.assertGreater(end,begin)
            self.assertTrue(np.all(mesh.face_attributes['type'][begin:end]==group['type']))
            self.assertTrue(np.all(mesh.face_attributes['order'][begin:end]==group['order']))
            self.assertEqual(hashlib.sha256(bytes.fromhex(group['component_geometry_wkb_hex'])).hexdigest(),group['component_geometry_sha256'])
            self.assertEqual(hashlib.sha256(bytes.fromhex(group['free_domain_geometry_wkb_hex'])).hexdigest(),group['free_domain_geometry_sha256'])
            contact=report
            for key in group['contact_reference'].strip('/').split('/'):
                contact=contact[int(key)] if isinstance(contact,list) else contact[key]
            self.assertEqual(contact['component_geometry_sha256'],group['component_geometry_sha256'])
            self.assertEqual(contact['free_domain_geometry_sha256'],group['free_domain_geometry_sha256'])
            self.assertEqual(contact['upper_contact_traces_2d_mm'],group['upper_contact_traces_2d_mm'])
            self.assertGreater(group['upper_contact_trace_mm'],0)
            self.assertGreater(group['lower_contact_trace_mm'],0)

    def test_contact_of_one_strip_does_not_admit_a_floating_island(self):
        import shapely
        domain=shapely.box(0,0,10,10)
        strip=shapely.box(1,0,2,10);island=shapely.box(5,4,6,5)
        receipt=contacts(shapely.union_all([strip,island]),domain)
        intervals=[r for r in receipt if r['kind']=='required_free_interval']
        components=[r for r in receipt if r['kind']=='generated_material_component']
        self.assertTrue(intervals[0]['passed'])
        self.assertEqual(len(components),2)
        self.assertEqual(sum(r['passed'] for r in components),1)
        self.assertFalse(all(r['passed'] for r in receipt))
        floating=next(r for r in components if not r['passed'])
        self.assertEqual(floating['component_area_mm2'],1.)
        self.assertEqual(floating['upper_contact_trace_mm'],0.)
        self.assertEqual(floating['lower_contact_trace_mm'],0.)

    def test_empty_or_escaped_envelope_store_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=root/'store';store.mkdir();foreign=root/'foreign.txt';foreign.write_text('known fixture')
            manifest=dict(schema='carrier-exact-free-envelopes-v1',status='passed',input_sha256='a'*64,
                parameters={},files_sha256={},regions=[],expected_regions=0)
            (store/'envelopes.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Missing envelope region'):EnvelopeStore(store,'a'*64,{})
            manifest['files_sha256']={'../foreign.txt':hashlib.sha256(foreign.read_bytes()).hexdigest()}
            (store/'envelopes.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'file/identity mismatch'):EnvelopeStore(store,'a'*64,{})

    def test_status_flags_without_native_mesh_audits_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);mesh=trimesh.creation.box()
            path=root/'envelope-000.npz';np.savez_compressed(path,vertices=mesh.vertices,faces=mesh.faces)
            manifest=dict(schema='carrier-exact-free-envelopes-v1',status='passed',input_sha256='a'*64,parameters={},
                files_sha256={path.name:hashlib.sha256(path.read_bytes()).hexdigest()},expected_regions=1,
                regions=[dict(envelope=path.name,status='passed',all_vertical_intervals_retained=True,body_subtracted_in_same_coordinates=True)])
            (root/'envelopes.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'Native envelope audit is missing'):EnvelopeStore(root,'a'*64,{})

    def test_retriangulation_retains_every_boundary_edge_and_real_volume(self):
        vertices=np.asarray([[x,y,10.] for y in [0.,5.,10.] for x in [0.,5.,10.]])
        faces=[]
        for row in range(2):
            for col in range(2):
                a=3*row+col;faces.extend([[a,a+4,a+1],[a,a+3,a+4]])
        source=trimesh.Trimesh(vertices,faces,process=False)
        reduced,receipt=reduce_exact_horizontal_patches(source)
        self.assertEqual(len(reduced.faces),6)
        self.assertEqual(receipt['patches'][0]['boundary_edges'],8)
        self.assertTrue(receipt['patches'][0]['boundary_edges_exactly_equal'])
        self.assertEqual(receipt['patches'][0]['symmetric_difference_area_mm2'],0)
        self.assertTrue(np.array_equal(reduced.vertices,vertices))
        original,a=prism_boundary_chain(source);smaller,b=prism_boundary_chain(reduced)
        self.assertEqual(original.volume,1000.)
        self.assertEqual(smaller.volume,1000.)
        self.assertTrue(smaller.is_watertight)

    def test_boundary_chain_preserves_multiplicity_not_a_max_height_proxy(self):
        xy=np.asarray([[0.,0.],[20.,0.],[0.,20.]])
        vertices=np.vstack([np.column_stack([xy,np.full(3,z)]) for z in [10.,20.]])
        source=trimesh.Trimesh(vertices,[[0,2,1],[3,5,4]],process=False)
        chain,receipt=prism_boundary_chain(source)
        self.assertEqual(chain.volume,6000.)
        self.assertEqual(receipt['sum_prism_volumes_mm3'],6000.)
        self.assertIn('not an embedded volume',receipt['interpretation'])

    def test_axis_sections_are_closed_without_ulp_gap_welding(self):
        volume=trimesh.creation.box([30,20,10]);volume.apply_translation([15,10,5])
        for value in [0.,5.,10.,30.]:
            section=free_section(volume,0,value)
            self.assertTrue(section.is_valid)
            self.assertAlmostEqual(section.area,200.,places=12)

    def test_full_triangle_clipping_removes_internal_opening_bridge(self):
        import pyslm.support
        polygon=Polygon([(0,0),(40,0),(40,30),(0,30)],holes=[[(11,11),(11,21),(21,21),(21,11)]])
        volume=trimesh.creation.extrude_polygon(polygon,10)
        # Both long-edge endpoints lie in the free material, while their interior
        # crosses the opening. An endpoint-only collision check would miss it.
        bridge=trimesh.Trimesh([[15,10,4],[15,22,4],[15,22,6],[15,10,6]],[[0,1,2],[0,2,3]],process=False)
        bridge.face_attributes['order']=np.zeros(2,dtype=int);bridge.face_attributes['type']=np.zeros(2,dtype=int)
        block=pyslm.support.GridBlockSupport(supportVolume=volume);block.gridSpacing=[5,5]
        native=block.generateSupportSlices()[0]
        order=next(int(o) for o in np.unique(native.face_attributes['order'])
            if native.triangles[np.flatnonzero(native.face_attributes['order']==o)[0],0,0]==15.)
        bridge.face_attributes['order'][:]=order
        mesh,receipt=trim_and_admit(volume,block.concatenateMeshes([native,bridge]),0,.2)
        self.assertGreater(sum(p['explicitly_trimmed_area_mm2'] for p in receipt['planes']),19.99)
        self.assertTrue(all(p['whole_surface_outside_admitted_domain_area_mm2']==0 for p in receipt['planes']))
        self.assertTrue(all(c['passed'] for p in receipt['planes'] for c in p['contacts']))


if __name__=='__main__':unittest.main()
