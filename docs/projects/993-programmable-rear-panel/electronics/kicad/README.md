# Native schematic of the E0 coupon

October 2, 2026 — **NOT VALIDATED FOR MANUFACTURING. 3.3 V BENCH ONLY.**

Open `coupon-e0.kicad_pro` in **KiCad 9**, then
[coupon-e0.kicad_sch](coupon-e0.kicad_sch). The project has three A3 sheets:
power/control, [drivers](drivers.kicad_sch), [128 LEDs](leds.kicad_sch).
The [review PDF](../coupon-e0.pdf) is an export of the same sheets.
The native files are the editable source; after a change, re-export the
PDF and rerun the checks. No Python EDA library is needed.

## What is represented

The schematic transcribes [coupon.md](../coupon.md), its BOM and its connections:
172 components, 541 pins, 172 nets, including 18 nets of pins left unconnected
(U6 OUT8–23, U7.11 and U8.1). Global labels link the three sheets.
The test compares **all** pin groups of the netlist, the references and
the values against the E0 contract, in addition to the ERC: an LED permutation can pass
the ERC but must fail this comparison.

- U1–U6: **DAP**, PowerPAD represented by KiCad pin **33**, to GND like
  pin 1. This number 33 is a CAD convention for the pad, not an additional
  lead in TI's 32-pin table.
- D1–D128: KiCad symbol `Device:LED`, **1 = K, 2 = A**. These numbers are a
  symbol convention; the cathode mark and the mapping to the pads of the
  Kingbright footprint remain to be examined on the manufacturer drawing.
- TP1–TP8: VCC, VLED, GND, SIN, SCLK, XLAT, BLANK, SOUT_TEST, in that order.
- The two PWR_FLAG declare the external supply on VCC/GND to the ERC; they are
  neither protections nor components to buy. J2 carries no rail from the DK.
  The connectors and S1 remain generic references to be chosen.
- All footprints are **deliberately unassigned**. No PCB, no Gerber, no
  placement, no PCB DRC and no assembly order.

## Reproducible checks

With KiCad 9 and its official libraries installed, from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v
kicad-cli sch erc --severity-all --exit-code-violations -o /tmp/coupon-e0-erc.rpt docs/projects/993-programmable-rear-panel/electronics/kicad/coupon-e0.kicad_sch
kicad-cli sch export pdf --exclude-pdf-property-popups --exclude-pdf-metadata -o /tmp/coupon-e0.pdf docs/projects/993-programmable-rear-panel/electronics/kicad/coupon-e0.kicad_sch
```

Without `kicad-cli`, the schematic test is explicitly skipped: the Python tests
alone do not validate the schematic. The test works in a temporary copy and
exports the netlist itself; no earlier export is used as evidence.
Results and the environment actually used: [verification.md](../../verification.md).

## Review before routing

The ERC simulates neither voltage, nor current, nor timing, nor temperature. An
electronics engineer must review the sequencing of the two supplies, the risk of
parasitic powering, BLANK/IREF, the thermal budget, the footprints and the keyed connectors.
The PCB will have to define outline, layers, copper, returns, decoupling, thermal vias,
optical distance and 2.5/4 mm pitch. No placement in the schematic is a physical dimension.
The limitation of a hung MCU with DISPLAY_EN high remains: **manual S1 and operator
present**; no guaranteed autonomous shutdown. The E0-01 to E0-07 plan remains to be
executed on hardware after review, routing/DRC and manufacturing authorization.

## Symbol provenance

Official **KiCad Community symbols, version 9.0.2**, distributed in the Debian
package `kicad-symbols 9.0.2-1`, under
[CC BY-SA 4.0 with an exception for circuits](https://www.kicad.org/libraries/license/)
(accessed October 2, 2026). The symbols used are embedded in the
sheets so they open; no proprietary manufacturer datasheet is copied.

The small local library `rear_panel_e0.kicad_sym` derives from `74xx:74LVC125`
(inheritance resolved, variant named SN74LVC125APW) and `74xGxx:74LVC1G04`
(NC pin 1 of the DBV package made explicit). It keeps the KiCad Community license
and attribution ([license text](LICENSE-symbols.txt));
pinouts cross-checked against TI [S32/S33](../../sources.md).
`sym-lib-table` uses `${KIPRJMOD}`, with no user path. The minimal project
contains no ERC exclusion and no disabled check rule.
