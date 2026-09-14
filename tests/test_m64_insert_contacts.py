import importlib.util
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source'))
import audit_insert_contact_surfaces as contacts


@unittest.skipUnless(importlib.util.find_spec('OCP'), 'qualified OCP runtime required')
class InsertContactTests(unittest.TestCase):
    def test_full_contact_and_half_exposed_guide(self):
        cad = contacts.design.CAD()
        outer = cad.BRepPrimAPI_MakeCylinder(5., 10.).Shape()
        bore = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        body = contacts.motion.native_boolean(cad, outer, bore, 'cut')
        insert = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        face = contacts.external_cylinder_face(cad, insert, 2.)
        removal = cad.BRepPrimAPI_MakeCylinder(3., 5.).Shape()
        modified = contacts.motion.native_boolean(cad, body, removal, 'cut')
        _, record = contacts.compare_contact(cad, face, body, modified, 40*math.pi)
        self.assertAlmostEqual(record['reference_nominal_fraction'], 1., places=9)
        self.assertAlmostEqual(record['candidate_nominal_fraction'], .5, places=9)
        self.assertAlmostEqual(record['area_removed_by_porting'], 20*math.pi, places=7)
        self.assertFalse(record['load_capacity_or_heat_conductance_proven'])

    def test_gap_is_not_contact_and_wrong_side_is_rejected(self):
        cad = contacts.design.CAD()
        outer = cad.BRepPrimAPI_MakeCylinder(5., 10.).Shape()
        bore = cad.BRepPrimAPI_MakeCylinder(2.01, 10.).Shape()
        body = contacts.motion.native_boolean(cad, outer, bore, 'cut')
        insert = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        face = contacts.external_cylinder_face(cad, insert, 2.)
        _, report = contacts.contact_patch(cad, face, body)
        self.assertEqual(report['face_count'], 0)
        self.assertEqual(report['quadrature']['1e-11']['area'], 0.)
        with self.assertRaises(ValueError):
            contacts.external_cylinder_face(cad, insert, 2.01)

    def test_material_addition_cannot_pass_as_port_removal(self):
        cad = contacts.design.CAD()
        outer = cad.BRepPrimAPI_MakeCylinder(5., 10.).Shape()
        bore = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        full = contacts.motion.native_boolean(cad, outer, bore, 'cut')
        removal = cad.BRepPrimAPI_MakeCylinder(3., 5.).Shape()
        half = contacts.motion.native_boolean(cad, full, removal, 'cut')
        insert = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        face = contacts.external_cylinder_face(cad, insert, 2.)
        with self.assertRaisesRegex(ValueError, 'increased_after_material_removal'):
            contacts.compare_contact(cad, face, half, full, 40*math.pi)

    def test_embedded_insert_is_not_an_interface_contact(self):
        cad = contacts.design.CAD()
        unbored = cad.BRepPrimAPI_MakeCylinder(5., 10.).Shape()
        insert = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        # Surface Common alone would count this entirely buried insert.
        with self.assertRaisesRegex(ValueError, 'penetrates_body'):
            contacts.reject_insert_penetration(cad, insert, unbored)

    def test_subtolerance_gap_can_appear_coincident(self):
        cad = contacts.design.CAD()
        outer = cad.BRepPrimAPI_MakeCylinder(5., 10.).Shape()
        insert = cad.BRepPrimAPI_MakeCylinder(2., 10.).Shape()
        face = contacts.external_cylinder_face(cad, insert, 2.)
        for gap, expected_fraction in [(5e-8, 1.), (1e-6, 0.)]:
            bore = cad.BRepPrimAPI_MakeCylinder(2.+gap, 10.).Shape()
            body = contacts.motion.native_boolean(cad, outer, bore, 'cut')
            _, record = contacts.contact_patch(cad, face, body)
            fraction = record['quadrature']['1e-11']['area']/(40*math.pi)
            self.assertAlmostEqual(fraction, expected_fraction, places=7)
            self.assertEqual(contacts.reject_insert_penetration(cad, insert, body), 0.)
        tolerances = contacts.topology_tolerances(cad, insert)
        self.assertGreater(tolerances['face']['max'], 5e-8)


if __name__ == '__main__':
    unittest.main()
