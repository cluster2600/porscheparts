# GO-MELT boundary and material unit controls

On 6 November 2026, the unchanged GO-MELT CPU kernel passed fresh analytical
controls through its actual property and boundary functions. The convection
conversion raised in the [earlier carrier review](carrier-interface-20261028/NEW-TOOLS-ASSESSMENT.md)
is now checked: its input is **W/mm²/K**, converted internally to W/m²/K and
back to W/mm² before integration over the mesh surface. No upstream correction
was necessary. Passing an SI coefficient directly into this input would instead
introduce a factor of one million.

These are synthetic one-element controls. They do not supply the carrier's
thermal material laws, laser settings, build simulation or temperature transfer.

## Results

Both test domains have one hexahedral element and eight nodes, coordinates in
millimetres, and height 5 mm. Top-face areas are 1 and 6 mm². The surface is at
400 K and ambient at 300 K. Evaporation is disabled. Convection and radiation
are exercised separately through `SetupProperties` and `computeConvRadBC`.
Positive flux enters the domain, so the cooling results are negative.

| Control | Area, mm² | Expected total heat flow, W | Observed total heat flow, W |
|---|---:|---:|---:|
| Convection, h = 14.73e-6 W/mm²/K | 1 | -0.001473 | -0.001473 |
| Convection, same h | 6 | -0.008838 | -0.008838 |
| Radiation, emissivity = 0.6 | 1 | -0.00059535 | -0.00059535 |
| Radiation, same emissivity | 6 | -0.00357210 | -0.00357210 |

The independent expressions are `h × (T_ambient − T_surface) × area` and
`5.67e-8 × emissivity × (T_ambient⁴ − T_surface⁴) × 1e-6 × area`.
All four comparisons pass relative tolerance 1e-12 and absolute tolerance
1e-15 W; the [receipt](carrier-go-melt-units-20261106/evidence/unit-controls.json)
preserves the full floating-point values.

A separate `computeStateProperties` control explicitly supplies the existing
study density of 4.42e-6 kg/mm³, **synthetic constant** heat capacity
500 J/kg/K and conductivity 10 W/m/K at 300 K in the solid state. It returns
0.00221 J/mm³/K and 0.010 W/mm/K, respectively, as expected. The synthetic
capacity and conductivity are test fixtures, not titanium property data.

The [original kernel witness](carrier-go-melt-units-20261106/evidence/kernel-control.json)
also passes again: shape-function partition, unit volume, constant-temperature
equilibrium, uniform heating and source-free conservation. Heating gives
300.02000000000004 against 300.02. Both actual processes exited with code zero.
The published boundary test replay reproduces all values from the initial
inline check exactly.

## Provenance and reproduction

[GO-MELT](https://github.com/JLnorthwestern/GO-MELT) is MIT licensed. The installed
source is unchanged at commit `7dafdd8593711cf8ac6ccb18a1f475744610ea3d`.
Its `go_melt/computeFunctions.py` SHA-256 is
`cf1889dfb41e11591e4245a9199262e66ae972e3a75e2c00baddd30f32851176`.
Relevant functions are `SetupProperties` (line 267), `computeConvRadBC`
(line 2208) and `computeStateProperties` (line 2567) in that revision.

The isolated CPU/x64 runtime uses JAX and jaxlib 0.4.16, NumPy 1.24.1,
SciPy 1.9.0, ml-dtypes 0.2.0, pyevtk 1.6.0, dill 0.3.7 and opt-einsum 3.4.0.
The existing [runtime runbook](../architecture/usd-brep-lpbf.md) and
[dependency lock](../../benchmarks/go-melt/requirements.lock.txt) remain authoritative.

Executed commands, with 60 CPU-second limits and one BLAS/OpenMP thread:

```sh
(ulimit -t 60
 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 make go-melt-smoke \
   GO_MELT_OUTPUT=work/carrier-go-melt-units-20261106-001)

(ulimit -t 60
 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 "$HOME/Developer/GO-MELT/.venv/bin/python" \
   docs/reports/carrier-go-melt-units-20261106/evidence/check_units.py \
   --source "$HOME/Developer/GO-MELT" \
   --output work/carrier-go-melt-units-20261106-001/unit-controls-replay.json)
```

Choose unused output names on repetition; neither command overwrites receipts.
The [new test source](carrier-go-melt-units-20261106/evidence/check_units.py)
is original repository code calling the unchanged upstream functions. Public
receipts contain only synthetic controls, dependency versions and hashes; no
carrier field or private geometry is included.

| Artifact | SHA-256 |
|---|---|
| Boundary/material test source | `a046f654328364a5f7c0f53af980fd191e302bce1b7abcb5f109f36ef88ae51a` |
| Boundary/material receipt | `bdcbce58c274ce303bcdcedbd8cf0ccdef8ff1215695b749e69033854c73dbbd` |
| Fresh original-kernel receipt | `4a2f34ccd6f56a2b90bb36d6283a720b09638e51178d5c5162693efde42902be` |

## Remaining carrier adapter inputs

The adapter must explicitly supply the alloy's temperature-dependent solid,
powder and liquid conductivity/capacity laws, phase thresholds, latent-heat
model and optical/evaporation properties. The upstream density default is
8.0e-6 kg/mm³; the carrier's
[4.42e-6 study density](../../parts/993-eng-carrier-0001/source/bionic-20261011/material-process.json)
is a declared comparison input, not a complete thermal card. Other upstream
material and process defaults must not silently become carrier data.

The source expects geometry, layer height, laser dimensions and toolpath
positions in millimetres; temperatures in kelvin; power in watts; conductivity
inputs in W/m/K; capacity in J/kg/K; and convection inputs in W/mm²/K. Its laser
profile uses `exp(-3 r²/R²)`, so the adapter must map the supplied beam-radius
convention explicitly. Structured powder/solid activation, actual boundaries,
absorbed-power accounting, mesh/time refinement and conservative temperature
transfer to CalculiX remain unexecuted for this carrier. No multilevel scan,
CUDA run or complete carrier thermal calculation is claimed here.
