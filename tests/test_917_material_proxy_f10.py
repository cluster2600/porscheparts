"""Contrats purs du proxy Material Agent F10, sans runtime OpenUSD."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/reference-917-engine/source"
MANIFEST = ROOT / "twins/reference-917-engine/variant-configurations-f10.json"
PREPARE = SOURCE / "prepare_variant_configs_f10.py"
PROXY = SOURCE / "build_material_proxy_f10.py"
REMOTE = ROOT / "twins/reference-917-engine/remote-simready"
TRANSFER = ROOT / "deploy/vast/simready/transfer-job.sh"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


F10 = load_module("engine_917_f10_proxy_prepare", PREPARE)
MATERIAL_PROXY = load_module("engine_917_f10_material_proxy", PROXY)


class Engine917MaterialProxyF10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.variants = {item["variant_id"]: item for item in cls.manifest["variants"]}

    def configs(self, variant_id: str):
        geometry, _, detail = F10.generated_configs(
            self.manifest, ROOT, self.variants[variant_id]
        )
        return geometry, detail

    def test_un_representant_par_famille_reduit_le_travail_agent(self):
        expected = {
            "type_912_4_5_na": (37, 291),
            "917_30_turbo_5374": (44, 305),
        }
        for variant_id, (family_count, full_count) in expected.items():
            with self.subTest(variant_id=variant_id):
                plan = MATERIAL_PROXY.family_plan(*self.configs(variant_id))
                self.assertEqual(len(plan), family_count)
                self.assertEqual(sum(item["full_instance_count"] for item in plan), full_count)
                self.assertEqual(len({item["family"] for item in plan}), family_count)

    def test_seules_les_sept_familles_turbo_sont_ajoutees(self):
        na = {item["family"] for item in MATERIAL_PROXY.family_plan(*self.configs("type_912_4_5_na"))}
        turbo = {item["family"] for item in MATERIAL_PROXY.family_plan(*self.configs("917_30_turbo_5374"))}
        self.assertEqual(
            turbo - na,
            {
                "turbocharger",
                "charge_plenum",
                "turbo_turbine_wheel",
                "turbo_compressor_wheel",
                "turbo_shaft",
                "wastegate",
                "wastegate_bypass_pipe",
            },
        )

    def test_plan_refuse_chevauchement_compte_invalide_et_vide(self):
        geometry, detail = self.configs("type_912_4_5_na")
        overlap = copy.deepcopy(detail)
        overlap["families"].append(
            {"id": geometry["component_families"][0]["id"], "count": 1, "confidence": "test"}
        )
        with self.assertRaisesRegex(RuntimeError, "deux contrats"):
            MATERIAL_PROXY.family_plan(geometry, overlap)

        invalid = copy.deepcopy(geometry)
        invalid["component_families"][0]["count"] = 0
        with self.assertRaisesRegex(RuntimeError, "compte de famille invalide"):
            MATERIAL_PROXY.family_plan(invalid, detail)

        with self.assertRaisesRegex(RuntimeError, "aucune famille"):
            MATERIAL_PROXY.family_plan({"component_families": []}, {"families": []})

    def test_chaine_valide_proxy_et_recompose_le_stage_complet(self):
        f10 = (REMOTE / "phase-f10.sh").read_text(encoding="utf-8")
        minimum = (REMOTE / "phase-minimum-usd.sh").read_text(encoding="utf-8")
        material = (REMOTE / "phase-material.sh").read_text(encoding="utf-8")
        physics = (REMOTE / "phase-physics.sh").read_text(encoding="utf-8")
        self.assertIn("build_material_proxy_f10.py", f10)
        self.assertIn('phase_add_output "${DETAIL}"', f10)
        self.assertNotIn('phase_add_output "${MATERIAL_PROXY}"', f10)
        self.assertIn("validate-material-proxy-minimum.json", minimum)
        self.assertEqual(minimum.count('run_logged "${USD_PYTHON}" "${REFERENCE}"'), 2)
        self.assertIn('"${REFERENCE}" "${MATERIAL_PROXY}"', material)
        self.assertIn("--no-optimize-usd", material)
        self.assertIn("apply_family_material_bindings_f10.py", material)
        self.assertIn('phase_add_output "${FULL_MATERIAL_USD}"', material)
        self.assertNotIn('phase_add_output "${MATERIAL_PROXY}"', material)
        self.assertIn('MATERIAL_USD="$(report_output_path "${MATERIAL_REPORT}")"', physics)
        transfer = TRANSFER.read_text(encoding="utf-8")
        self.assertIn("source/build_material_proxy_f10.py", transfer)
        self.assertIn("source/apply_family_material_bindings_f10.py", transfer)


if __name__ == "__main__":
    unittest.main()
