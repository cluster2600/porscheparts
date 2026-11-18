# Interface ledger and comparison basis — 12 November 2026

Additive revision for [issue #396](https://github.com/cluster2600/porscheparts/issues/396),
gate `G03-measured-interfaces-and-basis`. It follows the
[recovery revision](../recovery-20261106/README.md) and changes no earlier
revision directory and nothing under `evidence/`.

**Result: the gate is `investigated`, not passed.** No interface and no
operating condition of the turbo is measured, and no physical turbocharger is
identified for a measurement to refer to. The unchanged evaluator refuses the
gate for four named blockers. Until they are lifted, the only comparison the
evidence supports is a provisional synthetic one, between two concept housings
that share one concept wheel, at declared hypothetical operating points.

No mesher, solver, container or remote host was run. The recurring turbo
automation stays paused. No dimension, speed, pressure, temperature or map
point was invented.

## What this revision contains

| File | Content |
|---|---|
| [PLAN.md](PLAN.md) | Method, acceptance criteria and limits |
| [source-allowlist.json](source-allowlist.json) | 21 committed files allowed as turbo sources, 73 exact spans, the exclusions |
| [turbo-corpus.json](turbo-corpus.json) | The documentary snapshot derived from the allowlist (76 documents) |
| [turbo-retrieval-cases.json](turbo-retrieval-cases.json) | 30 frozen retrieval cases |
| [known-citations.json](known-citations.json) | 26 citations written from the cited files |
| [interface-ledger.json](interface-ledger.json) | 79 interface and operating-condition entries, 14 missing-data gates |
| [conventions.json](conventions.json) | Quantities, signs and reference conditions |
| [gate-ledger.json](gate-ledger.json) | Ledger revision: only G03 changes |
| [G03-attestation.json](G03-attestation.json), [G03-evaluation.json](G03-evaluation.json) | What was submitted to the unchanged evaluator, and its verdict |
| [prerequisites.json](prerequisites.json) | Gate-level confirmation of #394 and #395 |
| [retrieval-receipt.json](retrieval-receipt.json) | Recorded retrieval evaluation |
| [host-observations-20261112.json](host-observations-20261112.json) | Read-only host inventory and the steps skipped |
| [basis.py](basis.py) | The checker and the convention functions |

## Prerequisites

Issues #394 and #395 are closed, but closure is not admission. The unchanged
[`baseline.py`](../baseline-20261106/baseline.py) validates the recovery
ledger, in which `G01-baseline-frozen`, `G01-execution-contract` and
`G02-evidence-recoverable` are `engineering_passed`, and it still accepts their
recorded attestations with no reason against. [prerequisites.json](prerequisites.json)
keeps that evaluation; `basis.py check` repeats it.

## Authorised sources and the FTS5 corpus

[`knowledge.py`](../../../benchmarks/free-tools/knowledge.py) is used
unchanged: its snapshot format, its index, its context contract and its
30-case evaluation. What is new is the turbo contract around it.

The allowlist names each source file with its SHA-256, its rights, a
**variant identity** and, per span, the **units** the span carries. A span is
either verbatim lines or one JSON node, so every corpus text is exact; only the
titles are authored retrieval labels. The sources are the turbo's own
generators, parameter files, contracts and evidence, the paired comparison
contract, and the repository's reviewed research registers for the K16 family.
For a register record the licence of each third-party source is copied from
its `catalog/sources` record; the registers hold factual notes, never the
publisher's document.

Thirteen variant identities keep things apart. The two that matter most: the
concept pair (`baseline.json` against `candidate.json`) and the stock 993 K16
units, which the concept explicitly does not reproduce. Every K16-family
record is labelled `published_other_variant` and is never transferable.

Excluded by rule, and enforced: the carrier corpus and cases, the carrier
catalogue record and study files, every report under `docs/reports/`, the
engine-mount twin, the training packs and the workshop-manual register. The
twin's own README is excluded too, because later revisions edit it; the frozen
files it summarises are cited instead. No status in the corpus means
"measured", because no admitted turbo measurement exists.

### Retrieval tested against known citations

The index is rebuilt in a private temporary directory and discarded.

- The unchanged evaluation passes **30 of 30** frozen cases: 10 references,
  10 unknowns, 5 conflicts, 5 hostile.
- **26 of 26** known citations are retrieved, each with its exact phrase, its
  locator (file and lines, or file and JSON pointer), its variant identity,
  its evidence status and its units, and each excerpt still equals the span
  read back from the pinned file. 25 come back first and one second.
- Each unknown case must return, first, a document that says the value is
  unknown or null. For example "What is the measured stock K16 shaft speed?"
  returns the register's own `UNKNOWN-004`.
- Four conflict cases are real ones the ledger has to keep apart:
  100,000 rpm is a case-generator default in one source and a supplier's
  balancing condition in another; "pressure ratio" is outlet-static over
  inlet-total in the case generator and total-to-total on a published map;
  three different reference conditions for corrected flow coexist; and the
  wheel-to-housing distance depends on the variant. The fifth is a synthetic
  control.
- The hostile fixture, which asks to mark the gate passed and a clearance
  measured, is retrieved as data for a genuine clearance question and changes
  nothing.

Retrieval is documentary. It finds what the repository says; it measures
nothing.

## Interface and operating-condition ledger

[interface-ledger.json](interface-ledger.json) has one entry per interface or
condition the issue names. Every entry is bound to a missing-data gate, because
none is measured.

| Group | Entries | With a labelled study value | Null |
|---|---:|---:|---:|
| Reference identity | 1 | 0 | 1 |
| Rotor and stator | 23 | 19 | 4 |
| Nut | 4 | 3 | 1 |
| Ports | 9 | 5 | 4 |
| MRF interface | 6 | 5 | 1 |
| Clearances | 8 | 4 | 4 |
| Shaft speed | 4 | 3 | 1 |
| Pressure and temperature boundary conditions | 15 | 9 | 6 |
| Reference geometry | 9 | 6 | 3 |
| **Total** | **79** | **54** | **25** |

A study value is not a measurement. It carries one of three labels, the file
and span it comes from, and a literal that must be found in that span. The span
must be one of the spans the allowlist selects in that file; a value whose
literals sit in two selected spans cites both:

- `assumed` (35): a design or operating hypothesis fixed by a generator or a
  parameter file. The hypotheses already used by the historical CFD are here
  and stay hypotheses: 100,000 rpm, inlet total pressure 101,325 Pa, inlet
  total temperature 298.15 K, outlet static pressure 121,590 Pa
  (static-to-total ratio 1.2), γ = 1.4, R = 287.05 J/(kg K), adiabatic walls.
- `model_derived` (4): computed or estimated from the concept geometry, such
  as the 1.7858 mm radial separation bound, which is not a running clearance.
- `numerical_construct` (15): an idealisation of the numerical domain with
  nothing physical to measure, such as the rotating zone (radius 32 mm,
  Z from −4 to +33 mm), the rear closure of radius 35.5 mm and the port planes.

The concept wheel's assumed diameters (60.5 mm and 40.6 mm) equal a
single-vendor declaration for a K16 unit. The ledger records that as published
context only: the declaration is not a measurement, it is unconfirmed, and the
concept is not a K16.

Promoting a field to measured needs an admitted measurement record, the
instrument, method, datum, specimen, licence, repeats, a numeric uncertainty
and a review independent of the contributor, as
[decision 0019](../../../docs/decisions/0019-accept-contributed-measurements.md)
requires. The linked record must pass the repository's measurement validator,
be a physical measurement (not a documented specification) of the same
specimen, and hold a reading whose value, unit, method, instrument, number of
samples and uncertainty are the field's. `basis.py check` refuses anything less.

## Essential missing measurements

| Gate | Missing | Needed before |
|---|---|---|
| MD-01 | Which physical turbocharger the interfaces refer to, and its identification | G05, G08, G09, R2 |
| MD-02 | Rotor metrology: diameters, blade count and profile, bore, mass and inertia | G05, G08 |
| MD-03 | Housing and port metrology: volute, diffuser, tongue, spigots, CHRA register; a licensed scan or drawing | G05, G08 |
| MD-04 | Clearances: tip and shroud, back-face and nut gaps, axial and radial play | G05, G08 |
| MD-05 | Rotor joint, nut thread and torque, balance record | G05, R3 |
| MD-06 | A compressor map with measured inlet and outlet states and its correction reference | G08, R2 |
| MD-07 | Measured operating shaft speed and the maximum permissible rotor speed | G08, R2 |
| MD-08 | Turbine-side state, gas flow and wastegate position | G09 |
| MD-09 | Engine operating points per bank | G09 |
| MD-10 | Oil, bearing and thermal state; thermal growth of the clearances | G09, R2 |
| MD-11 | Materials, processes and allowables | R3 |
| MD-12 | Datum scheme, declared frame and tolerances | G05, R3 |

MD-01 to MD-07 are essential before a compressor comparison can leave
synthetic scope. MD-01 comes first: with no unit named, a measurement has no
specimen. The project buys no part and commissions no measurement. Each gate
therefore states what an outside contributor could be asked for under decision
0019, through the [capture protocol](../../../docs/CAPTURE_PROTOCOL.md) and the
[measurement campaign](../../../docs/MEASUREMENT_CAMPAIGN.md). Map datasets
sold by quotation are not pursued.

Two further gates are not measurements. MD-N1 is the sensitivity of the result
to the numerical idealisations, which belongs to the mesh and solver gates.
MD-N2 is the equivalence of the representations, which belongs to #397 and #398.

## Quantities and conventions

[conventions.json](conventions.json) fixes the definitions before any
comparison is computed; `basis.py` implements them.

| Quantity | Definition |
|---|---|
| Mass flow `ṁ` | Solver output at imposed back-pressure, over the inlet and outlet sections outside the rotating zone; never imposed |
| Corrected mass flow | `ṁ · √(T01 / T_ref) / (p01 / p_ref)` |
| Corrected speed | `N / √(T01 / T_ref)` |
| Total pressure ratio | `p02 / p01`, absolute total pressures; not the static-to-total ratio the case generator takes |
| Total temperatures | Mass-flow-weighted at each section; `T01` is imposed, `T02` is an output |
| Shaft torque | `τ = −M_z`, with `M_z` the fluid-on-rotor moment about +Z |
| Shaft power | `P = ω · τ = −ω · M_z`, sign kept, positive for a compressor |
| Efficiency | `(π_tt^((γ−1)/γ) − 1) / (T02 / T01 − 1)`: an adiabatic-wall model efficiency of the idealised domain |

Reference conditions for corrected values are **288.15 K and 101,325 Pa**.
They are a convention, not a measurement: they are the one flow reference a
repository register already uses. A published map has its own (one in the
corpus states 981 mbar and 293 K), so a corrected value is compared with
another only after both are brought to the same reference, and every corrected
value is reported with its pair. The functions take the reference as an
explicit argument.

The corrected-flow function reproduces the 20 illustrative points of the
2026-10-02 research register, which were computed independently of it. At the
hypothetical operating point the conventions give a corrected speed of
98,308.7 rpm and a corrected flow 1.0172 times the actual flow. That is
arithmetic on hypotheses. No flow, torque, power or efficiency exists to report.

## Gate state

The [ledger revision](gate-ledger.json) inherits the opening rule, the
comparison contract and every other gate unchanged. G03 moves from
`not_started` to `investigated`, gains eight configuration pins and three
receipts, and keeps its two original blockers beside two more precise ones:

1. `no-measured-operating-conditions`
2. `no-measured-interfaces`
3. `no-physical-reference-variant`
4. `no-admitted-compressor-or-turbine-map`

Submitted to the unchanged evaluator, the [attestation](G03-attestation.json)
is [refused](G03-evaluation.json) for exactly those four reasons and no other:
the prerequisites, the pins and the receipts are in order. G05, G08 and G09
depend on G03 and stay closed.

## Not done, and why

- **CloudCompare** was not used. No turbo surface is committed in the
  worktree, and the runtime matrix records the CloudCompare image identity as
  unknown. A local image exists on the host; it was not run.
- **Qwen** was not used.
- **No web research.** The repository's registers already cover the K16
  family with recorded rights, and none supplies a map or a measurement for
  the concept. Two standards are named in `conventions.json` as unverified
  leads; nothing is taken from them.
- **The runtime matrix is not revised.** Its SQLite FTS5 row still reads
  "carrier and synthetic controls only" and has no pinned identity, so G03
  binds no runtime. SQLite 3.45.1 was observed on this host.
- **The automation's state** could not be observed from this host. It was last
  recorded paused on the Mac, and this work started nothing recurring.
- The retrieval cases were tried once while being drafted; none was changed
  or removed afterwards.

## Verify

```sh
python3 twins/bionic-turbo-f1/basis-20261112/basis.py check
python3 twins/bionic-turbo-f1/basis-20261112/basis.py gate
python3 twins/bionic-turbo-f1/basis-20261112/basis.py retrieval
python3 -m unittest tests.test_bionic_turbo_basis
```

`check` exits 0 on the committed files. `gate` exits 1 and prints the four
refusals: that is the recorded verdict, not a fault. The 22 focused tests also
show that a carrier document, a stale hash, a moved span, an unsourced value or
a field marked measured without evidence is refused.

## Next permitted action

Issue #397 may proceed on its own prerequisites. Whether the roadmap continues
as an explicitly provisional synthetic comparison, or waits for MD-01 to MD-07,
is a decision for the owner; it is not taken here. Nothing in this revision
authorises geometry admission, meshing, CFD, a performance claim, fabrication
or a physical test.
