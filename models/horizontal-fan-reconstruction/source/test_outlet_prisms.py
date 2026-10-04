#!/usr/bin/env python3
"""Independent small geometric/conservation tests, no solver or private inputs."""
import copy,unittest,tempfile,json
from pathlib import Path
import numpy as np
from append_outlet_prisms import append_arrays,write_mesh,add_zones,initialize_fields,listfile
from analyze_flow_balance import field_values,patch_block
from analyze_d2_result import native_table
from measurement_window import require_measurement_window
from verify_d2 import validate_partial


def face_geometry(points,faces):
    tri=points[faces[:,:3]];sf=.5*np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);fc=tri.mean(axis=1);quad=faces[:,3]>=0
    if quad.any():
        q=points[faces[quad]];sf[quad]=.5*np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])+.5*np.cross(q[:,2]-q[:,0],q[:,3]-q[:,0]);fc[quad]=q.mean(axis=1)
    return sf,fc


def volumes(points,faces,owner,neighbour):
    sf,fc=face_geometry(points,faces);v=np.einsum('ij,ij->i',sf,fc)/3;nc=int(max(owner.max(),neighbour.max()))+1;out=np.zeros(nc);np.add.at(out,owner,v);np.add.at(out,neighbour,-v[:len(neighbour)]);return out


def fixture():
    p=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1],[1,1,0]],dtype=float)
    # Two tetrahedra forming a pyramid, with a two-triangle planar base.
    f=np.array([[1,2,3],[0,1,3],[0,3,2],[1,4,3],[2,3,4],[0,2,1],[1,2,4]])
    o=np.array([0,0,0,1,1,0,1]);n=np.array([1]);patches=[{'name':name,'type':typ,'nFaces':nf,'startFace':s} for name,typ,nf,s in [('rotor','wall',2,1),('shroud','wall',1,3),('inlet','patch',1,4),('outlet','patch',2,5)]]
    return p,f,o,n,patches


class Conservation(unittest.TestCase):
    def test_core_face_map_and_cells(self):
        p,f,o,n,patches=fixture();m=append_arrays(p,f,o,n,patches,2,.275);map=m['old_to_new_faces']
        np.testing.assert_array_equal(m['points'][:len(p)],p);np.testing.assert_array_equal(m['faces'][map,:3],f);np.testing.assert_array_equal(m['owner'][map],o);np.testing.assert_array_equal(m['neighbour'][map[:len(n)]],n)
        np.testing.assert_allclose(volumes(m['points'],m['faces'],m['owner'],m['neighbour'])[:2],volumes(p,np.column_stack((f,np.full(len(f),-1))),o,n),atol=1e-15,rtol=0)
        self.assertTrue((m['owner'][:len(m['neighbour'])]<m['neighbour']).all());self.assertEqual(len(set(map)),len(f))
    def test_added_volume_and_orientation(self):
        m=append_arrays(*fixture(),2,.275);v=volumes(m['points'],m['faces'],m['owner'],m['neighbour']);self.assertTrue((v>0).all());self.assertAlmostEqual(v[2:].sum(),.275,14)
        sf,_=face_geometry(m['points'],m['faces']);map=m['old_to_new_faces'];self.assertTrue((sf[map[5:7],2]<0).all());self.assertEqual(m['side_edges'],4);self.assertEqual(len(v),6)
        patch=next(p for p in m['patches'] if p['name']=='outlet');self.assertTrue((sf[patch['startFace']:patch['startFace']+patch['nFaces'],2]<0).all())
    def test_common_flux_conservation(self):
        m=append_arrays(*fixture(),2,.275);flux=np.zeros(len(m['faces']));outlet=np.array([2.,3.]);caps=m['kind']==1;far=m['kind']==3;flux[caps|far]=outlet[m['column'][caps|far]];div=np.zeros(6);np.add.at(div,m['owner'],flux);np.add.at(div,m['neighbour'],-flux[:len(m['neighbour'])]);np.testing.assert_allclose(div[2:],0,atol=0,rtol=0);self.assertEqual(flux[m['old_to_new_faces'][5:7]].sum(),5.)
    def test_written_zones_maps_and_seed_correspondence(self):
        p,f,o,n,patches=fixture();m=append_arrays(p,f,o,n,patches,2,.275)
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';case=Path(directory)/'case';mesh=source/'constant/polyMesh';mesh.mkdir(parents=True);(source/'960').mkdir();(case/'960').mkdir(parents=True)
            listfile(mesh/'points','vectorField',['('+ ' '.join(map(str,row))+')' for row in p]);listfile(mesh/'neighbour','labelList',n)
            write_mesh(case,m,(mesh/'points').read_text())
            ids={'commonPressureBand':np.array([0]),'commonOutletOwners':np.array([0,1]),'commonTipWake':np.array([1])}
            oldzone='FoamFile {version2.0; format ascii; class regIOobject; object cellZones;}\n1\n(\nrotorZone {type cellZone; cellLabels List<label> 1(1); }\n)\n'
            add_zones(case,oldzone,ids,m['old_to_new_faces'][5:7]);text=(case/'constant/polyMesh/cellZones').read_text();self.assertIn('rotorZone {type cellZone; cellLabels List<label> 1(1); }',text);self.assertIn('commonOutletFlux',(case/'constant/polyMesh/faceZones').read_text())
            for name in ['U','p','k','omega','nut','phi','Uf']:
                components=3 if name in ['U','Uf'] else 1;isvol=name not in ['phi','Uf'];values=['(1 2 3)','(4 5 6)'] if components==3 else ['1','2'];values=values if isvol else values[:1];outvalues=['(2 3 -4)','(5 6 -7)'] if components==3 else ['2','3'];kind='vector' if components==3 else 'scalar';zero='(0 0 0)' if components==3 else '0'
                text='FoamFile {version 2.0; format ascii; class '+('vol' if isvol else 'surface')+kind.title()+'Field; object '+name+';}\ninternalField nonuniform List<'+kind+'>\n'+str(len(values))+'\n(\n'+'\n'.join(values)+'\n);\nboundaryField {\n'
                for patch in patches:
                    text+=patch['name']+' {type calculated; value '+('nonuniform List<'+kind+'>\n2\n(\n'+'\n'.join(outvalues)+'\n);' if patch['name']=='outlet' else 'uniform '+zero+';')+'}\n'
                (source/'960'/name).write_text(text+'}\n')
            records=initialize_fields(source,case,m);self.assertTrue(all(x['core_values_identical'] for x in records.values()));phi=field_values((case/'960/phi').read_text(),'internalField',len(m['neighbour']),1);np.testing.assert_array_equal(phi[m['old_to_new_faces'][5:7]],[2,3]);self.assertIn('bufferSides',(case/'960/U').read_text())

    def test_actual_vector_table_syntax_and_partial_window_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'forces.dat';p.write_text('# Time forces moments\n1000 ((1e-3 2 3) (4 5 6)) ((7 8 -3.8) (10 11 -0.04))\n')
            row=native_table(p);self.assertEqual(row.shape,(1,13));self.assertAlmostEqual(row[0,9]+row[0,12],-3.84)
            partial=[[i,1] for i in range(961,1001)]
            with self.assertRaises(ValueError):require_measurement_window(list(range(961,1021)),partial,partial,partial,60)

    def test_partial_native_report_cannot_be_promoted(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'results/cfd/D2-partial-pair-analysis.json').read_text());validate_partial(r)
        for key in ['extended_completed60','both_cases_stationary_admitted','domain_comparison_gate_evaluated']:
            q=copy.deepcopy(r);q[key]=True
            with self.assertRaises(ValueError):validate_partial(q)
        q=copy.deepcopy(r);del q['MPI1000_coverage']['finite_completed1000_field_counts']['k']
        with self.assertRaises(ValueError):validate_partial(q)

    def test_nonplanar_or_reverse_exit_rejected(self):
        for reverse in [False,True]:
            p,f,o,n,patches=fixture()
            if reverse:f[5]=f[5,::-1]
            else:p[4,2]=.01
            with self.assertRaises(ValueError):append_arrays(p,f,o,n,patches,2,.275)


if __name__=='__main__':unittest.main()
