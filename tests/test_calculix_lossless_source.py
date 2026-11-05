"""Keep complete scientific bytes verifiable without a raw disk duplicate."""
import hashlib
import io
import lzma
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from calculix_lossless_source import CountSink, VerifiedXZSource
from calculix_stream_decode import decode


class LosslessSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'field.dat.xz'
        self.raw = b'known scientific decimal rows\n' * 10000
        self.encoded = lzma.compress(self.raw, check=lzma.CHECK_CRC64, preset=1)
        self.path.write_bytes(self.encoded)

    @staticmethod
    def digest(data):
        return hashlib.sha256(data).hexdigest()

    def source(self, **kwargs):
        values = dict(path=self.path, compressed_sha256=self.digest(self.encoded),
                      raw_bytes=len(self.raw), raw_sha256=self.digest(self.raw), decoder=decode)
        values.update(kwargs)
        return VerifiedXZSource(**values)

    def test_complete_binary_and_text_views_preserve_every_byte(self):
        source = self.source()
        proof = source.verify()
        self.assertEqual(proof['raw_bytes'], len(self.raw))
        with source.open('rb') as stream:
            self.assertEqual(stream.read(), self.raw)
        with source.open() as stream:
            self.assertEqual(stream.read(), self.raw.decode())
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [self.path])

    def test_wrong_raw_hash_and_size_are_rejected(self):
        for kwargs in [dict(raw_sha256='0'*64), dict(raw_bytes=len(self.raw)-1),
                       dict(raw_bytes=len(self.raw)+1)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(AssertionError):
                self.source(**kwargs).verify()

    def test_changed_compressed_bytes_are_rejected_before_read(self):
        source = self.source()
        source.verify()
        self.path.write_bytes(self.encoded + b'x')
        with self.assertRaises(AssertionError):
            with source.open('rb'):
                self.fail('Changed archive exposed')

    def test_truncated_trailing_and_concatenated_streams_are_rejected(self):
        for damaged in [self.encoded[:-4], self.encoded+b'x', self.encoded+self.encoded]:
            self.path.write_bytes(damaged)
            with self.subTest(size=len(damaged)), self.assertRaises((AssertionError, lzma.LZMAError)):
                self.source(compressed_sha256=self.digest(damaged)).verify()

    def test_declared_raw_cap_is_checked(self):
        with self.assertRaises(AssertionError):
            self.source(maximum_raw_bytes=len(self.raw)-1).verify()

    def test_decoder_bounds_output_chunks_and_checks_complete_digest(self):
        sink = CountSink()
        result = decode(io.BytesIO(self.encoded), sink, len(self.raw), self.digest(self.raw))
        self.assertEqual(sink.bytes, len(self.raw))
        self.assertLessEqual(result['maximum_decoded_chunk_bytes'], 1024**2)
        self.assertTrue(result['complete_source_SHA256_verified'])


if __name__ == '__main__':
    unittest.main()
