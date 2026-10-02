"""Check the actual KiCad export against the E0 wiring contract, not a cached netlist."""
from collections import defaultdict
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET


DESIGN = Path(__file__).resolve().parents[1] / "docs/projects/993-programmable-rear-panel/electronics/kicad"


@unittest.skipUnless(shutil.which("kicad-cli"), "KiCad CLI required; no schematic validation without it")
class SchematicTests(unittest.TestCase):
    def test_erc_and_complete_pin_connectivity(self):
        with tempfile.TemporaryDirectory() as directory:
            # KiCad may create project-local files. Never write them into the checkout.
            design = Path(directory) / "kicad"
            shutil.copytree(DESIGN, design)
            schematic = design / "coupon-e0.kicad_sch"
            for command in (
                ["sch", "erc", "--severity-all", "--exit-code-violations",
                 "-o", str(design / "erc.rpt"), str(schematic)],
                ["sch", "export", "netlist", "--format", "kicadxml",
                 "-o", str(design / "netlist.xml"), str(schematic)],
            ):
                result = subprocess.run(["kicad-cli", *command], capture_output=True, text=True, timeout=60)
                report = design / "erc.rpt"
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr +
                                 (report.read_text() if report.exists() else ""))
            root = ET.parse(design / "netlist.xml")

        expected = defaultdict(set)

        def bind(net, ref, *pins):
            expected[net].update((ref, str(pin)) for pin in pins)

        values = {}
        for i in range(1, 129):
            ref = f"D{i}"
            values[ref] = "APHHS1005LSECK/J3-PF"
            bind("VLED_3V3", ref, 2)  # Anode, KiCad Device:LED convention.
            bind(f"LED_K{i:03}", ref, 1)
            bind(f"LED_K{i:03}", f"U{(i - 1) // 24 + 1}", (i - 1) % 24 + 5)
        for i in range(1, 7):
            ref = f"U{i}"
            values[ref] = "TLC5947DAP"
            for net, pins in {"GND": (1, 33), "VCC_3V3": (32,),
                              "BLANK": (2,), "SCLK": (3,), "XLAT": (30,)}.items():
                bind(net, ref, *pins)
            bind("SIN" if i == 1 else f"CHAIN_{i-1}_{i}", ref, 4)
            bind("SOUT_TEST" if i == 6 else f"CHAIN_{i}_{i+1}", ref, 29)
            bind(f"iref-{i}", ref, 31)
            bind(f"iref-{i}", f"R{i}", 1)
            bind("GND", f"R{i}", 2)
            values[f"R{i}"] = "20k / 1%"
        for pin in range(13, 29):
            bind(f"nc-U6-{pin}", "U6", pin)

        for ref, value, pins in (
            ("U7", "SN74LVC125APW", {1: "GND", 2: "MCU_SCLK", 3: "buffer-clock",
              4: "GND", 5: "MCU_SIN", 6: "buffer-data", 7: "GND", 8: "buffer-latch",
              9: "MCU_XLAT", 10: "GND", 11: "nc-U7-11", 12: "GND", 13: "VCC_3V3", 14: "VCC_3V3"}),
            ("U8", "SN74LVC1G04DBVR", {1: "nc-U8-1", 2: "DISPLAY_EN", 3: "GND", 4: "BLANK", 5: "VCC_3V3"}),
            ("J1", "3V3 LAB", {1: "VCC_3V3", 2: "GND"}),
            ("J2", "LOGIC / DK USB SEPARE", {1: "GND", 2: "MCU_SIN", 3: "MCU_SCLK",
              4: "MCU_XLAT", 5: "DISPLAY_EN", 6: "GND"}),
            ("S1", "COUPURE LED", {1: "VCC_3V3", 2: "VLED_3V3"}),
        ):
            values[ref] = value
            for pin, net in pins.items():
                bind(net, ref, pin)
        for number, value, first, second in (
            (7, "10k / 1%", "BLANK", "VCC_3V3"),
            (8, "100k / 1%", "MCU_SIN", "GND"),
            (9, "100k / 1%", "MCU_SCLK", "GND"),
            (10, "100k / 1%", "MCU_XLAT", "GND"),
            (11, "100k / 1%", "DISPLAY_EN", "GND"),
            (12, "33R", "buffer-clock", "SCLK"),
            (13, "33R", "buffer-data", "SIN"),
            (14, "33R", "buffer-latch", "XLAT"),
            (15, "1k / 1%", "VLED_3V3", "GND"),
        ):
            ref = f"R{number}"
            values[ref] = value
            bind(first, ref, 1)
            bind(second, ref, 2)
        for i in range(1, 11):
            ref = f"C{i}"
            values[ref] = "100n / X7R / 10V" if i <= 8 else "10u / X7R / 10V"
            bind("VLED_3V3" if i == 10 else "VCC_3V3", ref, 1)
            bind("GND", ref, 2)
        for i, net in enumerate(("VCC_3V3", "VLED_3V3", "GND", "SIN", "SCLK", "XLAT", "BLANK", "SOUT_TEST"), 1):
            values[f"TP{i}"] = net
            bind(net, f"TP{i}", 1)

        components = root.findall("components/comp")
        self.assertEqual(len(components), 172)
        self.assertEqual({c.get("ref"): c.findtext("value") for c in components}, values)
        # Footprints deliberately unassigned: this is a schematic, not a fabrication release.
        self.assertTrue(all(not c.findtext("footprint") for c in components))
        nets = root.findall("nets/net")
        actual = [frozenset((n.get("ref"), n.get("pin")) for n in net.findall("node")) for net in nets]
        self.assertEqual(len(nets), len(expected))
        self.assertEqual(set(actual), {frozenset(nodes) for nodes in expected.values()})
        self.assertEqual(sum(map(len, actual)), 541)
        # Pin types matter for ERC; the DBV NC and thermal pads must be represented.
        pins = {(n.get("ref"), n.get("pin")): n for net in nets for n in net.findall("node")}
        self.assertEqual(pins["U8", "1"].get("pintype"), "no_connect")
        for i in range(1, 7):
            self.assertEqual(pins[f"U{i}", "33"].get("pintype"), "power_in")
        self.assertEqual(pins["D1", "1"].get("pinfunction"), "K")
        self.assertEqual(pins["D1", "2"].get("pinfunction"), "A")


if __name__ == "__main__":
    unittest.main()
