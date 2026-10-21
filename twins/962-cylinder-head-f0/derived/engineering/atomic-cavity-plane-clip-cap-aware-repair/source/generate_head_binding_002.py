"""Freeze the exact209a poor-face partition; no geometry/runtime import."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'work/962-engineering/atomic-cavity-plane-clip-readback-001/readback-report.json'
EXPECTED_SHA256 = '209a4a35033c036ee4f0dc66c6285e49db4c85f1039d89feb52b45899562db80'


def validated_ids(record):
    classes = record['candidate']['plane_classes']
    if set(classes) != {'cap_all_z0','noncap_mixed_plane_vertices','noncap_no_plane_vertices'}:
        raise ValueError('Exact three plane classes required')
    result = []
    for name,count in [('cap_all_z0',2396),('noncap_mixed_plane_vertices',716),('noncap_no_plane_vertices',0)]:
        ids = classes[name]['poor_face_ids']
        if (type(ids) is not list or len(ids) != count
                or any(type(i) is not int or not 0 <= i < 1739126 for i in ids)):
            raise ValueError('Exact valid poor class required')
        result.extend(ids)
    if len(set(result)) != 3112:
        raise ValueError('Distinct complete poor partition required')
    return sorted(result)


def render(raw):
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        raise ValueError('Frozen209a record bytes required')
    ids = validated_ids(json.loads(raw))
    rows = ['  '+','.join(map(str,ids[i:i+16]))+',' for i in range(0,len(ids),16)]
    return ('// Generated from exact209a record '+EXPECTED_SHA256+'.\n#pragma once\n'
            '#include <array>\n#include <cstddef>\nnamespace head_binding {\n'
            'inline constexpr std::array<std::size_t,3112> poor_face_ids{{\n'
            +'\n'.join(rows)+'\n}};\n}\n').encode()


def write_header(raw, destination):
    content = render(raw)
    with Path(destination).open('xb') as stream:
        stream.write(content)


if __name__=='__main__':
    write_header(SOURCE.read_bytes(),Path(__file__).with_name('head_binding.hpp'))
