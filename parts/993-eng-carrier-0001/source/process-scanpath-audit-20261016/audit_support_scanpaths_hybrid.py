"""Use the sealed mixed native-envelope reader in the unchanged exposure audit.

Only one import in a private copy of the frozen audit is intercepted. Neither
the process snapshot nor Python's shared importlib is modified.
"""
import argparse
import importlib.metadata
import importlib.util
import inspect
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import audit_support_scanpaths_exact_anchors as anchors

SOURCE = Path(__file__).resolve().parent
ANCHORS_SHA256 = 'fb47084b163648df7eac3f99b7c2fb2a9982ac48b919bef31cb84b68b77dfd06'
BOTH_SHA256 = 'be4ce81a979ad2a42ca6136e7321f926630bbb2b6fae1f5739a71941aedb5d9a'
STORE_SOURCES = {
    'admitted_regions.py': '8bcebff36c4e5f992842f33666bf36a1734d1859541a64a9be57f7bf15293463',
    'admitted_regions_v2.py': 'f16e09b40ba3cc75d33be17d8f08c1599ece8197c9691c164ed005079325431e',
    'native_prism_case.py': 'd4c8131feb365fbbfe8a92a39398bd89d9728916062ed1a2d9c67a19015f9259',
    'interface_sources.py': 'cfe0c0c7ccbeffcd21f96500aa5c546826cdd6be47a77428f506e20e99e106c4',
    'interface_sources_prisms.py': '31d636f9eea43d60d6c5024e216827084ed8318d2e051c2b2c3677e54bf4f7d5',
    'interface_sources_prisms_v2.py': 'a8f9113ab78b7ac1489b8a183eddfebf6399058df72ccdec51e4b713351c4d0e',
}
sha = anchors.sha
triangle_section, encode, canonical, verified_file = (
    anchors.triangle_section, anchors.encode, anchors.canonical, anchors.verified_file)


def private_module(path, digest, name):
    if sha(path) != digest:
        raise ValueError('Frozen audit dependency changed: '+Path(path).name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HybridImport:
    def __init__(self, directory, report):
        directory = Path(directory).resolve()
        self.snapshot = directory/'source'
        self.input_sha256, self.parameters = report['input_sha256'], report['parameters']
        self.dependencies = {}
        for name, digest in STORE_SOURCES.items():
            if report['outputs_sha256'].get('source/'+name) != digest:
                raise ValueError('Process omits the approved mixed-store source: '+name)
            path = verified_file(directory, 'source/'+name, digest)
            self.dependencies[path] = digest
        self.loads, self.stores, self.store = 0, 0, None

    def verify(self):
        if any(sha(path) != digest for path, digest in self.dependencies.items()):
            raise ValueError('Mixed-store snapshot changed during the exposure audit')
        if self.loads != 1 or self.stores != 1 or self.store is None:
            raise ValueError('Exactly one verified mixed-store load and instance are required')
        self.store.verify()

    def spec_from_file_location(self, name, location, *args, **kwargs):
        path = Path(location).resolve()
        if name != 'support_audit_envelopes':
            return importlib.util.spec_from_file_location(name, location, *args, **kwargs)
        if path != self.snapshot/'admitted_regions.py' or self.loads:
            raise ValueError('Unexpected or repeated envelope-reader import')
        if sha(path) != self.dependencies[path]:
            raise ValueError('Historical reader digest changed before the private import')
        spec = importlib.util.spec_from_file_location(name, location, *args, **kwargs)
        loader, owner = spec.loader, self

        class PrivateLoader:
            def create_module(self, imported_spec):
                return loader.create_module(imported_spec)

            def exec_module(self, module):
                loader.exec_module(module)
                owner.loads += 1
                owner.inject(module)

        spec.loader = PrivateLoader()
        return spec

    def inject(self, module):
        if not sys.path or Path(sys.path[0]).resolve() != self.snapshot:
            raise ValueError('The frozen audit must load from its own source snapshot')
        if Path(inspect.getfile(module.EnvelopeStore.__init__)).resolve() != self.snapshot/'admitted_regions.py':
            raise ValueError('Historical reader was imported from another snapshot')
        hybrid = private_module(self.snapshot/'admitted_regions_v2.py',
            STORE_SOURCES['admitted_regions_v2.py'], '_private_carrier_mixed_store')
        for obj, name in ((hybrid.HistoricalStore.__init__, 'admitted_regions.py'),
                          (hybrid.load_case, 'native_prism_case.py'),
                          (hybrid.EnvelopeStore.__init__, 'admitted_regions_v2.py')):
            if Path(inspect.getfile(obj)).resolve() != self.snapshot/name:
                raise ValueError('Mixed-store dependency was imported from another snapshot: '+name)

        def verified_store(path, input_sha256, parameters):
            if (self.stores or Path(path).resolve() != self.snapshot or
                    input_sha256 != self.input_sha256 or parameters != self.parameters):
                raise ValueError('Mixed-store constructor uses another input, parameters or snapshot')
            self.store = hybrid.EnvelopeStore(path, input_sha256, parameters)
            self.stores += 1
            self.verify()
            return self.store

        module.EnvelopeStore = verified_store

    def private_importlib(self):
        # This namespace belongs only to the isolated legacy module. All other
        # spec requests and metadata calls retain their original implementations.
        class Utilities:
            def __getattr__(self, name):
                return getattr(importlib.util, name)
        utilities = Utilities()
        utilities.spec_from_file_location = self.spec_from_file_location
        return SimpleNamespace(util=utilities, metadata=importlib.metadata)


def isolated_anchor_audit(injection):
    previous = private_module(SOURCE/'audit_support_scanpaths_both.py', BOTH_SHA256,
                              '_private_carrier_hybrid_both')
    original_factory = previous.legacy_module

    def legacy_module():
        module = original_factory()
        module.importlib = injection.private_importlib()
        return module

    previous.legacy_module = legacy_module
    module = private_module(SOURCE/'audit_support_scanpaths_exact_anchors.py', ANCHORS_SHA256,
                            '_private_carrier_hybrid_anchors')
    module.previous = previous
    return module


def audit(directory, output, source_stl, part_cache=None):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    own, process_sha = sha(__file__), sha(directory/'report.json')
    report = json.loads((directory/'report.json').read_text())
    injection = HybridImport(directory, report)
    module = isolated_anchor_audit(injection)
    result = module.audit(directory, output, source_stl, part_cache)
    injection.verify()
    if sha(__file__) != own or sha(directory/'report.json') != process_sha:
        raise ValueError('Hybrid adapter or process report changed during the audit')
    for path in [Path(__file__), *injection.dependencies]:
        shutil.copy2(path, output/'source'/path.name)
    result.update(schema='carrier-support-exposure-hybrid-store-v1',
        hybrid_envelope_store_verified=True, hybrid_store_imports=injection.loads,
        hybrid_store_instances=injection.stores,
        hybrid_store_sources_sha256={path.name: digest for path, digest in injection.dependencies.items()},
        hybrid_adapter_source_sha256=own, frozen_rational_anchor_source_sha256=ANCHORS_SHA256)
    (output/'assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-stl', type=Path, required=True)
    parser.add_argument('--part-cache', type=Path)
    args = parser.parse_args()
    result = audit(args.directory, args.output, args.source_stl, args.part_cache)
    print(json.dumps({key: result[key] for key in ('status', 'layers_audited',
        'rational_part_contact_intersections', 'hybrid_envelope_store_verified')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
