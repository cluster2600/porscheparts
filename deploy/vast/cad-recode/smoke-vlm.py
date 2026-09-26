#!/usr/bin/env python3
"""Verify a local image request using a synthetic red PNG; no external API."""
import base64
import json
import struct
import urllib.request
import zlib


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 256, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress((b'\0' + b'\xff\0\0' * 256) * 256)) + chunk(b'IEND', b'')
body = {'model': 'cad-vlm', 'messages': [{'role': 'user', 'content': [
    {'type': 'text', 'text': 'Name the dominant color in one word.'},
    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(png).decode()}}
]}], 'max_tokens': 32, 'temperature': 0}
request = urllib.request.Request('http://127.0.0.1:8003/v1/chat/completions',
    data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=180) as response:
    result = json.load(response)
answer = result['choices'][0]['message']['content']
assert 'red' in answer.lower(), answer
print(json.dumps({'status': 'passed', 'check': 'vlm_image_input', 'response': answer}))
