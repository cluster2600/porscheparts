"""Work-only private v6 adapter; immutable originals precede certified faces.

No capsule is authorised by this source alone. The caller must pin the exact
flat manifest. All six historical gates and the complete exposure audit remain.
"""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path
import sys

V6_SHA='6a6d3720e4a9c98c05393ea6446b33f6596ba3addcd73184ccaec5c8b64b9343'
GRAPH_SHA='1bc3fbebe739a08f72d5f8b5e85841b3f67d40f035f9bd0c283492c2bbf077e6'
CHECKPOINT_SHA='943c8f9193f3ea8a4d1654fec91482e4167c4c4ce351a65c9fd8623ddb9ac589'
INDICES=(0,1,2,3,8,9,10)
MANIFEST='topology-manifest.json'
KEY='certified_support_topology'
ARRAYS={'vertices','faces','order','type'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def identity(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def array_identity(array):return dict(dtype=array.dtype.str,shape=list(array.shape),sha256=hashlib.sha256(array.tobytes()).hexdigest())
def array_identities(arrays):return {n:array_identity(a)for n,a in arrays.items()}


def local_name(name):
    if (not isinstance(name,str)or Path(name).name!=name or name in ('.','..')or
            not name.startswith('topology-')or '/'in name or '\\'in name):
        raise ValueError('Only unique flat topology-* capsule names are allowed')
    return name


def load_arrays(np,path):
    with np.load(path,allow_pickle=False)as data:
        if set(data.files)!=ARRAYS:raise ValueError('Exactly four retained arrays are required')
        return {n:data[n].copy()for n in data.files}


def validate_arrays(arrays):
    if set(arrays)!=ARRAYS:raise ValueError('Exactly four retained arrays are required')
    vertices,faces=arrays['vertices'],arrays['faces'];nv=len(vertices);nf=len(faces)
    if (vertices.dtype.str not in ('<f8','=f8')or list(vertices.shape)!=[nv,3]or not nv or
            list(faces.shape)!=[nf,3]or faces.dtype.kind not in 'iu'or not nf or
            any(not math.isfinite(v)for row in vertices.tolist()for v in row)or
            any(type(i)is not int or i<0 or i>=nv for row in faces.tolist()for i in row)or
            any(list(arrays[n].shape)!=[nf]or arrays[n].dtype.kind not in 'iuf'or
                any(not math.isfinite(v)or v!=int(v)for v in arrays[n].tolist())for n in ('order','type'))):
        raise ValueError('Invalid finite retained support array shapes, dtypes or indices')


def check_groups(groups,arrays):
    faces=arrays['faces'].tolist();order=arrays['order'].tolist();kind=arrays['type'].tolist()
    cursor=0;names=set()
    for group in groups:
        lo,hi=group['face_range']
        if (type(lo)is not int or type(hi)is not int or lo!=cursor or not lo<hi<=len(faces)or
                group['id']in names or group['kind']not in ('grid','skin')or
                order[lo:hi]!=[group['order']]*(hi-lo)or kind[lo:hi]!=[group['type']]*(hi-lo)):
            raise ValueError('Material groups or unchanged scan attributes differ')
        names.add(group['id']);cursor=hi
    if cursor!=len(faces):raise ValueError('Every candidate face must retain its original owner')


def historical_skin(skin):return {k:v for k,v in skin.items()if k not in ('material_connection_graph',KEY)}


class Capsule:
    def __init__(self,path,expected):
        self.path=Path(path).absolute()
        if self.path.name!=MANIFEST or any(p.is_symlink()for p in (self.path,*self.path.parents))or sha(self.path)!=expected:
            raise ValueError('The pinned real flat capsule manifest differs')
        self.digest=expected;self.document=json.loads(self.path.read_text());self.files={self.path:expected}
        d=self.document
        if d.get('schema')!='certified-support-topology-capsule-1' or d.get('global_admission')is not False:
            raise ValueError('Unknown certified support capsule authority')
        for name,digest in d['files_sha256'].items():
            if name==MANIFEST:raise ValueError('The manifest cannot hash itself')
            self.files[self.path.parent/local_name(name)]=digest
        self.rows={}
        for row in d['rows']:
            index=row['source_index']
            if type(index)is not int or index not in INDICES or index in self.rows:raise ValueError('Duplicate or foreign source derivation')
            for role in ('parent_checkpoint','original_npz','candidate_npz','candidate_receipt','strict_plan','strict_receipt','trace_npz','trace_receipt','remap_bundle'):
                if local_name(row[role])not in d['files_sha256']:raise ValueError('A required derivation proof is unbound')
            self.rows[index]=deepcopy(row)
        if not self.rows:raise ValueError('A real nonempty derivation capsule is required')
        if (len(set(d['runtime_helpers']))!=len(d['runtime_helpers'])or
                set(d['runtime_helpers'])!={n for n in d['files_sha256']if n.endswith('.py')}or
                any(local_name(n)not in d['files_sha256']or not n.endswith('.py')for n in d['runtime_helpers'])):
            raise ValueError('Runtime helpers must be explicitly pinned unique Python sources')
        self._frozen=(str(self.path),self.digest,deepcopy(self.document),deepcopy(self.rows),dict(self.files))
        self.verify()

    def verify(self):
        if (str(self.path),self.digest,self.document,self.rows,self.files)!=self._frozen:
            raise ValueError('The public capsule identity or parsed bindings changed')
        if any(p.is_symlink()for p in self.path.parents):raise ValueError('Capsule parent symlinks are forbidden')
        if any(p.is_symlink()or not p.is_file()or sha(p)!=h for p,h in self.files.items()):
            raise ValueError('A pinned topology capsule file changed')

    def file(self,name):
        p=self.path.parent/local_name(name)
        if p not in self.files:raise ValueError('A topology file is not in the manifest')
        return p

    def read(self,name):return json.loads(self.file(name).read_text())

    def binding(self):
        return dict(manifest=MANIFEST,manifest_sha256=self.digest,
            files_sha256={p.name:h for p,h in self.files.items()})

    def evidence(self,row,np):
        self.verify();parent=self.read(row['parent_checkpoint']);receipt=self.read(row['candidate_receipt'])
        strict=self.read(row['strict_receipt']);plan=self.read(row['strict_plan'])
        trace=self.read(row['trace_receipt']);remap=self.read(row['remap_bundle'])
        original=load_arrays(np,self.file(row['original_npz']));candidate=load_arrays(np,self.file(row['candidate_npz']))
        for arrays in (original,candidate):validate_arrays(arrays)
        if (parent.get('status')!='region_geometry_completed_no_global_admission'or parent['source_index']!=row['source_index']or
                parent['files_sha256']['support.npz']!=self.files[self.file(row['original_npz'])]or
                parent.get('runtime_unchanged')is not True or parent['runtime_before']!=parent['runtime_after']or
                receipt.get('status')!='certified_local_flip_candidate_no_global_admission'or receipt.get('global_admission')is not False or
                receipt.get('inputs_unchanged')is not True or receipt['inputs_sha256_before']!=receipt['inputs_sha256_after']or
                receipt['runtime_before_sha256']!=identity(parent['runtime_before'])or receipt['runtime_after_sha256']!=identity(parent['runtime_after'])or
                receipt['output_npz_sha256']!=self.files[self.file(row['candidate_npz'])]or
                receipt['original_arrays']!=array_identities(original)or receipt['candidate_arrays']!=array_identities(candidate)):
            raise ValueError('Original checkpoint, candidate arrays or runtime ancestry differs')
        if any(array_identity(original[n])!=array_identity(candidate[n])for n in ('vertices','order','type'))or array_identity(original['faces'])['shape']!=array_identity(candidate['faces'])['shape']or original['faces'].dtype.str!=candidate['faces'].dtype.str:
            raise ValueError('Only same-shape face indices may be derived')
        ancestry=set(receipt['inputs_sha256_before'].values())
        if (not {self.files[self.file(row[n])]for n in ('original_npz','trace_npz','trace_receipt')}<=ancestry or
                trace.get('status')!='original_skin_parameter_trace_verified_no_repair'or
                trace.get('source_index')!=row['source_index']or
                trace.get('original_surface_sha256')!=self.files[self.file(row['original_npz'])]or
                trace.get('base_surface_sha256')!=remap.get('trace_base_surface_sha256')or
                trace.get('base_surface_sha256')not in ancestry or
                trace.get('base_surface_sha256')not in trace['files_sha256_before'].values()or
                trace.get('metadata_sha256')!=parent['files_sha256']['geometry-assessment.json']or
                trace.get('trace_npz_sha256')!=self.files[self.file(row['trace_npz'])]or
                trace.get('runtime_before_sha256')!=identity(parent['runtime_before'])or
                trace.get('runtime_after_sha256')!=identity(parent['runtime_after'])or
                remap.get('candidate_npz_sha256')!=self.files[self.file(row['candidate_npz'])]or
                remap.get('candidate_receipt_sha256')!=self.files[self.file(row['candidate_receipt'])]):
            raise ValueError('The authentic parameter trace or remap candidate binding differs')
        changed=[i for i,(a,b)in enumerate(zip(original['faces'].tolist(),candidate['faces'].tolist()))if a!=b]
        if (not changed or any(type(i)is not int for i in receipt['proof']['changed_face_ids'])or
                changed!=receipt['proof']['changed_face_ids']or type(receipt['proof']['final_collapsed_cuts'])is not int or
                receipt['proof']['final_collapsed_cuts']!=0 or type(receipt['proof']['initial_collapsed_cuts'])is not int or receipt['proof']['initial_collapsed_cuts']<=0):
            raise ValueError('The exact changed face set or strict counter certificate differs')
        candidate_sha=self.files[self.file(row['candidate_npz'])]
        if (strict.get('status')!='strict_candidate_sections_completed_no_global_admission'or strict.get('source_index')!=row['source_index']or
                strict.get('declared_layers')!=1034 or strict.get('completed_layers')!=1034 or strict.get('first_refusal')is not None or
                strict.get('runtime_unchanged')is not True or strict.get('files_unchanged')is not True or
                strict.get('global_admission')is not False or strict.get('plan_sha256')!=self.files[self.file(row['strict_plan'])]or
                strict['parallel_sections'].get('worker_group_closed')is not True or
                candidate_sha not in strict['parallel_sections']['sources_and_inputs_sha256'].values()or
                candidate_sha not in plan['files_sha256'].values()):
            raise ValueError('The complete strict-calendar proof is not linked to this candidate')
        return parent,receipt,original,candidate,changed

    def supplement(self,row,receipt,graph,changed):
        return dict(schema='certified-support-topology-derivation-1',source_index=row['source_index'],
            manifest_sha256=self.digest,parent_checkpoint_sha256=self.files[self.file(row['parent_checkpoint'])],
            original_npz_sha256=self.files[self.file(row['original_npz'])],candidate_npz_sha256=self.files[self.file(row['candidate_npz'])],
            candidate_receipt_sha256=self.files[self.file(row['candidate_receipt'])],strict_receipt_sha256=self.files[self.file(row['strict_receipt'])],
            remap_bundle_sha256=self.files[self.file(row['remap_bundle'])],changed_face_ids=changed,
            candidate_arrays=receipt['candidate_arrays'],material_graph_sha256=identity(graph),
            historical_skin_sha256=row['historical_skin_sha256'],historical_grid_sha256=row['historical_grid_sha256'],
            exact_GRID_point_set_and_quantified_SKIN_proofs_remain_separate=True,global_admission=False)

    def geometry(self,row,surface,block,np,connect,check_graph,parent_sha):
        parent,receipt,original,candidate,changed=self.evidence(row,np)
        if parent_sha!=self.files[self.file(row['parent_checkpoint'])]:raise ValueError('The verified original region uses another parent checkpoint')
        actual=dict(vertices=surface.vertices,faces=surface.faces,**{n:surface.face_attributes[n]for n in ('order','type')})
        skin=deepcopy(block.skinCoverage);grid=deepcopy(block.gridCoverage)
        if (array_identities(actual)!=receipt['original_arrays']or
                identity(historical_skin(skin))!=row['historical_skin_sha256']or identity(grid)!=row['historical_grid_sha256']):
            raise ValueError('The authentic original geometry or metadata changed before derivation')
        groups=skin['support_surface_face_groups'];check_groups(groups,candidate)
        derived=surface.copy();derived.faces=candidate['faces'].copy()
        graph=connect(derived.vertices,derived.faces,deepcopy(groups))
        check_graph(graph,skin,derived.vertices,derived.faces)
        if (array_identities(dict(vertices=derived.vertices,faces=derived.faces,**{n:derived.face_attributes[n]for n in ('order','type')}))!=receipt['candidate_arrays']or
                array_identities(actual)!=receipt['original_arrays']):raise ValueError('A mesh copy changed arrays outside the certificate')
        skin['material_connection_graph']=graph;skin[KEY]=self.supplement(row,receipt,graph,changed)
        self.verify();block.skinCoverage=skin
        return derived

    def copy_to(self,directory,checkpoint):
        self.verify();directory=Path(directory)
        for source,digest in self.files.items():
            target=directory/source.name
            if target.is_symlink():raise ValueError('Capsule output symlinks are forbidden')
            if target.exists():
                if sha(target)!=digest:raise ValueError('Existing capsule output differs')
            else:
                with target.open('xb')as stream:stream.write(source.read_bytes())
            if sha(target)!=digest:raise ValueError('Copied topology proof differs')
        checkpoint[KEY]=self.binding();checkpoint['outputs_sha256'].update(self.binding()['files_sha256']);self.verify()

    def verify_stage(self,directory,checkpoint,np,check_graph):
        self.verify();directory=Path(directory)
        if checkpoint.get(KEY)!=self.binding():raise ValueError('The stage omits its certified topology capsule')
        for name,digest in self.binding()['files_sha256'].items():
            p=directory/name
            if p.is_symlink()or not p.is_file()or sha(p)!=digest or checkpoint['outputs_sha256'].get(name)!=digest:
                raise ValueError('A stage topology capsule output is missing or changed')
        item=checkpoint['admission']['contacts'];contacts_path=directory/'admission-contacts.json'
        if (item.get('receipt')!=contacts_path.name or contacts_path.is_symlink()or not contacts_path.is_file()or
                sha(contacts_path)!=item.get('receipt_sha256')):
            raise ValueError('The original contacts admission graph copy is not bound')
        contacts=json.loads(contacts_path.read_text())
        if contacts.get('passed')is not True:raise ValueError('The original contacts admission was rejected')
        for source,row in self.rows.items():
            _,receipt,_,candidate,changed=self.evidence(row,np)
            index=INDICES.index(source);support=checkpoint['supports'][index]
            p=directory/f'support-{index:03d}.npz'
            if p.is_symlink()or checkpoint['outputs_sha256'].get(p.name)!=sha(p):raise ValueError('The actual support file is not sealed')
            actual=load_arrays(np,p)
            if array_identities(actual)!=receipt['candidate_arrays']:raise ValueError('Delivered derived support arrays differ')
            skin=support['peripheral_skin'];graph=skin['material_connection_graph']
            recorded=[r for r in contacts['actual_material_connection_graphs']if r['region']==index]
            if len(recorded)!=1 or recorded[0].get('passed')is not True or identity(recorded[0]['receipt'])!=identity(graph):
                raise ValueError('The complete graph differs from the sealed original contacts admission')
            if (identity(historical_skin(skin))!=row['historical_skin_sha256']or identity(support['grid_coverage'])!=row['historical_grid_sha256']or
                    skin.get(KEY)!=self.supplement(row,receipt,graph,changed)):
                raise ValueError('A derived support history, graph or supplement changed')
            check_groups(skin['support_surface_face_groups'],actual);check_graph(graph,skin,actual['vertices'],actual['faces'])


def install(consumer,capsule,np,connect,check_graph):
    """Patch only the supplied private instance; runtime dependencies are explicit."""
    if getattr(consumer,'_certified_topology_installed',False):raise ValueError('The private consumer was already configured')
    original_policy_files=consumer._v5.POLICY_FILES
    extra={Path(__file__).resolve():sha(__file__),**capsule.files}
    names=[p.name for p in (*consumer.POLICY_SHA256,*extra)]
    if len(set(names))!=len(names):raise ValueError('Policy/snapshot basenames collide')
    hook=dict(source=Path(__file__).name,source_sha256=sha(__file__),**capsule.binding(),
        derivations=[dict(source_index=s,parent_checkpoint_sha256=capsule.files[capsule.file(r['parent_checkpoint'])],
            candidate_npz_sha256=capsule.files[capsule.file(r['candidate_npz'])])for s,r in capsule.rows.items()])
    consumer.POLICY_SHA256.update(extra);consumer._v5.POLICY_SHA256.update(extra)
    consumer.RUNTIME_HOOKS[KEY]=deepcopy(hook);consumer._v5.RUNTIME_HOOKS=consumer.RUNTIME_HOOKS
    old_prepared=consumer._prepared;old_seal=consumer.seal;old_verify=consumer.verify_v6_stage;old_restore=consumer._restore_execution

    def prepared(*args,**kwargs):
        result=old_prepared(*args,**kwargs);result.files.update(extra);result.verify()
        if [r['source_index']for r in result.rows]!=list(INDICES):raise ValueError('The original seven prepared regions are required')
        original_geometry=result.geometry;original_complete=result.complete;used=set()
        def geometry(block):
            before=result.index;row=result.rows[before];source=row['source_index']
            surface=original_geometry(block)  # Every original check must finish first.
            if result.index!=before+1:raise ValueError('The original prepared-region cursor differs')
            if source not in capsule.rows:return surface
            if source in used:raise ValueError('A certified source derivation was requested twice')
            surface=capsule.geometry(capsule.rows[source],surface,block,np,connect,check_graph,row['checkpoint_sha256'])
            used.add(source);result.verify();return surface
        def complete():
            original_complete()
            if used!=set(capsule.rows):raise ValueError('Not every declared derivation was consumed exactly once')
        result.geometry=geometry;result.complete=complete
        return result

    def seal(output,checkpoint,store):
        capsule.copy_to(output,checkpoint)
        result=old_seal(output,checkpoint,store)
        # The original seal owns every gate and all six hook bindings.
        capsule.verify_stage(output,checkpoint,np,check_graph)
        return result

    def verify(directory):
        checkpoint=old_verify(directory)  # Original six gates and replay proof first.
        capsule.verify_stage(directory,checkpoint,np,check_graph)
        return checkpoint

    def restore(source,output,result,supports_only):
        result=old_restore(source,output,result,supports_only)
        prior=json.loads((Path(source)/'support-stage.json').read_text())
        if prior.get(KEY)!=capsule.binding():raise ValueError('The reused source has another topology capsule')
        target=json.loads((Path(output)/'support-stage.json').read_text())
        capsule.copy_to(output,target);write(Path(output)/'support-stage.json',target)
        if supports_only:result.update(target)
        else:
            result['outputs_sha256'].update(capsule.binding()['files_sha256'])
            result['outputs_sha256']['support-stage.json']=sha(Path(output)/'support-stage.json')
        return result

    consumer._prepared=prepared;consumer.seal=seal;consumer._v5._base.seal=seal
    consumer.verify_v6_stage=verify;consumer._restore_execution=restore
    if consumer._v5.POLICY_FILES!=original_policy_files:raise ValueError('Historical FourProvenResults policy files changed')
    consumer._certified_topology_installed=True
    return consumer


def private_consumer(source,manifest,manifest_sha256):
    """Create a new private v6 instance; this function requires the real AM runtime."""
    source=Path(source).resolve();path=source/'build_cached_v6.py'
    expected={path:V6_SHA,source/'material_connections.py':GRAPH_SHA,source/'region_checkpoints.py':CHECKPOINT_SHA}
    if any(sha(p)!=h for p,h in expected.items()):raise ValueError('The unchanged runtime consumer or graph source differs')
    capsule=Capsule(manifest,manifest_sha256);saved=list(sys.path)
    try:
        sys.path.insert(0,str(source))
        spec=importlib.util.spec_from_file_location('_private_certified_support_consumer_v6',path)
        consumer=importlib.util.module_from_spec(spec);spec.loader.exec_module(consumer)
        graph=importlib.import_module('material_connections');checkpoints=importlib.import_module('region_checkpoints')
        if Path(graph.__file__).resolve()!=source/'material_connections.py'or Path(checkpoints.__file__).resolve()!=source/'region_checkpoints.py':
            raise ValueError('Graph/checkpoint functions came from another runtime snapshot')
    finally:sys.path[:]=saved
    # These original runtime functions also remain pinned on stage reuse, when
    # PreparedRegion.geometry() and connected_material() are not called.
    consumer.POLICY_SHA256.update(expected);consumer._v5.POLICY_SHA256.update(expected)
    installed=install(consumer,capsule,consumer._v5._base.np,graph.connected_material,checkpoints._check_graph)
    if any(sha(p)!=h for p,h in expected.items()):raise ValueError('A runtime source changed during the private import')
    return installed
