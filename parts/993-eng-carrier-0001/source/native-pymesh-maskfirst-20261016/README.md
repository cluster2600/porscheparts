# Mask first, local cutter, single exact tree

This variant computes `(chain ∩ mask) \ (part ∩ B)` in a single Epeck
CSGTree. The box B strictly enclosing chain reuses exactly the
`nextafter` construction and the guards of the previous clip version.
The identity with `(chain ∩ mask) \ part` follows from `chain ⊂ B`.
No intermediate result is converted to doubles.

```sh
python3 parts/993-eng-carrier-0001/source/native-pymesh-maskfirst-20261016/setup.py \
  /chemin/neuf/maskfirst --pymesh-runtime /chemin/pymesh
python3 /chemin/neuf/maskfirst/run.py CHAIN.npz MASK.npz PART.npz \
  /chemin/neuf/maskfirst/jobs/essai-001 --timeout-seconds 1200
```

(`/chemin/neuf` = a new, empty path; `/chemin/pymesh` = the PyMesh path.)

The leaves are ordered `chain, mask, part, clip_bbox`. The source attributes
refer to this order, recorded with the face counts. The existing PyMesh
rootfs is explicit, verified and used read-only. Image, Python modules,
libraries and sources are hashed before/after. Explicit budgets of 600 or
1,200 s, two CPUs, 4 GiB, no swap and no network.

The executed witness contains two stacked prisms of height 10 and 20 mm,
then a Z8–Z12 subtraction. After export, snap51/5 and exact measurement:
3,200 mm³, two closed/manifold/oriented components, presence of Z4/Z16 and
absence of Z9/Z10/Z11. The 15 libigl warnings are point contacts within
the already shared simplex, verified by the pinned rational classifier;
no additional intersection. The raw results remain preserved.

This witness establishes the software behaviour of this expression. Every real
output must still pass its own exact, topological and drift checks. This
variant changes neither the snap nor its bound.

Engine/licences: same `pymesh/pymesh` image and same native binary as
`native-pymesh-20261016`, identifiers verified by the bootstrap. The installed
C++ commit, which the image does not expose, remains unknown.
