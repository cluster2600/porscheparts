import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'twins/m64-cylinder-head/source/flowbench-intake/unify_native_port_partition.py'
SPEC=importlib.util.spec_from_file_location('port_unify',SOURCE)
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)


class NativePortUnificationTests(unittest.TestCase):
    def fixture(self):
        return {i:{'role':'walls_port','support_sha256':MODULE.SUPPORT,
            'source_match':[{'source':'raw_intake_face_8','role':'walls_port'}]} for i in (37,38,40)}

    def test_exact_same_support_group(self):
        MODULE.validate_selection(self.fixture(),MODULE.INTERNAL)

    def test_only_explicit_verified_seam_may_be_unprotected(self):
        self.assertEqual(MODULE.unprotected_edges(False,(40,),True),{101,102,103,104})
        self.assertEqual(MODULE.unprotected_edges(True,(40,),True),{101,102,103,104,105})
        for flag,incidence,closed in ((True,(37,40),True),(True,(40,),False),(True,(41,),True),('yes',(40,),True)):
            with self.subTest(incidence=incidence),self.assertRaises(ValueError):MODULE.unprotected_edges(flag,incidence,closed)

    def test_post_operation_protected_edges_and_source_are_required(self):
        report={'source_in_memory_serialization_unchanged':True,'unprotected_original_edges':[101,102,103,104,105],
            'in_memory_edge_identity_retained_original_ids':[i for i in range(1,196) if i not in MODULE.INTERNAL]}
        self.assertTrue(MODULE.protected_geometry_retained(report))
        for field,value in (('source_in_memory_serialization_unchanged',False),
                ('in_memory_edge_identity_retained_original_ids',[i for i in range(1,196) if i!=82]),
                ('unprotected_original_edges',[82,101,102,103,104,105]),
                ('in_memory_edge_identity_retained_original_ids',list(range(1,197)))):
            with self.subTest(field=field):self.assertFalse(MODULE.protected_geometry_retained({**report,field:value}))
        # Retaining every edge is also safe, but does not establish that a merge occurred.
        self.assertTrue(MODULE.protected_geometry_retained({**report,'in_memory_edge_identity_retained_original_ids':list(range(1,196))}))

    def test_wrong_support_role_or_provenance_rejected(self):
        for field,value in (('role','walls_seat'),('support_sha256','0'*64),('source_match',[])):
            faces=self.fixture();faces[38][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):MODULE.validate_selection(faces,MODULE.INTERNAL)

    def test_extra_face_or_protected_interface_never_removed(self):
        faces=self.fixture();faces[36]=deepcopy(faces[38])
        with self.assertRaises(ValueError):MODULE.validate_selection(faces,MODULE.INTERNAL)
        for incidence in ({102:(37,38)}, {**MODULE.INTERNAL,82:(30,38)}, {**MODULE.INTERNAL,102:(36,37)}):
            with self.subTest(incidence=incidence),self.assertRaises(ValueError):MODULE.validate_selection(self.fixture(),incidence)


if __name__=='__main__':unittest.main()
