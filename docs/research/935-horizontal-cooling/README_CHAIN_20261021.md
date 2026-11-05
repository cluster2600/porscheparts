# 935 — rerun through the README software chain

This rerun follows the [technical overview chain](../../ENGINEERING_OVERVIEW.md#software-chain-qwen-and-picogk)
on the rotor derived from the scans, with its [corrected tip 03](TIP_CORRECTION_20261013.md).
The batch examines the sensitivity of the mechanics to the selection of fixed nodes
in the bore. It keeps the geometry, the acquired profiles and the repairs.
It defines no new physical support.

The main checkout contained other work and an old README. The
dedicated worktree took `origin/main` at `e3cd41df`. The update first
failed for lack of space; the checkout was restored after checking and
deleting local copies already archived on private GitHub. The scans,
parameters and results needed for the batch remain available.

## Identity, interfaces and assumptions

The README also points to the [analytical reconstructions R0/V2/S1](../../../models/horizontal-fan-reconstruction/README.en.md)
and their CAD/CFD chain. Their geometries and conditions have their own
identity. The CFD results or modes of V2 do not characterise the corrected
scanned rotor. The present calculation does not launch their D3 supervisor and does not
modify their frozen sources.

The [935 system entry](../../../twins/935-horizontal-cooling-system/README.md)
and the [contract of the 17 interfaces](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
keep the definition gaps. The load path studied runs from the rotor
to the hub, then the shaft and its bearings. The fit dimensions, bearing
surfaces, axial retention, preload, support stiffness and exact variant are
not measured. None of these unknown fields is filled in by the calculation.

The scenario keeps 6,000 rpm, elastic AlSi10Mg at E = 70 GPa,
ν = 0.33 and ρ = 2.67 g/cm³, with no qualification of process, orientation or
temperature. Only the centrifugal force is applied. The scale assumption
remains 1 mm per source unit; the precisions declared in the names of the
scans do not constitute that calibration.

## Position of the batch in the chain

| README step | Execution and evidence boundary |
|---|---|
| Catalogue, requirements and interfaces | Reuse of the documented identities and gaps; no new physical dimension admitted |
| Qwen then independent check | Optional assistance; no new inference nor execution of code proposed by a model |
| C# / PicoGK recipes | Native rotor kept; digest and volumetric moments re-verified, earlier topological checks referenced |
| Gmsh / preparation | Existing meshes kept; only the `BORE` list modified, without changing nodes, elements, material or loads |
| CalculiX / numerical review | Local Linux aarch64 calculations on the Mac, then complete coverage of results and force/moment balances |
| OpenFOAM | No new calculation; the earlier CFD values are not transferred to the corrected rotor |
| OpenUSD / Omniverse | Separate visual inspection; no new SimReady result or qualified physical twin |
| PhysicsNeMo and manufacturing | No training from refused calculations; no machine preparation or manufacturing release |

This use of the existing masters follows the [workflow contract](../../architecture/engineering-workflow.md).
The presence of a tool does not require running it in every batch. The previously
frozen PicoGK sources and calculation programs remain unchanged.

## Experiment: isolating the support selection

The previous calculation chose nodes such that
`abs(sqrt(x²+y²) - R_bore) < h`, where `h` is the mesh step. The fixing
condition therefore varied with the discretisation, in addition to the voxelised
geometry. An experiment with a constant assumed radial half-width of 1.5 mm
decouples these two parameters. A second value of 0.6 mm at the fine
step measures the sensitivity. These values are numerical selection
bands, not clearances, bearing seats or machining tolerances.

The [preparer](../../../twins/935-horizontal-cooling-system-f0/source/prepare_bore_sensitivity.py)
checks the digests of the parent, the rotor and the grid, then replaces
only the `*NSET,NSET=BORE` block. It checks node coverage and
keeps the text outside that block exactly. The receipt records the radial
range actually selected, the number of fixed nodes and the
before/after digests. The parent is not modified.

At the 1.35 mm step, the 1.5 mm band produces exactly the same deck as
the earlier case: its result is reused with its digest. Only two
additional calculations are needed at the 1.2 mm step.
Each new solver run is limited to 240 s, with a global budget of 900 s
including the review; the cases remain sequential. No Kali calculation, no
Vast rental, no image download or modification of a third-party service.

## Reproduction and checks

The [structured receipt](readme-chain-20261021.json) keeps the digests and
the checks. The inputs, decks and outputs remain in the [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/readme-chain-20261021).

| Assumed step, mm | Radial half-width, mm | Fixed nodes | Max. displacement, mm | Difference from the parent at the same step |
|---|---:|---:|---:|---:|
| 1.35 | 1.50 | 3,848 | 0.603618 | 0 %, identical deck reused |
| 1.20 | 1.20, reference | 4,264 | 0.759834 | reference |
| 1.20 | 1.50 | 4,920 | 0.759617 | −0.0285 % |
| 1.20 | 0.60 | 2,952 | 0.760114 | +0.0369 % |

The two new calculations finish in 139.3 and 146.5 s of solver time.
The independent force and moment balances pass; the largest
relative error of the three cases is below 3 × 10⁻⁹. The maximum stresses
of the fine mesh remain close to 197.46 MPa and the P95 of the peaks
outside r = 25 mm close to 34.54 MPa. These stresses are not admissible
limits of the part.

At a constant half-width of 1.5 mm, the displacement difference between the two
fine meshes remains **25.84 %**. The band variation therefore does not explain
the non-convergence of this campaign. This result does not assert that the
real supports have no influence: they are not represented by a measured
contact or bearing model.

The numerical next step is an independent bending witness, then a comparison
of element formulations on identical geometry, with a fixed numerical
support. The acquired surfaces will not be thickened to force a criterion
to pass. Metrology of the installation and material qualification remain
separate work needed for validation of the system.

The detailed cases, inputs and results remain private under
`work/935-readme-chain-20261021/`. The preparer's input case fixes the
parent directory, the three digests `receipt.json`, `case.json` and
`rotor.inp`, the rotor path, the half-width and the assumption status.

```sh
python prepare_bore_sensitivity.py CASE.json work/NEW-prepared
timeout --signal=TERM --kill-after=10s 240s bash run_candidate_fea.sh \
  work/NEW-prepared/rotor.inp DECK_SHA256 work/NEW-solved
cp work/NEW-solved/ccx.log work/NEW-solved/log.rotor
python assess_mac_fea.py work/NEW-prepared work/NEW-solved work/NEW-assessed
```

The solver launch uses native Linux in the existing local container.
The audit is that of the previous campaign: displacements of all
nodes, eight integration points per C3D8, reactions of all fixed nodes,
independent balances, maximum stresses and P95 outside r = 25 mm. The review
script requires the log alias to be identical to the original log.
The targeted tests verify that the modification is limited to the support block, the
selection, the preservation of the text and the refusal of invalid inputs.

The [CalculiX documentation, section 6.2](https://www.dhondt.de/ccx_2.15.pdf)
notes the possible excessive stiffness of the fully integrated C3D8 in bending.
This limitation is a diagnostic lead, not a cause demonstrated by
the present batch. An independent bending witness and a comparison of
formulations must precede any conclusion on this mechanism.

The results remain studies under assumptions. The numerical criteria
replace neither metrology, nor the characterisation of supports and materials,
nor contained rotation tests and professional mechanical review.
