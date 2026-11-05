# Public M64/60 engine data (993 Turbo) — survey of 2026-09-27

External survey (research agent, read-only) to seed the parametric skeleton of
the programme `M64-WHOLE-ENGINE-TWIN-0001`. Each value carries an evidence
level. **Nothing here is a project measurement**: none of these values promotes
a geometry beyond `F1_envelope` without metrology.

Levels: `FACT_public` = published by Porsche (brochure, factory technical
manual) · `CROSSCHECKED` = two independent concordant secondary sources
· `SINGLE_SOURCE` = a single secondary source · `ASSUMPTION` = engineering
inference.

## Established values

| Item | Value | Level | Source |
|---|---|---|---|
| Architecture | Flat-six, air/oil, parallel twin-turbo (1 turbo per bank), dry sump | FACT_public | Porsche UK brochure "993 the Turbo" (1995); 1996 OBD supplement |
| Bore × stroke | 100.0 × 76.4 mm | FACT_public | Brochure + Porsche 993 US Parts Guide |
| Displacement | 3,600 cm³ | FACT_public | Brochure |
| Compression ratio | 9.5:1 | FACT_public | 993 Turbo brochure |
| Power / torque | 408 PS (300 kW) / 540 Nm | FACT_public | Brochure |
| Boost pressure | 1.0 bar (350 kPa absolute) | FACT_public | 993 Turbo brochure (note: 0.8 bar effective measured in normal service; the brochure publishes the maximum set-point pressure) |
| Dry mass | 232 kg | FACT_public | 993 Turbo brochure |
| Firing order | 1-6-2-4-3-5 | FACT_public | Carrera M64/23-24 spec document (single shared distributor); cross-checked with a 964 Turbo 3.6 article |
| Valve clearance | Hydraulic compensation (self-adjusting lifters) — no static specification | FACT_public | Parts Guide + Carrera spec document |
| Cylinder head studs | 12 × M8×22 per cylinder head | FACT_public | Parts Guide (parts/quantities) |
| Cylinder seal | 1 O-ring 102×2 per cylinder + 6 cylinder head gaskets + 6 air-guide discs (quantities) | FACT_public | Parts Guide |
| Fan drive | Toothed belt/V-belt from the crankshaft, ratio ≈ 1:1.6 | FACT_public | 1996 OBD supplement "Engine Specifications" |
| Cooling air flow | 1,010 l/s at 6,100 rpm | FACT_public | 1996 OBD supplement |
| Cooling air flow (second value, not corroborated) | 1,210 l/s at 5,750 rpm | FACT_community | elferclassic.de (level C, declared) — demoted to cross-check; the primary value 1,010 l/s is level A (1996 OBD supplement). NB: the 993 manual p.17 (OCR not proofread) mentions "1010 l/sec at 6,000 rpm" — rpm to be checked visually before F2 |
| Oil capacity | 12 L including filter | FACT_public | Brochure |

## NON-public values (block F2, see acquisition contracts)

- Cylinder centre distance (pitch) and crankshaft-to-joint-plane height: **not published** → M64-ACQ-0004.
- Fan blade count and pulley diameters: **not published**
  - Software path: scan `Fan+Drive+0.21mm.obj` (sha256 6c0b12d4…, 1.26 M vertices; provenance to be entered in the register) analysed in `work/obj-intake-20260927/` — angular harmonics 4–7 on the lower slab at this stage, inconclusive before the complete study. Geometric diameters extracted: toothed sprocket OD≈127.6 mm (height 67.9 mm), pulley r_max≈127.8 mm. Flows: primary value **1,010 l/s at ≈6,100 rpm** (level A, 1996 OBD supplement; echoed in manual p.17 "1010 l/sec at 6,000 rpm", OCR not proofread, rpm to be checked visually); 1,210 l/s @ 5,750 demoted to cross-check (elferclassic, level C).
 → M64-ACQ-0005 (the total flow of 1,010 l/s is published, not the wheel geometry).
- Bank designation (left/right) and part numbers of the variants: to be confirmed on the plate.
  - Review note 2026-09-27: deriving the stud pattern from "98.07/43.27" is REJECTED —
    these are camshaft sprocket dimensions ("Engine, Cylinder Head, Valve Drive", OCR not
    proofread), not the bolt pattern. Studs established: 12× M8×22 per cylinder head (level A). Pattern, cylinder
    head height, gasket thickness = physical metrology (ACQ-0001). ACQ-0004 bonus: centre distances
    crankshaft→intermediate bearings 133.57 and 78.77 ±0.25 mm (p.177, to be re-read visually).
- Cam profile: not public → M64-ACQ-0002.
- K16 compressor map: not public → M64-ACQ-0003.

## Sources consulted (identifiers to be recorded in catalog/sources/)

1. Porsche UK brochure "993 the Turbo", 1995, anstack static archive (GitHub) — technical data sheet.
2. 993 Technical Specification Booklet (factory) — Carrera/Carrera 4 data.
3. Porsche 993 US Parts Guide (porscheknowledge.com) — split lines, fasteners, lifters, belt drive, cooling fan impeller.
4. 1996 OBD supplement "Engine Specifications" (993 Carrera M64/23-24) — common M64 architecture: ignition, fan ratio, flow, hydraulic valve train, dry sump.

## Rule applied

No SINGLE_SOURCE or ASSUMPTION value migrates into the geometry code without
prior promotion (ADR-0004, project charter).

---

## PicoGK scaffold run (2026-09-27, evening)

- Build verified in the `m64-engineering-worker` container (image
  `m64-engineering-worker:latest`): .NET SDK 8.0.131, PicoGK 2.3.0 compiled
  from `/opt/PicoGK` (target retargeted to `net8.0`; the official NuGet package
  requires `net9.0`).
- The native runtime `picogk.so` is exposed under the name expected by the
  binding (`picogk.26.2.so`) and the viewer runs under `xvfb-run` (no display).
- Outputs exported and copied into the repository:
  `twins/m64-engine-system/picogk/out/m64-engine-layout.stl` (326,296
  triangles, 5 mm voxel) and `m64-layout.log`. The `.vdb` stays in the worker
  (`/build/picogk/out`).
- The geometry remains at status `F1_envelope`: beams and bounding spheres;
  the ASSUMPTION values in `M64EngineLayout.cs` only become usable after
  promotion through the `M64-ACQ-*` contracts.

## K16 addendum (K16 research lane, 2026-09-27 evening)

Final report of the K16 lane (read-only; repository verified as not modified by the lane):

- Cross-checked identity: left = BorgWarner/KKK **5316-988-6736** (Porsche 993 123 013 51→52),
  right = **5316-988-6735** (993 123 014 51→52), designation **K16-2467GGA/8.88** on both sides
  (CROSSCHECKED: TurboMaster 6735/6736 pages consulted live, BorgWarner catalogue, design911 cross-ref).
- Wheels (SINGLE_SOURCE Invasion Auto): turbine ⌀inducer 54.96 / ⌀exducer 48.97 mm, 12 blades;
  compressor ⌀inducer 40.6 / ⌀exducer 60.5 mm, 6+6. Turbine A/R **8.0 cm²** (CROSSCHECKED, two
  vendor catalogues). Volute angles α 307.5° / β 70°. Wastegate 5825-110-4006, spring
  0.50 bar / lift 4.20 mm (SINGLE_SOURCE). Left bearing housing 5316-151-0008 ≠ right 5316-151-0002.
- Boost pressure: 0.8 bar effective retained (brochure figures quoted in Christophorus /
  catalogues); the "1.0 bar" note in the initial survey is a maximum set-point pressure; the
  350 kPa absolute reading is kept but to be re-checked against the paper brochure.
- **Compressor map still absent from the public domain** → M64-ACQ-0003 remains blocking;
  efficiency, internal clearances, maximum rotor speed, journal/bearings not published.
- Source records created: `SRC-TURBOMASTER-993-K16-6736-LEFT-UNIT`,
  `SRC-INVASIONAUTOPRODUCTS-993-K16-INTERNAL-DATA` (sources validator OK, 358 records).
