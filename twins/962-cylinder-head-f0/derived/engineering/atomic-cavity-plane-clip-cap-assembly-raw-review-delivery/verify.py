"""Check sealed capsule bytes and closure; do not execute geometry or native code."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
receipt = json.loads((root / 'receipt.json').read_text())
payloads = receipt['payloads']
actual = set()
for path in root.rglob('*'):
    if path.is_symlink():
        raise ValueError('Symlink in capsule')
    if path.is_file():
        actual.add(path.relative_to(root).as_posix())
if actual != set(payloads) | {'receipt.json'}:
    raise ValueError('Capsule file closure differs')
total = 0
for name, expected in payloads.items():
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Invalid payload name')
    raw = (root / relative).read_bytes()
    if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError('Changed payload: ' + name)
    total += len(raw)
if len(payloads) != receipt['payload_count'] or total != receipt['payload_bytes']:
    raise ValueError('Payload totals differ')
print('PASS: %d payloads, %d bytes; complete sealed closure' % (len(payloads), total))
