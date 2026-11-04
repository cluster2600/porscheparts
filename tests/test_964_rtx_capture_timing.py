"""Exercise the capture adapter's time contract without claiming GPU execution."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "capture_964_timing", ROOT / "twins/964-chassis/monocoque/omniverse/capture_rtx.py"
)
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


@unittest.skipIf(np is None, "NumPy is required for the mocked frame contract")
class RTXTimingTests(unittest.TestCase):
    def test_orbit_evaluates_all_120_samples_in_seconds(self):
        # The qualified stage authors timecodes 0..119 at 24 timecodes/second.
        # OVRTX consumes seconds, including its synchronous stage-time update.
        pixels = np.zeros((1000, 1600, 4), dtype=np.uint8)
        pixels[:, 800:, :] = 255
        mapping = MagicMock()
        mapping.__enter__.return_value = pixels
        variable = types.SimpleNamespace(map=MagicMock(return_value=mapping))
        frame = types.SimpleNamespace(render_vars={"LdrColor": variable})
        renderer = MagicMock()
        renderer.step.side_effect = lambda *, render_products, delta_time: {
            product: types.SimpleNamespace(frames=[frame]) for product in render_products
        }
        ovrtx = types.SimpleNamespace(
            __version__="0.3.0", Renderer=MagicMock(return_value=renderer),
            RendererConfig=MagicMock(), Device=types.SimpleNamespace(CPU="mock-cpu"),
        )
        image = types.SimpleNamespace(fromarray=lambda _: types.SimpleNamespace(
            save=lambda path: Path(path).write_bytes(b"mock frame; not a rendered image")
        ))

        def command(args, **kwargs):
            if args[0] == "nvidia-smi":
                return types.SimpleNamespace(stdout="MOCK GPU, MOCK DRIVER, MOCK UUID")
            self.assertEqual(args[0], "ffmpeg")
            Path(args[-1]).write_bytes(b"mock encoder; not a video")
            return types.SimpleNamespace(returncode=0)

        with tempfile.TemporaryDirectory() as temp, patch.dict(
            sys.modules, {"ovrtx": ovrtx, "PIL": types.SimpleNamespace(Image=image)}
        ), patch.object(CAPTURE.subprocess, "run", side_effect=command):
            output = Path(temp) / "output"
            CAPTURE.capture(ROOT / "twins/964-chassis/monocoque/omniverse/bundle-001", output)
            times = [call.args[0] for call in renderer.update_from_usd_time.call_args_list]
            self.assertEqual(len(times), 123)
            self.assertEqual(times[:2], [0.0, 0.0])
            self.assertEqual(times[-1], 0.0)
            self.assertEqual(times[2:122], [index / 24.0 for index in range(120)])
            # In the broken adapter, 115 updates were already beyond the animation.
            self.assertAlmostEqual(times[121], 119.0 / 24.0)
            report = json.loads((output / "capture.json").read_text())
            self.assertEqual(report["video_frames"], 120)
            self.assertEqual(report["video_fps"], 24)


if __name__ == "__main__":
    unittest.main()
