"""Host-only checks: no BLE, hardware or manufacturing claims."""
import copy
from decimal import Decimal
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / "docs/projects/993-programmable-rear-panel"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "software" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sim = load("panel_simulator")
cost = load("cost_model")


class RearPanelTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.panel = sim.Panel(clock=lambda: self.now)
        self.document = sim.demo_document()

    def ready(self):
        self.panel.connect(authenticated=True)
        sim.upload(self.panel, self.document)

    def test_authentication_and_local_arm_required(self):
        with self.assertRaises(PermissionError):
            self.panel.connect()
        with self.assertRaises(PermissionError):
            sim.upload(self.panel, self.document)
        self.ready()
        with self.assertRaises(PermissionError):
            self.panel.play()
        self.panel.arm_local()
        self.panel.play()
        self.assertEqual(self.panel.render(), bytes(self.document["frames"][0]["pixels"]))
        self.now = 0.21
        self.assertEqual(self.panel.render(), bytes(self.document["frames"][1]["pixels"]))

    def test_watchdog_disconnect_and_reconnect_are_dark(self):
        self.ready()
        self.panel.arm_local()
        self.panel.play()
        self.now = 2.0
        self.assertFalse(any(self.panel.render()))
        with self.assertRaises(PermissionError):
            self.panel.heartbeat()
        self.panel.connect(authenticated=True)
        with self.assertRaises(PermissionError):
            self.panel.play()
        self.panel.arm_local()
        self.panel.play()
        self.panel.fault()
        self.assertFalse(any(self.panel.render()))

    def test_bad_transfer_preserves_previous_content(self):
        self.ready()
        previous = self.panel.active
        width, height, durations, payload = sim.pack(self.document)
        for incomplete in (True, False):
            self.panel.begin(width, height, durations, len(payload), "0" * 64)
            if not incomplete:
                for offset in range(0, len(payload), sim.CHUNK_BYTES):
                    self.panel.data(offset, payload[offset:offset + sim.CHUNK_BYTES])
            with self.assertRaises(ValueError):
                self.panel.commit()
            self.assertEqual(previous, self.panel.active)
            self.assertFalse(any(self.panel.render()))

    def test_invalid_offsets_overflow_and_replay_abandon_transfer(self):
        self.ready()
        width, height, durations, payload = sim.pack(self.document)
        digest = hashlib.sha256(payload).hexdigest()
        for offset, chunk in [(1, b"a"), (False, b"a"), (0, b""), (0, b"a" * 129)]:
            with self.subTest(offset=offset, size=len(chunk)):
                self.panel.begin(width, height, durations, len(payload), digest)
                with self.assertRaises(ValueError):
                    self.panel.data(offset, chunk)
                self.assertIsNone(self.panel.pending)
        self.panel.begin(1, 1, [100], 1, hashlib.sha256(b"a").hexdigest())
        with self.assertRaises(ValueError):
            self.panel.data(0, b"ab")
        self.panel.begin(width, height, durations, len(payload), digest)
        self.panel.data(0, payload[:128])
        with self.assertRaises(ValueError):
            self.panel.data(0, payload[:128])
        self.assertIsNone(self.panel.pending)

    def test_document_limits(self):
        cases = []
        for key, value in [("version", True), ("width", 0), ("height", 4097), ("format", "rgb"), ("frames", [])]:
            doc = copy.deepcopy(self.document)
            doc[key] = value
            cases.append(doc)
        for key, value in [("duration_ms", 99), ("duration_ms", 10001), ("pixels", [0]), ("pixels", [True] * 128), ("pixels", [256] * 128)]:
            doc = copy.deepcopy(self.document)
            doc["frames"][0][key] = value
            cases.append(doc)
        for doc in cases:
            with self.subTest(doc=str(doc)[:90]), self.assertRaises(ValueError):
                sim.pack(doc)

    def test_metadata_cannot_allocate_unbounded_buffer(self):
        self.ready()
        for arguments in [(4096, 4096, [100], 1, "0" * 64),
                          (1, 1, [100] * 61, 61, "0" * 64),
                          (1, 1, [100], 1, "z" * 64),
                          (1, 1, [100], 300000, "0" * 64)]:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                self.panel.begin(*arguments)
            self.assertIsNone(self.panel.pending)
            self.assertFalse(self.panel.armed)

    def test_stop_aborts_transfer(self):
        self.ready()
        width, height, durations, payload = sim.pack(self.document)
        self.panel.begin(width, height, durations, len(payload), hashlib.sha256(payload).hexdigest())
        self.panel.data(0, payload[:128])
        self.panel.stop()
        with self.assertRaises(ValueError):
            self.panel.commit()

    def test_gif_conversion_and_limits_if_pillow_available(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("optional host GIF decoder Pillow not installed")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coupon.gif"
            first = Image.new("RGB", (32, 8), "white")
            first.save(path, save_all=True, append_images=[Image.new("RGB", (32, 8), "black")], duration=[50, 200])
            doc = sim.gif_document(path)
            self.assertEqual(len(doc["frames"]), 2)
            self.assertEqual(doc["frames"][0]["duration_ms"], 100)
            self.assertEqual(len(doc["frames"][0]["pixels"]), 128)
            self.assertEqual(doc["frames"][0]["pixels"][:16], [0] * 16)  # letterbox
            first.save(path, save_all=True, append_images=[Image.new("RGB", (32, 8), (i, i, i)) for i in range(60)], duration=100)
            with self.assertRaises(ValueError):
                sim.gif_document(path)
            Image.new("L", (1001, 1000)).save(path)
            with self.assertRaises(ValueError):
                sim.gif_document(path)

    def test_budget_and_origin_are_consistent(self):
        totals = cost.costs(ROOT / "budget.csv")
        self.assertEqual(totals["unit_100"], totals["historical_100"])
        self.assertEqual(totals["unit_1000"], totals["historical_1000"])
        self.assertEqual(totals["candidate_250"], [Decimal(250), Decimal(250)])
        swiss, total, excluded, percent = cost.origin(ROOT / "swissness.csv")
        self.assertEqual((swiss, total, excluded), (115, 205, 45))
        self.assertEqual(total + excluded, totals["candidate_250"][0])
        self.assertLess(percent, 60)
        self.assertGreater(cost.origin(ROOT / "swissness.csv", "20700", units=1000)[3], 60)
        self.assertLess(cost.origin(ROOT / "swissness.csv", "20700", units=2000)[3], 60)
        self.assertLess(cost.origin(ROOT / "swissness.csv", "20700", "20700", units=1000)[3], 60)
        for value in ("NaN", "Infinity", "-1", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cost.amount(value)
        with self.assertRaises(ValueError):
            cost.origin(ROOT / "swissness.csv", units=0)

    def test_unknown_origin_treatment_and_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.csv"
            for body in ["x,10,CH,mistake", "x,10,XX,include", "x,10,CH,include\nx,10,CH,include"]:
                path.write_text("item,cost_chf,origin,treatment\n" + body + "\n")
                with self.assertRaises(ValueError):
                    cost.origin(path)


if __name__ == "__main__":
    unittest.main()
