# Gearbox research for the 911–917 — F0/F1

## F1 architecture decision

Priority given to road/circuit behaviour reverses the F0 decision: the flat-12
moves ahead of the rear axle and the transaxle goes behind it. The published
topology of the Hewland LWS-200 — bevel gear set facing forward, longitudinal
gear train behind — serves only as a drawing reference. The LWS-200 is not
selected: its published torque of 935 Nm is below the screening requirement and
its public general dimensions remain insufficient.

The F1 drawing keeps a hypothetical historical envelope of **650 × 500 × 460 mm**,
with the engine face 100 mm ahead of the differential plane and 550 mm available
behind that plane. These values come from no manufacturer and F9 no longer treats
them as a design target. Torque capacity and the load spectrum now take priority
over compactness. A bespoke gearbox or a split-torque transmission may prove
necessary if the 1,600 hp target and the duty cycle are kept.

## Reminder of the F0 architecture

The configuration studied at the time followed the 911: the transaxle sat ahead
of the flat-12, its differential staying close to the rear axle. The gearbox
thus occupied part of the volume freed by removing the rear seats. A 917-type
layout, with the engine ahead of the gearbox, remains drawn as a comparison and
encroached further on the occupant zone at standard wheelbase. F1 resolves this
conflict with the wheelbase extension described above.

## Public candidates

| Candidate | Useful published data | Limitation for this project | Current decision |
|---|---|---|---|
| Porsche Type 920 | Porsche documentation describes a four-speed longitudinal gearbox on the 917/30. | No dimensioned general arrangement, STEP, current torque rating or verified supply route. | Historical architecture reference only. |
| D.M.A. 1071-W-2WD | Sequential 5/6-speed, 1,200 Nm in 5-speed and 900 Nm in 6-speed form; D.M.A. advertises front-, mid- or rear-engine installations and cites Porsche among existing applications. | Dimensions, exact differential position, 917 bellhousing and load cycle not published. | Most directly compatible candidate for a "gearbox ahead" study, subject to the manufacturer's dossier. |
| D.M.A. S1098 | 6-speed, 900 Nm endurance or 1,300 Nm sprint/hill-climb, 76 kg, longitudinal layout with the gear train ahead of the differential. | Overall dimensions and interfaces are not public; 1,300 Nm gives no demonstrated margin for the maximum target. | High-load candidate to study, not selected. |
| Hewland LWS-200 | 6-speed, 935 Nm, 69 kg in aluminium or 63 kg in magnesium; longitudinal gear train behind the bevel set. | Published torque below the screening requirement and no public overall dimensions on the product page. | Good compactness/topology reference, insufficient capacity. |
| Xtrac P1192 | 7-speed transverse, 1,100 Nm depending on cycle, about 115 kg with actuation. | Transverse architecture differs from F1 and no public overall dimensions. | Capacity reference only, not a candidate for the current longitudinal layout. |

Primary sources consulted:

- [Porsche — driving the 917/30 and its four-speed gearbox](https://newsroom.porsche.com/en_AU/2019/history/porsche-goodwood-members-meeting-andrew-frankel-917-19271.html)
- [D.M.A. Racing Gears — 1071-W-2WD](https://dmaracinggears.com/2wd-transaxle-sequential-1071-w-2wd/)
- [D.M.A. Racing Gears — S1098](https://dmaracinggears.com/2wd-transaxle-sequential-s1098/)
- [Hewland — LWS-200](https://motorsport.hewland.com/browse-products/?singleproduct=725)
- [Xtrac — P1192](https://www.xtrac.com/product/p1192-supercar-transverse-synchromesh-gearbox/)

## Torque screening

F9 provisionally reads « 1 600 ch » ("1,600 hp") as 1,600 mechanical hp at the
crankshaft, i.e. 1,193.1 kW. This unit and this point of application still have
to be confirmed. The mathematical conversion gives:

| Engine speed | Equivalent torque | Screening torque × 1.30 |
|---:|---:|---:|
| 7,000 rpm | 1,627.6 Nm | 2,115.9 Nm |
| 7,500 rpm | 1,519.1 Nm | 1,974.9 Nm |
| 8,000 rpm | 1,424.2 Nm | 1,851.4 Nm |
| 8,500 rpm | 1,340.4 Nm | 1,742.5 Nm |
| 9,000 rpm | 1,265.9 Nm | 1,645.7 Nm |

This calculation is not a measured engine curve: each row assumes that maximum
power is reached at that speed. The 1.30 factor is a provisional screening
filter, not a validated sizing rule. It shows that none of the public values
above allows the gearbox to be validated with a service margin, boost
transients and the thermal cycle. Even the S1098 at 1,300 Nm fails the F9
screening.

## Envelope used in the drawing

In the absence of a manufacturer's drawing, F0 reserves a volume of
**650 × 500 × 460 mm**: 550 mm ahead of the differential plane and 100 mm between
that plane and the engine face. This volume is deliberately identified as a
hypothesis; it must be neither read as a D.M.A./Hewland dimension nor used to
manufacture a carrier, a bellhousing or drive shafts.

## Dossier to obtain before freezing F1

The technical request to the manufacturer must cover at least:

1. a dimensioned general arrangement or STEP under acceptable confidentiality terms;
2. engine face to differential axis distance and the complete envelope with
   actuator, pump, filter and fittings;
3. relative height of the input shaft and the differential outputs;
4. permitted direction of rotation, bevel set position and compatibility with a
   rear mid-engine layout;
5. continuous, transient and per-gear torque for the planned engine speed,
   tyres, mass and duty cycle;
6. bellhousing, input shaft, clutch, starter and mounting to the flat-12;
7. drive shaft flanges, permissible angles and travel;
8. mass, centre of gravity, load-bearing points and permissible suspension loads;
9. oil flow, cooling, temperatures, sensors and maintenance;
10. specific validation of the reduced mode and of the 1,600 hp mode.

The selection therefore stays `null` in the F0 and F1 reports. The drawing
chooses an **architecture**, not yet a product.
