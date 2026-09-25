# Local scan of a Porsche 917 engine with cylinders

## Status

- Level: `F0_reference`.
- Provenance: commercial product "Porsche 917 Engine Case Scan" from Wolfe
  Classics, cross-checked against the file name and its local digest.
- Identification: the seller declares a 917 engine case with cylinders, but
  the exact variant remains unknown.
- License: open reuse confirmed by the project owner, exact text not archived;
  redistribution right not displayed and publication of the raw file blocked.
- 993 or 935 compatibility: not demonstrated.

The file found in iCloud Drive matches the
[Wolfe Classics listing](https://www.wolfeclassics.com/shop/p/porsche-917-engine-case-scan),
which describes it as a scan accurate to 0.5 mm of a 917 engine case with the
cylinders fitted, acquired during a reseal. The local name is
`917+engine+case+w+cyl+0.5mm.obj` and its digest is the one recorded below.
This match establishes the commercial provenance, not the exact variant, the
OBJ unit, independent metrological accuracy or the internal geometry.

## Digest and inspection

```text
SHA-256 428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae
```

| Property | Result |
|---|---:|
| Size | 107,128,223 bytes |
| Vertices | 1,282,880 |
| Triangles | 2,465,879 |
| Topological components | 3 |
| Envelope | 1002.175 × 768.275 × 739.765 OBJ units |
| Open edges | 101,809 |
| Non-manifold edges | 0 |
| Zero-area faces | 2 |
| Watertight | no |

The three components contain about 2,320,604, 141,542 and 3,747 triangles
respectively. The first groups most of the case and the cylinders; the other
two will have to be identified visually before any deletion.

## Possible contribution to the project

This scan can help develop and verify the generic methods for:

- segmentation of a large engine assembly;
- repeated detection of cylinder axes and center distances;
- registration of cylinder banks and gasket planes;
- construction of collision envelopes;
- comparison of air-cooling architectures.

It must not be used directly to manufacture a 993 part. The interfaces,
materials and loads of a 917 engine differ, and no equivalence is currently
demonstrated.

## Derived results

The F0/F1 chain under `twins/reference-917-engine/` has now produced:

- a 600,000-triangle working mesh, p95 deviation 0.107 OBJ unit;
- two banks of six visible openings, mean diameter 86.63 units;
- a regular pitch close to 118 and a central gap close to 173;
- a parametric twelve-cylinder envelope STEP;
- two watertight display STLs at the candidate scales 1:4 and 1:8;
- an external CFD skin and an OpenFOAM case whose solver remains blocked by two
  failing mesh quality checks.

All these results keep identity and scale at unconfirmed status.

## Data to recover

1. exact license text and redistribution right;
2. metrology report demonstrating the declared 0.5 mm accuracy;
3. native unit of the OBJ;
4. 917 engine variant and scan configuration;
5. three independent physical dimensions on the same surfaces of the scan.

The associated structured record is
`catalog/sources/src-local-917-engine-case-cylinders-scan.json`.
