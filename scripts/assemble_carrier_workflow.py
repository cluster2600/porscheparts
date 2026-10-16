"""Assemble the verified carrier prefix and a separately admitted LPBF preparation."""
import argparse
import json
from pathlib import Path
import shutil

import run_part_workflow as workflow
import build_carrier_workshop_guide_v2 as guide
from build_carrier_workshop_guide_v2 import admitted_process

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ('cad', 'inspect-protected', 'surface', 'surface-brep', 'surface-audit',
          'mesh-9', 'mesh-7', 'mechanics', 'comparison', 'fields', 'dimensions', 'surface-figure')


def verification_sources():
    return {name: workflow.sha(path) for name, path in
            (('assembler', __file__), ('workflow_verifier', workflow.__file__),
             ('support_admission', guide.__file__))}


def regular(base, name):
    path = workflow.inside(base, name)
    original = base
    for component in Path(name).parts:
        original = original / component
        if original.is_symlink():
            raise ValueError('Assembly sources cannot contain symbolic links')
    return path


def files(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('Assembly sources cannot contain symbolic links')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = workflow.sha(path)
    return result


def prefix(source):
    receipt_hash = workflow.sha(source / 'workflow.json')
    receipt = workflow.verify(source)
    stages = receipt['stages'][:len(PREFIX)]
    if (receipt['part_id'] != '993-ENG-CARRIER-0001'
            or tuple(stage['id'] for stage in stages) != PREFIX
            or any(stage['status'] != 'executed' or stage.get('returncode') != 0 for stage in stages)):
        raise ValueError('All twelve declared carrier prefix stages must have executed successfully')
    selected = {}
    for stage in stages:
        for name, digest in stage['outputs_sha256'].items():
            path = regular(source, name)
            if path.is_symlink() or not path.is_file() or stage['output_types'].get(name, 'file') != 'file':
                raise ValueError('Carrier prefix imports only recorded regular files')
            if name in selected and selected[name] != digest:
                raise ValueError('Conflicting prefix file identities')
            selected[name] = digest
    if workflow.sha(source / 'workflow.json') != receipt_hash:
        raise ValueError('Source workflow receipt changed during prefix verification')
    return receipt, receipt_hash, selected


def process_check(process, audit, support_audit, mesh_hash):
    report_path = process / 'report.json'
    report_hash = workflow.sha(report_path)
    report = json.loads(report_path.read_text())
    if (report.get('status') != 'open_build_preparation_completed'
            or report.get('source_and_runtime_unchanged_at_completion') is not True
            or report.get('input_sha256') != mesh_hash):
        raise ValueError('Complete LPBF preparation for the exact imported surface is required')
    admitted_process(process, report)
    for name, expected in report['outputs_sha256'].items():
        path = workflow.inside(process, name)
        if not path.is_file() or workflow.sha(path) != expected:
            raise ValueError('Process artifact identity mismatch: ' + name)
    assessment = json.loads((audit / 'assessment.json').read_text())
    if (assessment.get('status') != 'passed' or assessment.get('complete_build_audited') is not True
            or assessment.get('layers_audited') != report['n_layers']
            or assessment.get('input_receipt_sha256') != report_hash):
        raise ValueError('An admitted audit of every layer of this exact process is required')
    assessment = json.loads((support_audit / 'assessment.json').read_text())
    if (assessment.get('status') != 'passed' or assessment.get('complete_build_audited') is not True
            or assessment.get('layers_audited') != report['n_layers']
            or assessment.get('input_receipt_sha256') != report_hash
            or any(assessment.get(key) is not True for key in
                   ('support_scanpaths_audited', 'geometric_confinement_passed', 'exposure_connectivity_passed'))):
        raise ValueError('A complete geometric encoding and exposure contact audit of support paths is required')
    return report, report_hash


def copy_files(source, target, selected):
    for name, expected in selected.items():
        origin = regular(source, name)
        if origin.is_symlink() or workflow.sha(origin) != expected:
            raise ValueError('Assembly input changed before copying: ' + name)
        destination = workflow.inside(target, name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, destination)
        if workflow.sha(destination) != expected or workflow.sha(origin) != expected:
            raise ValueError('Assembly input changed while copying: ' + name)


def assemble(source, process, audit, support_audit, output):
    source, process, audit, support_audit, output = [Path(path).resolve() for path in
                                                   (source, process, audit, support_audit, output)]
    if output.exists():
        raise FileExistsError('Use a fresh assembly directory')
    if not output.is_relative_to(ROOT / 'work'):
        raise ValueError('Carrier assemblies must remain in repository work/')
    for parent in (source, process, audit, support_audit):
        if output.is_relative_to(parent) or parent.is_relative_to(output):
            raise ValueError('Assembly output and inputs cannot contain one another')
    original, original_hash, selected = prefix(source)
    _, process_hash = process_check(process, audit, support_audit, selected['surface/carrier-remeshed.stl'])
    process_files, audit_files, support_audit_files = files(process), files(audit), files(support_audit)
    output.mkdir(parents=True, exist_ok=False)
    copy_files(source, output, selected)
    (output / 'process').mkdir()
    copy_files(process, output / 'process', process_files)
    (output / 'scanpath-audit').mkdir()
    copy_files(audit, output / 'scanpath-audit', audit_files)
    (output / 'support-scanpath-audit').mkdir()
    copy_files(support_audit, output / 'support-scanpath-audit', support_audit_files)
    provenance = output / 'provenance'
    provenance.mkdir()
    shutil.copyfile(source / 'workflow.json', provenance / 'source-workflow.json')
    if workflow.sha(provenance / 'source-workflow.json') != original_hash:
        raise ValueError('Source workflow changed while copying its provenance')
    process_check(output / 'process', output / 'scanpath-audit', output / 'support-scanpath-audit',
                  selected['surface/carrier-remeshed.stl'])
    if (files(process) != process_files or files(audit) != audit_files or files(support_audit) != support_audit_files
            or workflow.sha(source / 'workflow.json') != original_hash):
        raise ValueError('An assembly source changed during copying')
    receipt = {'schema': 'porscheparts.carrier-assembly@1', 'status': 'artifacts_assembled',
               'part_id': original['part_id'], 'verification_sources_sha256': verification_sources(),
               'meaning': 'Verified existing CAD and mechanics results combined with a separately completed LPBF preparation; no solver was rerun by this assembly.',
               'source_workflow': {'path': str(source), 'sha256': original_hash,
                                   'status': original['status'], 'imported_stage_ids': list(PREFIX),
                                   'later_source_stages_imported': False},
               'process': {'path': str(process), 'report_sha256': process_hash},
               'scanpath_audit': {'path': str(audit), 'assessment_sha256': workflow.sha(audit / 'assessment.json')},
               'support_scanpath_audit': {'path': str(support_audit),
                                         'assessment_sha256': workflow.sha(support_audit / 'assessment.json')},
               'outputs_sha256': files(output)}
    workflow.write(output / 'assembly.json', receipt)
    return verify(output)


def verify(output):
    output = Path(output).resolve()
    receipt = json.loads((output / 'assembly.json').read_text())
    if (receipt.get('schema') != 'porscheparts.carrier-assembly@1'
            or receipt.get('status') != 'artifacts_assembled'
            or receipt['verification_sources_sha256'] != verification_sources()):
        raise ValueError('Unrecognised assembly or changed assembly source')
    for name, expected in receipt['outputs_sha256'].items():
        path = regular(output, name)
        if path.is_symlink() or not path.is_file() or workflow.sha(path) != expected:
            raise ValueError('Assembly output identity mismatch: ' + name)
    if (workflow.sha(output / 'provenance/source-workflow.json') != receipt['source_workflow']['sha256']
            or workflow.sha(output / 'process/report.json') != receipt['process']['report_sha256']
            or workflow.sha(output / 'scanpath-audit/assessment.json') != receipt['scanpath_audit']['assessment_sha256']
            or workflow.sha(output / 'support-scanpath-audit/assessment.json') != receipt['support_scanpath_audit']['assessment_sha256']):
        raise ValueError('Assembly provenance identity mismatch')
    process_check(output / 'process', output / 'scanpath-audit', output / 'support-scanpath-audit',
                  workflow.sha(output / 'surface/carrier-remeshed.stl'))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    create = commands.add_parser('assemble')
    for name in ('source', 'process', 'audit', 'support-audit', 'output'):
        create.add_argument('--' + name, type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('output', type=Path)
    args = parser.parse_args()
    result = (assemble(args.source, args.process, args.audit, args.support_audit, args.output)
              if args.action == 'assemble' else verify(args.output))
    print(json.dumps({key: result[key] for key in ('part_id', 'status', 'meaning')}))
