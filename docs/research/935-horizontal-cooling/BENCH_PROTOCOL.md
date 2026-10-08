# Bench protocol for the horizontal 935 system

This protocol prepares future tests of the reference and of the variant.
It gives no authorized speed. The maximum speed, vibration thresholds,
temperatures, loads and lubrication conditions remain to be
defined by the mechanical review and the component data. The
[measurement contract](../../../twins/935-horizontal-cooling-system-f0/measurement-contract.json)
keeps the fifteen existing channels and their unknowns.

## Dossier to freeze before testing

Associate a specimen identifier and the CAD/mesh digests with the
bill of materials, the interfaces, the actual material of each part, the printing
process, the orientation, the treatments, the machining and the inspection.
Check the seats, clearances, fasteners and shaft retainers.
Record the balancing, the housing configuration and the pressure stations.
The historical reference and the variant are two distinct configurations.

The bench uses a controlled drive, independent speed measurements
at the input and at the rotor, a torque measurement and an enclosure suited to the rotor.
The shutdown protocol follows from the documented limits of the parts and the bench.
Any overspeed test is the subject of a specific protocol, after
the initial characterization. This document triggers no physical test.

## Acquisition and calculations

| Measurements | Placement and processing |
|---|---|
| Input/output speeds | Independent sensors; positive direction defined per axis and view; signed ratio and slip measured. |
| Input and rotor torque | Calibrated chains; `P = 2π n τ / 60` for `n` in rpm; losses from the difference of powers after stabilization. |
| Flow | Calibrated flow-measurement device in the bench circuit; keep actual volumetric flow, mass flow, temperature and absolute pressure. |
| Pressures | Identified upstream/downstream stations and probes; distinguish static and total; keep the same reference frame as the CFD. |
| Vibrations | Mount accelerometers and rotor phase measurement; spectra, orders and evolution with speed. |
| Temperatures | Inlet/outlet air, housing, bearings and lubricant as accessible; common timestamping. |
| Lubrication | Pressure, temperature and supply actually defined for the angle drive; check losses and leaks. |

Document sensor number, position/reference mark, calibration before/after,
sampling frequency, filtering, synchronization, unit and uncertainty.
The vibration acquisition frequency must resolve the orders studied,
with an anti-aliasing filter; it depends on the identified speeds and gear teeth.
The blade-passing frequency is `Z |n| / 60`. The current geometric
count gives nine blade regions; confirm this number on the specimen.

Keep the raw data and the averaged windows. Estimate the uncertainty
of flow, pressure, torque and power from the measurement chains.
Do not confuse the allowable test errors with the solver convergence
thresholds.

## Sequence

1. Transmission alone: controlled ramp-up within the authorized envelope, check
   of the ratio, directions, vibrations, lubrication and losses.
2. Rotor and housing on the bench: for each selected speed, vary the
   circuit resistance; measure flow, pressure and torque up to the documented
   allowable domain. Keep a common measurement station across variants.
3. Repeatability: repeat points, repeat at stabilized temperature and
   compare ramp-up/ramp-down. Record drifts and interventions.
4. Validation: reserve points before any model adjustment; compare
   predictions and measurements with their uncertainties and the pre-established tolerances.
5. Installed system: add the engine passages and loads only
   once the variant, the interfaces and the network are identified.

The comparison aims for more useful air at comparable absorbed power,
counting the transmission. Also keep mass, inertia, running clearances,
temperatures and vibration. An increase in free flow does not prove an increase
in installed cooling.

## Archiving and status

Each series references the configuration, the native files, the versions,
the sensors, the conditions and the SHA-256 digests. Separate the calibration
data from the points reserved for validation. The status
"physically validated operation" requires the results of these tests
and their review; it remains false in the current digital deliverables.
