"""Nine independent analytic/word guard groups. SOURCE ONLY; all UNRUN."""

from fractions import Fraction
import importlib.util
import pathlib
import struct
import unittest


def load_validator():
    source = pathlib.Path(__file__).with_name("validate_binary64_words.py")
    spec = importlib.util.spec_from_file_location("held_independent_word_validator",source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(tag, values):
    return dict(node_tag=tag,coordinates_mm=list(values),binary64_hex=[float(v).hex() for v in values],
                words_le_hex=struct.pack("<3d",*values).hex())


class IndependentWordValidatorFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = load_validator()

    def test_01_exact_integer_decoder_zero_subnormal_normal_and_maximum(self):
        v = self.v
        self.assertEqual(v.fraction_word(0),Fraction(0))
        self.assertEqual(v.fraction_word(2**63),Fraction(0))
        self.assertEqual(v.fraction_word(1),Fraction(1,2**1074))
        self.assertEqual(v.fraction_word(2**52),Fraction(1,2**1022))
        self.assertEqual(v.fraction_word(0x3ff0000000000000),Fraction(1))
        self.assertEqual(v.fraction_word(0x7fefffffffffffff),Fraction((2**53-1)*2**971))
        for bad in (True,-1,2**64,0x7ff0000000000000,0x7ff8000000000001):
            with self.assertRaises(ValueError):
                v.fraction_word(bad)

    def test_02_coordinate_bits_and_signed_zero_roundtrip_refuse_stale_fields(self):
        v = self.v
        original = row(10,(-0.0,1.0,0.0))
        points,words,raw = v.coordinate(original,proposed=True)
        self.assertEqual(points,(Fraction(0),Fraction(1),Fraction(0)))
        self.assertEqual(words[0],2**63)
        self.assertEqual(raw,"0000000000000080000000000000f03f0000000000000000")
        for changed in (dict(original,binary64_hex=["0x0.0p+0","0x1.0000000000000p+0","0x0.0p+0"]),
                        dict(original,words_le_hex="00"*24),dict(original,node_tag=True),
                        dict(original,coordinates_mm=[False,1.0,0.0])):
            with self.assertRaises(ValueError):
                v.coordinate(changed,proposed=True)

    def test_03_right_and_integer_regular_tetrahedra_have_analytic_values(self):
        v = self.v
        right = v.metrics([(0,0,0),(1,0,0),(0,1,0),(0,0,1)])
        self.assertEqual((right["D"],right["S"],right["T"],right["Q_squared"]),(1,9,6,Fraction(2,3)))
        self.assertTrue(right["gate"])
        regular = v.metrics([(1,1,1),(-1,1,-1),(1,-1,-1),(-1,-1,1)])
        self.assertEqual((regular["D"],regular["S"],regular["T"],regular["Q_squared"]),(16,48,192,Fraction(1)))
        self.assertTrue(regular["gate"])

    def test_04_orientation_planar_coincident_and_closed_scalar_threshold(self):
        v = self.v
        inverted = v.metrics([(0,0,0),(0,1,0),(1,0,0),(0,0,1)])
        self.assertEqual(inverted["D"],-1)
        self.assertEqual(inverted["Q_squared"],Fraction(2,3))
        self.assertFalse(inverted["gate"])
        for points in ([(0,0,0),(1,0,0),(0,1,0),(1,1,0)],[(0,0,0)]*4):
            self.assertFalse(v.metrics(points)["gate"])
        # Predicate-only equality: these scalars are not asserted to realize a tetrahedron.
        self.assertTrue(v.quality_gate(Fraction(1),Fraction(3600),Fraction(1)))
        self.assertFalse(v.quality_gate(Fraction(1),Fraction(3601),Fraction(1)))
        self.assertFalse(v.quality_gate(Fraction(-1),Fraction(3600),Fraction(1)))
        self.assertFalse(v.quality_gate(Fraction(0),Fraction(0),Fraction(0)))

    def test_05_oriented_local_face_cancellation_and_nonmanifold_refusals(self):
        v = self.v
        faces,count = v.boundary_faces([(1,2,3,4),(1,3,2,5)])
        self.assertEqual(count,1)
        self.assertEqual(len(faces),6)
        self.assertNotIn((1,3,2),faces)
        for cells in ([(1,2,3,4),(1,2,3,5)],[(1,2,3,4)]*3,[(1,1,2,3)]):
            with self.assertRaises(ValueError):
                v.boundary_faces(cells)

    def test_06_fixed_word_signed_zero_and_complete_row_protection(self):
        v = self.v
        original = [row(1,(0.0,0.0,0.0)),row(2,(-0.0,1.0,0.0))]
        old = {r["node_tag"]:v.coordinate(r,True)[1] for r in original}
        proposed = [row(1,(1.0,0.0,0.0)),original[1]]
        points,words = v.proposed_word_rows(proposed,[1,2],{1},old)
        self.assertEqual(points[1][0],Fraction(1))
        self.assertEqual(words[2][0],2**63)
        for bad in ([proposed[0]],list(reversed(proposed)),[proposed[0],row(2,(0.0,1.0,0.0))],
                    [proposed[0],proposed[0]]):
            with self.assertRaises(ValueError):
                v.proposed_word_rows(bad,[1,2],{1},old)

    def test_07_positive_determinants_and_total_volume_do_not_override_quality(self):
        v = self.v
        # Same base and height: x shear changes quality but not signed volume.
        before = v.metrics([(0,0,0),(1,0,0),(0,1,0),(0,0,1)])
        after = v.metrics([(0,0,0),(1,0,0),(0,1,0),(100,0,1)])
        self.assertEqual(before["D"],after["D"])
        self.assertTrue(after["D"]>0)
        self.assertFalse(after["gate"])
        self.assertLess(after["Q_squared"],Fraction(1,100))
        # Real positive height can round to zero: correct word decoding still refuses the cell.
        rounded = v.metrics([(0,0,0),(1,0,0),(0,1,0),(0,0,v.fraction_word(0))])
        self.assertFalse(rounded["gate"])

    def test_08_typed_serialization_and_strict_json_refuse_ambiguous_inputs(self):
        v = self.v
        self.assertNotEqual(v.typed_digest([1,2],"Q"),v.typed_digest([2,1],"Q"))
        self.assertNotEqual(v.typed_digest([0.0],"d"),v.typed_digest([-0.0],"d"))
        for payload in (b"{\"a\":1,\"a\":2}",b"[NaN]",b"[Infinity]"):
            with self.assertRaises(ValueError):
                v.strict_json(payload)
        for values in ([True],[2,1],[1,1]):
            with self.assertRaises(ValueError):
                v.ordered_ints(values)
        with self.assertRaises(ValueError):
            v.rebuild_baseline({}, {})

    def test_09_complete_frozen_block_bookkeeping_and_pure_import_surface(self):
        v = self.v
        self.assertEqual([b[0] for b in v.BLOCKS],[2,7,8,9,10,21,28,30,31,39,45])
        self.assertEqual(sum(len(b[1]) for b in v.BLOCKS),16)
        self.assertEqual(sum(b[2] for b in v.BLOCKS),499)
        self.assertEqual(sum(b[3] for b in v.BLOCKS),24)
        self.assertEqual(sum(b[4] for b in v.BLOCKS),33)
        self.assertFalse(any(name in v.__dict__ for name in ("os","subprocess","pathlib","z3","qfnra_emitter")))


if __name__ == "__main__":
    unittest.main(defaultTest="IndependentWordValidatorFixtures",verbosity=2)
