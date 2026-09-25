# M64 G2 — candidate spark plugs and a digitally closed chamber

**Two spark plug envelopes and their stepped wells are added as an option to the G2.**
The external shape, the valve positions and the interfaces of the G2 do not change.
This model remains synthetic: **neither a fitted M64 cylinder head, nor a part authorized for printing**.
No Vast rental was needed.

## Results

| Check | Result on this configuration |
|---|---:|
| Cylinder head | 1 valid BRep solid, 403 faces |
| Candidate spark plugs | 2 valid solids; zero volumetric intersection with the head |
| Connected volume at TDC | 94.384567 cm³ |
| Conditional geometric ratio | 7.35744:1, below the 8–9 target hypothesis |
| Volume variation over three windows | 0 at the reported precision |
| Conservative plug / valve bound, full cold stroke | 4.118 mm for a 1 mm design threshold |
| Conservative plug / crown bound at TDC | 12.005 mm for the same threshold |
| One plug removed: negative control | chamber open, usable volume and ratio absent |

The independent calculation by integrating the roof and the piston gives **94.463376 cm³**,
i.e. about **+0.0835%**. This proxy ignores the details of the seats and spark plugs: its closeness
on a single point is neither a physical validation nor a transferable calibration.
The historical ×1.075 calibration was neither modified nor used to announce the ratio above.

The geometric checks report 44 passes, two non-blocking indicative failures and one
inter-cylinder spacing that cannot be computed. Their `accepted` concerns only these criteria:
the compression remains off target and no engine qualification follows from it.
The existing geometric margin between stud and spring pocket remains very small: **0.08 mm beyond
the chosen threshold**, without manufacturing tolerances or thermal expansion. It is not an industrial margin.

## Geometry and hypotheses

The candidate family [NGK BKR EIX-P](https://ngk-sparkplugs.jp/ngk/sparkplugs/products/max/)
publishes a thread diameter of 14 mm, a thread length of 19 mm and a 16 mm hex
(table "品番ラインアップ" — "part number lineup", consulted on September 24, 2026). This selects **no heat
range for 700 hp**, nor an approved Porsche application.

The 20 mm seat diameter, its 1.5 mm height, the 22 mm wrench well and the dimensions of the nose
and insulator are **explicit hypotheses** in
[the optional parameter set](../../twins/m64-cylinder-head/source/fourvalve/params-plugs/spark_plug_envelope.json).
The widened well starts at the seat, 19 mm above the axis/roof intersection; it creates the flat
shoulder without enlarging the hole on the chamber side. The threads remain smooth cylinders.
The well check uses the same primitives as the CAD; the valve/plug collisions use capsules
bounding the solids and their whole stroke, without assuming a single crank angle.

The spark plug is a solid assembly envelope, **not supplier CAD**: nose crevices, threads, ring
clearance, gasket compression and thermal contacts are missing. The valves and seats remain
simplified overlapping solids, not a qualified mechanical contact.
The absence of a topological leak in the model does not prove physical sealing.

## Measurement and reproducibility

The probe now encloses the entire height of the cylinder head, then adds 2, 5 or 10 mm.
Limiting the probe to the roof +2 mm truncated some seat pockets: it was not a sufficient
window, even with the spark plugs. The three new upper bounds are
88.461, 91.461 and 96.461 mm.

A multi-tool difference also produced an invalid BRep during one trial. The measurement first
fuses the occupants, then subtracts this union, with serial non-destructive operations so as not
to modify shared inputs. Any invalid result remains refused; no automatic repair or widened
tolerance is used to accept a volume.

```mermaid
flowchart LR
    A[Frozen G2] --> B[Candidate plugs and seats]
    B --> C[Union of occupants then connected void]
    C --> D[3 windows and control without plug]
    D --> E[Conditional ratio 7.36 - target not reached]
    E --> F[Chamber and contacts to rework before thermal]
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    class E stop;
```

[Audit, checks and digests](../../twins/m64-cylinder-head/evidence/g2-spark-plug-packaging-20260924/audit.json)
and [STEP of the two envelopes](../../twins/m64-cylinder-head/evidence/g2-spark-plug-packaging-20260924/spark-plug-envelopes.step).
CAD section in the plane of the spark plug axes, piston on the left and spark plugs on the right; this is not a photo:

![CAD section of the two candidate spark plugs](../../twins/m64-cylinder-head/evidence/g2-spark-plug-packaging-20260924/plug-section.svg)

*CAD section of the synthetic plug envelopes; it does not prove physical sealing or supplier fit.*

```sh
uv run --python 3.12 --no-project --with cadquery==2.6.1 python \
  twins/m64-cylinder-head/source/fourvalve/audit_spark_plugs.py \
  twins/m64-cylinder-head/evidence/g2-head-features-20260916/parameters-resolved.json \
  work/m64-g2-plug-replay
uv run --python 3.12 --no-project --with cadquery==2.6.1 python tests/test_m64_g2_head_features.py -v
uv run --python 3.12 --no-project --with cadquery==2.6.1 python tests/test_m64_g1_four_valve_twins.py -v
make check
```

The script refuses to overwrite existing evidence. The previous G1/G2 evidence remains unchanged.
The window change makes the old **open diagnostic** volumes not directly comparable; the old audit
is reproducible with its code at commit `f4cfddb`.

Checks: **15 G2 tests and 21 G1 tests passed under CadQuery 2.6.1**, with no CAD tests skipped.
The SHA-256 digests of the code, parameters and exports of this audit were rechecked.
`make check` runs 3,032 tests successfully (120 skipped in its default environment),
then fails on the stale F46 report, already failing on
[the starting `main`](https://github.com/cluster2600/porscheparts/actions/runs/35085578047).
The F46 report and its contract are not modified; the PR remains a draft.

## Next steps

Follow-up run on September 25: [concordant seats and per-port leak test](M64_G3_SEAT_CONTACT_20260925.md).
That follow-up also fixes the lateral truncation of the probe; the figures above remain
those of the historical evidence of September 24, not rewritten.

Rework the chamber profile for the chosen compression range, without arbitrarily touching the
exterior, and replace the simplified seats/valves with consistent seats. Only then recalibrate
the proxy on several closed geometries and prepare the thermal/conjugate meshes.
Supplier drawing of the spark plugs, hot contacts, materials, M64 interfaces and LPBF qualification
remain separate requirements: this work does not replace them.
