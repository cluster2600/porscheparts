# Conditional compliance envelope

This calculation answers a limited design question: how much can the **current
linear FE model's force-controlled compliance** change if the selected elements
receive the computed homogeneous cellular constitutive tensor? It does not
represent explicit cells, skin connections, local stresses or a new part.

Keep the same mesh, external force vector `f`, zero support displacements and
dense baseline tensor `C0`. On the free degrees of freedom, let the original
stiffness be `K0 > 0`, with the selected elements contributing `Kc`. Then
`0 <= Kc <= K0`. Let the proposed tensor obey
`eta_min*C0 <= Ccell <= eta_max*C0`, with `0 < eta_min <= eta_max <= 1`.
These are positive-semidefinite matrix inequalities, not componentwise ones.
The generalized tensor eigenvalues determine the two eta values.

For the original solution `u0 = inverse(K0)*f`, define

```text
J0 = transpose(f)*u0
q  = transpose(u0)*Kc*u0 / J0 = selected baseline strain energy / total energy
```

The same force-controlled objective is the standard matrix fractional function
`transpose(f)*inverse(K)*f`; see the
[Boyd–Vandenberghe convex optimization text](https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf).
The following envelope is derived directly for this selected-region problem:

```text
1 / (1 - (1 - eta_max)*q) <= Jnew/J0 <= 1 + (1/eta_min - 1)*q
```

For the lower bound, use `u0` as a trial displacement in the variational
expression for `Jnew`. Optimizing its scalar multiplier gives
`Jnew >= J0^2 / (transpose(u0)*Knew*u0)`. The upper constitutive inequality
bounds that denominator by `J0*(1-(1-eta_max)*q)`.

For the upper bound, put `P = inverse(sqrt(K0))*Kc*inverse(sqrt(K0))`.
Its eigenvalues lie in `[0,1]`. The lower constitutive inequality gives
`Knew >= K0-(1-eta_min)*Kc`. For each eigenvalue `lambda` of `P`,

```text
1/(1-(1-eta_min)*lambda) <= 1+(1/eta_min-1)*lambda
```

Apply this scalar chord inequality spectrally, transform back, and multiply
by `f` on both sides to obtain the stated upper compliance bound. No assumption
that the old stress is pointwise equilibrated in the continuum is needed.

The implementation is tested against **200 independently solved five-dimensional
anisotropic SPD stiffness substitutions**, plus endpoint and invalid-hypothesis
controls. The proof applies to exact arithmetic under the stated hypotheses;
the reported eigenvalues, energy fractions and plotted numbers are evaluated in
float64 and are not a formal interval certificate.

Use `bound_cellular_compliance.py --material <complete-cell-assessment.json>
--skin-sweep <frozen-sweep-assessment.json> --output <fresh-directory>`.
The input dense material must match the admitted E=107000 MPa, nu=0.31 baseline.
The conditional mass arithmetic uses the **actual computed cell solid fraction**,
which is recorded separately from the earlier 0.4 design scenario.

The result bounds compliance of this hypothetical constitutive substitution.
It does not bound maximum nodal displacement, local stress, fatigue or strength,
and does not establish mesh convergence of the carrier or create cellular CAD.
