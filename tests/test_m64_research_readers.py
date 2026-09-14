"""Offline readers: mocked HTTP only; no model, socket or secret access."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("m64_readers", ROOT / "twins/m64-cylinder-head/source/run_research_readers.py")
READERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READERS)


class ResearchReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m64-readers-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "missions.json"
        self.corpus = self.root / "corpus.json"
        self.output = self.root / "new-output"
        self.source = {"url": "https://example.org/paper", "text": "Exact evidence. Données partielles.",
                       "read_level": "abstract"}
        self.source["sha256"] = READERS.sha(self.source["text"])
        self.missions = [{"id": "reader_" + str(i), "title": "Lecture " + str(i), "question": "Comparer les limites.",
                          "sources": [self.source["url"]]} for i in range(24)]
        self.answer = {"summary": "Résultat documentaire à examiner.", "findings": [{"claim": "Données partielles.",
                       "source_url": self.source["url"], "evidence_excerpt": "Exact evidence.",
                       "application": "Transfert M64 inconnu.", "limits": "Résumé seulement."}],
                       "proposed_tests": ["Mesures indépendantes futures."], "unknowns": ["Conditions moteur."]}
        self.store_inputs()

    def store_inputs(self, sources=None):
        self.manifest.write_text(json.dumps({"missions": self.missions}))
        self.corpus.write_text(json.dumps([self.source] if sources is None else sources))

    def response(self, answer=None, **updates):
        envelope = {"model": "local-reader", "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(self.answer if answer is None else answer)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}}
        envelope.update(updates)
        return 200, json.dumps(envelope).encode()

    def argv(self, *extra):
        return ["--manifest", str(self.manifest), "--corpus", str(self.corpus), "--output", str(self.output),
                "--endpoint", "http://127.0.0.1:18000/v1", "--model", "local-reader", "--limit", "1", *extra]

    def run_reader(self, response=None, extra=(), effect=None):
        with mock.patch.object(READERS, "request_chat", return_value=response or self.response(), side_effect=effect) as http:
            with redirect_stdout(io.StringIO()) as stdout:
                code = READERS.main(self.argv(*extra))
        index = json.loads(stdout.getvalue())
        report = json.loads((self.output / "reader_0.json").read_text())
        return code, index, report, http

    def test_valid_pilot_private_reports_and_tokens(self):
        code, index, report, http = self.run_reader(extra=("--limit", "4"))
        self.assertEqual((code, http.call_count, index["counts"]), (0, 4, {"unreviewed": 4}))
        self.assertEqual(index["usage"]["total_tokens"], 600)
        self.assertEqual(report["citation_checks"], "passed")
        self.assertFalse(report["physical_validation"])
        self.assertEqual(report["answer"]["findings"][0]["read_level"], "abstract")
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in self.output.iterdir()))
        self.assertLessEqual(len((self.output / "reader_0.md").read_text().split()), 800)
        port, payload, timeout = http.call_args.args
        self.assertEqual(port, 18000)
        self.assertEqual(payload["max_tokens"], 1600)
        self.assertNotIn("tools", payload)
        self.assertLessEqual(timeout, 180)

    def test_missing_empty_and_skipped_block_without_http(self):
        for source in ([], [dict(self.source, text="", sha256=READERS.sha(""))], [dict(self.source, read_level="skipped")]):
            with self.subTest(source=source):
                self.output = self.root / ("blocked-" + str(len(list(self.root.iterdir()))))
                self.store_inputs(source)
                code, _, report, http = self.run_reader()
                self.assertEqual((code, report["status"]), (1, "blocked"))
                http.assert_not_called()

    def test_invalid_json_url_and_evidence_retain_raw(self):
        cases = [(200, b"not json"), self.response(answer=dict(self.answer, findings=[dict(self.answer["findings"][0],
                 source_url="https://invented.org/paper")])), self.response(answer=dict(self.answer, findings=[
                 dict(self.answer["findings"][0], evidence_excerpt="Absent evidence")])), self.response(model="wrong-model")]
        for i, response in enumerate(cases):
            with self.subTest(case=i):
                self.output = self.root / ("invalid-" + str(i))
                code, _, report, http = self.run_reader(response)
                self.assertEqual((code, report["status"], http.call_count), (1, "invalid", 1))
                self.assertNotIn("answer", report)
                self.assertEqual((self.output / "reader_0.raw.txt").read_bytes(), response[1])

    def test_citations_must_be_in_actual_truncated_excerpt(self):
        self.source["text"] = "A" * 8000 + " Exact evidence."
        self.source["sha256"] = READERS.sha(self.source["text"])
        self.store_inputs()
        code, _, report, http = self.run_reader()
        supplied = json.loads(http.call_args.args[1]["messages"][1]["content"])["sources"][0]
        self.assertEqual((code, len(supplied["text"])), (1, 8000))
        self.assertTrue(supplied["truncated"])
        self.assertEqual(report["reason"], "excerpt_not_in_supplied_text")

    def test_invalid_schema_and_output_budgets(self):
        cases = [self.response(answer={"summary": "Missing required fields"}),
                 self.response(answer=dict(self.answer, summary="word " * 801)),
                 self.response(usage={"completion_tokens": 1601}),
                 self.response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}]),
                 self.response(choices=[{"finish_reason": "stop", "message": {
                     "content": json.dumps(self.answer), "tool_calls": [{"name": "anything"}]}}])]
        for i, response in enumerate(cases):
            with self.subTest(case=i):
                self.output = self.root / ("budget-" + str(i))
                code, _, report, http = self.run_reader(response)
                self.assertEqual((code, report["status"], http.call_count), (1, "invalid", 1))
                self.assertNotIn("answer", report)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "index.json"
        marker.write_text("preserve")
        with mock.patch.object(READERS, "request_chat") as http, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                READERS.main(self.argv())
        http.assert_not_called()
        self.assertEqual(marker.read_text(), "preserve")

    def test_input_sha_rejected_before_any_request_or_output(self):
        self.source["sha256"] = "0" * 64
        self.store_inputs()
        with mock.patch.object(READERS, "request_chat") as http, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                READERS.main(self.argv())
        http.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_endpoint_and_budget_bounds_rejected_before_http(self):
        invalid = [("--endpoint", v) for v in ("http://localhost:1/v1", "https://127.0.0.1:1/v1",
                   "http://127.0.0.1:0/v1", "http://127.0.0.1:1/v1?x=1", "http://127.0.0.1:1/v1/", "http://example.org:1/v1")]
        invalid += [("--concurrency", "5"), ("--concurrency", "0"), ("--max-tokens", "1601"), ("--limit", "25"),
                    ("--http-timeout", "181"), ("--deadline-seconds", "1801"), ("--http-timeout", "nan")]
        with mock.patch.object(READERS, "request_chat") as http:
            for flags in invalid:
                with self.subTest(flags=flags), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    READERS.main(self.argv(*flags))
            http.assert_not_called()

    def test_deadline_reduces_timeout_and_blocks_queued_work(self):
        clock = [0.0]
        def request(port, payload, timeout):
            self.assertEqual(timeout, 1)
            clock[0] = 2.0
            raise TimeoutError()
        with mock.patch.object(READERS.time, "monotonic", side_effect=lambda: clock[0]):
            code, index, report, http = self.run_reader(extra=("--limit", "4", "--concurrency", "1", "--deadline-seconds", "1"), effect=request)
        self.assertEqual((code, http.call_count, report["status"]), (1, 1, "timeout"))
        self.assertEqual(index["counts"], {"timeout": 1, "blocked": 3})

    def test_all_twenty_four_missions_respect_four_workers(self):
        barrier = threading.Barrier(4, timeout=5)
        lock = threading.Lock()
        active = maximum = 0
        def request(*args):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            barrier.wait()
            with lock:
                active -= 1
            return self.response()
        code, index, _, http = self.run_reader(extra=("--limit", "24"), effect=request)
        self.assertEqual((code, http.call_count, maximum, index["requests"]), (0, 24, 4, 24))

    def test_http_transport_no_redirect_proxy_or_authorization(self):
        with mock.patch.object(READERS.http.client, "HTTPConnection") as factory:
            connection = factory.return_value
            response = connection.getresponse.return_value
            response.status, response.read.return_value = 302, b"redirect"
            self.assertEqual(READERS.request_chat(18000, {"model": "local-reader"}, 1), (302, b"redirect"))
            factory.assert_called_once_with("127.0.0.1", 18000, timeout=1)
            self.assertEqual(connection.request.call_args.args[0:2], ("POST", "/v1/chat/completions"))
            self.assertEqual(connection.request.call_args.args[3], {"Content-Type": "application/json"})
            connection.close.assert_called_once()

    def test_watchdog_interrupts_even_detached_slow_response_socket(self):
        with mock.patch.object(READERS.http.client, "HTTPConnection") as factory:
            connection = factory.return_value
            peer = connection.sock
            response = connection.getresponse.return_value
            released = threading.Event()
            peer.shutdown.side_effect = lambda *_: released.set()
            def read(*_):
                connection.sock = None
                self.assertTrue(released.wait(2))
                return b"trickle"
            response.read.side_effect = read
            with self.assertRaises(TimeoutError):
                READERS.request_chat(18000, {}, 0.02)
            peer.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
