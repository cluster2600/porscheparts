"""A synthetic STEP round trip validates only the software toolchain."""
import tempfile
from pathlib import Path
from build123d import Box, export_step, import_step

with tempfile.TemporaryDirectory() as directory:
    target = Path(directory) / "witness.step"
    assert export_step(Box(10, 20, 30), target)
    recovered = import_step(target)
    assert abs(recovered.volume - 6000) < 1e-6
    assert recovered.is_valid
print("CAD_STEP_ROUNDTRIP_PASS")
