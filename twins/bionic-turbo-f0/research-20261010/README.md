# Examples of turbomachines designed with PicoGK

Research of **10 October 2026** to continue the
[39-component conceptual bionic turbo](../assembly/README.md).
Two public projects provide code close to our cold and hot sides:
**QUASAR Phy-CC** and **QUASAR Phy-CT**. The LEAP 71 models complement these
references with downloadable wheels and turbopumps under development.

The sources examined do not demonstrate a **complete PicoGK automotive turbo,
manufactured and tested**. This conclusion concerns this research, not the
possible existence of other prototypes. A turbine, a compressor or a
turbopump does not by itself constitute a complete automotive turbo.

## Comparison of the examples

| Example | Useful elements | Availability and licence | Available evidence |
|---|---|---|---|
| [QUASAR Phy-CC](https://github.com/QU01/Quasar-Phy-CC) | Centrifugal wheel, inlet, diffuser, hollow volute and tangential outlet | C# PicoGK; Apache-2.0 | Code and numerical comparisons with published data; no physical test specific to the project established |
| [QUASAR Phy-CT](https://github.com/QU01/Quasar-Phy-CT) | Radial inflow turbine wheel, optional nozzle, volute, diffuser and shaft section | C# PicoGK; Apache-2.0 | Code, provenance of the comparison cases and declared limits; no tested assembled automotive turbo established |
| [LEAP 71 wheels with integrated inducer](https://leap71.com/downloads/) | Three turbomachine wheels; visual and geometric interest | STL; CC BY-SA 4.0; generator absent from this page | The gallery shows printed wheels; no operational qualification of these three files established |
| [LEAP 71 turbopump for a 28 kN methane/LOX engine](https://www.linkedin.com/posts/leap71_we-are-making-progress-in-building-an-integrated-activity-7313126036693524481-oYCQ) | LOX pump, gas generator, turbine and exhaust | Noyron development; proprietary design code | Post describing work in progress and future hot-fire tests |

## 1. QUASAR Phy-CC: reference for the cold side

Author: Quasar Solutions Lab, GitHub account `QU01`. Version examined:
`fd2b4f2066176265d77bfaa860bda7030578ffc6`.

The [main generator](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/CompressorDesigner/src/CompressorDesigner/CentrifugalCompressor.cs)
separates the rotor and the housing. The sources describe among other things
the main and splitter blades, the meridional passage, the vaneless diffuser
and the volute. These are the elements to compare with our current geometry.
The [project](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/CompressorDesigner/src/CompressorDesigner/CompressorDesigner.csproj)
targets .NET 9 for Windows with PicoGK 2.2.0. Our assembly uses PicoGK
2.3.0 on macOS: compatibility has not been tried.
The [Apache-2.0 licence](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/LICENSE)
of the code is verified at this revision.

The [numerical report](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/validation/RESULTS.md)
compares a one-dimensional mean-line model with the Eckardt O rotor: the
pressure ratio shows a deviation of +0.22 %, while the efficiency shows
**+2.7 points**, a failure against its own 2-point threshold. The report also
flags a difference in diffuser length. Its internal case REF_PR5 is a
regression reference, not an independent measurement.
The [validation plan](https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/docs/VALIDATION.md)
places building a project-specific test bench among its medium-term goals.

## 2. QUASAR Phy-CT: reference for the hot side

Same author. Version examined: `fd9d78f6cccca0850273884e31faec7632810842`.
The [main generator](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/RadialTurbineDesigner/src/RadialTurbineDesigner/RadialTurbine.cs)
and the [wheel generator](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/RadialTurbineDesigner/src/RadialTurbineDesigner/RadialWheel.cs)
are direct references for our turbine and its volute.
The [code licence is Apache-2.0](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/LICENSE).

The [README at this revision](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/README.md)
describes intersection checks on the complete 360° assembly and comparisons
with published data. We have not reproduced them.
The CT-3 and CT-4 geometries are scaled, not independently measured; the
TurboGrid export remains unverified and the STEP blades are surfaces, not
closed solids. The project advises against calibration with the available
observations. The table of cases includes four NASA cases and one conditional
Imperial College case, despite broader wording in its introduction.

The [data manifest](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/validation/data/MANIFEST.json)
and the [CT-1 case with provenance](https://github.com/QU01/Quasar-Phy-CT/blob/fd9d78f6cccca0850273884e31faec7632810842/validation/data/ct1_tp1730.json)
deserve a review before any reuse of parameters. This project does not
provide our complete centre housing with bearings, seals and wastegate.

## 3. LEAP 71: available wheels and turbopumps under development

[See the official illustration of the three LEAP 71 wheels with integrated inducer](https://i0.wp.com/leap71.com/wp-content/uploads/2025/07/62BA1CA0-1871-4129-A387-7C3C7A34477C-1.jpg?resize=1080%2C608&ssl=1).

The [download page](https://leap71.com/downloads/) offers three wheels in STL
format, with an advertised 170 MB archive. It links these models to Noyron and
PicoGK. The [gallery](https://leap71.com/gallery/) shows printed wheels; this
does not prove the performance of the three downloadable models. The STL
archive was neither downloaded nor inspected.

The [post on the 28 kN turbopump](https://www.linkedin.com/posts/leap71_we-are-making-progress-in-building-an-integrated-activity-7313126036693524481-oYCQ)
shows a more advanced integration of components, still under development.
The [official description of Noyron](https://leap71.com/Noyron/) states its
relationship to the PicoGK kernel. **Opening the geometry kernel does not give
access to the Noyron engineering model, which remains proprietary.**

The downloadable models are offered under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The illustration stays linked on the LEAP 71 site: no copy is embedded here,
because the scope of this licence over this presentation image is not
established. This illustration is not evidence of manufacturing or testing.

## Application to our project

1. Compare the meridional passages, blade angles, diffuser and volute section
   law of Phy-CC with our cold side; document the differences before adopting
   code or parameters.
2. Compare the hot passage and volute law of Phy-CT; examine its checks of the
   complete assembly. A 360° check is not enough to establish rotating and hot
   clearances.
3. Define the service conditions common to both wheels and record the
   interfaces of the centre housing, bearings, seals and retainers. Unknown
   values remain `null`; no default value from an example becomes a measured
   dimension of our turbo.

The proposed priority is **QUASAR for studying the code of both sides**, and
**LEAP 71 for examples of shapes and manufacturing**. Assembling two
generators demonstrates neither their aerodynamic matching nor their ability
to share the same shaft and the same speed.

## Scope of the research

Targeted search on PicoGK, turbocharger, compressor, turbine, impeller,
volute and LEAP 71; review of the official pages and of pinned C# sources.
Results relating to the Porsche cooling fan of our own project were excluded
from the independent turbo examples.
No third-party code was executed, no simulation reproduced, and no external
model was integrated into the assembly. This directory adds only
documentation and links; the existing geometry sources and evidence remain
unchanged.
