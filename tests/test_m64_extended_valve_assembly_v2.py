"""Pure retained-stem and translation gates; no private geometry imported."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/wholebody'
sys.path.insert(0,str(HERE))
SPEC=importlib.util.spec_from_file_location('extended_valves_v2',HERE/'build_extended_valve_assembly_v2.py')
valves=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(valves)


class ExtendedValveV2Tests(unittest.TestCase):
    def test_positive_lift_moves_toward_chamber(self):
        angle=math.radians(8);axis=[0.,-math.sin(angle),math.cos(angle)]
        for bank,lift in [('intake',11.5),('exhaust',9.6)]:
            moved=valves.stroke_vector(bank,axis)
            self.assertAlmostEqual(sum(a*b for a,b in zip(axis,moved)),-lift)
        for bank,axis in [('G7',[0.,0.,1.]),('intake',[0.,0.,2.]),('exhaust',[0.,0.,-1.]),('intake',[False,0.,1.])]:
            with self.assertRaises(ValueError):valves.stroke_vector(bank,axis)

    def test_exact_retained_native_stem_gate(self):
        good=[3.,9.,82.,1.,math.pi*9.,0.]
        self.assertTrue(valves.native_stem_gate(*good))
        self.assertTrue(valves.native_stem_gate(3.,9.,82.,-1.,math.pi*9.,0.))
        for index in range(6):
            bad=good[:];bad[index]=math.nan
            self.assertFalse(valves.native_stem_gate(*bad))
        self.assertFalse(valves.native_stem_gate(3.1,9.,82.,1.,math.pi*9.,0.))
        self.assertFalse(valves.native_stem_gate(3.,9.,105.,1.,math.pi*9.,0.))

    def test_only_positive_local_extension_is_accepted(self):
        self.assertAlmostEqual(valves.ADDED_VOLUME,650.3096792930871)
        self.assertTrue(valves.addition_gate(0,0.,valves.ADDED_VOLUME,0,0.))
        for args in [(1,0.,valves.ADDED_VOLUME,0,0.),(0,1.,valves.ADDED_VOLUME,0,0.),
                     (0,0.,0.,0,0.),(0,0.,math.inf,0,0.),(0,0.,valves.ADDED_VOLUME,1,0.),
                     (0,0.,valves.ADDED_VOLUME,0,1.),(False,0.,valves.ADDED_VOLUME,0,0.)]:
            self.assertFalse(valves.addition_gate(*args))

    def test_positive_interference_is_never_clear(self):
        self.assertTrue(valves.zero_volume(0,0.))
        self.assertFalse(valves.zero_volume(1,1e-10))
        self.assertFalse(valves.zero_volume(0,-1.))


if __name__=='__main__':unittest.main()

