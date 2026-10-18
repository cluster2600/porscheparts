# Measured-conductivity software witnesses completed

Separate Z and XY nonlinear steady-conduction bars pass all **109 final-field
checks per case** against a frozen, mesh-independent Kirchhoff reference. The
assumed bar is 1 × 2 × 10 mm, with 16 HEX8 cells and 68 temperature nodes, held at
23/250 °C. These are material-law software checks; no head solve was performed.

The measured means come from Willkomm et al. (2021),
[DOI 10.1088/1757-899X/1097/1/012021](https://doi.org/10.1088/1757-899X/1097/1/012021),
for a separate treated LPBF AlSi10Mg recipe. Piecewise-linear interpolation over
23–250 °C is an explicit numerical assumption, with conductivity divided by 1,000
for W/(mm·K). No CP1/HT1 transfer or head material selection is claimed.

Maximum nodal errors are **0.00229348 K (Z)** and **0.00119561 K (XY)**. Worst raw
end-power errors are **0.438664% / 0.254609%**, and raw end-power imbalances are
**0.413191% / 0.261112%**. All remain below the unchanged 1% criteria. Native powers
match independent Q1 boundary integration; weak consistent cell powers are almost
constant. Finite-mesh boundary gradients and weak cell fluxes are distinct checks.
FINAL CSVs provide the assessed powers; earlier console tables show pre-FINAL zeros.

The [selected evidence capsule](derived/engineering/material-conductivity-witness/README.md)
contains complete numerical assessments, six final CSVs, two native logs, exact
sources and explicit provenance projections. It preserves the complete original
77-file hash inventory while omitting private transport/runtime locations.
Outside-knot behavior and intermediate nonlinear/material evaluations remain
unobserved. There is no mesh-convergence, head strength, tensor orientation,
process calibration, physical correlation or manufacturing qualification.
