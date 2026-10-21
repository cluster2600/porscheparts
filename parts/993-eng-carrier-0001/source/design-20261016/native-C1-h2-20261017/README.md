# C1 local h/2 refinement and two complete native results

This extension depends on the sibling `native-C1-20261017` capsule. It reuses its 186 members and adds only the new paths for C1 refinement, the paired serialized-volume diagnostic, h/2 qualification and the two CCX cases. Existing files are never overwritten. BREP a42e remains the master; the STEP exchange refusals and the original h/2 volume refusal remain unchanged historical evidence.

| Case | Coarse → h/2 Umax (mm) | Coarse → h/2 VMmax (MPa) | h/2 relative energy error |
|---|---:|---:|---:|
| Rigid supports | 2.794104095 → 2.794565820 | 907.278068 → 996.757555 | 8.55524e-9 |
| K1000 per eye and axis | 18.171491077 → 18.174421153 | 2663.075178 → 2996.496111 | 2.50912e-8 |

Both actual cases closed with RC0 and their owned containers removed. Complete loads and supports equal those of the coarse C1 cases. The existing candidate has 168,248 nodes and 90,766 C3D10 elements. The complete measurement gives h = 0.46689542695319447 mm in both target boxes (target 0.4668954269534402 mm), with all 3,210 protected BC facets and six node rosters preserved. Its distinct volume authority is binary64 equality of both serialized meshes under the same operator, with zero tolerance; the original refused guard is not relabelled.

Both h/2 global maxima are at element 90371/IP2, reference XYZ [82.162332198, -14.460778140, 12.883191321] mm. VM increased by 9.86% and 12.52%; stress convergence is not established. All peaks are retained, including C2. The optional native diagnostic concerns the **coarse** 84037/IP1 peak: its local normal chord is neither a global minimum thickness nor a classification of the new h/2 peak.

Each new ZIP must remain strictly below 100 MB. They preserve complete actual DAT/FRD/NPZ/INP outputs, sources and receipts. The 186 C1 members, its 577f surface and coarse raw fields are not duplicated in these ZIPs. Installed runtimes are not copied. Unchanged b716 energy, 9623 peak and 07 BREP-binding sources are read from the SHA-bound C1 dependency.

## Verify and restore

```sh
python3 -I -B restore.py verify --manifest-sha256 REVIEWED_HASH
python3 -I -B restore.py restore FRESH_DIRECTORY --manifest-sha256 REVIEWED_HASH
```

The sibling C1 capsule is the default dependency. `--base-capsule PATH` supports relocation without symlinks. Its manifest, complete durable inventory, sources and ZIPs are verified before new members are created exclusively. Available storage is checked before materializing one complete restoration, approximately 818 MB of raw data.

The separately authorized analysis replay recalculates only the two energy audits and two peak reports using unchanged sources, the C1-pinned NumPy runtime, cwd `/`, nice 10 and one BLAS thread. It requires equality of all four complete objects **and their JSON bytes**, then verifies every restored original. It runs no CCX, Gmsh, refinement or CAD kernel. A real replay receipt is delivered separately after execution; source preparation alone does not prove that replay.

The model retains the same BREP, E = 107,000 MPa, nu = 0.31, Fz = -4,000 N, My = 850,000 Nmm, and total spring stiffness of 1,000 N/mm per eye and axis. Loads and supports are hypotheses within a linear model. No material allowable, physical validation or manufacturing qualification is added.
