"""Reuse one generated region with exact input, source and runtime identities.

A checkpoint supplies geometry and its receipts. It does not grant any global
support admission or prove the exposure of the eventual layer vectors.
"""
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import sys

import numpy as np
import trimesh

SOURCE=Path(__file__).resolve().parent
DISTRIBUTIONS=('PythonSLM','numpy','trimesh','shapely','pyclipr','mapbox_earcut',
               'scipy','networkx','rtree','manifold3d','triangle')
LOCAL_SOURCES=('region_checkpoints.py','peripheral_skins.py','grid_intervals.py',
    'exact_regions.py','prismatic_envelopes.py','material_connections.py',
    'quantized_contacts.py','layer_schedule.py','zero_area_faces.py',
    'interface_sources.py','solid_sheets.py','continuous_interfaces.py')
AUDIT_SOURCES=('exact_contacts.py','exact_contacts_both.py','exact_zero_face_coverage.py',
               'exact_polygon_coverage.py','exact_intended_holes.py')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


def geometry_sources():
    result=[SOURCE/name for name in LOCAL_SOURCES]
    result.extend(SOURCE/name if (SOURCE/name).is_file() else SOURCE.parent/'process-scanpath-audit-20261016'/name for name in AUDIT_SOURCES)
    classifier=SOURCE/'classify_mesh_contacts.py'
    result.append(classifier if classifier.is_file() else SOURCE.parent/'design-20261016/classify_mesh_contacts.py')
    return result


def runtime_identity():
    """Hash installed geometry code and native extensions, excluding bytecode."""
    import pyslm
    files={};versions={}
    for name in DISTRIBUTIONS:
        distribution=metadata.distribution(name);versions[name]=distribution.version
        for item in distribution.files or []:
            path=Path(distribution.locate_file(item))
            if path.is_file() and (path.suffix in {'.py','.so','.dylib','.dll','.pyd'} or '.so.' in path.name):
                files[name+'/'+str(item)]=sha(path)
    # The editable PySLM distribution omits its source package from RECORD.
    package=Path(pyslm.__file__).resolve().parent
    for path in sorted(package.rglob('*.py')):files['PythonSLM/package/'+str(path.relative_to(package))]=sha(path)
    return dict(python_version=sys.version,python_executable_sha256=sha(sys.executable),
        platform=platform.platform(),machine=platform.machine(),versions=versions,files_sha256=files)


def array_identity(array):
    array=np.ascontiguousarray(array)
    return dict(dtype=array.dtype.str,shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest())


def _check_graph(graph,skin,vertices,faces):
    groups=skin.get('support_surface_face_groups',[])
    ids=[group['id'] for group in groups]
    actual=hashlib.sha256(vertices.tobytes()+faces.tobytes()).hexdigest()
    components=graph.get('components',[]);internal=graph.get('internal_connectivity',[])
    if (not groups or graph.get('status')!='passed' or graph.get('input_geometry_sha256')!=actual or
        graph.get('groups')!=len(groups) or graph.get('faces')!=len(faces) or
        sorted(i for component in components for i in component['group_ids'])!=sorted(ids) or
        not all(c.get('passed') and c.get('upper_contact_group_ids') and c.get('lower_contact_group_ids') for c in components) or
        sorted(c['group_id'] for c in internal)!=sorted(ids) or
        not all(c.get('passed') and c.get('remaining_components')==1 for c in internal)):
        raise ValueError('Region checkpoint has no complete material graph linked to its surface')


def block_identity(block):
    from exact_regions import GRID_PARAMETERS
    def mesh_identity(mesh):
        if mesh is None:return None
        return dict(vertices=array_identity(mesh.vertices),faces=array_identity(mesh.faces))
    parameters={name:getattr(block,name) for name in GRID_PARAMETERS}
    parameters.update(generateTrussGrid=block.generateTrussGrid,
        continuousFragmentedInterfaces=getattr(block,'continuousFragmentedInterfaces',False))
    parameters=json.loads(json.dumps(parameters,default=encoded,allow_nan=False))
    if 'interface_kind' not in block.supportVolume.face_attributes:raise ValueError('A checkpoint requires attested interface faces')
    attestation=json.loads(json.dumps(block.interfaceSourceReceipt,default=encoded,allow_nan=False))
    # Runtime file locations may change after an immutable store is packaged.
    # Their content hashes and all remaining ancestry fields stay binding.
    for source in attestation.get('source_meshes',{}).values():source.pop('path',None)
    return dict(part=mesh_identity(block.supportObject.geometry) if block.supportObject is not None else None,
        envelope=mesh_identity(block.supportVolume),overhang=mesh_identity(block.supportSurface),
        interface_kind=array_identity(block.supportVolume.face_attributes['interface_kind']),
        interface_attestation=attestation,
        parameters=parameters,calendar=array_identity(block.exposureCalendar))


def write_checkpoint(output,block,graph,block_before,runtime_before,runtime_after,source_sha256,source_index):
    """Seal a completed region, conservatively refusing an unanchored graph."""
    output=Path(output)
    if runtime_before!=runtime_after:raise ValueError('Region geometry runtime changed during generation')
    if block_identity(block)!=block_before:raise ValueError('Region inputs or parameters changed during generation')
    if graph.get('status')!='passed':raise ValueError('An unanchored region cannot become a reusable checkpoint')
    source_hashes={p.name:sha(p) for p in geometry_sources()}
    if any(source_sha256.get(str(p))!=h for p in geometry_sources() for h in [source_hashes[p.name]]):
        raise ValueError('Region source identities differ from the frozen generation inputs')
    files={name:sha(output/name) for name in ['support.npz','geometry-assessment.json','material-connections.json']}
    metadata_receipt=json.loads((output/'geometry-assessment.json').read_text())
    with np.load(output/'support.npz',allow_pickle=False) as mesh:
        _check_graph(graph,metadata_receipt['peripheral_skin'],mesh['vertices'],mesh['faces'])
    receipt=dict(schema='support-region-checkpoint-1',status='region_geometry_completed_no_global_admission',
        scope='Reusable generated material only; six global admissions and actual layer exposure audit remain required.',
        source_index=source_index,block_identity=block_before,source_sha256=source_hashes,
        runtime_before=runtime_before,runtime_after=runtime_after,runtime_unchanged=True,
        files_sha256=files)
    (output/'region-checkpoint.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    return receipt


class PreparedRegion:
    """Validate and load a sealed region against the block the recipe requests."""
    def __init__(self,directory):
        self.directory=Path(directory).resolve()
        self.path=self.directory/'region-checkpoint.json';self.receipt_sha256=sha(self.path);self.receipt=json.loads(self.path.read_text())
        receipt=self.receipt
        if receipt.get('schema')!='support-region-checkpoint-1' or receipt.get('status')!='region_geometry_completed_no_global_admission':
            raise ValueError('Not a completed region checkpoint')
        current={p.name:sha(p) for p in geometry_sources()}
        if current!=receipt['source_sha256']:raise ValueError('Region checkpoint geometry sources differ')
        if not receipt.get('runtime_unchanged') or receipt['runtime_before']!=receipt['runtime_after'] or runtime_identity()!=receipt['runtime_before']:
            raise ValueError('Region checkpoint runtime differs')
        if set(receipt['files_sha256'])!={'support.npz','geometry-assessment.json','material-connections.json'}:
            raise ValueError('A region checkpoint must bind all three outputs')
        self.verify()
        self.metadata=json.loads((self.directory/'geometry-assessment.json').read_text())
        self.graph=json.loads((self.directory/'material-connections.json').read_text())
        if self.graph.get('status')!='passed':raise ValueError('Region checkpoint graph was rejected')
        with np.load(self.directory/'support.npz',allow_pickle=False) as mesh:
            self.surface=trimesh.Trimesh(mesh['vertices'],mesh['faces'],process=False,
                face_attributes={name:mesh[name] for name in ['order','type']})
        geometry_sha=hashlib.sha256(self.surface.vertices.tobytes()+self.surface.faces.tobytes()).hexdigest()
        if self.graph.get('input_geometry_sha256')!=geometry_sha:raise ValueError('Region checkpoint graph and material differ')
        _check_graph(self.graph,self.metadata['peripheral_skin'],self.surface.vertices,self.surface.faces)
        if sha(self.directory/'support.npz')!=self.metadata['surface_sha256']:raise ValueError('Region metadata and material differ')
        self.verify()
        if runtime_identity()!=receipt['runtime_before']:raise ValueError('Region checkpoint runtime changed while loading')

    def verify(self):
        if sha(self.path)!=self.receipt_sha256:raise ValueError('Region checkpoint receipt changed')
        if any(sha(self.directory/name)!=value for name,value in self.receipt['files_sha256'].items()):
            raise ValueError('Region checkpoint output identity mismatch')
        if {p.name:sha(p) for p in geometry_sources()}!=self.receipt['source_sha256']:
            raise ValueError('Region checkpoint geometry sources changed')

    def geometry(self,block):
        self.verify()
        if block_identity(block)!=self.receipt['block_identity']:raise ValueError('Region checkpoint requested geometry, parameters or layer schedule differ')
        # Copy metadata to avoid mutating the receipt when the caller assembles it.
        block.skinCoverage=json.loads(json.dumps(self.metadata['peripheral_skin']))
        block.skinCoverage['material_connection_graph']=self.graph
        block.gridCoverage=json.loads(json.dumps(self.metadata['grid_coverage']))
        surface=self.surface.copy();self.verify()
        return surface
