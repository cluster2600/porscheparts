"""Independent bit-order and power-screen checks; no hardware validation."""
import csv
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOFTWARE = Path(__file__).resolve().parents[1] / "docs/projects/993-programmable-rear-panel/software"
with patch.object(sys, "path", [str(SOFTWARE), *sys.path]):
    spec = importlib.util.spec_from_file_location("rear_panel_coupon", SOFTWARE / "coupon_driver.py")
    coupon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coupon)


class CouponTests(unittest.TestCase):
    def test_walking_pixel_reaches_correct_chip_and_channel(self):
        # Model six serial 288-bit registers, rather than reversing the encoder.
        for pixel in range(128):
            frame = [0] * 128
            frame[pixel] = 255
            wire = coupon.encode_frame(frame, pwm_cap=4095)
            self.assertEqual(len(wire), 216)
            chips = [0] * 6
            for byte in wire:
                for bit_index in range(7, -1, -1):
                    carry = (byte >> bit_index) & 1
                    for chip in range(6):
                        outgoing = (chips[chip] >> 287) & 1
                        chips[chip] = ((chips[chip] << 1) | carry) & ((1 << 288) - 1)
                        carry = outgoing
            for chip in range(6):
                for channel in range(24):
                    actual = (chips[chip] >> (channel * 12)) & 4095
                    self.assertEqual(actual, 4095 if chip * 24 + channel == pixel else 0)

    def test_known_vector_cap_and_zero(self):
        frame = [255, 128] + [0] * 126
        self.assertEqual(coupon.encode_frame(frame)[-3:], bytes.fromhex("202400"))
        self.assertEqual(coupon.encode_frame([255] * 128, 0), bytes(216))
        self.assertEqual(coupon.encode_frame([255] * 128)[:24], bytes(24))
        for bad in ([0] * 127, [False] * 128, [256] * 128, [-1] * 128):
            with self.subTest(bad=bad[:2]), self.assertRaises(ValueError):
                coupon.encode_frame(bad)
        for cap in (True, -1, 4096, 1.5):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                coupon.encode_frame([0] * 128, cap)

    def test_faulted_simulator_produces_zero_wire_data(self):
        sim = coupon.panel_simulator
        panel = sim.Panel(clock=lambda: 0)
        panel.connect(authenticated=True)
        sim.upload(panel, sim.demo_document())
        panel.arm_local()
        panel.play()
        self.assertTrue(any(coupon.encode_frame(panel.render())))
        panel.fault()
        self.assertEqual(coupon.encode_frame(panel.render()), bytes(216))

    def test_channel_map_and_pitch_are_independent_of_package(self):
        for pitch in (2.5, 4):
            rows = list(coupon.channel_map(pitch))
            self.assertEqual(len({(r["driver"], r["output"]) for r in rows}), 128)
            self.assertEqual(rows[0]["dap_pin"], 5)
            self.assertEqual((rows[-1]["driver"], rows[-1]["output"], rows[-1]["dap_pin"]), ("U6", 7, 12))
            self.assertEqual((rows[-1]["center_x_mm"], rows[-1]["center_y_mm"]), (15 * pitch, 7 * pitch))
        with self.assertRaises(ValueError):
            list(coupon.channel_map(1))

    def test_power_corners_and_rejection_of_unsafe_assumptions(self):
        power = coupon.estimate()
        self.assertAlmostEqual(power["led_nominal_ma"], 2.46)
        self.assertAlmostEqual(power["all_leds_peak_ma"], 346.368)
        self.assertAlmostEqual(power["headroom_min_v"], 0.901)
        self.assertAlmostEqual(power["spi_shift_ms_at_1mhz"], 1.728)
        self.assertGreater(power["coupon_source_peak_ma"], 620)
        self.assertLess(power["coupon_source_peak_ma"], 650)
        for inputs in ({"supply_v": 12}, {"supply_v": float("nan")},
                       {"rref_ohm": float("inf")}, {"rref_ohm": True},
                       {"rref_ohm": 1000}, {"rref_ohm": 24900},
                       {"rref_ohm": 15000}, {"vf_max_v": 3.0},
                       {"vf_min_v": 2.5, "vf_max_v": 2.0}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                coupon.estimate(**inputs)

    def test_artifacts_match_document_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "coupon"
            coupon.write_outputs(destination, coupon.panel_simulator.demo_document())
            with (destination / "channel-map.csv").open() as source:
                self.assertEqual(len(list(csv.DictReader(source))), 128)
            frames = (destination / "frames-spi.hex").read_text().splitlines()
            self.assertEqual([len(bytes.fromhex(frame)) for frame in frames], [216, 216])
            self.assertEqual(json.loads((destination / "estimate.json").read_text())["frame_durations_ms"], [200, 200])
            with self.assertRaises(FileExistsError):
                coupon.write_outputs(destination, coupon.panel_simulator.demo_document())
            doc = {"version": 1, "width": 1, "height": 1, "format": "mono8",
                   "frames": [{"duration_ms": 100, "pixels": [0]}]}
            with self.assertRaises(ValueError):
                coupon.write_outputs(Path(temporary) / "invalid", doc)
            self.assertFalse((Path(temporary) / "invalid").exists())


if __name__ == "__main__":
    unittest.main()
