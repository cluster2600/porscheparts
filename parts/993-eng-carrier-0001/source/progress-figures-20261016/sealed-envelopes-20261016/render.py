"""Replay the retained seven-envelope figures; no native construction."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = {
    'render_v3.py': '7af654a6550234c869df4c45263abbac2132900f010b464fc2750d59b052360d',
    'render_v4c.py': '96834a99113d33c7dba781a09aac1a04bfc54e95ac7ddd46679cec872850d0be',
    'raster_ghost.py': 'f35f6f0affa3564d566d1809521521a293c3639e9474639f9aca8ee336eeb42a',
    'raster_unlit.py': '262e766aee94a0244037f89194453726953ddc4016c7bdccda63ff9ac866f6e0',
}
STORE_SHA = '63391aa2b74094887155346841db493f57c0eb0a0b8d8998c4c748c95bf13ec4'
STL_SHA = '443b5ae20f7f1b2fd19a210aa5347890086523bc66749dfc95fa3560b85e9a6e'
RASTER_SHA = 'ed589c99365537eb165ecffbd48a70200507a005c2e3be7a22dfc6c2681f4eaf'
PNG_SHA = {
    'sealed-envelopes-overview.png': '4211c068aae0f9e065ab807e93c14a4ba6bb0998dbed6dd1a6ec62bfb3cc2a7d',
    'small-envelopes-details.png': 'a6b4cf9bc3f7e69bd74cf0f02864556648394975576fc4184106c3ff4148ec5c',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(workspace, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('The output directory must be fresh')
    workspace, output = Path(workspace).resolve(), output.resolve()
    sources = {HERE/'sources'/name: digest for name, digest in SOURCES.items()}
    sources[Path(__file__).resolve()] = sha(__file__)
    if any(sha(path) != digest for path, digest in sources.items()):
        raise ValueError('A retained rendering source differs')
    store = workspace/'work/carrier-process-20261016/sealed-envelopes-v2-001'
    stl = workspace/'work/part-workflow/run-001/surface/carrier-remeshed.stl'
    raster = workspace/'scripts/render_carrier_progress.py'
    inputs = {store/'envelopes.json': STORE_SHA, stl: STL_SHA, raster: RASTER_SHA}
    if any(sha(path) != digest for path, digest in inputs.items()):
        raise ValueError('The exact retained store, part STL and renderer are required')
    for name, digest in PNG_SHA.items():
        if sha(HERE/'reference'/name) != digest:
            raise ValueError('A retained reference PNG differs')
    # The two unchanged sources retain their own CAD, cache, store and array gates.
    overview = load('_retained_seven_envelopes_overview', HERE/'sources/render_v3.py')
    overview.ROOT = workspace
    overview.SOURCE = workspace/'parts/993-eng-carrier-0001/source/process-skins-20261016'
    overview.STORE = store
    overview.RENDERER = raster
    output.mkdir(parents=True, exist_ok=False)
    overview.main(output/'global')
    details = load('_retained_seven_envelopes_details', HERE/'sources/render_v4c.py')
    details.ROOT = workspace
    details.STORE = store
    details.RASTER = raster
    details.REFERENCE = output/'global'
    details.RECEIPT_SHA = sha(output/'global/render-receipt.json')
    details.DETAIL_RASTER = HERE/'sources/raster_unlit.py'
    details.main(output/'details')
    png_matches = {name: sha(output/'details'/name) == digest for name, digest in PNG_SHA.items()}
    if not all(png_matches.values()):
        raise ValueError('A rendered PNG differs from the retained reference')
    if any(sha(path) != digest for path, digest in {**sources, **inputs}.items()):
        raise ValueError('A source or rendering input changed')
    receipt = {
        'status': 'replayed_retained_envelope_figures_no_final_support_admission',
        'scope': 'The exact historical sealed store only; no native construction or support slicing',
        'source_sha256': {str(path.relative_to(HERE)): digest for path, digest in sources.items()},
        'source_files_unchanged': True,
        'workspace_inputs_sha256': {str(path.relative_to(workspace)): digest for path, digest in inputs.items()},
        'workspace_inputs_unchanged': True,
        'global_receipt_sha256': sha(output/'global/render-receipt.json'),
        'details_receipt_sha256': sha(output/'details/render-receipt.json'),
        'png_byte_identical_to_reference': png_matches,
        'outputs_sha256': {str(path.relative_to(output)): sha(path)
                           for path in sorted(output.rglob('*')) if path.is_file()},
        'geometry_modified': False,
        'native_cases_rerun': False,
        'full_support_preparation_admitted': False,
    }
    (output/'replay-receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'status': receipt['status'], 'png_byte_identical': all(png_matches.values())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path, help='Workspace containing the exact retained store and part')
    parser.add_argument('output', type=Path, help='Fresh output directory')
    args = parser.parse_args()
    main(args.workspace, args.output)
