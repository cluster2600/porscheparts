# Bore95 vendor conversion: strict parity rejected

One geometry-only conversion ran through the unchanged installed
`convert-to-usd` reference and NVIDIA converter 0.2.0. It returned successfully
in 5.43 seconds. The original inspected STL and converted USD remain unchanged;
their exact hashes are bound by the [receipt](receipt.json) and the pre-run
[contract](frozen-contract.json). The raw derivative is retained privately.

The formal minimum USD reference subsequently passed eight checks. Its first
attempt was blocked because the validation preflight could not discover the
wheel's bundled `pxr` module. A separate genuine preflight exposed that existing
module directory through Python's normal startup path and established the
required component readiness. No guard or manifest was altered. The broader
validation target still lacks Asset Validator and SimReady dependencies.

**The derivative fails the frozen source-parity check.** It contains 1,804,452
triangles against 1,804,706 in the source: 254 fewer. At original STL float32
precision, the complete oriented-triangle multisets differ. Counts preserve
duplicate multiplicity, allow cyclic vertex order and preserve winding.
No fitted transform or relaxed tolerance was used.

The USD declares millimeter stage units and Z-up. It recenters mesh points with
an authored Z translation of 45.000001118 mm; the composed world bounds differ
from the source by at most 0.000001119 mm. These close bounds do not establish
identical topology or coordinates. The causes of every omitted or changed
triangle remain under investigation.

Metadata review found no authored private paths or nonempty external asset
dependencies. Internal instance references, two visual material prims and a
default kilogram stage unit are recorded separately; there are no physical
schemas or physical-property attributes. No material calibration, solver field,
head simulation or manufacturing claim follows from this conversion.
