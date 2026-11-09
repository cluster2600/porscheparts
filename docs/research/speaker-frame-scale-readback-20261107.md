# Speaker-frame coordinate readback

Issue #1 follow-up, 2026-11-07. **Scale unresolved; excluded from use.**

The [primary page](https://www.thingiverse.com/thing:6901857) identifies
Garagefab and explicitly links [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Its [Files tab](https://www.thingiverse.com/thing:6901857/files) lists the two
STLs below. The creator describes 993 HiFi frames for 4x6 speakers and warns
about automatic scaling, without supplying a numerical scale or calibrated datum.

Both files were downloaded through the ordinary browser after the licence read.
They remain outside Git in the private artifact store; no mesh is committed.

| File | Bytes | Triangles | SHA-256 |
|---|---:|---:|---|
| `speaker-grill-left.stl` | 1,083,784 | 21,674 | `4ca9160fd298e1ab30076f1f4b930daac78f529abfb6fc84569dbd8ea8f12e1f` |
| `speaker-grill-right.stl` | 1,083,484 | 21,668 | `e04bf920d6b83f01a87e5631c3f742cd665863c6b654af5099da5a27249389c8` |

A direct little-endian binary STL read checked exact byte length and finite
vertex coordinates. A separate Trimesh 5.1.0 read with `process=False` agreed
within 1e-9 coordinate units. Both files have raw X/Y/Z extents:

`[2152.0400390625, 126.98751098662615, 1437.9400634765625]`

| File | Raw minimum X/Y/Z | Raw maximum X/Y/Z |
|---|---|---|
| Left | `[-1118.9200439453125, -0.007500000298023224, -737.219970703125]` | `[1033.1199951171875, 126.98001098632812, 700.7200927734375]` |
| Right | `[1506.860107421875, -0.007500000298023224, -737.219970703125]` | `[3658.900146484375, 126.98001098632812, 700.7200927734375]` |

The binary headers identify STLB ATF 13.14.0.145 and a colour, but no unit.
These are coordinate measurements, not millimetres or a physical-frame inspection.
The archive's previously reported 2152.040 × 1437.940 × 253.976 mm envelope
is not reproduced as the X/Y/Z extent of either downloaded file. Its two larger
numbers match two raw extents after reordering, while its third differs. The
archive's exact files, transform and aggregation are not established here.

The earlier proposed division by ten is therefore still an unsupported hypothesis.
Do not rescale to a print bed, infer a unit from a printer model, or transfer the
author's material/fit claims into a qualified part. A source-backed unit/scale
and independent same-variant mounting/interface measurements remain necessary.
No geometry repair, manufacturing or fitment approval follows from this readback.

## Reproduce the raw-coordinate check

Place the two licensed originals in a private directory and run the following
from that directory using the project's dependency environment (Trimesh 5.1.0).
The checks reject changed files and compare independent readers without scaling
or mesh processing.

```python
from pathlib import Path
import hashlib
import math
import struct
import trimesh

expected = {
    "speaker-grill-left.stl": "4ca9160fd298e1ab30076f1f4b930daac78f529abfb6fc84569dbd8ea8f12e1f",
    "speaker-grill-right.stl": "e04bf920d6b83f01a87e5631c3f742cd665863c6b654af5099da5a27249389c8",
}
for name, sha in expected.items():
    raw = Path(name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha
    count = struct.unpack_from("<I", raw, 80)[0]
    assert len(raw) == 84 + 50 * count
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for face in range(count):
        vertices = struct.unpack_from("<12fH", raw, 84 + 50 * face)[3:12]
        assert all(math.isfinite(value) for value in vertices)
        for axis in range(3):
            lo[axis] = min(lo[axis], *vertices[axis::3])
            hi[axis] = max(hi[axis], *vertices[axis::3])
    extent = [hi[axis] - lo[axis] for axis in range(3)]
    other = trimesh.load(name, process=False).extents
    assert all(abs(a - b) < 1e-9 for a, b in zip(extent, other))
    print(name, count, lo, hi, extent)
```
