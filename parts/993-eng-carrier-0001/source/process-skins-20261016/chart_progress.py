"""Capture each real chart before expensive infill, without changing its result."""
import hashlib
import json
import os
from pathlib import Path
import time


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path,data):
    temporary=path.with_name('.'+path.name+'.tmp')
    with temporary.open('x') as target:
        json.dump(data,target,separators=(',',':'),allow_nan=False);target.write('\n')
    try:os.link(temporary,path)
    finally:temporary.unlink()


def install(module,directory):
    directory=Path(directory).resolve();directory.mkdir(exist_ok=False)
    original=module.native_infill
    if getattr(original,'_carrier_chart_progress',False):raise ValueError('Chart capture is already installed')
    source_path=Path(__file__).resolve();source_sha=sha(source_path)
    calls=[0]
    def captured(block,domain,defer_component_contacts=False,diagnostic_contacts=False,interfaces=None):
        index=calls[0];calls[0]+=1;prefix=f'chart-{index:04d}'
        start_path=directory/(prefix+'-input.json')
        _write(start_path,dict(status='started_no_admission',chart_call_index=index,
            source_domain_geometry_wkb_hex=domain.wkb_hex,
            source_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
            attested_source_interfaces=interfaces,penetration_mm=block.supportTeethUpperPenetration,
            solid_sheets=not block.generateTrussGrid,
            defer_component_contacts=defer_component_contacts,diagnostic_contacts=diagnostic_contacts,
            capture_source_sha256=source_sha))
        input_sha256=sha(start_path)
        started=time.monotonic()
        try:
            result,receipt=original(block,domain,defer_component_contacts,diagnostic_contacts,interfaces)
            if sha(start_path)!=input_sha256:raise ValueError('Captured chart input changed during its call')
        except BaseException as error:
            _write(directory/(prefix+'-error.json'),dict(status='call_failed_no_admission',chart_call_index=index,
                input_sha256=input_sha256,captured_input_unchanged=sha(start_path)==input_sha256,seconds=time.monotonic()-started,
                error_type=type(error).__name__,error=str(error)))
            raise
        _write(directory/(prefix+'-completed.json'),dict(status='call_completed_no_global_admission',chart_call_index=index,
            input_sha256=input_sha256,captured_input_unchanged=sha(start_path)==input_sha256,seconds=time.monotonic()-started,
            generated_material_geometry_sha256=hashlib.sha256(result.wkb).hexdigest()))
        return result,receipt
    captured._carrier_chart_progress=True
    module.native_infill=captured
    def manifest():
        if sha(source_path)!=source_sha:raise ValueError('Chart capture source changed')
        return dict(status='chart_calls_observed_not_an_admission',calls=calls[0],source_sha256=source_sha,
            files_sha256={p.name:sha(p) for p in sorted(directory.glob('chart-*.json'))})
    return manifest
