<a id="module-thermique--waterblocks-ventilateurs-et-peltier"></a>

# Thermal module: waterblocks, fans and Peltier devices

The owner proposes an enclosure inspired by the GemaTEG principle to improve
962 kit cooling. This option is added to the program as **a study of targeted
thermal regulation**. Its cooling capacity, envelope and automotive performance
are not established.

<a id="principe-retenu-et-limite-énergétique"></a>

## Selected principle and energy limit

[GemaTEG](https://www.gemateg.com/solution) describes active cold plates and
CPU/GPU temperature supervision. We retain the idea of local control, a
liquid loop and instrumented monitoring. Benefits published in that context
are not transferred to the engine. No internal GemaTEG drawing, firmware or
document is reused; this is not a GemaTEG automotive product.

A Peltier device pumps heat to its hot face, which also receives its electrical
consumption. The [Ferrotec](https://thermal.ferrotec.com/technology/thermoelectric-reference-guide/thermalref11/)
relations are `COP = Qcold / Pelectrical` and `Qhot = Qcold + Pelectrical`.
COP must come from the module at its actual operating point; its maximum
value or a commercial rating at zero ΔT is insufficient for sizing.

**Examples only**, assuming COP of 1, 90% DC conversion efficiency and a
14 V bus; pumps/fans are excluded because measurements are absent:

| Requested cooling | Electricity at TECs | Hot-face heat | Bus consumption | Bus current |
|---|---:|---:|---:|---:|
| 500 W | 500 W | 1,000 W | 556 W | 39.7 A |
| 1 kW | 1 kW | 2 kW | 1.111 kW | 79.4 A |
| 10 kW | 10 kW | 20 kW | 11.111 kW | 793.7 A |

Engine load is unmeasured and is not represented by any of these rows.
This is not the current of modules mounted directly on 14 V: it is the
upstream supply current of an assumed conversion. Converter losses and
auxiliary heat add to the overall balance; their rejection locations must be
defined. The alternator's mechanical load additionally needs its own
efficiency map; it is not calculated here.

The [scoping tool](source/thermal_budget.py) exposes all assumptions and rejects
non-finite or inconsistent values. It predicts neither temperature, actual
COP, airflow, module count nor radiator capacity.

```sh
python3 twins/962-cylinder-head-f0/source/thermal_budget.py \
  --cold-load-w 1000 --assumed-cop 1 --assumed-bus-v 14 \
  --assumed-dc-efficiency 0.9 --auxiliaries-w 0
```

<a id="architecture-proposée"></a>

## Proposed architecture

![Separation of main cooling and the TEC branch](derived/thermal-module.png)

The [editable SVG diagram](source/thermal-module.svg) represents heat transfers
and functions, not hydraulic routing or enclosure CAD.

| Function | Architecture to compare |
|---|---|
| Heads/cylinders and oil | Main liquid cooling and exchangers to outside air, capable of operating without TECs |
| Charge air | Air/liquid exchanger and low-temperature loop as the reference; optional TEC branch for targeted regulation or transients |
| Cold TEC branch | Cold waterblock, separate fluid, pump, sensors and bypass designed not to block main circulation |
| Hot TEC branch | Hot waterblock, pump and fan-cooled exchanger sized for Qhot, with an outside-air path |
| Control | Controlled TEC current; measurements of both faces, flows, voltages/currents, pressure and relevant humidity |
| Possible buffer tank | Transient energy reserve to quantify; does not replace steady-state heat rejection |

This separation is **an engineering proposal**, not a compatibility decision.
The two engine-bank circuits remain separate interfaces to measure.
Do not combine engine water, oil and the TEC circuit in one fluid for
convenience alone. The hot side must not heat the air drawn into the charge-air
cooler or recirculate hot air into the engine.

A temperature reduction justifies the active branch only if the measured
benefit warrants its consumption, mass, complexity and maintenance.
Compare at least an improved conventional exchanger, the TEC branch and,
if subambient cooling is needed, a compression option; no compressor COP
is assumed and no equipment is selected.

<a id="contraintes-à-fermer-avant-une-cao-fonctionnelle"></a>

## Constraints to close before functional CAD

- Measure engine, oil and charge-air thermal loads and transients separately.
  For a liquid loop: mass flow, composition, Cp(T) and inlet/outlet temperatures;
  for air: flow, pressure and temperatures.
- Obtain Qcold/Pelectrical/COP curves at both face temperatures, including aging
  and module limits, then qualify contacts and clamping. The enclosure must not
  transmit mounting loads into fragile modules without validated mechanical support.
- Establish **electrical and mechanical** budgets, alternator/DC capacity,
  fuses/wiring, pump/fan consumption and the overall heat balance.
- Check radiator, airflow and recirculation at adverse ambient temperature,
  idle and load. A fan redistributes air; it does not eliminate the watts to reject.
- Define condensation control using the **local** dew point, humidity and
  pressure at the location considered. External surfaces and compressed intake
  air do not necessarily share a dew point. The [NWS](https://www.weather.gov/asos/AmbientDewPointTemperature.html)
  describes measurement of this threshold by condensation on a Peltier-cooled surface.
- Validate degraded modes: TEC stopped, lost flow, fan/pump failure, hot-side
  overtemperature, sensor failure and leakage. Reference cooling must remain
  available; the engine builder sets load limits and protective shutdown.
- Qualify pressure, vibration, thermal shock, corrosion, insulation, sealing
  and enclosure access in the vehicle. No material, connection, location or
  dimension has yet been selected.

The first proposed experiment is an electrical thermal bench with a resistive
load and measured transfers, before any engine installation. Compare TEC
off/on under identical load and external conditions; close
`Qhot ≈ Qcold + Pelectrical`, including losses and uncertainties.
Active control is retained only after observing a useful benefit within
budgets and without degrading reference operation.

Unknown requirements are retained in [thermal-module.json](thermal-module.json).
This study performs no purchase, pressurized prototype, supplier contact or
copying of GemaTEG geometry or firmware. The [kit program](KIT_962_PROGRAMME.md)
remains the commercial target; its qualification does not follow from this calculation.
