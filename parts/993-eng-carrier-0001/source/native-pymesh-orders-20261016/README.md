# Explicit historical PyMesh orders

This adapter preserves the two admitted expression trees, without converting an
intermediate exact mesh to double. It uses the immutable PyMesh image/rootfs and
native module pinned by `../native-pymesh-20261016`; it does not install or modify
the base runtime. PyMesh reports 0.3 (MPL-2.0); its bundled libigl/CGAL Boolean
implementation has copyleft dependencies. The exact installed upstream C++
commit is unavailable: image, archive, native module, Python source and runtime
files are identified instead. See the base directory for the upstream sources
and licence material.

```sh
python3 setup.py NEW_PREFIX --pymesh-runtime IMMUTABLE_PYMESH_PREFIX
python3 NEW_PREFIX/run.py CHAIN.npz MASK.npz PART.npz NEW_PREFIX/jobs/NEW_JOB --timeout-seconds 600 --order mask-first
python3 NEW_PREFIX/run.py CHAIN.npz MASK.npz PART.npz NEW_PREFIX/jobs/OTHER_NEW_JOB --timeout-seconds 600 --order difference-first
```

`mask-first` means `(chain ∩ mask) \ part`, with leaf roles chain/mask/part.
`difference-first` means `(chain \ part) ∩ mask`, with roles chain/part/mask.
The adapter records the order and copies the actual runner/worker before work.
The child is bounded to two CPUs, 4 GiB, no swap, no network and 600 or 1200 s;
the owned systemd scope is checked inactive in the receipt. Output still needs
the separate snap, exact-distance, topology and contact gates.

Both software witnesses were executed natively: two overlapping closed positive
triangular prisms of heights 10/20, a containing mask, and subtraction of Z8–12.
Each expression gives 3200 mm³, no open/nonmanifold edges and the expected five
occupancy probes. The triangulations differ, as expected. The linked receipts
are retained under `work/carrier-pymesh-orders-20261016/software-001` locally;
`reproduction-results.json` contains their hashes. No carrier was replayed.
