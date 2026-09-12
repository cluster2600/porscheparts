"""Offline bounded CAD proposals; HTTP and all inference are mocked."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "twins/m64-cylinder-head/source"
SPEC = importlib.util.spec_from_file_location("m64_cad_proposals", SOURCE / "run_cad_proposal_agents.py")
CAD = importlib.util.module_from_spec(SPEC)
with mock.patch.object(sys, "path", [str(SOURCE), *sys.path]):
    SPEC.loader.exec_module(CAD)


class CadProposalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m64-cad-proposals-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context_path = self.root / "context.json"
        self.output = self.root / "new-output"
        text = "# Authorized fillet excerpt\nradius = requested_radius\n"
        self.context = {"source_excerpts": [{"path": "twins/example.py", "text": text, "sha256": CAD.sha(text)}],
                        "user_constraints": ["Original contour preserved; no arbitrary oval."],
                        "historical_trial_summary": "R0.25 has unresolved volume discrepancy; no validated candidate."}
        self.answer = {"mission_id": "cad_01", "radius_scan_units": 0.125, "construction_mode": "default",
                       "hypothesis": "Unverified local trial only.", "risks": ["Volume discrepancy unresolved."]}
        self.write_context()

    def write_context(self):
        self.context_path.write_text(json.dumps(self.context, ensure_ascii=False), encoding="utf-8")

    def response(self, answer=None, **updates):
        envelope = {"model": CAD.MODEL, "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(self.answer if answer is None else answer)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
        envelope.update(updates)
        return 200, json.dumps(envelope).encode()

    def argv(self, *extra):
        return ["--context", str(self.context_path), "--output", str(self.output),
                "--endpoint", "http://127.0.0.1:18000/v1", "--model", CAD.MODEL, "--limit", "1", *extra]

    def run_pilot(self, response=None, extra=(), effect=None):
        with mock.patch.object(CAD, "request_chat", return_value=response or self.response(), side_effect=effect) as http:
            with redirect_stdout(io.StringIO()) as stdout:
                code = CAD.main(self.argv(*extra))
        return code, json.loads(stdout.getvalue()), json.loads((self.output / "cad_01.json").read_text()), http

    def assert_bad_args(self, extra):
        with mock.patch.object(CAD, "request_chat") as http, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            CAD.main(self.argv(*extra))
        http.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_valid_proposal_private_hashed_unreviewed(self):
        response = self.response()
        code, index, report, http = self.run_pilot(response)
        self.assertEqual((code, http.call_count, index["counts"]), (0, 1, {"unreviewed": 1}))
        self.assertFalse(index["geometry_executed"])
        self.assertFalse(index["physical_validation"])
        self.assertFalse(index["server_weight_revision_attested_by_client"])
        self.assertEqual(index["usage"]["total_tokens"], 150)
        self.assertEqual(report["answer"], self.answer)
        self.assertEqual(report["raw_sha256"], hashlib.sha256(response[1]).hexdigest())
        digest = report.pop("record_sha256")
        self.assertEqual(digest, CAD.sha(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))))
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in self.output.iterdir()))
        port, payload, timeout = http.call_args.args
        self.assertEqual((port, payload["max_tokens"]), (18000, 900))
        self.assertLessEqual(timeout, 120)
        self.assertNotIn("tools", payload)
        self.assertEqual(json.loads(payload["messages"][1]["content"])["context"], self.context)

    def test_abstention_is_a_valid_unreviewed_result(self):
        answer = {"mission_id": "cad_01", "abstain": True, "reason": "Reconcile historical volume first."}
        code, index, report, _ = self.run_pilot(self.response(answer))
        self.assertEqual((code, index["abstentions"], report["status"]), (0, 1, "unreviewed"))
        self.assertNotIn("radius_scan_units", report["answer"])

    def test_strict_finite_radius_and_modes(self):
        for radius in (True, False, None, "0.1", [], -0.1, 0, 1.01, float("nan"), float("inf"), 10 ** 999):
            with self.subTest(radius=str(radius)[:20]), self.assertRaises(ValueError):
                CAD.validate_answer(dict(self.answer, radius_scan_units=radius), "cad_01")
        for radius in (0.0001, 0.25, 1):
            self.assertEqual(CAD.validate_answer(dict(self.answer, radius_scan_units=radius), "cad_01")["radius_scan_units"], radius)
        for mode in ("new-mode", True, [], None):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                CAD.validate_answer(dict(self.answer, construction_mode=mode), "cad_01")
        CAD.validate_answer(dict(self.answer, construction_mode="strict-approximation-v1"), "cad_01")

    def test_schema_extra_keys_wrong_id_and_text_limits(self):
        cases = [dict(self.answer, code="import os"), dict(self.answer, mission_id="cad_02"),
                 dict(self.answer, hypothesis="x" * 601), dict(self.answer, risks=[]),
                 dict(self.answer, risks=["risk"] * 7), dict(self.answer, risks=["x" * 241]),
                 dict(self.answer, risks=[True]), dict(self.answer, hypothesis=" "),
                 {"mission_id": "cad_01", "abstain": False, "reason": "no"},
                 {"mission_id": "cad_01", "abstain": True, "reason": "no", "radius_scan_units": 0.1}]
        for answer in cases:
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                CAD.validate_answer(answer, "cad_01")

    def test_json_rejects_duplicates_and_nonfinite_literals(self):
        for text in ('{"a":1,"a":2}', '{"nested":{"a":1,"a":2}}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                CAD.strict_json(text)

    def test_invalid_responses_no_retry_keep_raw(self):
        cases = [(302, b"redirect"), (200, b"not JSON"), (200, b"x" * 65537),
                 self.response(model="wrong-model"), self.response(usage={"completion_tokens": 901}),
                 self.response(usage={"prompt_tokens": True, "completion_tokens": 1, "total_tokens": 2}),
                 self.response(usage={"prompt_tokens": 1, "completion_tokens": 901, "total_tokens": 902}),
                 self.response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}]),
                 self.response(choices=[{"finish_reason": "stop", "message": {"content": "{}", "tool_calls": [{}]}}]),
                 self.response(choices=[{"finish_reason": "stop", "message": {"content": "{}", "function_call": {"name": "x"}}}]),
                 self.response(choices=[])]
        for i, response in enumerate(cases):
            with self.subTest(case=i):
                self.output = self.root / f"invalid-{i}"
                code, _, report, http = self.run_pilot(response)
                self.assertEqual((code, report["status"], http.call_count), (1, "invalid", 1))
                self.assertNotIn("answer", report)
                self.assertEqual((self.output / "cad_01.raw.txt").read_bytes(), response[1])

    def test_context_hash_schema_and_source_bounds_before_http(self):
        original = json.loads(json.dumps(self.context))
        cases = [dict(original, extra="forbidden"), dict(original, user_constraints=[]),
                 dict(original, historical_trial_summary=""), dict(original, source_excerpts=[])]
        for key, value in (("sha256", "0" * 64), ("path", "../private.py"), ("path", "/private.py"), ("text", "")):
            cases.append(dict(original, source_excerpts=[dict(original["source_excerpts"][0], **{key: value})]))
        for context in cases:
            with self.subTest(context=context):
                self.context = context
                self.write_context()
                self.assert_bad_args(())
        self.context_path.write_text(" " * 20001)
        self.assert_bad_args(())

    def test_endpoint_model_and_budgets_rejected_before_http(self):
        cases = [("--endpoint", value) for value in ("http://localhost:18000/v1", "https://127.0.0.1:18000/v1",
                 "http://127.0.0.1:0/v1", "http://127.0.0.1:65536/v1", "http://127.0.0.1:1/v1?x=1",
                 "http://127.0.0.1:1/v1/", "http://example.org:1/v1")]
        cases += [("--model", "arbitrary"), ("--concurrency", "5"), ("--concurrency", "0"), ("--limit", "25"),
                  ("--max-tokens", "901"), ("--http-timeout", "121"), ("--deadline-seconds", "1201"),
                  ("--deadline-seconds", "nan"), ("--deadline-seconds", "inf")]
        for flags in cases:
            with self.subTest(flags=flags):
                self.assert_bad_args(flags)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "index.json"
        marker.write_text("preserved")
        with mock.patch.object(CAD, "request_chat") as http, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            CAD.main(self.argv())
        http.assert_not_called()
        self.assertEqual(marker.read_text(), "preserved")

    def test_twenty_four_independent_missions_four_workers_same_radius_allowed(self):
        barrier = threading.Barrier(4, timeout=5)
        lock = threading.Lock()
        active = maximum = 0
        seen = []
        def request(port, payload, timeout):
            nonlocal active, maximum
            mission = json.loads(payload["messages"][1]["content"])
            with lock:
                active += 1
                maximum = max(maximum, active)
                seen.append(mission["mission_id"])
            barrier.wait()
            with lock:
                active -= 1
            return self.response(dict(self.answer, mission_id=mission["mission_id"]))
        code, index, _, http = self.run_pilot(extra=("--limit", "24"), effect=request)
        self.assertEqual((code, http.call_count, maximum, index["requests"]), (0, 24, 4, 24))
        self.assertEqual(len(set(seen)), 24)
        self.assertEqual(index["output_token_ceiling"], 21600)
        self.assertEqual(index["usage"]["total_tokens"], 3600)

    def test_global_deadline_cuts_request_and_blocks_queue_without_retries(self):
        clock = [0.0]
        def request(port, payload, timeout):
            self.assertEqual(timeout, 1)
            clock[0] = 2.0
            raise TimeoutError()
        with mock.patch.object(CAD.time, "monotonic", side_effect=lambda: clock[0]):
            code, index, report, http = self.run_pilot(extra=("--limit", "4", "--concurrency", "1", "--deadline-seconds", "1"), effect=request)
        self.assertEqual((code, http.call_count, index["counts"], index["requests"]), (1, 1, {"invalid": 4}, 1))
        self.assertEqual(report["reason"], "http_deadline")
        self.assertEqual(json.loads((self.output / "cad_02.json").read_text())["reason"], "global_deadline_exhausted")


if __name__ == "__main__":
    unittest.main()
