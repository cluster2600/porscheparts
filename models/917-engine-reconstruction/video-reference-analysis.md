# Visual analysis of the 917/30 reference

Analysis of 12 October 2026, based on the images actually extracted from
the [supplied video](https://www.youtube.com/watch?v=NI_jfBTtziQ).
Comparison with the [current PicoGK render](mechanical-detail/engine-surfaces.png).
A [second, animated reference](animation-reference-analysis.md) provides
a reading of the open mechanism and a valvetrain layout discrepancy
to investigate before freezing the cases.
The main discrepancy concerns the external architecture: fragmented side
envelopes, ducts too exposed above the engine and accessories still
insufficiently integrated. Adding decorative ribs would not resolve this
discrepancy.

## Source and method

- Author given by YouTube: Racetrack Retreats; publication date given:
  9 May 2023; identifier: `NI_jfBTtziQ`.
- The title presents a 1973 Porsche 917/30 engine and announces 1580 HP.
  These statements belong to the author; the power is not a verified
  design load and the variant is not identified by the pixels.
- Viewing copy: 640 × 360 pixels, 30 frames/s, 241.433333 s.
  The YouTube metadata announce a higher maximum resolution,
  but the analysis covers the copy actually downloaded.
- SHA-256 of this copy:
  `8686cfdb8ea1a825dfaa43d622f41df22f45cd8c669dae32c9d02e91a32d593a`.
- Two contact sheets were examined, then nine frames extracted
  separately at 40, 60, 70, 90, 100, 130, 135, 145 and 150 seconds. The single
  frames support the landmarks below; the contact sheets are not used to
  assign an exact second.
- Reproducible extraction:
  `ffmpeg -ss 40 -i video.mp4 -frames:v 1 frame-040.png`, changing the second.
  The video and the viewing frames are kept in `/tmp/`, outside Git.
- The automatic subtitles could not be retrieved (HTTP 429).
  No identification below relies on an assumed transcript.
- The views of the engine on a stand and those of the engine in the chassis are
  treated separately. Their equipment equivalence is not established.
- Licence for reproducing the images and right to derive surfaces from them:
  unknown. This document publishes the observations and links, without images,
  video, plates or vehicle identifiers.

## Observations and consequences for our model

| Frame | Visible observation | Design consequence; limit |
|---|---|---|
| [00:40](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=40s), engine on stand | Two long, rounded envelopes frame a row of wires and side passages. Perimeter screws, beads and a joint line are visible. | The six nearly cubic covers per bank in our render do not reproduce this silhouette. Study a longitudinal cladding for the 4V cylinder heads, with clearances for the mechanism and access to the fasteners. The number of parts, the joints and the internal axes remain to be measured. |
| [01:00](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=60s) and [02:15](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=135s), engine on stand | Block with repeated metal fittings, individual black lines, bolted cover, red cap, rods and levers. | The assembly suggests a mechanical metering/injection unit; its identity and operation are not proven by the image. Above all it shows the lack of fittings, controls and maintenance access on our accessories. It does not justify replacing our control architecture or designing a functional fuel circuit. |
| [01:10](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=70s), engine on stand | Cylindrical body adjacent to pulleys and a belt; small housings with bosses, bolted plates, lines and manifolds close to the engine body. | Group the accessories around plausible but explicitly candidate interfaces; show flanges, seats and screws. The identity of each accessory and its drive must be confirmed separately. Our large valvetrain plate remains a candidate solution, with no established historical fidelity. |
| [01:30](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=90s) and [02:10](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=130s), engine installed | Two long grey volumes, one on each side of the central zone; longitudinal blue tubes, orange hoses with clamps, transverse linkage, harnesses and a gold central envelope. The chassis closely surrounds these volumes. | Bring the forced-induction routes closer to the banks and treat tubes, hoses, clamps and brackets separately. Then check clearances against a measured chassis. The precise role of all the volumes and the inside of the central envelope are not visible. |
| [01:40](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=100s), engine installed | Large rounded volute-shaped housing, short elbow, several orange hoses and clamps; neighbouring curved black volume and chassis tubes in front of the assembly. | The assembly is visually compatible with part of the forced-induction system. Keep our parametric turbos and replace the generic connections with measured interfaces. The image gives no compressor map, no rotor clearance, no certain identification of the black volume, and no complete second turbo in this view. |
| [02:25](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=145s) and [02:30](https://www.youtube.com/watch?v=NI_jfBTtziQ&t=150s), engine installed | Ribbed metal bodies, elbow fittings, flexible hoses, pipes and brackets, partly hidden by the structure. A large open outlet is visible at 150 s. | Add service routes and fasteners after the components are identified. Do not attribute these ribs to the cylinders nor the housing to a particular function: the proximity of the transmission and the occlusions make this identification uncertain. The large outlet is not enough to reconstruct the whole exhaust. |

## What explains the current simplified look

1. **Bank silhouette.** The repetition of six independent boxes draws
   the eye more than the cylinder heads and the cases. The radii added to the
   current covers do not create the longitudinal envelope visible at 40 s.
2. **Duct layout.** The large isolated loops above the model
   exaggerate its height. The installed reference shows ducts contained
   by the banks and the chassis. Merely lowering a loop without checking
   the interfaces and clearances is not enough.
3. **Mechanical junctions.** The reference contains many fittings, clamps,
   seats, bosses, joint lines and control devices. A continuous tube
   and a neatly closed accessory do not represent these removable assemblies.
4. **Presentation and architecture.** Opaque surfaces and mesh detail
   improve readability, but correct neither the design proportions
   nor the integration of the components. The observed differences require
   changes of geometry and layout.

## Priority PicoGK next steps

The 4V cylinder heads and the existing turbos remain the basis of our hybrid engine.
This video does not turn their design into a reproduction of the filmed engine.

| Priority | Change to study | Check needed before acceptance |
|---|---|---|
| 1 | Rounded longitudinal bank envelopes, with hollow volumes and removable access | Cylinder-head interfaces preserved; clearance for valves, cams and valvetrain; surface closure and screw access; joint plane to qualify |
| 2 | More compact routes around the turbo and heat-exchanger outlets | Ports and poses preserved; open passages; intersections with other parts; radii and depowdering; pressure losses and sealing interfaces still to calculate/measure |
| 3 | Integrated accessories: bosses, plates, brackets, fittings and controls | Components identified, anchorages and load path documented; removal and maintenance possible; no purely decorative screw accepted as evidence of attachment |
| 4 | Bionic brackets and internal transitions via the existing PicoGK functions | Fastening zones and keep-out zones preserved; comparable dense witness; strength, stiffness, fatigue and process to qualify |

Bionics suit brackets and channel transitions, starting from
known anchorages and loads. No external branched structure is
identifiable in these images. Spreading branches over all the cases would be
a new design choice, with no justification from this reference.

## Information these images do not provide

No calibrated scale, orthographic view or calibrated camera is available. The
diameters, centre distances, thicknesses and volumes are therefore not measured here.
A dimension taken from another FIA dossier or from the scan must keep its own
variant and provenance, without being attributed to this video.

The gold, grey, blue and black colours do not determine the alloys,
treatments, coatings or manufacturing process. The interiors
of the cylinder heads, the four requested valves, the chambers, the clearances, the
crankshaft, the oil/water passages and the hidden interfaces are not
validated by these views. Pressures, temperatures, loads, thermal
performance, fatigue and suitability for metal printing remain unknown.

This analysis provides a silhouette and integration reference. It does not
qualify any part as functional or ready to manufacture. It does not modify
the sources or the execution receipts of the mechanical step already published.
