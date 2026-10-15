# Validation plan — no physical test performed

Each test must record the part/PCB/firmware version, a non-personal internal
number, the conditions, the instruments/calibration, the data, a criterion
defined **before** the test, and the signature of the person responsible. The
physical thresholds below remain to be set with the specialist and the
laboratory; an empty cell is a blocker, never an implicit "compliant".

The [E0-01 to E0-07 bring-up protocol](electronics/coupon.md) details the first
bench checks, the quantified stop assumptions and the known limit in case of a
hung MCU. None of these physical tests has been performed yet.

| ID / gate | Test | Owner / evidence | Criterion before passing |
|---|---|---|---|
| V01 / G0 | Inventory of the original regulatory functions | owner + laboratory; reference, markings, photos | all functions and markets identified; written opinion on a possible route |
| V02 / G1 | Scan and independent critical measurements | scanner + owner; coverage/uncertainty report | datums and tolerances agreed, no interpolated hole on a fastening without measurement |
| V03 / G2 | Tint/thickness/air-gap coupons | owner; R/G/B spectrum or transmission, haze, lux/contrast, photos at fixed settings | contrast/readability thresholds at 1/3/5 m and angles agreed; day, sun and night test, absence of glare assessed. Distances = proposed protocol, not part dimensions |
| V04 / G2 | Coupon power and temperature | electronics engineer; mean and peak voltage/current, thermocouples | thermal ceiling defined by components/materials; closed and degraded measurements without exceedance |
| V05 / G3 | Fit jig, then fitting | owner; native CAD, deviation report and photos | same interfaces; no drilling/splicing; no body contact, expansion, clearances and tightening validated |
| V06 / G4 | Power supply on the bench | specialist; start-up/transient/polarity/short-circuit profiles on a suitable generator | ISO levels and criteria agreed; no fire/smoke, defined recovery, regulatory functions preserved |
| V07 / G4 | Real firmware and radio | specialist; OS/model/version matrix + logs | MITM/replay/non-owner rejected; max stream, MTU 23, cutoffs at every offset; watchdog and black screen verified electrically |
| V08 / G4 | Secure DFU | specialist; signed/invalid images, power cut at each step | signature/anti-rollback enforced, no partial image booted, local recovery and protected keys |
| V09 / G5 | Climate/UV/water/vibration | laboratory; protocol and optical/fit before/after | T range, number of cycles, UV dose, vibration and IP level agreed; no leak, corrosion, yellowing/clearance out of tolerance. No IP claim before a complete test |
| V10 / G5 | EMC/ESD/RF | competent laboratory; reports tied to the exact revision | chosen limits/standards met; immunity with safe behavior and BLE reception verified when fitted |
| V11 / G5 | Photometry/reflection/installation | laboratory + authority | each required function and visibility compliant; documents and markings legally authorized, not merely a software shutdown |
| V12 / G6 | Pre-series of 10 parts | owner + EMS; time, yield, FAI/AOI, 100% test | acceptance criteria before manufacturing; zero units shipped without a test record, rework documented |
| V13 / G6 | Repairability | owner; documented disassembly/reassembly | front face/PCB/seal replaced without destroying the rest; sealing and optics retested |
| V14 / G6 | Packaged shipping | supplier + owner; drop/vibration/compression according to an agreed method | no scratch, crack or fastening damage; electrical check before/after; height/loads according to the final mass and the logistics chain |
| V15 / G7 | Budget and origin | owner + adviser; quotes, invoices, hours, register | acceptable delivered cost; independent evidence of the ratio and essential activity before a Swiss claim |

## Faults to inject

Power cut, brownout, hung MCU, watchdog, thermal sensor open/short circuit,
overheating, LED/driver short circuit, corrupted memory, partially connected
cable, humidity and lost phone link. The programmable display must return to
black without affecting the mandatory lighting. Verify this independence under a
hardware fault, not only with `STOP` in the app.

## Traceability and acceptance

Private measurements/reports stored with identifiers and access rights; publish
a sanitized summary and its hash if authorized. Any change to the optics,
driver, power supply, firmware or supplier triggers an analysis of the tests to
repeat. The Python tests in this dossier verify a host contract; they close no
mechanical, electrical, radio, road safety or manufacturing qualification gate.
