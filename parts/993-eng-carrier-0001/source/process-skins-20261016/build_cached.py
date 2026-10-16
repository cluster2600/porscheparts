"""Build admitted support sheets, then reuse an immutable complete part-layer cache.

The original coverage CORE and historical rejected runs remain unchanged.
The adjacent OUTPUT-supports checkpoint is retained if any admission fails.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from admitted_regions import sha
from admitted_regions_v2 import EnvelopeStore
from admissions_v2 import seal
from prepared_regions import PreparedRegions
from compact_json import install as compact_core_json
from layer_schedule import calendar

SOURCE=Path(__file__).resolve().parent
CORE=SOURCE.parent/'process-coverage-20261016/build_pyslm.py'
CORE_SHA256='418482002d75e4b160f5837fdef91042fc63c3c1c85750a20d5359c53018e01f'
CACHE_SOURCE=SOURCE.parent/'process-cache-20261016'
SECTION_SOURCE=SOURCE.parent/'process-scanpath-audit-20261016/exact_support_section.py'
sys.path.insert(0,str(CACHE_SOURCE))
from part_cache import CachedLayers
PARALLEL_SOURCE=SOURCE.parent/'process-support-slicing-20261016/parallel_support_sections.py'
sys.path.insert(0,str(PARALLEL_SOURCE.parent))
from parallel_support_sections import ParallelSupportSections


def build(input_path,output,envelopes,part_cache,expected_sha256=None,identity_receipt=None,solid_sheets=False,continuous_interfaces=False,region_checkpoints=None,supports_only=False,reuse_support_stage=None):
    input_path=Path(input_path).resolve();output=Path(output).resolve()
    identity_receipt=Path(identity_receipt).resolve() if identity_receipt is not None else None
    if (expected_sha256 is None)==(identity_receipt is None):raise ValueError('Choose exactly one input identity')
    if identity_receipt is not None:expected_sha256=json.loads(identity_receipt.read_text())['candidate_STL_sha256']
    if sha(input_path)!=expected_sha256:raise ValueError('Input SHA-256 mismatch')
    if sha(CORE)!=CORE_SHA256:raise ValueError('The immutable part CORE identity differs')
    spec=importlib.util.spec_from_file_location('carrier_coverage_core_immutable',CORE)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    compact_core_json(core)
    if sha(SECTION_SOURCE)!='7a6416ca48322b0be9210117c660d830e1f14183a7e49a58d755ae674f81aef4':
        raise ValueError('Exact support-section hook differs from the admitted version')
    hook_spec=importlib.util.spec_from_file_location('carrier_exact_support_section',SECTION_SOURCE)
    hook=importlib.util.module_from_spec(hook_spec);hook_spec.loader.exec_module(hook)
    core.support_section=hook.support_section
    frozen_core=sha(CORE)
    store=EnvelopeStore(envelopes,expected_sha256,core.PARAMETERS)
    if not solid_sheets or not continuous_interfaces:raise ValueError('The v2 build requires explicit continuous full sheets')
    if region_checkpoints is None:raise ValueError('All seven successful region checkpoints are required')
    prepared=PreparedRegions(region_checkpoints,[r['source_index'] for r in store.report['regions']],store.manifest_sha256)
    def selected_geometry(block):
        if continuous_interfaces and not solid_sheets:raise ValueError('Continuous interfaces require explicit full sheets')
        if solid_sheets:block.generateTrussGrid=False
        block.continuousFragmentedInterfaces=continuous_interfaces
        return prepared.geometry(block)
    identify_with_true_interfaces=store.identify
    cached=CachedLayers(Path(part_cache).resolve(),input_path,core.PARAMETERS)
    if supports_only and reuse_support_stage is not None:raise ValueError('Cannot assemble and reuse the same support stage')
    checkpoint_path=Path(reuse_support_stage).resolve() if reuse_support_stage is not None else output if supports_only else output.with_name(output.name+'-supports')
    if output.exists() or reuse_support_stage is None and checkpoint_path.exists():raise ValueError('New output directories are required')
    extensions=[SOURCE/name for name in ['build_cached.py','admitted_regions.py','admitted_regions_v2.py','admissions.py','admissions_v2.py',
        'prepared_regions.py','region_checkpoints.py','compact_json.py','native_prism_case.py','interface_sources_prisms.py','interface_sources_prisms_v2.py',
        'peripheral_skins.py','grid_intervals.py','exact_regions.py','prismatic_envelopes.py','quantized_contacts.py','material_connections.py','layer_schedule.py','zero_area_faces.py','interface_sources.py','solid_sheets.py','continuous_interfaces.py']]
    extensions.extend([CACHE_SOURCE/'part_cache.py',SECTION_SOURCE,SECTION_SOURCE.parent/'exact_contacts.py',SECTION_SOURCE.parent/'exact_contacts_both.py',SECTION_SOURCE.parent/'exact_zero_face_coverage.py',SECTION_SOURCE.parent/'exact_polygon_coverage.py',SECTION_SOURCE.parent/'exact_intended_holes.py',*store.files])
    extensions.append(SOURCE.parent/'design-20261016/classify_mesh_contacts.py')
    extensions.extend([PARALLEL_SOURCE,Path(region_checkpoints).resolve()])
    extensions.extend(p for p in prepared.files if p.suffix=='.py')
    extensions=list(dict.fromkeys(p.resolve() for p in extensions))
    if len({p.name for p in extensions})!=len(extensions):raise ValueError('Extension/store snapshot filenames collide')
    identity=dict(expected_sha256=expected_sha256) if identity_receipt is None else dict(identity_receipt=identity_receipt)
    if reuse_support_stage is None:
        try:
            checkpoint=core.build(input_path,checkpoint_path,**identity,supports_only=True,
                identify_generator=identify_with_true_interfaces,geometry_generator=selected_geometry,source_extensions=extensions)
        except ValueError as error:
            if hasattr(error,'receipt') and checkpoint_path.exists():
                (checkpoint_path/'support-rejection.json').write_text(json.dumps(dict(error.receipt,
                    input_sha256=expected_sha256,message=str(error)),separators=(',',':'),allow_nan=False)+'\n')
            raise
        prepared.complete()
        admission,admitted=seal(checkpoint_path,checkpoint,store)
        if not admitted:raise ValueError('At least one support admission was rejected; no full slicing started')
    else:
        checkpoint=json.loads((checkpoint_path/'support-stage.json').read_text());admission=checkpoint['admission']
        if checkpoint.get('prepared_regions_manifest_sha256')!=prepared.manifest_sha256:
            raise ValueError('The reusable support stage uses another prepared-region manifest')
        if (set(admission)!={'envelopes','regions','skins','grids','contacts','collisions'} or
            not checkpoint.get('manufacturing_preparation_admitted') or checkpoint['input_sha256']!=expected_sha256):
            raise ValueError('The reusable support stage lacks six admissions for this input')
        for key,item in admission.items():
            path=checkpoint_path/item['receipt']
            if item['status']!='passed' or sha(path)!=item['receipt_sha256']:raise ValueError('A reusable admission changed or was rejected')
            receipt=json.loads(path.read_text())
            if not receipt['passed'] or receipt['input_sha256']!=expected_sha256:raise ValueError('A reusable admission belongs to another input')
            if key=='envelopes' and receipt['store_manifest_sha256']!=store.manifest_sha256:raise ValueError('The reusable admission uses another envelope store')
    # Reuse the exact, admitted sheets; include every admission in the checkpoint
    # hash map so that the immutable CORE copies and verifies it as well.
    checkpoint['outputs_sha256'].update({item['receipt']:item['receipt_sha256'] for item in admission.values()})
    if reuse_support_stage is None:
        checkpoint['prepared_regions_manifest_sha256']=prepared.manifest_sha256
        (checkpoint_path/'support-stage.json').write_text(json.dumps(checkpoint,separators=(',',':'),allow_nan=False)+'\n')
    if supports_only:
        prepared.verify();store.verify()
        if sha(CORE)!=CORE_SHA256:raise ValueError('The immutable part CORE changed before support-stage completion')
        return checkpoint
    with np.load(store.path/'input-part.npz',allow_pickle=False) as part_data:
        heights=calendar(float(part_data['vertices'][:,2].max()),core.PARAMETERS['layer_height_mm'])
    paths=[checkpoint_path/f'support-{i:03d}.npz' for i in range(len(checkpoint['supports']))]
    with ParallelSupportSections(paths,heights,workers=4) as cuts:
        core.support_section=cuts
        report=core.build(input_path,output,**identity,reuse_supports=checkpoint_path,
            layer_generator=cached,source_extensions=extensions)
    report['parallel_support_sections']=cuts.receipt()
    if cached.index!=report['n_layers'] or cached.index!=cached.report['n_layers']:
        raise ValueError('Complete cached part layers were not consumed exactly once')
    store.verify()
    prepared.verify()
    if sha(CORE)!=frozen_core:raise ValueError('Immutable part CORE changed')
    final_checkpoint=json.loads((output/'support-stage.json').read_text())
    final_checkpoint.update(admission=admission,manufacturing_preparation_admitted=True)
    (output/'support-stage.json').write_text(json.dumps(final_checkpoint,separators=(',',':'),allow_nan=False)+'\n')
    report.update(admission=admission,manufacturing_preparation_admitted=True,
        support_strategy='continuous_fragmented_interfaces_with_native_full_sheets' if continuous_interfaces else 'native_full_sheet_no_truss_perforation' if solid_sheets else 'native_perforated_truss',
        envelope_store_sha256=store.manifest_sha256,
        part_layer_cache=dict(directory=str(Path(part_cache).resolve()),report_sha256=cached.report_sha256,
            complete_cached_layers=cached.report['n_layers'],consumed_layers=cached.index,
            method='exact_cached_contours_hatches_and_areas_with_per_layer_identity_checks'),
        support_checkpoint=str(checkpoint_path),immutable_core_sha256=frozen_core,
        runner_source_sha256=sha(__file__))
    report['outputs_sha256'].update({item['receipt']:item['receipt_sha256'] for item in admission.values()})
    report['outputs_sha256']['support-stage.json']=sha(output/'support-stage.json')
    (output/'report.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    identity=p.add_mutually_exclusive_group(required=True);identity.add_argument('--sha256');identity.add_argument('--identity-receipt',type=Path)
    p.add_argument('--envelopes',type=Path,required=True);p.add_argument('--part-cache',type=Path,required=True)
    p.add_argument('--region-checkpoints',type=Path,required=True)
    p.add_argument('--supports-only',action='store_true');p.add_argument('--reuse-support-stage',type=Path)
    p.add_argument('--solid-sheets',action='store_true');p.add_argument('--continuous-interfaces',action='store_true');a=p.parse_args()
    r=build(a.input,a.output,a.envelopes,a.part_cache,a.sha256,a.identity_receipt,a.solid_sheets,a.continuous_interfaces,a.region_checkpoints,a.supports_only,a.reuse_support_stage)
    print(json.dumps({key:r[key] for key in ['status','manufacturing_preparation_admitted','n_layers'] if key in r}))
