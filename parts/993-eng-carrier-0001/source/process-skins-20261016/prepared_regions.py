"""Load every required region checkpoint, preserving separate global admissions."""
import json
from pathlib import Path
from region_checkpoints import PreparedRegion,sha

SOURCE=Path(__file__).resolve().parent


class PreparedRegions:
    def __init__(self,manifest,expected_source_indices,expected_store_sha256=None):
        self.manifest=Path(manifest).resolve();self.manifest_sha256=sha(self.manifest)
        data=json.loads(self.manifest.read_text());self.rows=data['regions'];self.index=0
        self.envelope_store_sha256=data.get('envelope_store_sha256')
        if expected_store_sha256 is not None and self.envelope_store_sha256!=expected_store_sha256:
            raise ValueError('Prepared regions belong to another envelope store')
        if data.get('schema')!='prepared-support-regions-1' or [r['source_index'] for r in self.rows]!=list(expected_source_indices):
            raise ValueError('Prepared regions omit or reorder a required source')
        self.files={self.manifest:self.manifest_sha256}
        for row in self.rows:
            path=(self.manifest.parent/row['checkpoint']).resolve()
            if sha(path)!=row['checkpoint_sha256']:raise ValueError('Prepared region checkpoint identity differs')
            receipt=json.loads(path.read_text())
            if receipt.get('status')!='region_geometry_completed_no_global_admission' or receipt['source_index']!=row['source_index']:
                raise ValueError('A generated diagnostic without its successful checkpoint cannot be reused')
            self.files[path]=row['checkpoint_sha256']
            if set(receipt['files_sha256'])!={'support.npz','geometry-assessment.json','material-connections.json'}:
                raise ValueError('Incomplete prepared region files')
            for name,digest in receipt['files_sha256'].items():self.files[path.parent/name]=digest
            for name,digest in receipt.get('additional_source_sha256',{}).items():
                source_path=SOURCE/name
                if not source_path.is_file():source_path=SOURCE.parent/'process-scanpath-audit-20261016'/name
                if Path(name).name!=name or sha(source_path)!=digest:raise ValueError('Additional prism generation source changed')
                self.files[source_path]=digest
            row['_directory']=path.parent
        self.verify()

    def verify(self):
        if any(sha(path)!=digest for path,digest in self.files.items()):raise ValueError('Prepared region evidence changed')

    def geometry(self,block):
        self.verify()
        if self.index>=len(self.rows):raise ValueError('An extra support region was requested')
        row=self.rows[self.index];reader=PreparedRegion(row['_directory'])
        surface=reader.geometry(block);self.index+=1;self.verify()
        return surface

    def complete(self):
        self.verify()
        if self.index!=len(self.rows):raise ValueError('Not all required region checkpoints were consumed')
