import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'twins/m64-cylinder-head/source/picogk-peripherals'


class PeripheralsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('prepare', SOURCE / 'prepare.py')
        cls.prepare = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.prepare)
        previous = sys.modules.get('prepare')
        try:
            sys.modules['prepare'] = cls.prepare
            spec = importlib.util.spec_from_file_location('peripheral_counter_audit', SOURCE / 'audit.py')
            cls.audit = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.audit)
        finally:
            if previous is None:
                del sys.modules['prepare']
            else:
                sys.modules['prepare'] = previous

    def registration(self):
        p = self.prepare
        rows = []
        for name in p.NAMES:
            sign = 1 if name.startswith('intake') else -1
            rows.append(dict(name=name, axis_origin=[-22.5 if name.endswith('1') else 22.5,
                                                     18. if sign == 1 else -23.5, 3.],
                             axis_direction=[0., sign * math.sin(math.radians(8)), math.cos(math.radians(8))],
                             guide_OD=11., guide_axial_interval=[20., 55.]))
        return dict(registration={'scale_scan_units_per_mm_hypothesis': 1., 'rotation_Z_deg_hypothesis': -90.,
                                  'translation_Z_hypothesis': 3.}, module_sha256=p.PINS['module'], tools_private=rows,
                    components_imported_from_exact_STEP=[dict(name=f'{name}_{role}', imported_module_solid_id=i*3+j+1)
                                                         for i,name in enumerate(p.NAMES)
                                                         for j,role in enumerate(('valve','seat','guide'))])

    def manifest(self):
        return dict(schema='m64-picogk-peripherals/v1', source_sha256=self.prepare.PINS.copy(),
                    voxel_world_units=.2, status='research_assembly_incomplete_not_released',
                    units='uncalibrated_scan_unit_assumed_mm',
                    assembly_complete=False, manufacturing_authorized=False, source_master_modified=False,
                    dynamics_validated=False, thermal_validated=False,
                    parts=[dict(name=n, role=r, filename=n+'.stl', transform='identity_already_registered',
                                reference=r in ('head','seat','guide'), manufacturing_authorized=False)
                           for n,r in self.audit.expected_roles().items()])

    def test_exact_registration(self):
        axes, parts = self.prepare.validate_registration(self.registration())
        self.assertEqual((len(axes),len(parts)), (4,12))

    def test_registration_changes_reject(self):
        for value in (float('nan'),float('inf'),True,.5):
            data=self.registration(); data['tools_private'][0]['axis_direction'][1]=value
            with self.assertRaises(ValueError): self.prepare.validate_registration(data)
        for mutate in (
            lambda r:r['registration'].update(scale_scan_units_per_mm_hypothesis=True),
            lambda r:r['registration'].update(rotation_Z_deg_hypothesis=90),
            lambda r:r['tools_private'].pop(),
            lambda r:r['tools_private'][0].update(guide_OD=8),
            lambda r:r['components_imported_from_exact_STEP'][0].update(imported_module_solid_id=2),
        ):
            data=self.registration();mutate(data)
            with self.assertRaises(ValueError): self.prepare.validate_registration(data)

    def test_manifest_does_not_call_envelopes_springs_or_grant_authority(self):
        rows=self.audit.validate_manifest(self.manifest())
        self.assertEqual(sum(r['role']=='keepout_not_spring' for r in rows),4)
        self.assertEqual(sum(r['reference'] for r in rows),9)
        self.assertEqual(len(rows),28)

    def test_missing_or_promoted_authority_rejects(self):
        for field in ('assembly_complete','manufacturing_authorized','source_master_modified','dynamics_validated','thermal_validated'):
            for value in (None,True,0):
                data=self.manifest();data[field]=value
                with self.assertRaises(ValueError):self.audit.validate_manifest(data)

    def test_part_renames_reposition_and_path_escape_reject(self):
        for key,value in (('filename','../secret.stl'),('transform','translate'),('role','supplier_spring'),
                          ('manufacturing_authorized',True),('reference',False)):
            data=self.manifest();data['parts'][0][key]=value
            with self.assertRaises(ValueError):self.audit.validate_manifest(data)
        data=self.manifest();data['parts'].pop()
        with self.assertRaises(ValueError):self.audit.validate_manifest(data)

    def test_wrong_scale_resolution_and_source_reject(self):
        for key,value in (('voxel_world_units',True),('voxel_world_units',.04),('units','certified_mm'),
                          ('source_sha256',{})):
            data=self.manifest();data[key]=value
            with self.assertRaises(ValueError):self.audit.validate_manifest(data)

    def test_volume_screen_is_not_surface_or_print_authority(self):
        self.assertTrue(self.audit.volume_comparison(101,100)['passes'])
        self.assertFalse(self.audit.volume_comparison(103,100)['passes'])
        self.assertFalse(self.audit.volume_comparison(100,100)['continuous_surface_error_proved'])
        for v in (0,-1,True,float('inf'),float('nan')):
            with self.assertRaises(ValueError):self.audit.volume_comparison(v,100)

    def test_no_receipt_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'receipt.json'
            self.prepare.write_json(path,{'original':True});digest=self.prepare.sha(path)
            with self.assertRaises(FileExistsError):self.prepare.write_json(path,{})
            self.assertEqual(digest,self.prepare.sha(path))

    def test_new_geometry_is_picogk_and_shared_helpers_not_copied(self):
        project=(SOURCE/'Peripherals.csproj').read_text()
        self.assertIn('picogk-catalog/common/Sdf.cs',project)
        self.assertIn('picogk-catalog/engine/EngineSdf.cs',project)
        self.assertFalse((SOURCE/'Sdf.cs').exists())
        prepare=(SOURCE/'prepare.py').read_text()
        self.assertNotIn('BRepPrimAPI',prepare)
        self.assertNotIn('BRepAlgoAPI',prepare)


if __name__=='__main__':
    unittest.main()
