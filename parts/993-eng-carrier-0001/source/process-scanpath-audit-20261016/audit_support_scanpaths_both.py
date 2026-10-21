"""Audit the new two-domain contact contract with the frozen full exposure audit."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import shapely

from exact_contacts_both import clip_contacts_in_both, contact_encoding_check_in_both

SOURCE = Path(__file__).resolve().parent
LEGACY_SHA256 = '4ace9f24b61fa8f2d514f18d2e3eb6e9794983d6dee41fad4a8f44dc1f4c53ef'
BOTH_SHA256 = '102aaffcf0c1ac2646b2aef8d5e0dfbfebf14a9b2182b59a731434bcd6a7a855'
CONTRACT = 'source_interface_intersect_material_intersect_free_domain_exact_before_single_float64_encoding'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def legacy_module():
    path = SOURCE/'audit_support_scanpaths.py'
    if sha(path) != LEGACY_SHA256:
        raise ValueError('The frozen whole-build support audit changed')
    spec = importlib.util.spec_from_file_location('carrier_isolated_frozen_exposure_audit_both', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_utilities = legacy_module()
triangle_section = _utilities.triangle_section
encode = _utilities.encode
canonical = _utilities.canonical
verified_file = _utilities.verified_file


class ContactDomains:
    """Bind every callback to the sealed material/source-contact/domain tuple.

    The frozen auditor passes material and raw source paths to its contact
    predicates. This adapter supplies the separately verified second domain.
    A tuple with two different domains is rejected as ambiguous; it never
    silently chooses one. No implicit current-group or iteration state is used.
    """
    def __init__(self, report, pointer):
        self.domains, self.groups = {}, 0
        cache = {}
        for support in report['supports']:
            for group in support['peripheral_skin']['support_surface_face_groups']:
                contact = pointer(support, group['contact_reference'])
                for field in ('free_domain_geometry_wkb_hex', 'free_domain_geometry_sha256', 'contact_clip_scope'):
                    if field not in group or field not in contact:
                        raise ValueError('Missing explicit free-domain contact identity or scope')
                    if group[field] != contact[field]:
                        raise ValueError('Free-domain identity differs between material group and contact')
                if group['contact_clip_scope'] != CONTRACT:
                    raise ValueError('The new simultaneous contact clipping contract is required')
                raw = bytes.fromhex(group['free_domain_geometry_wkb_hex'])
                digest = hashlib.sha256(raw).hexdigest()
                if digest != group['free_domain_geometry_sha256']:
                    raise ValueError('Free-domain WKB hash mismatch')
                if digest not in cache:
                    polygon = shapely.from_wkb(raw)
                    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
                        raise ValueError('Invalid free contact domain')
                    cache[digest] = polygon
                material = shapely.from_wkb(bytes.fromhex(group['component_geometry_wkb_hex']))
                for side in ('upper', 'lower'):
                    paths = group[side+'_interface_traces_2d_mm']
                    if paths != contact[side+'_interface_traces_2d_mm']:
                        raise ValueError('Raw source contact paths differ between group and contact')
                    key = self.key(material, paths)
                    if key in self.domains and self.domains[key][0] != digest:
                        raise ValueError('Ambiguous free domain for the same material/source contact tuple')
                    self.domains[key] = digest, cache[digest]
                self.groups += 1

    @staticmethod
    def key(material, interfaces):
        return hashlib.sha256(material.wkb).digest(), json.dumps(interfaces, separators=(',', ':'), allow_nan=False)

    def domain(self, material, interfaces):
        key = self.key(material, interfaces)
        if key not in self.domains:
            raise ValueError('Contact predicate has no sealed second-domain identity')
        return self.domains[key][1]

    def clip(self, material, interfaces):
        return clip_contacts_in_both(material, self.domain(material, interfaces), interfaces)

    def encoding_check(self, material, interfaces, recorded):
        return contact_encoding_check_in_both(material, self.domain(material, interfaces), interfaces, recorded)


def audit(directory, output, source_stl, part_cache=None):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    paths = [Path(__file__), SOURCE/'audit_support_scanpaths.py', SOURCE/'exact_contacts.py',
             SOURCE/'exact_contacts_both.py', directory/'report.json']
    frozen = {path: sha(path) for path in paths}
    if frozen[SOURCE/'exact_contacts_both.py'] != BOTH_SHA256:
        raise ValueError('The simultaneous contact predicate changed')
    legacy = legacy_module()
    domains = ContactDomains(json.loads((directory/'report.json').read_text()), legacy.pointer)
    # An isolated copy of the unchanged auditor receives only the new contact
    # predicates. Its full layer loop, independent triangle cuts, enclosure,
    # chronology, actual part/plate anchor test and graph checks are unchanged.
    legacy.clip_contacts = domains.clip
    legacy.contact_encoding_check = domains.encoding_check
    result = legacy.audit(directory, output, source_stl, part_cache)
    if any(sha(path) != digest for path, digest in frozen.items()):
        raise ValueError('Contact adapter, predicate, process or frozen audit changed')
    for path in (Path(__file__), SOURCE/'exact_contacts_both.py'):
        shutil.copy2(path, output/'source'/path.name)
    result.update(contact_clip_scope=CONTRACT, contact_domain_groups_verified=domains.groups,
        contact_adapter_source_sha256=frozen[Path(__file__)],
        simultaneous_contact_predicate_sha256=BOTH_SHA256,
        frozen_full_audit_source_sha256=LEGACY_SHA256)
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
    print(json.dumps({key: result[key] for key in ('status', 'layers_audited', 'contact_domain_groups_verified')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
