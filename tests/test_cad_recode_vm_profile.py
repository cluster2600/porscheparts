"""Offline checks for the bounded VM discovery extension."""
from pathlib import Path
import runpy
import unittest
import tempfile
from contextlib import nullcontext
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class VMProfileTests(unittest.TestCase):
    def test_launch_and_expiry_use_fixed_scope(self):
        base = runpy.run_path(str(ROOT / "deploy/openbao/openbao-vastai"))
        p = runpy.run_path(str(ROOT / "deploy/openbao/cad_recode_vm_profile.py"), init_globals=base)
        g = p["launch_cad_recode_vm"].__globals__
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder) / "state.json"
            request, destroy = Mock(return_value={"new_contract": 321}), Mock()
            inventory = Mock(return_value=[])
            with patch.dict(g, CAD_RECODE_VM_STATE=state,
                            simready_launch_lock=lambda: nullcontext(), list_instances=inventory,
                            picogk_account_balance=lambda _: {"conservative_available_usd": 20},
                            get_cad_recode_vm_offers=lambda _: {"offers": [{"id": 123, "dph_total": 2}]},
                            ensure_local_ssh_registered=Mock(), vast_request=request,
                            destroy_instance_verified=destroy), patch.object(g["subprocess"], "run", return_value=Mock(returncode=0)):
                result = p["launch_cad_recode_vm"]("unused", "123")
                self.assertEqual(result["instance_id"], 321)
                payload = request.call_args.kwargs["payload"]
                self.assertEqual(payload["disk"], 500)
                self.assertIs(payload["vm"], True)
                self.assertEqual(payload["template_hash_id"], p["CAD_RECODE_VM_TEMPLATE"])
                self.assertNotIn("runtype", payload)
                with self.assertRaises(p["SafeError"]):
                    p["launch_cad_recode_vm"]("unused", "123")
                self.assertEqual(request.call_count, 1)
                inventory.return_value = [{"id": 321}]
                with patch.object(g["time"], "time", return_value=result["deadline_epoch"] + 1):
                    p["expire_cad_recode_vm"]("unused")
                destroy.assert_called_once_with("unused", 321, expected_label=p["CAD_RECODE_VM_LABEL"])

    def test_hardware_vm_and_cost_boundary(self):
        base = runpy.run_path(str(ROOT / "deploy/openbao/openbao-vastai"))
        p = runpy.run_path(str(ROOT / "deploy/openbao/cad_recode_vm_profile.py"), init_globals=base)
        valid = dict(gpu_name="RTX PRO 6000 WS", num_gpus=1, gpu_frac=1,
                     gpu_ram=98304, cpu_cores_effective=32, cpu_ram=128000,
                     disk_space=500, dph_total=2, reliability=.999,
                     verified=True, rentable=True, rented=False, vms_enabled=True,
                     inet_up_cost=.01, inet_down_cost=.01)
        self.assertTrue(p["cad_recode_vm_eligible"](valid))
        self.assertTrue(p["cad_recode_vm_eligible"](dict(valid, gpu_frac=.5)))
        for key, value in (("vms_enabled", False), ("vms_enabled", "true"),
                           ("gpu_name", "H100"), ("gpu_ram", 48000),
                           ("cpu_cores_effective", 24), ("dph_total", 2.51)):
            self.assertFalse(p["cad_recode_vm_eligible"](dict(valid, **{key: value})))
        query = p["cad_recode_vm_query"]()
        self.assertEqual(query["allocated_storage"], 500)
        self.assertEqual(query["vms_enabled"], {"eq": True})
        self.assertEqual(query["dph_total"], {"lte": 2.5})
        self.assertEqual(query["gpu_frac"], {"gt": 0, "lte": 1})
        alternative = dict(valid, id=123, gpu_name="L40S", gpu_ram=48000,
                           cpu_cores_effective=12, cpu_ram=64000, disk_space=300,
                           gpu_frac=.25)
        self.assertTrue(p["cad_recode_vm_alternative_eligible"](alternative))
        for key, value in (("vms_enabled", False), ("dph_total", 2.51),
                           ("gpu_frac", 0), ("gpu_ram", 24000),
                           ("inet_up_cost", .06)):
            self.assertFalse(p["cad_recode_vm_alternative_eligible"](dict(alternative, **{key: value})))


if __name__ == "__main__":
    unittest.main()
