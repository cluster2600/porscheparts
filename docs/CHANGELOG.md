# Changelog

All notable changes to the project are recorded in this file.

## Unreleased

Decision 0008, modern magnesium beats titanium, September 11, 2026:

- the 1995 cover does not rot because it is magnesium, but because it is
  magnesium **from 1995**: standard purity and hexavalent chromate conversion;
- what has changed — magnesium corrosion is driven by three internal
  impurities, iron, nickel and copper; the ASTM limits for AZ91D cap them at
  0.004 / 0.001 / 0.015 %, and high purity is given as **up to 100×** more
  resistant to salt spray, more than cast 380 aluminum or cold-rolled steel;
  PEO replaces chromate conversion, without hexavalent chromium;
- final comparison: modern magnesium wins **both** plate-bending indices
  (1.965 and 6.988), removes the galvanic couple since it is the same material
  as the case, cancels differential expansion and addresses the failure mode at
  its root;
- titanium is ruled out on these numbers: heavier, less stiff, and carrying the
  worst galvanic couple in the grid against a magnesium case;
- lesson recorded: three times in this project the right answer has been the
  original material done properly — the question to ask first is not "what to
  replace it with" but "what can we do today that we could not do then";
- obstacles not investigated: a shop able to machine magnesium, a PEO thickness
  of 5 to 40 µm on a sealing face, and availability as AZ31B plate rather than
  cast AZ91E.

The original part is magnesium, not aluminum, September 11, 2026:

- major correction: the factory-fitted 964/993 chain housing covers are **cast
  magnesium**, and their failure mode is corrosion of the sealing faces — that
  is the reason the billet cover market exists;
- every mass comparison run so far set titanium against aluminum, hence
  **against the aftermarket product and not the original part**;
- redone against magnesium at 1.81 g/cm³: titanium is 2.45× denser and loses
  **both** plate-bending indices, strength included, 6.503 versus 6.988 —
  "stronger, therefore lighter" does not hold here;
- on the other hand, the corrosion criterion of `TITANIUM.md` now applies in
  full, and it is a stronger argument than mass;
- new, unresolved obstacle: the mating case is also magnesium, and the
  titanium/magnesium couple is the least favorable in the grid — a titanium
  cover could shift corrosion onto the part that cannot be replaced;
- bug fixed in the screening: a mitigation whose text admitted it was
  "unresolved" counted as a mitigation; the script now raises an error.

Plate-bending performance indices, September 11, 2026:

- the mass trade-off is restated with Ashby indices: at imposed stiffness
  `E^⅓/ρ` gives 1.526 for aluminum versus 1.095 for titanium, aluminum wins;
  at imposed strength `σ_y^½/ρ` gives 4.969 versus 6.503, titanium wins by
  31 %;
- "titanium is stronger, therefore thinner, therefore lighter" is thus
  correct, on the condition that strength is what sizes the part;
- note added: in pure tension `E/ρ` is 25.9 and 25.7, the two materials are
  equivalent; it is the ⅓ exponent of plate bending that makes the difference;
- for this cover, four observations converge on "neither stiffness nor
  strength sizes it" — 9.7 Nm tightening torque, M6 fasteners hence probably
  short bolt spacings with a deflection in `L⁴`, negligible case pressure, and
  a cast part; in that case thin machined titanium is lighter.

Cover expansion margin redone, September 11, 2026:

- two errors corrected at once. The formula compared the expansion of an
  entire face to a **radial** clearance, which overstated the problem by a
  factor of two; what must fit within the clearance is the offset at the hole
  farthest from the fixed point, hence `δ = r · Δα · ΔT`. And the fasteners
  were assumed to be M8 while the manual tightens this cover to 9.7 Nm, i.e.
  M6;
- result: **0.072 mm of offset versus 0.300 mm of clearance** in medium-fit
  M6, with only **24 %** of the clearance used instead of the 72 % announced;
- sensitivity published over six combinations of hole and fixed point: all
  pass, the tightest — dowel location and close-fit hole — using 72 %;
- `--datum dowel` option added: plate 103-05 shows a locating dowel
  `993 105 175 00`, and if it holds the cover the unfavorable radius doubles;
- installation assumption declared: bolts centered in their holes when cold,
  otherwise half the margin is an assembly tolerance and not a reserve;
- mass threshold made decidable: titanium machined to the strictly necessary
  stiffness beats the casting as soon as the casting carries **39 % more
  thickness than its stiffness requirement**, and LN Engineering's 6061
  billet cover, free of casting constraints, measures that excess directly;
- the 9.7 Nm torque on M6 points the same way: low clamping, low gasket
  reaction, a part that carries almost no load;
- correction propagated to the camshaft housing, where the decisive reason is
  requalified: it is not hole clearance that governs but the alignment of the
  camshaft bearing faces, which has no clearance to consume.

Acquiring dimensions without access to parts, September 11, 2026:

- online search for the dimensions of cover `964 105 107 01`: **none are
  published**, but the search establishes something else — two independent
  reproducers, LN Engineering in 6061 aluminum and Auto-Service Schefter in
  CNC, confirm that the part number is the **left** cover, that it is paired
  with gasket `964 105 181 01`, and that the part is made **by machining from
  solid**, which until now was only reasoning;
- both reproducers use aluminum: titanium is a deliberate departure;
- the workshop manual gives "Chain housing cover : 9,7 Nm" (9.7 Nm), which
  puts the fasteners at **M6** and not M8 — the expansion margin computed on an
  M8 assumption must be redone;
- strategy recorded: the right question is not where to find the dimensions
  but what is the cheapest object that carries them — the $13 gasket gives
  outline and bolt spacings, a used cover gives everything, and neither
  requires access to a car.

The whole factory catalog dispositioned, September 11, 2026:

- `scripts/dispose_pet_catalogue.py` gives a category and a reason to the
  **1,026 designations**: not a single silent loss anymore, where 956 used to
  drop out without a reason;
- 373 designations investigated by hand, versus 72 before; **zero**
  designations remain without a verdict;
- `muffler`, 12 part numbers, rises out of the batch: the lexical triage had
  missed it because its name contained no vocabulary term, and together with
  the tip it is the best titanium candidate on the car; `y-piece` joins it;
- the verdict now covers everything judged and not only the 70 designations
  the vocabulary recognized — the pool grows from 7 to 9;
- limitation counted rather than hidden: **50 generic designations, 751 part
  numbers**, where the word does not name a function — `support` covers 142 of
  them — and which require part-number-by-part-number work, not done.

Chain housing cover 964 105 107 01 in Ti-6Al-4V, September 11, 2026:

- part explicitly requested; at equal geometry titanium adds 64 % of mass, but
  there is no reason for the thickness to stay equal, and the opposite claim
  was an error;
- thickness equivalence computed on three criteria: at equal bending
  stiffness titanium is 85 % of the thickness and stays 1.39 times heavier; at
  equal strength it is 46.6 % and becomes 24 % lighter; at equal mass it is
  60.9 % and keeps only 37 % of the stiffness;
- third case recorded, the most likely for a cast part: the original thickness
  is dictated by the foundry — minimum wall, draft, filling — and a machined
  part has none of these constraints, so it can be thinner while staying stiff
  enough; `D03` and the eye will decide, not the calculation;
- parametric screening: differential expansion against the aluminum case is
  0.144 mm over a 100 mm bolt spacing at 100 K, and fits within the 0.200 mm
  clearance of a Ø8.4 hole for M8 bolts, margin +0.056 mm;
- that is what separates the cover from the whole case, rejected on these
  grounds: beyond a bolt spacing of about 139 mm at the same clearance, the
  margin disappears;
- the galvanic couple is already handled by the bill of materials: gasket
  964 105 181 01 separates the two metals over the whole sealing face;
- route chosen: **milling** from Ti-6Al-4V plate, not printing — none of the
  three additive families;
- measurement plan published, thirteen dimensions of which two decide: the
  bolt spacings and the internal clearance to the chain.

Querying the screening on a specific part number, September 11, 2026:

- `scripts/explain_pet_reference.py` and the `pet-explain` target answer part
  by part: designation, plates, triage score, reasons, and judgment;
- it says explicitly when a designation has **never been judged**, instead of
  implying a rejection — a designation dropped by the vocabulary used to
  disappear silently;
- `993 102 050 01`, crankshaft pulley, investigated in answer to a question:
  ruled out, on four independent grounds.

The 70 factory-catalog designations investigated, September 11, 2026:

- `catalog/manufacturing/pet-candidate-judgements.json` judges the 70
  designations kept by the triage: presumed original material, actual benefit
  of titanium, presumed class, additive families;
- `scripts/screen_pet_candidates.py` **derives** the verdict from these
  entries and refuses to run if a written verdict no longer follows from its
  reasons — the guard that previous screenings lacked;
- **seven designations deserve a record**, covering 40 part numbers, six of
  them new; they form a single family, the hot-air and secondary-air circuit
  around the exhaust heat exchangers;
- this pool passes because it is hot without being at gas temperature, made
  of sheet steel and not aluminum, thin and consolidatable, and benign in
  failure;
- the 63 rejections are mechanically justified: titanium does not improve on
  the original material, presumed-critical domain, no additive family, or
  physical impossibility for a heat exchanger whose function is to conduct
  heat;
- `docs/993/993_BACKLOG_TITANE.md` publishes the three denominators side by
  side so they stop being quoted for one another.

SAFETY.md rewritten and chain housing investigated, September 11, 2026:

- `SAFETY.md` rewritten: classes, presumed-critical domains, downgrade rule
  and reporting kept identical, with the addition of what the project has
  learned — failure mode outranks domain and fire is its forgotten case, a
  screening authorizes nothing, service temperature is checked against the
  alloy's ceiling, disassembly is part of the part's life, process and
  material are two separate judgments, and raising a class requires six named
  pieces of evidence while lowering it requires none;
- chain housing of plate 103-05 investigated: eight part numbers established,
  including three bridges, two of which are also designated oil galleries;
- verdict: a genuine case for additive consolidation, but titanium rejected
  three times — differential expansion with the aluminum case, galling on
  re-cut threads, galvanic couple; the answer is aluminum;
- two corrections to the screening, the first of which was wrong: making the
  five contraindications disqualifying removed the words "not addressed" and
  "not controlled" that the grid contains;
- corrected model: a contraindication is a **condition to be lifted**, which
  blocks without a declared mitigation and becomes a requirement carried into
  the route when a mitigation is declared; only the two physical
  impossibilities remain absolute, conducting heat and keeping the stiffness
  of steel;
- missing criterion added, and it was the deciding one: **does titanium
  improve on the original material?** The grid already asked it — "corrosion
  problematic with the original material" — and without it the screening
  ranked a lukewarm aluminum intake manifold first;
- the report now carries its own denominator: 33 records, not 6,259 part
  numbers, and says so in `scope_warning`.

Turbo oil circuit investigated and ruled out, September 11, 2026:

- identity established from factory plate 202-16: four `oil pipe` in two
  positions, three `vent line`, two `oil collection container`, two `bracket`;
- four Porsche part numbers entered in the repository record, which carried
  none;
- correction recorded: the record calls itself "return" without the plate
  establishing it; the feed/return assignment remains to be done;
- rejection justified twice — the failure mode is fire in the sense of
  `SAFETY.md`, and the `TITANIUM.md` grid rules out titanium on repeated
  threading exposed to galling;
- conclusion: the best additive candidate in the triage is not a titanium
  candidate; the two questions are not the same.

Titanium triages of the factory catalog, September 11, 2026:

- finding that the titanium screening covered 32 records, i.e. 0.51 % of the
  6,259 distinct part numbers in the 993 catalog: "applied to the catalog" was
  an overstatement of scope, corrected in an addendum to decision 0007;
- `screen_pet_zones_for_titanium.py` triages the 239 illustrations of the
  skeleton using only repository data, 23 zones kept out of 1,538 part
  numbers;
- `screen_pet_parts_for_titanium.py` triages 1,026 designations from a
  transcription kept outside the repository, 70 kept, publishing only the
  short list;
- the exhaust tip comes out in the top four of the broadened triage, the two
  designations ahead of it falling on exhaust temperature;
- per-plate exclusion rule corrected: it applies only if all the plates of a
  designation are critical, otherwise `oil pipe` wrongly disappeared.

Decision 0007, first titanium part selected by grid, September 11, 2026:

- `scripts/screen_titanium_candidates.py` applies the `TITANIUM.md` grid and
  the three additive families to the 32 records, refusing to run if a record
  is not judged; only five parts are eligible;
- `993-EXH-OVAL-TIP-TI-F1-0001` chosen at +6, the exhaust manifold being ruled
  out despite its +7 because 900 °C is a nickel case;
- tip generator parameterized by `--material`, one geometry and three material
  cards, with STL export and temperature verdict;
- step 02 `passed`, step 03 `completed_screening` at 4,936 layers of 30 µm;
- two mutually exclusive titanium route cards: Ti-6Al-4V is available
  everywhere and blocked by a −27 °C margin, Ti-6242 passes the temperature
  and has no machine, no layer thickness and no supplier;
- generic temperature gate added to `build_process_route_card.py`;
- finding: the decision hinges on 427 °C never measured, and an infrared
  thermometer settles what twelve thousand lines of calculation will not.

Decision 0006, the ring will be turned in 6063 T6, September 11, 2026:

- turning route card `cnc-turning-6063-t6-bright-anodised.json`, grade chosen
  on appearance with 6061 T6 as fallback and 6262 ruled out for its lead;
- generator `scripts/build_turning_route_card.py` and associated turning
  quote, targets `turning-trim-ring` and `turning-trim-ring-check`;
- the ring's `preferred_process` changed from `undecided` to `CNC`, LPBF
  remaining a screened candidate;
- twin renamed `twins/993-switch-trim-ring-f1`, the directory name no longer
  asserting a material the repository has ruled out;
- finding recorded: changing process closed neither of the two gates that
  matter, the untoleranced fit dimension and the undefined edges.

Decision 0005, the ring's material was never chosen, September 11, 2026:

- finding that AlSi10Mg is inherited from the repository's only process card,
  and that the ring is the only `non_critical` LPBF candidate in the catalog;
- two sources on anodizing: AlSi10Mg anodizes gray-brown because of its 9 to
  11 % silicon, while 6063 T6 is excellent for bright anodizing;
- consequence recorded: for this part the material question and the process
  question are one and the same, and the likely answer is turned 6xxx bar.

First LPBF sourcing pass in China, September 10, 2026:

- four source records qualified for Unionfab, JLC3DP and Eplus3D;
- Unionfab kept as the only candidate, JLC3DP ruled out for lack of AlSi10Mg
  in its metal catalog;
- three contradictions recorded and not smoothed over: three layer
  thicknesses for the same subject, two of them from the same supplier, a
  provider material card far below the EOS coupons, and a minimum-wall rule
  the ring passes with one supplier and not the other.

Material-machine-process card for the switch trim ring, step 04, September 10,
2026:

- added `scripts/build_process_route_card.py`, a generic generator of a route
  card and a quote-request package linked to the files by SHA-256, with eleven
  gates evaluated and a `--check` mode;
- first step 04 of the AM pipeline, on `993-INT-SWITCH-TRIM-RING-F1-0001`,
  concluded `blocked_missing_input` with seven gates closed;
- internal inconsistency uncovered: the step 03 screening settles on 50 µm
  when the only published AlSi10Mg route on the EOS M 290 is at 30 µm;
- targets `route-trim-ring` and `route-trim-ring-check`, and guard
  `tests/test_993_switch_trim_ring_route_f1.py`, which fails if a gate opened
  without a coupon, heat treatment or powder lot.

993 Turbo/GT2 intercooler bracket Ti-6Al-4V F0, September 8, 2026:

- creation of an F1 twin record limited to the supplier envelope and the
  PorscheFanatics/PET identities;
- three quadratic Gmsh/CalculiX meshes run on the exact STEP, with regression
  convergence obtained on the p95 and the deflection;
- OpenUSD conversion and minimal validation through the locked NVIDIA
  workflow, without physics attribution, GPU or PhysicsNeMo;
- LPBF choice reduced to a conditional candidate against the CNC and sheet
  metal routes, all manufacturing and fitting gates remaining closed.

993 engine cooling subassembly F0, September 8, 2026:

- composition of the F0 housing and fan in a dedicated interface twin;
- cold clearance and free-when-hot calculation, exact BRep intersection check
  and explicit rejection of the 40,388.378651 mm³ collision;
- conversion of the two STEP files and composition of the assembly into
  minimal OpenUSD on Linux AMD64, with NVIDIA preflight and minimal
  validations passing without a GPU;
- SimReady properties, PhysicsNeMo, manufacturing, rotation and engine
  start-up kept closed.

917-inspired F34 four-valve air-cooled cylinder head, September 2, 2026:

- parametric CAD and process STEP generated locally from only the interfaces
  observable in the two scans, without republishing the raw scans;
- external cooling computed separately with OpenFOAM 14 (finite volumes) and
  FluidX3D (LBM), cycle cross-checked with Cantera and Wiebe, then a sequence
  of three CalculiX meshes;
- `linux/amd64` images of the CAE chain and of FluidX3D built and tested;
- all metal printing and engine start-up gates remain closed, in particular
  for scale, hot material properties, convergence, fatigue/TMF and the absence
  of physical correlation.

Phase 1, batch 1 — official catalogs, accessible manuals and measurements:

- thirteen new source records verified one by one on August 28, 2026;
- actual access statuses recorded, including refusals, paywalls and dead URLs;
- inventory log and justified list of rejected sources.

Phase 1, batches 2 and 5 — German research, scans and measurement handoff,
August 30, 2026:

- register brought to 225 valid source records, with manufacturers, forums,
  declared measurements and CAD/CT/LiDAR leads assessed separately;
- no calibrated, freely reusable 993 scan added, and no third-party file
  copied without an established license;
- two distinct German leads added: 964/993 bumper brackets with declared
  commercial dimensions, and an amateur repair of the sunroof deflector with a
  part number;
- prioritized measurement campaign for the three polymer pilots, with handoff
  procedure, confidentiality rules and an optional CT brief.

Compute environment:

- two container images, `recon` (CUDA) and `cadsim` (CPU), with a smoke test;
- toolchain redirected toward scriptable commands and APIs (ADR 0002);
- deployment procedure on a rented GPU machine and data hygiene rules.

Phase 1, batch 7 — Porsche Fanatics manual and data, August 30, 2026:

- provenance bridge to the public Porsche Fanatics index: 235 procedures,
  195 tightening torques and 111 technical data entries;
- French mapping of the manual's pages and values, with separation of the
  ROW/USA, Carrera/Carrera 4/Carrera 4S and Carrera RS variants;
- Printables lead added for the 964/993 console switch bracket, without
  copying the file and with the license not yet verified;
- exhaustive quantitative register added: 111 technical data entries, 195
  torques and 2,190 OCR occurrences with page, short context and review
  status.
- import of these 2,496 specifications into `catalog/measurements/` as a
  separate documentary record; no physical session is created without a part,
  an instrument and raw readings.

Measurement traceability:

- schema, validator and register of measurement sessions;
- direct capture from an instrument with data output, or manual entry
  explicitly marked as such;
- photogrammetric capture with a manifest and a mandatory scale reference.

## 0.1.0 — 2026-08-28

First public foundation of the project:

- charter, roadmap, safety rules and quality gates;
- free and open-source toolchain;
- schemas and templates for parts, sources, measurements and titanium
  manufacturing;
- local validators, automated tests and GitHub continuous integration;
- initial register of five sources and contribution workflow.

No part is declared printable, fitted or validated in this version.
