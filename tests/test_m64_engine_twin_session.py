import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "twins/m64-engine-twin/session-20260915.json"
spec = importlib.util.spec_from_file_location("orch", ROOT / "twins/m64-engine-twin/source/orchestrate_agents.py")
orch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orch)

GOOD = "```python\nimport cadquery as cq\ndef build(p):\n    return cq.Workplane().box(10, 10, 10)\n```"
BAD = "```python\nimport os\ndef build(p):\n    return None\n```"


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session = orch.load_session(SESSION)

    def test_budget_and_no_manufacturing(self):
        self.assertFalse(self.session["manufacturing_authorized"])
        self.assertLessEqual(self.session["budget"]["max_total_usd"], 60.0)
        nodes = self.session["nodes"]
        hourly = nodes["llm"]["max_dph"] + nodes["compute"]["max_dph"]
        hours = self.session["budget"]["max_wall_seconds"] / 3600
        self.assertLessEqual(hourly * hours + self.session["budget"]["cleanup_reserve_usd"], 60.0)

    def test_images_pinned_by_digest(self):
        images = [self.session["nodes"]["llm"]["image"], *self.session["nodes"]["compute"]["images"].values()]
        for image in images:
            self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")

    def test_levels_respect_dependencies(self):
        seen = set()
        produced = {c["id"] for lvl in orch.levels(self.session) for c in lvl}
        for level in orch.levels(self.session):
            for c in level:
                self.assertTrue(set(c.get("depends_on", [])) & produced <= seen, c["id"])
            seen |= {c["id"] for c in level}
        self.assertIn("crankshaft", seen)

    def test_code_filter(self):
        self.assertIsNotNone(orch.extract_code(GOOD)[0])
        self.assertEqual(orch.extract_code(BAD)[1], "forbidden_construct")
        self.assertTrue(orch.extract_code("pas de code")[1].startswith("no_build_function"))
        self.assertIn("tronquee", orch.extract_code("```python\nimport cadquery as cq\n")[1])

    def test_flat_params_keeps_numeric_leaves_only(self):
        flat = orch.flat_params({"bore": {"nominal": 100.0, "source": "P3"}, "ok": True, "n": 6, "l": [1, 2]})
        self.assertEqual(flat, {"bore.nominal": 100.0, "n": 6})

    def test_only_reruns_selected_and_keeps_previous_acceptances(self):
        previous = {"crankshaft": {"status": "accepted_unreviewed", "iterations": 2, "report": {"bbox_mm": [1, 1, 1]}, "job": "x"},
                    "connecting_rod": {"status": "failed_closed", "iterations": 6, "report": None, "job": None}}
        seen = []

        def llm(messages):
            seen.append(json.loads(messages[1]["content"].split("\n")[1])["id"])
            return GOOD

        executor = lambda job: {"ok": True, "brep_valid": True, "solid_count": 1, "volume_mm3": 1.0, "bbox_mm": [10, 10, 10]}
        with tempfile.TemporaryDirectory() as tmp:
            results = orch.Orchestrator(self.session, llm, executor, tmp, time.time() + 86400, {}).run(
                2, only={"connecting_rod"}, previous=previous)
        self.assertEqual(seen, ["connecting_rod"])
        self.assertEqual(results["connecting_rod"]["status"], "accepted_unreviewed")
        self.assertEqual(results["crankshaft"]["iterations"], 2)

    def test_envelope_rejects_oversize(self):
        report = {"ok": True, "brep_valid": True, "solid_count": 1, "volume_mm3": 1.0, "bbox_mm": [10, 900, 10]}
        self.assertIn("exceeds_envelope", orch.check_report(report, [620, 140, 140]))
        report["bbox_mm"] = [600, 100, 100]
        self.assertIsNone(orch.check_report(report, [140, 620, 140]))

    def test_orchestrator_retries_then_accepts_and_blocks_dependents(self):
        answers = {}

        def llm(messages):
            cid = json.loads(messages[1]["content"].split("\n")[1])["id"]
            answers[cid] = answers.get(cid, 0) + 1
            if cid == "crankshaft":
                return BAD
            return BAD if answers[cid] == 1 else GOOD

        def executor(job):
            return {"ok": True, "brep_valid": True, "solid_count": 1, "volume_mm3": 1000.0, "bbox_mm": [10, 10, 10]}

        with tempfile.TemporaryDirectory() as tmp:
            o = orch.Orchestrator(self.session, llm, executor, tmp, time.time() + 86400, {})
            results = o.run(concurrency=4)
            self.assertEqual(results["crankshaft"]["status"], "failed_closed")
            self.assertEqual(results["connecting_rod"]["status"], "blocked_dependency")
            self.assertEqual(results["piston_pin"]["status"], "accepted_unreviewed")
            self.assertEqual(results["piston_pin"]["iterations"], 2)
            self.assertTrue((Path(tmp) / "summary.json").exists())

    def test_deadline_stops_new_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = orch.Orchestrator(self.session, lambda m: GOOD, lambda j: {}, tmp, time.time() + 60, {})
            results = o.run(concurrency=2)
            self.assertTrue(all(r["status"] in {"stopped_deadline", "blocked_dependency"} for r in results.values()))


if __name__ == "__main__":
    unittest.main()
