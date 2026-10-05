#!/usr/bin/env python3
"""Bounded CAD-image rental; reuse the exact-identity PicoGK cleanup engine.

No OpenBao changes or secret access. An explicitly recorded, unrelated rental
may coexist; it is never a lifecycle target. Maximum three hours and USD 10.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

IMAGE = 'ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:c59c53b2611a1e3a9e9de5d2cedf8bfb0cd57e72582b2d6b29f6c8fc82bf7e6b'
path = Path(__file__).resolve().parents[1]/'picogk/deadline_guard.py'
if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != 'c1d82cfaf5c8f178b5eaeb32ca5d98774b3dd60502087310f10a2966e53ff3f4':
    raise RuntimeError('cleanup_engine_changed')
spec = importlib.util.spec_from_file_location('cad_cleanup_engine', path)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def validate(manifest):
    if (manifest.get('profile') != 'm64-cad-parallel-v1' or manifest.get('image_ref') != IMAGE
        or not re.fullmatch(r'3dprinting993-component-factory-f41-cad-[0-9a-f]{20}', str(manifest.get('attempt_label')))
        or type(manifest.get('created_epoch')) is not int or type(manifest.get('deadline_epoch')) is not int
        or not manifest['created_epoch'] <= time.time() < manifest['deadline_epoch']
        or not 60 <= manifest['deadline_epoch']-manifest['created_epoch'] <= 10800
        or not engine.finite(manifest.get('budget_usd')) or not 1 < manifest['budget_usd'] <= 10):
        raise engine.GuardError('bounded_CAD_manifest_required')
    for key, maximum in (('image_download_gb', 20), ('max_input_gb', 2), ('max_output_gb', 2)):
        if not engine.finite(manifest.get(key)) or not 0 <= manifest[key] <= maximum:
            raise engine.GuardError('bounded_transfer_allocation_required')
    background = manifest.get('background_instance')
    if (not isinstance(background, dict) or set(background) != {'id', 'label', 'image'}
        or type(background['id']) is not int or background['id'] <= 0
        or not isinstance(background['label'], str) or not isinstance(background['image'], str)
        or background['label'].startswith('3dprinting993-component-factory-f41-cad')):
        raise engine.GuardError('exact_unrelated_background_identity_required')


def visible_inventory(rows, background):
    matches = [row for row in rows if row.get('id') == background['id']]
    if len(matches) > 1 or any({key: row.get(key) for key in background} != background for row in matches):
        raise engine.GuardError('background_identity_changed')
    return [row for row in rows if row.get('id') != background['id']]


def cost_valid(instance, manifest, first_price=None):
    p, up, down = (instance.get(k) for k in ('dph_total', 'inet_up_cost_usd_per_gb', 'inet_down_cost_usd_per_gb'))
    if (not engine.finite(p) or not 0 < p <= 1.25 or first_price is not None and p != first_price
        or not all(engine.finite(v) and 0 <= v <= .05 for v in (up, down))):
        return False
    return (p*(manifest['deadline_epoch']-manifest['created_epoch'])/3600
            + down*(manifest['image_download_gb']+manifest['max_input_gb'])
            + up*manifest['max_output_gb']+1 <= manifest['budget_usd'])


def pending_metadata(instance):
    # Missing is not running. The reused engine permits this only within its
    # existing 120-second metadata grace, then destroys the exact owned rental.
    return instance.get('status') is None or instance.get('status') in ('created', 'loading')


def missing_cost(instance, first_price):
    missing = False
    for key, cap in (('dph_total', 1.25), ('inet_up_cost_usd_per_gb', .05), ('inet_down_cost_usd_per_gb', .05)):
        value = instance.get(key)
        if value is None:
            missing = True
        elif (not engine.finite(value) or not 0 <= value <= cap
              or key == 'dph_total' and (value == 0 or first_price is not None and value != first_price)):
            return False
    return missing


def guard(manifest_path):
    manifest = json.loads(engine.read_owned(manifest_path, 65536))
    validate(manifest)
    original_call = engine.wrapper_call
    background = manifest['background_instance']
    def call(*args):
        if args[0] in ('show', 'destroy') and args[1] == str(background['id']):
            raise engine.GuardError('background_is_not_a_lifecycle_target')
        rows = original_call(*args)
        return visible_inventory(rows, background) if args == ('instances',) else rows
    engine.wrapper_call = call
    engine.validate_manifest = validate
    engine.cost_valid = cost_valid
    engine.startup_pending = pending_metadata
    engine.only_cost_metadata_missing = missing_cost
    return engine.guard(manifest_path)


if __name__ == '__main__':
    print(json.dumps(guard(Path(sys.argv[1]).absolute()), sort_keys=True), flush=True)
