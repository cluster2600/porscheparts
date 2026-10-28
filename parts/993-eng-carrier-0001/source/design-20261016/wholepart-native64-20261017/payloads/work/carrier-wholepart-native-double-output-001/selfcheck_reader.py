"""Software binary records only; no native CCX invocation."""
import importlib.util
import math
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('_native_double_reader',HERE/'read_double_frd.py');reader=importlib.util.module_from_spec(s);s.loader.exec_module(reader)


class Check(unittest.TestCase):
    nodes={i:(float(i),float(i)/3.,-0. if i==1 else float(i)/7.)for i in range(1,11)}
    cells={1:tuple(range(1,11))}
    def binary(self,format=3,duplicate=False,coordinate_bad=False,cell_bad=False,times=(1.,)):
        out=b'    1C\n'+b'    2C                 '+('%12d%38d\n'%(10,3)).encode()
        # The production parser intentionally uses header fields, not fabricated padding.
        out=b'    1C\n    2C                        10                                     3\n'
        for i,xyz in self.nodes.items():out+=struct.pack('<i3d',i,*((math.nextafter(xyz[0],math.inf),*xyz[1:])if coordinate_bad and i==1 else xyz))
        out+=b'    3C                         1                                     2\n'
        conn=tuple(reversed(self.cells[1]))if cell_bad else self.cells[1]
        out+=struct.pack('<14i',1,6,0,1,*conn)
        for time in times:
            line=bytearray(b' '*75);line[:7]=b'  100CL';line[12:24]=('%12.9f'%time).encode();line[24:36]=('%12d'%10).encode();line[74]=ord(str(format));out+=bytes(line)+b'\n'
            out+=b' -4  DISP        4    1\n -5  D1          1    2    1    0\n -5  D2          1    2    2    0\n -5  D3          1    2    3    0\n -5  ALL         1    2    0    0    1ALL\n'
            for i in self.nodes:out+=struct.pack('<i3d',1 if duplicate else i,math.pi,math.nextafter(1.,2.),5e-324)
        return out
    def run_bytes(self,data,times=(1.,)):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'test.frd';p.write_bytes(data);return reader.read(p,self.nodes,self.cells,times)
    def test_double_bits_and_four_states(self):
        rows=self.run_bytes(self.binary(times=(1.,2.,3.,4.)),times=(1.,2.,3.,4.))
        self.assertEqual(struct.pack('<3d',*rows[4.][0][1:]),struct.pack('<3d',math.pi,math.nextafter(1.,2.),5e-324))
    def test_float32_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary(format=2))
    def test_duplicate_id_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary(duplicate=True))
    def test_coordinate_one_ULP_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary(coordinate_bad=True))
    def test_connectivity_changed_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary(cell_bad=True))
    def test_truncation_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary()[:-1])
    def test_repeated_state_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary(times=(1.,1.)))
    def test_missing_state_refused(self):
        with self.assertRaises(ValueError):self.run_bytes(self.binary(),times=(1.,2.))


if __name__=='__main__':unittest.main()
