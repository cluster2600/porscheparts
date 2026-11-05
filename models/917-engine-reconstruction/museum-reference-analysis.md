# Analysis of the 917 engine displayed in exploded view

Analysis of 12 October 2026 of the [third video provided](https://www.youtube.com/watch?v=bIT1i03EZWM).
It complements the [installed engine](video-reference-analysis.md) and
the [cutaway animation](animation-reference-analysis.md) with close-ups
of physical components. Its main contribution is the construction of the parts:
bearing caps, housings, fins, flanges, fittings and fasteners.

## Source examined

- Title: "917 Engine Display Porsche Museum"; stated author: BreitWerks;
  publication date stated by YouTube: 9 July 2017. The description places this
  display at the Porsche museum in Stuttgart; the exact variant of the engine is
  not established by this analysis.
- Copy actually examined: 1280 × 720 pixels, 30 frames/s, duration
  124.6 s. SHA-256:
  `c4301e525f4113a68f0846bbb5365d55b0b4e79be61a09d088a837c10f690eb0`.
- One contact sheet and fifteen individual frames were examined:
  4, 12, 20, 28, 36, 44, 52, 68, 76, 84, 92, 100, 108, 116 and 122 s.
  Reproducible extraction: `ffmpeg -ss 36 -i video.mp4 -frames:v 1 frame-036.png`.
- The parts are presented spread apart on stands: the museum
  displacement provides neither mounting centres nor running clearances.
  The pitch of the perforated base plate is unknown and is not a scale.
- Licence and reproduction/derivation rights unknown. Video and images remain
  in `/tmp/`, outside Git. No pixel, plate or vehicle identifier is
  published in this document. No sound or commentary is used as a measurement.

## Usable observations

| Timestamp | Parts and visible details | Consequence for PicoGK; limit |
|---|---|---|
| [00:12](https://www.youtube.com/watch?v=bIT1i03EZWM&t=12s), [00:20](https://www.youtube.com/watch?v=bIT1i03EZWM&t=20s) | Open case half with bearing housings and repeated bulkheads; separate pistons with grooves and pin bore; row of six individual cylinders with external fins. | Separate cylinder, piston, pin, bearings and case with their bearing faces and fasteners. Re-register their interfaces on the scan and the sourced dimensions. Neither the repetition nor the display stands give the dimensions. The fins must not be copied automatically onto a cylinder head whose cooling would be different. |
| [00:28](https://www.youtube.com/watch?v=bIT1i03EZWM&t=28s) | Long fasteners removed, laid next to the bench; cylinder head surfaces partially visible and image in motion. | Through-fasteners and nut access must appear in the assembly contract. The view is too blurred and obscured to establish the thread, the preload, a complete number of fasteners or the number of valves per cylinder. |
| [00:36](https://www.youtube.com/watch?v=bIT1i03EZWM&t=36s), [00:44](https://www.youtube.com/watch?v=bIT1i03EZWM&t=44s), [00:52](https://www.youtube.com/watch?v=bIT1i03EZWM&t=52s) | Camshaft in an open longitudinal housing: journals, lobes, bolted bearing caps, bosses and drive components near the lobes. A gear appears in the intermediate region at 44 s; the end visible at 36 s has a regular axial profile. | Replace the generic supports with removable housings and caps, with motion allowances, fasteners and lubrication. The toothed region is an additional physical clue for examining the central drive suggested by the animation. The end profile may correspond to splines: do not treat it as a pinion without a complementary view. The complete train, its ratios and its retainers are not established. |
| [01:08](https://www.youtube.com/watch?v=bIT1i03EZWM&t=68s), [01:16](https://www.youtube.com/watch?v=bIT1i03EZWM&t=76s), [01:24](https://www.youtube.com/watch?v=bIT1i03EZWM&t=84s) | Two assemblies with black volutes and bent metal ducts; central component with a tall black body; assembly held by drilled plates and brackets. | Useful physical reference for our turbos: flanges, fitting orientations, bend radii and supports must form a removable assembly. The central component is visually compatible with a bypass/regulation control, but its identity and circuit must be confirmed. The display poses do not fix those of the turbos in the engine. |
| [01:32](https://www.youtube.com/watch?v=bIT1i03EZWM&t=92s), [01:40](https://www.youtube.com/watch?v=bIT1i03EZWM&t=100s) | Black hose clamped by hose clips, beaded metal spigot, welded junctions, lower bolted flange, support brackets and several distinct outlets. | Distinguish hot/cold parts after identifying the circuit; create the real fittings around our candidate ports, rather than a single continuous tube. Thermal deformations, loads on the volutes, sealing and maintenance must be checked. Neither alloy, thickness, seal type, flow nor pressure can be measured here. No heat exchanger is identified in these close-ups. |
| [01:48](https://www.youtube.com/watch?v=bIT1i03EZWM&t=108s) | Shaped longitudinal cover with bumps and peripheral fasteners; several detached components lined up under the bench. | Confirms the priority of a coherent longitudinal cover over the six boxes of our current render. Our 4V cylinder heads need their own envelope, joint face and access: this historical cover does not prove their compatibility. |
| [01:56](https://www.youtube.com/watch?v=bIT1i03EZWM&t=116s), [02:02](https://www.youtube.com/watch?v=bIT1i03EZWM&t=122s) | Crankshaft, connecting rods and large shaped counterweights, neighbouring longitudinal shaft, gears under the central zone, horizontal fan with yellow shroud; clutch and transmission separate in the background. | Document each torque connection and distinguish cam drive, power output, fan and accessories. The central elements strengthen the case for a review of this architecture; they do not make it possible to assign every gear to a precise function. The connecting rods moved for the display do not give the kinematic phases. |

## Reconstruction steps based on the three references

1. **Review the timing drive path.** Cross-check the gears visible in the
   museum with the animation and the mechanical data of the selected variant.
   The current end-mounted trains remain a candidate solution; a new shaft or
   new gear teeth remain a design assumption as long as their
   interfaces are not sourced. Keep the axes of the 4V cylinder heads, then verify the ratios,
   directions of rotation, allowances and interfaces of the new path studied.
2. **Rebuild the envelopes with their fasteners.** Priority to the longitudinal
   housings and bearing caps, the joint faces, the accessible bolts,
   the journals and the channels. The transparent museum rods and the holes of the
   base plate are not engine parts; do not include them in the assembly.
3. **Integrate the turbos.** Keep our prototypes, identify the circuits and
   complete supports, flanges, hoses and regulation device. Revise the
   long loops from the ports and the keep-out volumes, then check
   clearances, contacts, flow, sealing and expansion.
4. **Use bionics where justified.** Reuse the PicoGK functions
   for branches, beams and implicit fields for the supports and
   internal transitions, keeping anchors and keep-out zones. These images
   do not show a bionic construction to copy. A reduction in volume
   alone qualifies neither the bearing caps, nor the connecting rods, nor the gear teeth.

The museum reference provides more detailed physical shapes than
the animation, without providing the necessary metrology. The black,
metallic and yellow colours do not identify the materials. The four valves,
dimensions, tolerances, internal circuits, loads, treatments and processes
must keep their own evidence. No part is declared functional
or printable for engine service by this analysis.

The PicoGK sources and run receipts already published remain unchanged; this
step adds observations and reconstruction criteria.
