"""Read a sealed mixed store without promoting geometric cases to process anchors."""
import json
from pathlib import Path
import numpy as np

from admitted_regions import EnvelopeStore as HistoricalStore,sha
from native_prism_case import load_case


class EnvelopeStore(HistoricalStore):
    def __init__(self,path,input_sha256,parameters):
        self.path=Path(path).resolve();self.manifest=self.path/'envelopes.json'
        self.report=json.loads(self.manifest.read_text());self.manifest_sha256=sha(self.manifest)
        self.cases={};r=self.report
        if r.get('schema')!='carrier-exact-free-envelopes-v2' or r.get('status')!='passed':
            raise ValueError('Mixed envelope store is not admitted')
        if r.get('input_sha256')!=input_sha256 or r.get('parameters')!=parameters:
            raise ValueError('Envelope store uses a different part or process parameters')
        self.files={self.manifest:self.manifest_sha256}
        for name,digest in r['files_sha256'].items():
            path=(self.path/name).resolve()
            if not path.is_relative_to(self.path) or not path.is_file() or sha(path)!=digest:
                raise ValueError('Mixed envelope store file/identity mismatch')
            self.files[path]=digest
        if len(r['regions'])!=r['expected_regions'] or not r['regions']:raise ValueError('Missing envelope region')
        for row in r['regions']:
            if (row.get('status')!='passed' or not row.get('all_vertical_intervals_retained') or
                not row.get('body_subtracted_in_same_coordinates') or self.path/row['envelope'] not in self.files):
                raise ValueError('Envelope lacks its interval or body-subtraction proof')
            self._admit_native(row)
        self.verify()

    def _admit_native(self,row):
        if row.get('backend')!='positive_prism_native_v2':return super()._admit_native(row)
        audit=row.get('prism_native_audit');mapping=row.get('prism_evidence_map')
        self._receipt(audit);local_map=self._receipt(mapping)
        case=load_case(self.path/audit['receipt'],self.path/mapping['receipt'])
        for item in local_map['files'].values():
            path=(self.path/item['path']).resolve()
            if path not in self.files or self.files[path]!=item['sha256']:
                raise ValueError('Native prism evidence is outside the sealed store')
        if (case.source_index!=row['source_index'] or case.final_npz!=self.path/row['envelope'] or
            case.boolean_audit['input_sha256']!=[row['roofs_sha256'],row['mask_sha256'],self.files[self.path/'input-part.npz']]):
            raise ValueError('Native prism case differs from the actual prepared leaves or final envelope')
        self.cases[row['source_index']]=case

    def verify(self):
        super().verify()
        for case in self.cases.values():case.verify()

    def identify(self,part,generator,overhang_angle):
        blocks=super().identify(part,generator,overhang_angle)
        for block,row in zip(blocks,self.report['regions']):
            if row.get('backend')=='positive_prism_native_v2':
                from interface_sources_prisms_v2 import attach
                case=self.cases[row['source_index']]
                with np.load(case.final_npz,allow_pickle=False) as final,np.load(case.original_raw_npz,allow_pickle=False) as raw:
                    block.interfaceSourceReceipt=attach(block.supportVolume,final,raw,case.boolean_audit,
                        self.path/('input-'+row['roofs']),self.path/('input-'+row['mask']),self.path/'input-part.npz',
                        case.schema_path,case.final_to_original_raw_face)
                block.interfaceSourceReceipt.update(native_case_audit_sha256=sha(self.path/row['prism_native_audit']['receipt']),
                    native_case_reader_sha256=sha(Path(__file__).with_name('native_prism_case.py')))
            else:
                from interface_sources import from_store
                block.interfaceSourceReceipt=from_store(self,row,block.supportVolume)
        self.verify();return blocks
