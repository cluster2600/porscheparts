"""Lightweight contracts; native numerical witnesses run in test-native.sh."""
from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'twins/m64-cylinder-head/source/picogk-cooling'


class PicoGKCoolingContracts(unittest.TestCase):
    def test_compiled_module_keeps_upstream_reference_and_no_assets(self):
        project = (SOURCE / 'CoolingDomains.csproj').read_text()
        self.assertIn('<TargetFramework>net9.0</TargetFramework>', project)
        self.assertIn('$(UpstreamRoot)/PicoGK/PicoGK.csproj', project)
        self.assertIn('<EnableDefaultCompileItems>false', project)
        self.assertFalse(list(SOURCE.rglob('*.stl')))
        self.assertFalse(list(SOURCE.rglob('*.vdb')))
        provenance = json.loads((SOURCE / 'provenance.json').read_text())
        for name in ('Program.cs', 'CoolingDomains.csproj'):
            self.assertEqual(hashlib.sha256((SOURCE / name).read_bytes()).hexdigest(),
                             provenance['module'][name + '_sha256'])

    def test_one_byte_bool_adapter_is_guarded_by_hollow_cube_witness(self):
        source = (SOURCE / 'Program.cs').read_text()
        self.assertIn('private static extern byte IsInsideByte', source)
        self.assertIn('bool[] expectedOccupancy = [false, true, false]', source)
        self.assertIn('correctedOccupancy.SequenceEqual(expectedOccupancy)', source)
        self.assertIn('if (result > 1) throw', source)
        patch = (SOURCE / 'patches/picogk-0e6cf6b-bIsInside-I1.patch').read_text()
        self.assertIn('[return: MarshalAs(UnmanagedType.I1)]', patch)

    def test_hollow_native_volume_is_not_accepted_as_truth(self):
        source = (SOURCE / 'Program.cs').read_text()
        self.assertIn('native_resampled_volume_mm3', source)
        self.assertIn('oriented_mesh_volume_mm3', source)
        self.assertIn('double analyticHollowCubeVolume = 20 * 20 * 20 - 12 * 12 * 12', source)
        self.assertIn('bodyMeshVolume + voidMeshVolume - enclosureMeshVolume', source)
        self.assertIn('volumeScreenPass && occupancyScreenPass ? 0 : 3', source)

    def test_fields_are_named_and_results_not_physical_qualification(self):
        source = (SOURCE / 'Program.cs').read_text()
        self.assertIn('restored.voxGet(item.Key)', source)
        self.assertIn('unclassified-void-complement.stl', source)
        for name in ('manufacturing_authorized', 'thermal_simulation',
                     'structural_simulation', 'channels_created', 'master_modified',
                     'external_cooling_domain_qualified',
                     'structural_material_removal_authorized'):
            self.assertIn(name + ' = false', source)
        self.assertIn('exhaustive = false', source)
        evidence_path = ROOT / 'twins/m64-cylinder-head/evidence/picogk-domains-20260907.json'
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual([r['voxel_mm'] for r in evidence['runs']], [.6, .3])
        self.assertFalse(evidence['manufacturing_authorized'])
        for prefix in ('/Users/', '/home/', '/tmp/', '/private/'):
            self.assertNotIn(prefix, evidence_path.read_text())


if __name__ == '__main__':
    unittest.main()
