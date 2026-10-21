# Fixed linear face quality: definition and exact necessary screen

**The recovered 8 GiB checkpoint cannot support a linear tetrahedral mesh with
every element's SICN ≥ 0.1 while its surface triangles remain fixed.** One
specific face proves this with exact rational arithmetic. This conclusion
applies only to the
[bound checkpoint](derived/engineering/analysis-envelope-trial-002.json), not
to a later remeshed surface. It adds no strength or thermal evidence.

The metric is Gmsh 4.15.2 `minSICN`, the signed normalized inverse Frobenius
condition number of the ideal-reference Jacobian. For a positive orientation,
`q_d = d / (||J||_F ||J^-1||_F)`. For a triangle, use its 3×2 full-column-rank
Jacobian and pseudoinverse. The reference face is equilateral. The
[source-reference record](source/gmsh_sicn_reference.json) binds the official
[4.15.2 source archive](https://gmsh.info/src/gmsh-4.15.2-source.tgz), its digest,
file digests and these call-chain locations:

- `src/common/gmsh.cpp:2423` dispatches `minSICN` to the element method.
- `src/geo/MElement.h:259` and `MElement.cpp:387` use the signed condition-number range.
- `src/numeric/CondNumBasis.h:46` uses ideal-reference shape gradients.
- `src/numeric/CondNumBasis.cpp:28–96` defines the normalized 2D and 3D formulas.

This is not the differently named `minICNMeasure` implementation in
`qualityMeasuresJacobian.cpp`, whose 3D formula is mean-ratio based. The
quantities are not substituted for one another. For linear triangles and
tetrahedra the Jacobian is constant; one native value covers the entire
element. The recovery audited **all 1,753,570 fixed linear faces**, using
their exact float64 indexed import and all element tags. No facet subset or
vertex-only quality sample was used.

To derive a necessary face restriction, rotate orthonormal physical and
reference bases so that the tetrahedron's Jacobian has the form

```text
    [ a  0  x ]
J = [ 0  b  y ],    a,b,z > 0.
    [ 0  0  z ]
```

The first two columns restrict the mapping to its fixed reference face.
Write `A=a²+b²` and `B=1/a²+1/b²`. Then `q₂=2/sqrt(A B)`.
The full matrix and inverse satisfy `||J||²_F ≥ A` and
`||J^-1||²_F ≥ B`, hence

```text
q₃ ≤ 3/sqrt(A B) = (3/2) q₂.
```

A sharper bound follows from
`||J||²_F ||J^-1||²_F ≥ (A+z²)(B+1/z²) ≥ (sqrt(A B)+1)²`, giving
`q₃ ≤ 3q₂/(2+q₂)`. The earlier numerical screen used this sharper expression
and reported 938 incompatible fixed faces. That count uses native floating
values and is a diagnostic, not an interval-arithmetic certificate. A good
face does not guarantee a good tetrahedron; the restriction is necessary only.

The exact rejection uses the looser bound. For triangle edges, let
`C=||cross(b-a,c-a)||²` and `S` be the sum of the three squared edge lengths.
Equilateral-reference normalization gives `q₂²=12 C/S²`, so
`q₃² ≤ 27 C/S²`. The rational inequality

```text
2700 C < S²
```

therefore proves that no positive linear tetrahedron retaining that fixed
face can reach `q₃=0.1`. No square root, rounded native SICN value or tolerance
is used in this decision.

The [exact certificate](derived/engineering/fixed-face-exact-certificate.json)
records face index 443972, its node indices, original NPZ digest, coordinate
byte digest, binary64 hexadecimal values and every numerator/denominator.
Its coordinates in millimetres are:

```text
(-75.75, -3.27991330095756e-7, 13)
(-75.25,  6.55982660191512e-7, 13)
(-75.75,  3.27991330095756e-7, 13)
```

`Fraction.from_float` treats those supplied binary64 numbers exactly. The
[certificate source](source/certify_fixed_face.py) and three focused tests
verify the strict rational check, a regular right-isosceles counterexample,
a known binary sliver and power-of-two scale invariance. The exactness is
about these study coordinates, not measured Porsche dimensions.

[Native regular/sliver witnesses](derived/engineering/sicn-regular-sliver-fixtures.json)
confirm the same normalization: a regular tetrahedron has `q₂=q₃=1`; an apex
compressed by 0.001 retains `q₂=1` but has `q₃=0.002121317691913124`, matching
the analytic inverse-Frobenius expression. The original stricter multi-case
[floating fixture failed](derived/engineering/sicn-failed-float-fixture.json)
at an extreme face: its native and analytic `q₂` differed by approximately
6.08×10⁻¹³. The failed fixture and its unchanged tolerances remain preserved.
They were not relabelled as a pass, and the head's SICN threshold was not
relaxed. The separate rational proof makes that floating discrepancy
irrelevant to this one-face impossibility result.
