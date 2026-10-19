# Current24af — all20 declared linear-static cases

SOURCE-only numerical summary. All20 cases are formally closed by ROOT `dc26accac6af16ba323b0e196555c681de95aeffff1d3fdb29c9fd12e145936c`; no convergence or strength qualification is assigned.

| Load | Rigid VM (MPa) | Spring VM (MPa) | Rigid U (mm) | Spring U (mm) |
|---|---:|---:|---:|---:|
| gravity | 166.100232 | 546.985752 | 0.889796 | 7.749252 |
| shock | 332.200388 | 1093.971428 | 1.779592 | 15.498502 |
| longitudinal | 84.870173 | 84.714350 | 0.203914 | 1.425444 |
| lateral | 15.813782 | 16.119342 | 0.014525 | 1.012310 |
| stock_torque_reference | 386.192919 | 514.785106 | 0.801609 | 1.353726 |
| combined | 602.291437 | 1564.897510 | 2.701142 | 16.425420 |
| reverse_torque_combined | 737.944458 | 1904.280173 | 2.701010 | 16.448780 |
| roll | 981.024401 | 988.182154 | 1.820988 | 83.227529 |
| pitch | 607.896223 | 810.309890 | 1.261792 | 2.130865 |
| yaw | 160.625780 | 130.791302 | 0.145573 | 1.588065 |

Largest stress: **1904.28017292 MPa**, reverse-torque combined / spring. Every complete original tie remains in `data.json`.
Largest movement: **83.2275286597 mm**, roll / spring. This all-node result remains visible without clipping or a green acceptance label.

The two heatmaps use separate numerical scales for VM and U. They compare actual case maxima, not stress allowables. Original vectors, both support conditions and every whole result, independent energy object and global tie report remain linked by exact SHA. No old geometry field is used.
