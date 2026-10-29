"""Describe checksummed, uncompressed NumPy tetrahedra for the exact C++ checker."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

import numpy as np


def describe(path, expected_sha256):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError('Frozen archive checksum mismatch')
    records = {}
    with zipfile.ZipFile(path) as archive, path.open('rb') as stream:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC failure')
        for name, width, allowed in [('vertices.npy', 3, ['<f8']),
                                     ('tetrahedra.npy', 4, ['<i8', '<u8'])]:
            item = archive.getinfo(name)
            if item.compress_type != zipfile.ZIP_STORED:
                raise ValueError('Exact checker requires stored array members')
            stream.seek(item.header_offset)
            header = stream.read(30)
            if header[:4] != b'PK\x03\x04':
                raise ValueError('Invalid ZIP local header')
            filename_size, extra_size = struct.unpack('<HH', header[26:])
            stream.seek(filename_size + extra_size, 1)
            beginning = stream.tell()
            if np.lib.format.read_magic(stream) != (1, 0):
                raise ValueError('Admitted NPY format is version 1.0')
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
            if (len(shape) != 2 or shape[1] != width or not 0 < shape[0] < 2**31
                    or dtype.str not in allowed
                    or (name == 'vertices.npy' and fortran)):
                raise ValueError('Unsupported point/cell shape, dtype or layout')
            if item.file_size != stream.tell() - beginning + int(np.prod(shape)) * 8:
                raise ValueError('Array payload length mismatch')
            records[name] = {'offset': stream.tell(), 'shape': list(shape),
                             'dtype': dtype.str, 'fortran_order': fortran}
    return {'archive_sha256': digest, 'all_member_crcs_valid': True, 'layout': records}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Fresh output required')
    result = describe(args.archive, args.sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
