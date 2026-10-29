# Reproduce the finite internal gyroid study

This workflow creates four internal void tools and fills their small disconnected
pockets. It does not modify the complete carrier. It complements the separate
periodic-cell CalculiX study in the [main report](../../README.md).

## 1. Install the small geometry environment

Run from the repository root, using Python 3.11. The reference interpreter is
3.11.18 on macOS ARM64. Use a fresh work directory for each replay: existing
result directories are deliberately refused.

```sh
CELL_SOURCE=parts/993-eng-carrier-0001/source/design-20261016/convergence-20261022
CELL_EVIDENCE=docs/reports/carrier-interface-20261028/evidence
CELL_FINITE_WORK=work/carrier-finite-repro
python3.11 -m venv "$CELL_FINITE_WORK/runtime"
CELL_GEOM_PY="$CELL_FINITE_WORK/runtime/bin/python"
"$CELL_GEOM_PY" -m pip install --index-url https://pypi.org/simple \
  -r "$CELL_EVIDENCE/finite-gyroid-001/requirements.txt"
"$CELL_GEOM_PY" -m pip check
```

The pinned environment contains NumPy, SciPy, Manifold, libigl and Matplotlib.
CadQuery, Microgen and VTK are unnecessary for this phase. Geometry construction
uses the previously checked [four envelope meshes](../core-envelopes-006/).

## 2. Generate all twelve finite cases and their two retained networks

```sh
for rank in 0 1 2 3; do
  for size in 0.25 0.125 0.0625; do
    run="$CELL_FINITE_WORK/r${rank}-h${size}"
    "$CELL_GEOM_PY" "$CELL_SOURCE/finite_gyroid_voids.py" \
      --envelope-directory "$CELL_EVIDENCE/core-envelopes-006" \
      --contract "$CELL_EVIDENCE/finite-gyroid-001/parameters.json" \
      --rank "$rank" --size "$size" --output "$run"
    "$CELL_GEOM_PY" "$CELL_SOURCE/finite_gyroid_networks.py" \
      --directory "$run" --output "${run}-networks"
  done
done
```

Each finite call recomputes the sphere controls, checks Boolean containment,
normalizes once before export, requires exact oriented-triangle transfer, and
checks non-cap field vertices. The sphere at 0.1 mm is intentionally retained
with its failed 1% volume criterion; both finer sphere controls must pass.

The network step keeps the largest positive-field and negative-field components.
The discarded void pockets become solid material. It does not create drainage
ports. Native meshes, receipts, exact inputs and source hashes are written into
each fresh run directory. Numerical comparisons use physical quantities and
fixed tolerances; bit-identical mesh ordering across platforms is not promised.

## 3. Assess raw and cleaned volume stabilization

The following command selects the twelve raw directories and the twelve matching
network directories created above. Each region must have both successive
comparisons below 2%; no claim about complete-carrier mechanics is produced.

```sh
"$CELL_GEOM_PY" "$CELL_SOURCE/assess_finite_voids.py" \
  --directories "$CELL_FINITE_WORK"/r*-h0.*[0-9] \
  --networks "$CELL_FINITE_WORK"/r*-h0.*-networks \
  --output "$CELL_FINITE_WORK/series"
```

The raw-directory glob ends with a digit and excludes the network directories.
Inspect `series/assessment.json`: both `finite_volume_stabilized` and
`cleaned_volume_stabilized` should be true. Topology convergence, complete-carrier
mechanical convergence and manufacturing authorization remain false.

## 4. Render the actual internal material cutaways

```sh
"$CELL_GEOM_PY" "$CELL_SOURCE/render_finite_gyroid.py" \
  --envelope-directory "$CELL_EVIDENCE/core-envelopes-006" \
  --networks "$CELL_FINITE_WORK/r0-h0.125-networks" \
    "$CELL_FINITE_WORK/r1-h0.125-networks" \
    "$CELL_FINITE_WORK/r2-h0.125-networks" \
    "$CELL_FINITE_WORK/r3-h0.125-networks" \
  --output "$CELL_FINITE_WORK/figures"
```

The renderer checks material volume against envelope volume minus the two void
volumes, and requires one positive material shell with two negative void shells.
It cuts only the displayed internal region at mid-height and simplifies
the display by 0.02 mm. It does not change the numerical meshes. The figure
receipt records all input hashes.

## 5. Assemble the complete closed-chamber carrier

This step uses the eight medium-resolution networks. It retains the complete
outer R2 surface exactly and produces a computational mesh with eight closed
internal chambers. It does not create a manufacturing release.

```sh
CELL_R2_SOURCE=parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/picogk-R2-study/surface.mesh64.gz
"$CELL_GEOM_PY" "$CELL_SOURCE/insert_finite_voids.py" \
  --reference "$CELL_R2_SOURCE" \
  --networks "$CELL_FINITE_WORK/r0-h0.125-networks" \
    "$CELL_FINITE_WORK/r1-h0.125-networks" \
    "$CELL_FINITE_WORK/r2-h0.125-networks" \
    "$CELL_FINITE_WORK/r3-h0.125-networks" \
  --output "$CELL_FINITE_WORK/complete-closed"
"$CELL_GEOM_PY" "$CELL_SOURCE/render_closed_carrier.py" \
  --directory "$CELL_FINITE_WORK/complete-closed" \
  --output "$CELL_FINITE_WORK/complete-closed-figures"
```

The assembly checks containment, nominal mass below 1.30 kg, one positive
material shell, eight negative cavity shells, the exact original exterior and
an exact complete oriented-triangle export/reimport. The illustration is an
actual Z = 0.5 mm section; orange shows the new voids.

## How to read the result

The four fine-level void volumes total 1,366.238188 mm³ after pocket filling,
equivalent to 6.038773 g at the study titanium density. This is a potential
subtraction before transition design. The assembled medium-level variant has
nominal computed mass 1.292162707 kg.
The next operations are transition blending, escape-route and wall/channel
checks, followed by complete-carrier mechanics on the modified geometry.
