from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'twins/935-horizontal-cooling-system-f0/source'))
try:
    import numpy as np
    import agglomerate_fluid_pairs as merge
    from import_conforming_volume import exact_orientation
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Requires NumPy')
class AgglomerationTests(unittest.TestCase):
    def geometry(self):
        return np.array([[1.,0,0],[0,1,0],[-1,-1,0],[0,0,1],[0,0,-1],[1,1,1]]),np.array([[0,1,2,3],[0,2,1,4],[5,0,3,1]])

    def fixture(self,root):
        parent=root/'parent';native=root/'native';proposal=root/'proposal'
        for p in [parent,native/'constant/polyMesh',native/'system',proposal]:p.mkdir(parents=True)
        v,c=self.geometry();boundary=merge.base.outer_faces(c);markers=np.array([1,2,3,3,3,4,4,4]);np.savez(parent/'volume.npz',vertices=v,tetrahedra=c,boundary=boundary,markers=markers)
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        audit={'volume_npz_sha256':sha(parent/'volume.npz'),'exact_PLC_volume_equal':True,'complete_boundary_coordinate_triangle_marker_bijection':True,'exact_cell_orientation':exact_orientation(v,c)}
        (parent/'assessment.json').write_text(json.dumps(audit))
        cells=c[[1,2,0]];rows,owners,cell_faces=merge.base.incidence(cells);tags={tuple(f):int(t) for f,t in zip(boundary,markers)};internal=np.flatnonzero(owners[:,1]>=0);external=np.flatnonzero(owners[:,1]<0);external=np.array(sorted(external,key=lambda i:(tags[tuple(rows[i])],*rows[i])));ids=np.r_[internal,external]
        faces=[]
        for fid in ids:
            owner=int(owners[fid,0]);position=np.flatnonzero(cell_faces[owner]==fid)[0];faces.append(cells[owner,merge.base.FACE_NODES[position]])
        faces=np.array(faces);o=owners[ids,0];n=owners[internal,1];mesh=native/'constant/polyMesh'
        def write(name,kind,values,fmt):
            with (mesh/name).open('w') as f:
                f.write(f'FoamFile\n{{format ascii;class {kind};object {name};}}\n{len(values)}\n(\n');np.savetxt(f,values,fmt=fmt);f.write(')\n')
        write('points','vectorField',v,'(%.17g %.17g %.17g)');write('faces','faceList',faces,'3(%d %d %d)');write('owner','labelList',o,'%d');write('neighbour','labelList',n,'%d')
        start=len(n);blocks=[]
        for name,kind,marker in [('inlet','patch',1),('outlet','patch',2),('duct','wall',3),('rotor','wall',4)]:
            size=int((markers==marker).sum());blocks.append(f'{name} {{type {kind};nFaces {size};startFace {start};}}');start+=size
        (mesh/'boundary').write_text('FoamFile\n{format ascii;class polyBoundaryMesh;object boundary;}\n4\n(\n'+'\n'.join(blocks)+'\n)\n')
        (native/'system/meshQualityDict').write_text('synthetic format fixture; no native CFD result\n')
        execution={'volume_audit_sha256':sha(parent/'assessment.json'),'result_sha256':{str(p.relative_to(native)):sha(p) for p in native.rglob('*') if p.is_file()}}
        (native/'execution.json').write_text(json.dumps(execution));np.savez(proposal/'pairs.npz',pairs=np.array([[0,1]]));(proposal/'receipt.json').write_text(json.dumps({'parent_audit_sha256':sha(parent/'assessment.json'),'proposal_sha256':sha(proposal/'pairs.npz')}))
        return parent,native,proposal,root/'output'

    def test_exact_unit_volume_convex_partition(self):
        v,c=self.geometry()
        self.assertEqual(merge.partition(v,c,np.array([[0,1]])),['6'])
        self.assertEqual(exact_orientation(v,c[:2])['signed_volume_exact'],'1')

    def test_nonconvex_duplicate_and_out_of_range_pairs_are_refused(self):
        v,c=self.geometry()
        for pairs in [np.array([[0,0]]),np.array([[0,1],[1,0]]),np.array([[0,3]])]:
            with self.assertRaises(ValueError):merge.partition(v,c,pairs)
        v[4]=[2,0,-1]
        with self.assertRaises(ValueError):merge.partition(v,c,np.array([[0,1]]))

    def test_empty_neighbour_list_requires_explicit_empty_support(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'neighbour';p.write_text('FoamFile {format ascii;class labelList;object neighbour;}\n0\n(\n)\n')
            self.assertEqual(merge.array(p,1,np.int64,empty=True).shape,(0,1))
            with self.assertRaises(ValueError):merge.array(p,1,np.int64)

    def test_complete_roundtrip_handles_reordered_native_cells_and_reversed_face(self):
        with tempfile.TemporaryDirectory() as folder:
            parent,native,proposal,out=self.fixture(Path(folder));merge.run(parent,native,proposal,out)
            m=np.load(out/'agglomeration.npz');np.testing.assert_array_equal(m['parent_to_native'],[2,0,1]);np.testing.assert_array_equal(m['parent_to_new'],[0,0,1]);self.assertTrue(m['face_reversed'].any())
            before=merge.read_mesh(native);after=merge.read_mesh(out)
            np.testing.assert_array_equal(after[0],before[0]);np.testing.assert_array_equal(after[1][len(after[3]):],before[1][len(before[3]):]);np.testing.assert_array_equal(after[2][:1],[0]);np.testing.assert_array_equal(after[3],[1])
            self.assertEqual((out/'constant/polyMesh/points').read_bytes(),(native/'constant/polyMesh/points').read_bytes())
            r=json.loads((out/'agglomeration.json').read_text());self.assertEqual(r['cells'],2);self.assertEqual(r['merged_polyhedral_cells'],1);self.assertFalse(r['CFD_accepted']);self.assertFalse(r['manufacturing_authorized'])

    def test_boundary_marker_mismatch_is_refused_even_with_updated_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            parent,native,proposal,out=self.fixture(Path(folder));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();z=np.load(parent/'volume.npz');values={k:z[k] for k in z.files};values['markers']=values['markers'].copy();values['markers'][0]=4;np.savez(parent/'volume.npz',**values)
            p=parent/'assessment.json';r=json.loads(p.read_text());r['volume_npz_sha256']=sha(parent/'volume.npz');p.write_text(json.dumps(r))
            for p,key in [(proposal/'receipt.json','parent_audit_sha256'),(native/'execution.json','volume_audit_sha256')]:
                r=json.loads(p.read_text());r[key]=sha(parent/'assessment.json');p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):merge.run(parent,native,proposal,out)
            self.assertFalse(out.exists())

    def test_modified_native_input_is_refused_before_output_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            parent,native,proposal,out=self.fixture(Path(folder));p=native/'constant/polyMesh/points';p.write_text(p.read_text()+'\n')
            with self.assertRaises(ValueError):merge.run(parent,native,proposal,out)
            self.assertFalse(out.exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'output';out.mkdir();(out/'keep').write_text('untouched')
            with self.assertRaises(ValueError):merge.run(root/'absent',root/'absent',root/'absent',out)
            self.assertEqual((out/'keep').read_text(),'untouched')


class AgglomerationCheckpointTests(unittest.TestCase):
    def test_complete_mixed_audits_do_not_qualify_CFD_or_physical_scope(self):
        r=json.loads((ROOT/'docs/research/935-horizontal-cooling/fluid-agglomeration-20261022.json').read_text())
        for path,digest in r['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
        self.assertTrue(all(value is False for value in r['scope'].values()))
        self.assertFalse(r['PicoGK_design_master_changed'])
        self.assertEqual(r['new_rotor_PDE_runs'],0)
        self.assertTrue(r['exact_PLC_volume_equal_from_complete_parent_partition'])
        self.assertEqual(r['full_proposal']['sampled_sources'],345)
        self.assertEqual(r['full_proposal']['decisions']['selected_disjoint_pair'],29)
        self.assertEqual([c['small_determinant_cells'] for c in r['mixed_native_cases'].values()],[442,419])
        for c in r['mixed_native_cases'].values():
            for flag in ['points_file_byte_identical','complete_parent_cell_partition_verified','every_native_cell_independently_checked','every_face_owner_neighbour_checked','complete_boundary_and_marker_bijection_preserved','exact_polyhedral_volume_equals_parent_sums','original_quality_dictionary_unchanged']:
                self.assertTrue(c[flag])
            self.assertFalse(c['extended_mesh_quality_passed'])
            self.assertEqual(c['failed_native_checks'],4)
        full=r['mixed_native_cases']['full'];self.assertEqual(full['cells'],890749);self.assertEqual(full['tetrahedra']+full['polyhedral_cells'],full['cells']);self.assertEqual(full['polyhedral_cells'],29)
        v=r['independent_final_verification'];self.assertEqual(v['VTK_point_precision_bits'],32);self.assertTrue(v['VTK_points_equal_exact_forward_precision_conversion']);self.assertTrue(v['native_double_points_exactly_preserved']);self.assertLessEqual(v['native_centroid_maximum_absolute_difference_m'],1e-12);self.assertLessEqual(v['native_volume_maximum_relative_difference'],1e-9)
        self.assertFalse(r['global_mesh_optimization_converged'])
        self.assertFalse(r['runtime']['new_paid_instance_created'])
        self.assertTrue(r['private_archive']['all_members_verified'])
        self.assertTrue(r['private_archive']['Mac_all_members_verified'])
        self.assertEqual(r['private_archive']['entries'],160)


if __name__=='__main__':unittest.main()
