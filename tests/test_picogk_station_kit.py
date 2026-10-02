"""Checks of the GPU and private signaling launch contract (no GPU needed)."""

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("station_kit", ROOT / "containers/picogk-station-kit/launch.py")
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


class StationKitTest(unittest.TestCase):
    def test_native_launch_uses_explicit_vulkan_ordinal_and_separate_nat_port(self):
        env = {"PUBLIC_IPADDR": "203.0.113.10", "VAST_UDP_PORT_47998": "32147", "STATION_KIT_GPU": "2"}
        args, connection = kit.command(env)
        self.assertIn("--/renderer/activeGpu=2", args)
        self.assertIn("--/renderer/multiGpu/enabled=false", args)
        self.assertIn("--/exts/omni.kit.livestream.app/primaryStream/streamPort=47998", args)
        self.assertEqual(connection["mediaPort"], 32147)
        self.assertEqual(connection["signalingServer"], "127.0.0.1")
        for changes in ({"STATION_KIT_GPU": "2;echo"}, {"PUBLIC_IPADDR": "not-an-ip"},
                        {"VAST_UDP_PORT_47998": "65536"}, {"VAST_UDP_PORT_47998": ""},
                        {"VAST_TCP_PORT_49100": "32000"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                kit.command(env | changes)


if __name__ == "__main__":
    unittest.main()
