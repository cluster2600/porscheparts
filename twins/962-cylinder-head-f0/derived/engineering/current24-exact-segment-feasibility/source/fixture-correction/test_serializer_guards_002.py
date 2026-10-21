"""HELD/UNRUN serializer-only synthetic fixtures. No worker import, SymPy or head data."""
import ast
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zlib
import _compression

SOURCE=Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/head-star-current24-exact-segment-feasibility-prep-002/classify_segment_feasibility.py')
namespace=dict(gzip=gzip,hashlib=hashlib,io=io,json=json)
tree=ast.parse(SOURCE.read_text())
names={"need","verify_lossless_gzip_bytes","lossless_gzip_certificate"}
definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name in names]
assert {node.name for node in definitions}==names and len(definitions)==3
# AST-extract only the two new byte serializers plus the exact old need() helper.
exec(compile(ast.Module(body=definitions,type_ignores=[]),str(SOURCE)+":serializer-fixtures-only","exec"),namespace)
pack=namespace["lossless_gzip_certificate"];verify=namespace["verify_lossless_gzip_bytes"]

def fixture():
    marker=dict(path="SYNTHETIC_FIXTURE_ONLY",sha256="0"*64,bytes=1)
    result=dict(schema="SYNTHETIC_COMPLETE_BYTES_NOT_A_HEAD_RESULT",status="fixture_only",
        source=marker,held_preparation=marker,own_actual=marker,tuple_list=marker,
        segment_count=19,complete_cell_dispositions=916,complete_constraint_associations=1832,
        qualification=dict(physics_qualified=False),
        every_logical_row=[dict(coefficient="-13/17",factor=[0,1,1],multiplicity=2,
            root_bracket=["1/7","2/7"],strict=True,witness="1/5",absent=None,
            signed_zero=-0.0,scientific_acceptance=False)]*19)
    encoded=(json.dumps(result,indent=2,allow_nan=False)+"\n").encode()
    compressed,manifest_bytes=pack(encoded,result)
    return encoded,compressed,json.loads(manifest_bytes),result

def repin(compressed,manifest):
    changed=copy.deepcopy(manifest)
    changed["compressed_payload"]=dict(filename="real-segment-feasibility.json.gz",
        bytes=len(compressed),sha256=hashlib.sha256(compressed).hexdigest())
    return changed

class SerializerFixtures(unittest.TestCase):
    def test_full_exact_roundtrip_and_hashes(self):
        encoded,compressed,manifest,result=fixture()
        observed=verify(compressed,manifest)
        self.assertEqual(observed["bytes"],len(encoded))
        self.assertEqual(observed["sha256"],hashlib.sha256(encoded).hexdigest())
        with gzip.GzipFile(fileobj=io.BytesIO(compressed),mode="rb")as stream:
            restored=stream.read(len(encoded)+1)
            self.assertEqual(stream.read(1),b"")
        self.assertEqual(restored,encoded)
        self.assertEqual(json.loads(restored),result)
        self.assertEqual(manifest["segment_count"],19)
        self.assertEqual(manifest["complete_cell_dispositions"],916)
        self.assertEqual(manifest["complete_constraint_associations"],1832)

    def test_determinism_fixed_header(self):
        first=fixture();second=fixture()
        self.assertEqual(first[1],second[1]);self.assertEqual(first[2],second[2])
        self.assertEqual(first[1][:10],b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff")

    def test_CRC_and_truncation_refuse(self):
        _,compressed,manifest,_=fixture()
        bad=bytearray(compressed);bad[-8]^=1;bad=bytes(bad)
        with self.assertRaises((gzip.BadGzipFile,EOFError,OSError,zlib.error,ValueError)):
            verify(bad,repin(bad,manifest))
        cut=compressed[:-2]
        with self.assertRaises((gzip.BadGzipFile,EOFError,OSError,zlib.error,ValueError)):
            verify(cut,repin(cut,manifest))

    def test_declared_bounds_and_hash_refuse(self):
        _,compressed,manifest,_=fixture()
        changed=copy.deepcopy(manifest);changed["logical_payload"]["bytes"]-=1
        with self.assertRaises(ValueError):verify(compressed,changed)
        changed=copy.deepcopy(manifest);changed["logical_payload"]["bytes"]=2147483649
        with self.assertRaises(ValueError):verify(compressed,changed)
        changed=copy.deepcopy(manifest);changed["logical_payload"]["sha256"]="0"*64
        with self.assertRaises(ValueError):verify(compressed,changed)
        changed=copy.deepcopy(manifest);changed["compressed_payload"]["bytes"]+=1
        with self.assertRaises(ValueError):verify(compressed,changed)

if __name__=="__main__":
    assert sys.implementation.name=="cpython" and sys.version_info[:3]==(3,12,11)
    print("SERIALIZER_RUNTIME "+json.dumps(dict(Python_executable=sys.executable,
        Python_version=sys.version.split()[0],gzip_origin=gzip.__spec__.origin,
        zlib_origin=zlib.__spec__.origin,compression_origin=_compression.__spec__.origin,
        io_origin=io.__spec__.origin,zlib_compile_version=zlib.ZLIB_VERSION,
        zlib_runtime_version=zlib.ZLIB_RUNTIME_VERSION,
        original_twelve_math_API_guards_repeated=False,head_or_SymPy_imported=False)),flush=True)
    unittest.main()
