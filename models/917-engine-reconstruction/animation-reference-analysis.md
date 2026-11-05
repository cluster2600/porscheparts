# Analysis of the 917 mechanical animation

Analysis dated 12 October 2026 of the [second video supplied](https://www.youtube.com/watch?v=j3CkVwtOPX4),
complementing the [analysis of the filmed engine](video-reference-analysis.md).
The [museum physical reference](museum-reference-analysis.md) adds close-ups
of the bearings, the central region and the forced-induction connections.
This reference provides a reading of the mechanism in section and an important
difference from our assembly: the large camshaft gears visible
are located towards their middle, whereas our [candidate valve train](cam-drive/README.md)
places its gear trains in the planes X = 400 and 424 mm, at the end of the engine.
This difference must be investigated before freezing the case architecture.

## Nature of the source

- Title: « PORSCHE 917 ENGINE ANIMATION »; stated author: `mwp917`;
  publication date stated by YouTube: 7 August 2009.
- The author describes a SolidWorks model rendered with PhotoView 360 and a repeated
  sequence. It is a CAD visualisation, with no evidence supplied here that the
  shapes, timing and interfaces reproduce an exact Porsche variant.
- Copy examined: 900 × 720 pixels, 24 frames/s, duration 30 s.
  SHA-256: `fb40259ed5f666dde5027bc3944fe4ea4647400dc5bb0dfecaad837bac9ebd42`.
- A contact sheet, then nine single frames at 1, 3, 5, 7, 10, 15, 20,
  25 and 29 s were examined. The camera keeps the same viewpoint; these
  frames give different positions of the mechanism, not views of additional
  faces. No real engine speed or valve timing diagram is deduced.
- Extraction: `ffmpeg -ss 3 -i video.mp4 -frames:v 1 frame-003.png`,
  replacing the second. The viewing files stay in `/tmp/`.
- Licence of the model, rights to geometric derivation and to republication of the
  images unknown. No SolidWorks model, mesh or external pixel is
  added to the repository. The analysis extracts no dimension from this animation.

## What the frames show

| Timestamps | Observation | Contribution to our reconstruction; limit |
|---|---|---|
| [00:01](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=1s), [00:03](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=3s), [00:05](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=5s) | On the open side, pistons, connecting rods and parts of the crankshaft are exposed. The positions of the pistons and connecting rods change between frames. The pistons have peripheral grooves; the shafts show counterweights and profiled blends. | The mechanical reading rests on the interfaces between parts and their motions, and demands more than generic cylinders and discs. Revise the volumes of the connecting rods, crankshaft counterweights, bearings and housings from the measured sources. The perspective does not allow counting all the crankpins, measuring the fillets or confirming the pairing of the connecting rods of the other bank. |
| [00:03](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=3s), [00:07](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=7s) | Two long parallel shafts are visible outside the open bank. They carry repeated lobes and large gears near their middle; several idler gears are grouped in the same region. | Study a valve train driven in the central region, compatible with our 4V camshaft axes. The animation proves neither the complete topology of the gear train, nor its ratios, nor the measured axial position, nor collision-free meshing. The shafts are shown outside their envelope: do not copy their apparent spacing as an assembly dimension. |
| [00:01](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=1s), [00:15](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=15s), [00:29](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=29s) | Components with stems and springs sit near the two camshaft lines. Their position and that of the lobes change. | Identify explicitly cam, transmission element, valve, guide, spring and seat in our model. An image does not allow validating the contacts, the lifts or the total number of valves per cylinder. This reference validates neither our 48 valves nor the laws already chosen under assumptions. |
| All frames | A row of six vertical trumpets with rounded lips is visible on the retained side. No turbo assembly or forced-induction duct is shown. | Useful reference for the repeated arrangement of the intakes and their bases. It does not define a twin-turbo circuit; our closed manifolds must keep their interfaces and be subject to flow and pressure checks. The other row and the exact variant cannot be deduced from this one side alone. |
| [00:01](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=1s), [00:07](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=7s), [00:25](https://www.youtube.com/watch?v=j3CkVwtOPX4&t=25s) | A bladed wheel in a horizontal plane occupies the upper central part and changes angular position. It is surrounded by a profiled volume; two bodies with orange caps, similar to distributors, are also visible. | Design the fan with its envelope, clearances, drive and mounting. The two orange components give a reference for the ignition layout, without identifying their internals. Airflow, drive ratio, cooling and electrical controls remain unknown. |
| All frames | On the retained side: longitudinal profiled case, body with fine fins and small fittings at the front; on the open side: envelopes absent to make the mechanism readable. | The holes and open parts of the cutaway serve to explain the mechanism; they must not become openings in our printable solids. The finned body cannot be qualified as a functional heat exchanger from its appearance. |

## Differences to investigate in PicoGK

1. **Valve-train architecture before the outer shell.** Compare the central
   drive suggested by the animation with the four current end-mounted gear trains.
   Our model already has a part named `central_output_gear` in the
   [assembly](assembly/README.md): the central power take-off and
   the camshaft drive are two distinct questions. The presence of this
   part does not validate our new valve-train gear trains. Record the position
   and role of the gears from an independent mechanical source, then rebuild
   the paths with the axes of the 4V cylinder heads kept.
2. **Inspectable mechanism.** Produce from our own solids a complete
   view and a section view that are consistent, at the same poses. A virtual
   section of the render must keep the manufacturing solids intact. The phases of
   crankshaft, connecting rods, camshafts and valves must come from our contract,
   with clearance checks over the cycle; the video does not supply this contract.
3. **Integrated cases and drives.** Define volumes of the bearings, housings,
   access and clearances around the adopted mechanism, before replacing the cubic
   covers. The connection of the fan, accessories and
   lubrication circuits remains to be completed with identified interfaces.
4. **Bionics with an explicit function.** Brackets and channel transitions
   can reuse the existing PicoGK functions. Shafts, connecting rods and
   gear teeth require fatigue, lubrication and finishing calculations before
   any lightening. The drilled gears of this CAD constitute no evidence
   of optimisation or of suitability for metal printing.

## Relation to the first video

| First reference: filmed engine | Second reference: animation |
|---|---|
| External envelope, longitudinal shell, fittings, accessories and installation in the chassis | Reading of the open mechanism, repetition of components and apparent central placement of the valve-train drive |
| Hidden parts remain unknown | Cases are removed and parts exposed for visualisation |
| Does not reveal our four valves per cylinder | Does not demonstrate their compatibility or their timing either |

The two videos are not two guaranteed complementary records of the same
engine: variant, scale, equipment and fidelity of the CAD remain to be established.
Our 4V twin-turbo reconstruction remains a hybrid design under assumptions.
The sources and receipts of the executed steps are not modified by this analysis.
