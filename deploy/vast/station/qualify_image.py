#!/usr/bin/env python3
"""Verify the station's anonymous registry access and compressed transfer size."""
import hashlib
import json
from pathlib import Path
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

PACKAGE = 'cluster2600/3dprinting993-picogk-m64'


def qualify(reference):
    match = re.fullmatch(r'ghcr\.io/' + PACKAGE + r'@(sha256:[0-9a-f]{64})', reference)
    if not match:
        raise ValueError('exact station package and immutable digest required')
    mac_ca = Path('/etc/ssl/cert.pem')
    context = ssl.create_default_context(cafile=str(mac_ca)) if mac_ca.is_file() else ssl.create_default_context()

    def get(url, headers=None):
        request = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(request, context=context, timeout=60) as response:
            data = response.read(4 * 1024**2 + 1)
        if len(data) > 4 * 1024**2:
            raise ValueError('registry metadata exceeded its size limit')
        return data

    scope = urllib.parse.quote('repository:' + PACKAGE + ':pull', safe='')
    # This is an anonymous public-registry token, never a workload credential.
    token = json.loads(get('https://ghcr.io/token?service=ghcr.io&scope=' + scope))['token']
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'}
    raw = get('https://ghcr.io/v2/' + PACKAGE + '/manifests/' + match[1], headers)
    if 'sha256:' + hashlib.sha256(raw).hexdigest() != match[1]:
        raise ValueError('registry manifest digest mismatch')
    manifest = json.loads(raw)
    config_digest = manifest['config']['digest']
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', config_digest):
        raise ValueError('invalid configuration digest')
    config_raw = get('https://ghcr.io/v2/' + PACKAGE + '/blobs/' + config_digest, headers)
    if 'sha256:' + hashlib.sha256(config_raw).hexdigest() != config_digest:
        raise ValueError('registry configuration digest mismatch')
    config = json.loads(config_raw)
    platform = config['os'] + '/' + config['architecture']
    ports = sorted(config['config'].get('ExposedPorts', {}))
    sizes = [layer['size'] for layer in manifest['layers']]
    if platform != 'linux/amd64' or ports != ['22/tcp', '47998/udp']:
        raise ValueError('image platform or published ports violate the station contract')
    if not sizes or any(type(n) is not int or n < 0 for n in sizes):
        raise ValueError('invalid registry layer sizes')
    return {'image_ref': reference, 'config_digest': config_digest, 'platform': platform,
            'anonymous_registry_verified': True, 'published_ports': ports,
            'image_download_bytes': sum(sizes) + len(raw) + len(config_raw),
            'layer_count': len(sizes), 'observed_epoch': int(time.time())}


if __name__ == '__main__':
    print(json.dumps(qualify(sys.argv[1]), indent=2))
