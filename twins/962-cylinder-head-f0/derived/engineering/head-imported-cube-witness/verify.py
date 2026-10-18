"""Standard-library sealed-byte check only; no solver or scientific imports."""
import hashlib
import json
from pathlib import Path


def main():
    base=Path(__file__).resolve().parent;receipt=base/'receipt.json'
    if not receipt.is_file():raise SystemExit('Unsealed preparation: final receipt is not present.')
    r=json.loads(receipt.read_text());pins=r.get('payload_sha256')
    if not isinstance(pins,dict) or not pins:raise ValueError('Sealed nonempty payload map required')
    for name,digest in pins.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or name=='receipt.json':raise ValueError('Unsafe/self-referential payload name')
        path=base/p
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Missing/changed payload: '+name)
    actual={str(p.relative_to(base)) for p in base.rglob('*') if p.is_file() or p.is_symlink()}
    if actual!=set(pins)|{'receipt.json'}:raise ValueError('Payload closure differs')
    print('Sealed bytes verified only; no numerical or physical execution credited.')


if __name__=='__main__':main()
