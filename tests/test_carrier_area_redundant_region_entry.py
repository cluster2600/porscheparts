import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
try:
    import shapely
    import pyslm.support.support as support
except ImportError:
    shapely=support=None
SOURCE=Path(__file__).resolve().parents[1]/'parts/993-eng-carrier-0001/source/process-skins-20261016'
AVAILABLE=(shapely is not None and hasattr(shapely,'constrained_delaunay_triangles')
    and hasattr(support,'_triangulate_exact_projected_domain'))


def load(name):
    spec=importlib.util.spec_from_file_location('area_redundant_entry_test_'+name,SOURCE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@unittest.skipUnless(AVAILABLE,'Patched PySLM and constrained-triangulation runtime required')
class AreaRedundantRegionEntryTests(unittest.TestCase):
    def test_small5047_repair_result_and_complete_receipt_are_identical(self):
        old=load('continuous_redundant_interfaces');new=load('continuous_area_redundant_interfaces')
        from shapely.geometry import box
        domain=box(0,10,5,11)
        interfaces={'upper':[[[0,10],[5,10]]],'lower':[[[0,11],[5,11]]]}
        with patch.object(sys,'path',[str(SOURCE),*sys.path]):
            a,ar=old.repair(domain,domain,interfaces,.2)
            b,br=new.repair(domain,domain,interfaces,.2)
        self.assertEqual(a.wkb,b.wkb);self.assertEqual(ar,br)
        self.assertEqual(br['combinatorial_construction_source_sha256'],old.CONSTRUCTOR_SHA256)

    def test_real_chart2_complete_repair_result_and_receipt_are_identical(self):
        fixture=SOURCE/'combinatorial-evidence/reentrant-chart002.json'
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),
            '679ce5d3f3b96af77bccf3fddacd76c814b9dfd9293c6be851c982ccf51cd21f')
        row=json.loads(fixture.read_text());domain=shapely.from_wkb(row['source_domain_geometry_wkb_hex'])
        old=load('continuous_redundant_interfaces');new=load('continuous_area_redundant_interfaces')
        with patch.object(sys,'path',[str(SOURCE),*sys.path]):
            a,ar=old.repair(domain,domain,row['attested_source_interfaces'],row['penetration_mm'])
            b,br=new.repair(domain,domain,row['attested_source_interfaces'],row['penetration_mm'])
        self.assertEqual(a.wkb,b.wkb);self.assertEqual(ar,br)

    def test_both_flat_snapshots_replay_from_root_and_refuse_changed_area_source(self):
        for kind in ['prism','legacy']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                target=Path(tmp);tree=ast.parse((SOURCE/f'generate_{kind}_region_v7.py').read_text())
                names=ast.literal_eval(next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign)
                    and any(isinstance(a,ast.Name) and a.id=='names' for a in n.targets)))
                self.assertTrue({'continuous_area_redundant_interfaces.py','incremental_combinatorial_interfaces_area.py',
                    'chart_progress.py','redundant_strip_interfaces.py','continuous_redundant_interfaces.py'}<=set(names))
                for name in names:shutil.copy2(SOURCE/name,target/name)
                audit=SOURCE.parent/'process-scanpath-audit-20261016'
                for name in ['exact_contacts.py','exact_contacts_both.py','exact_zero_face_coverage.py','exact_polygon_coverage.py',
                    'exact_intended_holes.py','exact_band_union.py','exact_convex_union.py','exact_convex_halfplanes.py']:
                    shutil.copy2(audit/name,target/name)
                shutil.copy2(SOURCE.parent/'design-20261016/classify_mesh_contacts.py',target/'classify_mesh_contacts.py')
                script="import sys;sys.path.insert(0,sys.argv[1]);import continuous_area_redundant_interfaces as p;from shapely.geometry import box;d=box(0,10,5,11);r,c=p.repair(d,d,{'upper':[[[0,10],[5,10]]],'lower':[[[0,11],[5,11]]]},.2);assert c['combinatorial_construction_source_sha256']==p._POLICY.CONSTRUCTOR_SHA256;assert c['intervals'][0]['exact_intended_band_union_confinement']['passed']"
                result=subprocess.run([sys.executable,'-B','-c',script,tmp],cwd='/',capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                with (target/'incremental_combinatorial_interfaces_area.py').open('a') as handle:handle.write('\n# changed\n')
                result=subprocess.run([sys.executable,'-B','-c',script,tmp],cwd='/',capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0);self.assertIn('dependency changed',result.stderr)

if __name__=='__main__':unittest.main()
