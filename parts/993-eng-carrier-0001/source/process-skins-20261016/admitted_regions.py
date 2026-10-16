"""Load only sealed, independently admitted free envelopes for the same real part."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pyslm.support
import shapely
import trimesh
from exact_regions import GRID_PARAMETERS,polygon_parts


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def geometry_sha(mesh):return hashlib.sha256(np.asarray(mesh.vertices,dtype=np.float64).tobytes()+np.asarray(mesh.faces,dtype=np.int64).tobytes()).hexdigest()


class EnvelopeStore:
    def __init__(self,path,input_sha256,parameters):
        self.path=Path(path).resolve();self.manifest=self.path/'envelopes.json'
        self.report=json.loads(self.manifest.read_text());self.manifest_sha256=sha(self.manifest)
        r=self.report
        if r.get('schema')!='carrier-exact-free-envelopes-v1' or r.get('status')!='passed':
            raise ValueError('Envelope store is not independently admitted')
        if r.get('input_sha256')!=input_sha256 or r.get('parameters')!=parameters:
            raise ValueError('Envelope store uses a different part or process parameters')
        self.files={self.manifest:self.manifest_sha256}
        for name,digest in r['files_sha256'].items():
            p=(self.path/name).resolve()
            if not p.is_relative_to(self.path) or not p.is_file() or sha(p)!=digest:
                raise ValueError('Envelope store file/identity mismatch')
            self.files[p]=digest
        if len(r['regions'])!=r['expected_regions'] or not r['regions']:raise ValueError('Missing envelope region')
        for row in r['regions']:
            if row.get('status')!='passed' or not row.get('all_vertical_intervals_retained') or not row.get('body_subtracted_in_same_coordinates'):
                raise ValueError('Envelope lacks free-interval/body subtraction admission')
            if self.path/row['envelope'] not in self.files:raise ValueError('Unhashed envelope')
            self._admit_native(row)
        self.verify()

    def _receipt(self,reference):
        if not isinstance(reference,dict) or set(reference)!={'receipt','receipt_sha256'}:
            raise ValueError('Native envelope audit is missing an explicit receipt identity')
        path=(self.path/reference['receipt']).resolve()
        if path not in self.files or self.files[path]!=reference['receipt_sha256']:
            raise ValueError('Native envelope audit receipt is not sealed')
        return json.loads(path.read_text())

    def _admit_native(self,row):
        mesh_sha=self.files[self.path/row['envelope']]
        audit=self._receipt(row.get('native_audit'))
        if audit.get('status')!='passed' or audit.get('final_mesh_sha256')!=mesh_sha:
            raise ValueError('Native envelope audit is not bound to its final mesh')
        topology=self._receipt(audit.get('topology'))
        exact=self._receipt(audit.get('exact_contacts'))
        repair=self._receipt(audit.get('repair'))
        if topology.get('input_sha256')!=mesh_sha or not topology.get('topology_passed'):
            raise ValueError('Native topology receipt refers to another or invalid mesh')
        counts=topology['topology']
        if any(counts[k]!=0 for k in ['open_edges','nonmanifold_edges','inconsistent_edge_orientation','zero_area_faces']) or counts['signed_volume_mm3']<=0:
            raise ValueError('Native envelope topology is rejected')
        if (exact.get('mesh_npz_sha256')!=mesh_sha or exact.get('raw_pairs_npz_sha256')!=topology['pairs_sha256'] or
                exact.get('raw_detector_pair_count_unchanged')!=topology['raw_pair_count'] or exact.get('remaining_pair_count')!=0):
            raise ValueError('Native intersection receipt is missing, rejected or belongs to another mesh')
        if topology['pairs_sha256'] not in self.files.values():raise ValueError('Native detector pairs are not sealed')
        if repair.get('final_mesh_sha256')!=mesh_sha or repair.get('status')!='passed':
            raise ValueError('Native coordinate-repair receipt is not admitted for this mesh')
        parameters=repair['parameters'];steps=repair['snap_step_mm_xyz']
        if parameters!={'snap_grid_size':51,'number_of_iterations':5} or len(steps)!=3 or any(not math.isfinite(s) or s<=0 for s in steps):
            raise ValueError('Unapproved coordinate-repair precision or iteration budget')
        bound=5*math.sqrt(sum(s*s for s in steps))/2
        if (repair.get('cumulative_displacement_bound_mm')!=bound or not repair.get('returned_intersection_free') or
                not 0<=repair['measured_bidirectional_deviation_max_mm']<=bound):
            raise ValueError('Native coordinate repair exceeds its declared mathematical bound')
        # The repair admission must also point to the retained native execution
        # and worker receipts, rather than accepting an unlinked status flag.
        execution=self._receipt(repair.get('native_execution'))
        native_audit=self._receipt(repair.get('native_audit'))
        native_json=self._receipt(repair.get('native_geometry'))
        distance_execution=self._receipt(repair.get('exact_distance_execution'))
        distance_audit=self._receipt(repair.get('exact_distance_audit'))
        if (not execution.get('identities_unchanged') or not execution.get('owned_scope_inactive') or
                execution.get('returncode') not in [0,2]):
            raise ValueError('Coordinate-repair execution was not confirmed immutable')
        if (native_audit.get('result_sha256')!=mesh_sha or not all(native_audit.get(k) for k in
                ['native_gate_pass','topology_gate_pass','source_face_lineage_complete'])):
            raise ValueError('Native coordinate-repair audit is not admitted for the mesh')
        native=native_audit['native']
        if native!=native_json:raise ValueError('Native snap geometry receipt differs from its audit')
        if (distance_execution.get('status')!='executed' or not distance_execution.get('identities_unchanged') or
                not distance_execution.get('owned_scope_inactive') or distance_audit.get('result_sha256')!=mesh_sha or
                distance_audit.get('input_sha256')!=native_audit['input_sha256'] or
                not all(distance_audit.get(k) for k in ['native_geometry_gate_pass','topology_gate_pass','drift_gate_pass','pass','source_face_lineage_complete']) or
                distance_audit.get('origin_audit_sha256')!=repair['native_audit']['receipt_sha256'] or
                distance_audit.get('origin_native_sha256')!=repair['native_geometry']['receipt_sha256'] or
                distance_audit.get('origin_execution_receipt_sha256')!=repair['native_execution']['receipt_sha256']):
            raise ValueError('Exact distance audit is missing, rejected or not bound to the original geometry execution')
        measurement=distance_audit['exact_distance']
        measured=max(measurement['input_to_output']['maximum_mm'],measurement['output_to_input']['maximum_mm'])
        if (not native['native_return'] or not native['all_output_coordinates_exactly_double'] or
                not native['post_double_self_intersection_free'] or native['exact_collinear_output_triangles']!=0 or
                native['snap_grid_bits']!=51 or native['iteration_budget']!=5 or native['grid_step_mm']!=steps or
                distance_audit['shape_drift_limit_mm']!=bound or not measurement['pass'] or
                measured!=repair['measured_bidirectional_deviation_max_mm']):
            raise ValueError('Repair admission differs from its actual native worker measurements')

    def verify(self):
        if any(sha(p)!=digest for p,digest in self.files.items()):raise ValueError('Sealed envelope store changed')

    def identify(self,part,generator,overhang_angle):
        self.verify();r=self.report
        if geometry_sha(part.geometry)!=r['part_geometry_sha256']:raise ValueError('Envelope/part build pose mismatch')
        if generator.outerSupportEdgeGap!=r['edge_gap_mm'] or generator.minimumAreaThreshold!=r['minimum_projected_area_mm2']:
            raise ValueError('Envelope projection parameters changed')
        sources=pyslm.support.utils.getOverhangMesh(part,overhang_angle,True)
        expected=[];exclusions=[]
        for i,source in enumerate(sources):
            projection=shapely.union_all(shapely.polygons(source.triangles[:,:,:2]))
            mask=projection.buffer(-generator.outerSupportEdgeGap)
            for j,polygon in enumerate(polygon_parts(mask)):
                if polygon.area>=generator.minimumAreaThreshold:expected.append((i,j,polygon))
                else:exclusions.append(dict(source_index=i,polygon_index=j,area_mm2=polygon.area))
        if len(expected)!=r['expected_regions']:raise ValueError('A complete required envelope region is missing')
        blocks=[];rows=[]
        for (source_index,polygon_index,polygon),record in zip(expected,r['regions']):
            if (source_index,polygon_index)!=(record['source_index'],record['source_polygon_index']):raise ValueError('Envelope region ordering differs')
            if polygon.area!=record['projected_area_mm2'] or list(polygon.bounds)!=record['bounds_xy_mm']:
                raise ValueError('Envelope projected domain differs from actual overhang')
            data=np.load(self.path/record['envelope'],allow_pickle=False)
            volume=trimesh.Trimesh(data['vertices'],data['faces'],process=False)
            if not volume.is_watertight or not volume.is_winding_consistent or volume.volume<=0 or np.any(volume.area_faces<=0):
                raise ValueError('Sealed envelope failed native topology checks')
            block=pyslm.support.GridBlockSupport(part,volume,sources[source_index],True)
            from layer_schedule import calendar
            block.exposureCalendar=calendar(float(part.geometry.bounds[1,2]),r['parameters']['layer_height_mm'])
            for name in GRID_PARAMETERS:setattr(block,name,getattr(generator,'_'+name))
            blocks.append(block);rows.append(dict(record,index=len(blocks)-1,generated=True,area_mm2=polygon.area,
                free_support_volume_mm3=volume.volume))
        generator.projectionCoverage=dict(algorithm=r['algorithm'],expected_regions=len(expected),generated_regions=len(blocks),
            complete_region_omissions=0,region_projection_admission_passed=True,configured_area_exclusions=exclusions,
            edge_gap_mm=r['edge_gap_mm'],minimum_projected_area_mm2=r['minimum_projected_area_mm2'],regions=rows,
            envelope_store_sha256=self.manifest_sha256,envelope_store_files_sha256={p.name:d for p,d in self.files.items()})
        self.verify();return blocks
