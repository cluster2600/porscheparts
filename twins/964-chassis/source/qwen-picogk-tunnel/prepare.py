#!/usr/bin/env python3
"""Reproduce a bounded Qwen transcription of existing, hypothetical C2/C4 envelopes."""
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import time

SCALE = 50
DESIGN_SHA = '7d66590268e8151242303461e43ecf3fbda5d2f9fb0f13152406d23236ad192f'
BASE_SHA = 'daeab4764fb420d161721791cf2e509e2de81a7af4223646e7bed2bf82c57b58'
ADAPTER_SHA = 'a1014c6f71b46d879c09462c4a57d17d00df8f11b8178dd53bf6d5f2ac2f778a'
PARSER_SHA = '3357a289b0314a4e7e24f1a0d515d1bebf55021ccacd2551650b830f352ac3c6'


def digest(path):
    with path.open('rb') as stream:
        h = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def specification(design):
    """Same placements as the legacy build_cad.py; no new Porsche dimensions."""
    package = design['vehicle_packaging_mm']
    common, c2, c4 = (package[k] for k in ('common_cell', 'c2_package', 'c4_package'))
    x0, x1 = common['tunnel_start_x'], common['tunnel_end_x']
    width, height = common['tunnel_outer_width'], common['tunnel_outer_height']
    floor = design['screening_geometry_mm']['floor_z']
    wall, nose, floor_thickness = 26, 38, 34  # Existing concept, not laminate thicknesses.
    boxes = [
        [(x0+x1)/2, sign*(width-wall)/2, floor+height/2, x1-x0, wall, height]
        for sign in (-1, 1)
    ]
    boxes += [[(x0+x1)/2, 0, floor+height, x1-x0, width, common['service_cover_thickness']],
              [x0, 0, floor+height/2, nose, width, height],
              [(x0+x1)/2, 0, floor, x1-x0, width, floor_thickness]]
    beams = {
        'c2_shift_rod': [c2['external_shift_rod_start_x'], c2['external_shift_rod_center_y'], c2['external_shift_rod_center_z'], c2['external_shift_rod_diameter']/2,
                         c2['external_shift_rod_end_x'], c2['external_shift_rod_center_y'], c2['external_shift_rod_center_z'], c2['external_shift_rod_diameter']/2, False],
        'c4_central_tube': [c4['central_tube_start_x'], 0, c4['central_tube_center_z'], c4['central_tube_outer_diameter']/2,
                            c4['central_tube_end_x'], 0, c4['central_tube_center_z'], c4['central_tube_outer_diameter']/2, False],
        'c4_shift_guide': [c4['central_tube_start_x']+130, c4['shift_guide_center_y'], c4['central_tube_center_z']+82, c4['shift_guide_diameter']/2,
                           c4['central_tube_end_x']-130, c4['shift_guide_center_y'], c4['central_tube_center_z']+82, c4['shift_guide_diameter']/2, False],
    }
    return {'scale': SCALE, 'boxes_mm': boxes, 'expected_beams_mm': beams,
            'tower_box_mm': c2['shifter_tower_center_xyz'] + c2['shifter_tower_envelope_xyz'],
            'analytic_collision_mm3': {'c2_shift_rod': 0, 'c4_central_tube': nose*math.pi*(c4['central_tube_outer_diameter']/2)**2,
                                      'c4_shift_guide': nose*math.pi*(c4['shift_guide_diameter']/2)**2,
                                      'c2_shifter_tower': c2['shifter_tower_envelope_xyz'][0]*c2['shifter_tower_envelope_xyz'][1]*common['service_cover_thickness']}}


def checked_response(text, expected, parse, signature):
    _, rows = parse(text)
    scaled = [round(v/SCALE, 6) for v in expected[:8]] + [expected[8]]
    if signature(rows) != signature([scaled]):
        raise ValueError('Qwen changed a coordinate, radius, cap or edge count')
    # Native code receives reviewed numbers, never the model's executable text.
    return expected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--training', type=Path, required=True)
    p.add_argument('--design', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('output must be new; receipts are never overwritten')
    training = a.training.resolve()
    helper = training/'training/m64-qwen'
    model = training/'work/m64-qwen/model-cache/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/snapshots/b3252a2f97102b1fb1571fec2c9b27219a8536be'
    adapter = training/'work/m64-qwen/coding-003/checkpoint-600'
    for path, sha in [(a.design, DESIGN_SHA), (model/'model.safetensors', BASE_SHA),
                      (adapter/'adapters.safetensors', ADAPTER_SHA), (helper/'picogk.py', PARSER_SHA)]:
        if digest(path) != sha:
            p.error(f'input hash mismatch: {path.name}')
    if importlib.metadata.version('mlx-lm') != '0.31.3':
        p.error('expected the existing mlx-lm 0.31.3 environment')
    if __import__('shutil').disk_usage(a.output.parent).free < 2*1024**3:
        p.error('preserve at least 2 GiB free disk')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_IMPLICIT_TOKEN='1',
                      HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
    sys.path.insert(0, str(helper))
    from picogk import SYSTEM, parse, signature
    from run import configure_tokenizer
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(42)
    network, tokenizer = load(str(model), adapter_path=str(adapter), tokenizer_config={'trust_remote_code': False})
    configure_tokenizer(tokenizer)
    spec = specification(json.loads(a.design.read_text()))
    records, accepted = [], {}
    for name, beam in spec['expected_beams_mm'].items():
        b = [round(v/SCALE, 6) for v in beam[:8]]
        prompt = ('Synthetic graph, not a vehicle measurement. Vertices in model mm: ' +
                  json.dumps({'A': b[:3], 'B': b[4:7]}) +
                  f'. Directed edges: A->B. Start radius {b[3]} mm, end radius {b[7]} mm. '
                  'Flat caps: rounded_caps=false. Emit exactly one AddBeam statement, using these radii unchanged.')
        messages = [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt}]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        started = time.perf_counter()
        response = ''.join(r.text for r in stream_generate(network, tokenizer, prompt=rendered, max_tokens=256, sampler=make_sampler(temp=0)))
        row = {'id': name, 'messages': messages, 'response': response, 'seconds': time.perf_counter()-started, 'semantic_passed': False}
        try:
            accepted[name] = checked_response(response, beam, parse, signature)
            row['semantic_passed'] = True
        except ValueError as exc:
            row['error'] = str(exc)
        records.append(row)
        print(json.dumps(row), flush=True)
    a.output.mkdir()
    passed = len(accepted) == len(spec['expected_beams_mm'])
    receipt = {'status': 'accepted_bounded_transcription' if passed else 'rejected_model_output',
               'base_model': 'Qwen2.5-Coder-1.5B-Instruct-4bit', 'base_sha256': BASE_SHA,
               'adapter': 'coding-003/checkpoint-600', 'adapter_sha256': ADAPTER_SHA,
               'parser_sha256': PARSER_SHA, 'design_sha256': DESIGN_SHA,
               'source_sha256': digest(Path(__file__)), 'temperature': 0, 'seed': 42, 'max_tokens': 256,
               'records': records, 'manufacturing_authorized': False, 'vehicle_fit_verified': False}
    (a.output/'inference.json').write_text(json.dumps(receipt, indent=2)+'\n')
    if not passed:
        raise SystemExit('No native job emitted: Qwen did not preserve the supplied geometry')
    spec.update(accepted_beams_mm=accepted, inference_sha256=digest(a.output/'inference.json'),
                status='hypothetical_tunnel_interference_study_not_oem', manufacturing_authorized=False,
                vehicle_fit_verified=False, design_sha256=DESIGN_SHA)
    (a.output/'input.json').write_text(json.dumps(spec, indent=2)+'\n')


if __name__ == '__main__':
    main()
