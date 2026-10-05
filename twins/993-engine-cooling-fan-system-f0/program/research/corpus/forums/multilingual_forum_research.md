# Porsche 911 / 935 cooling fans: multilingual community evidence

Research date: 2026-10-03. Scope: public forum posts, owner maintenance diaries and one adjacent first-party workshop report. This is a bounded literature search, not an examination of every forum or a production design specification.

## What the evidence supports

The most useful material is **original experiments, explicit corrections and failure histories**, rather than the number of times a specification is repeated. This corpus contains 36 source records, 45 individual claims, and nine reported bench observations. English, German, French, Italian, Japanese and Dutch material is represented. Every production-dimension flag is false.

Three research priorities emerge:

1. **Identify the complete assembly.** Rotor family, housing/stator, alternator, hub/bearing, pulley stack and engine code must travel together. A forum description such as “964 fan” is insufficient. The later NA and Turbo distinction has a concrete part-number lead in [F08](https://rennlist.com/forums/993-forum/355587-alternator-engine-fan-question.html); the 3.3 Turbo discriminator is separately discussed in [F16](https://www.pff.de/thread/2772479-porsche-911-luefterrad-unterschiede/?pageNo=5).
2. **Measure system resistance before optimising free airflow.** The strongest measurement discussion ultimately acknowledges difficulty obtaining valid shroud static pressure. Its later correction matters more than its dramatic initial title: [F05](https://forums.pelicanparts.com/porsche-911-technical-forum/483605-did-porsche-screw-up-my-engine-plugged.html), [F07](https://forums.pelicanparts.com/porsche-911-technical-forum/198878-cooling-fan-hp-5.html).
3. **Treat clearance as a dynamic assembly property.** Owner accounts repeatedly connect rubbing to bearing play, axial stack, seating, coating, corrosion and thermal condition. A nominal bore minus rotor diameter does not capture the failure envelope: [F08](https://rennlist.com/forums/993-forum/355587-alternator-engine-fan-question.html), [F09](https://forums.pelicanparts.com/porsche-911-technical-forum/1059881-993-fan-housing-salvageable-why-my-alternator-throwing-belts.html), [F23](https://www.p-horse.com/2024/04/08/993%E3%82%AB%E3%83%AC%E3%83%A9%E3%80%80%E3%82%AF%E3%83%BC%E3%83%AA%E3%83%B3%E3%82%B0%E3%83%95%E3%82%A1%E3%83%B3/).

## How to use the deliverables

- [forum_sources.csv](forum_sources.csv): source identity, language, exact observed URL, source date range, retrieval date and access limitations
- [forum_claims.csv](forum_claims.csv): author pseudonym, displayed post date, locator, claim, units/conditions, evidence type, engineering confidence, contradiction and required validation
- [reported_bench_series.csv](reported_bench_series.csv): nine rpm/CFM observations from F06; SI conversion is calculated, not independently measured
- [forum_corpus.json](forum_corpus.json): machine-readable source/claim relationship
- [coverage_and_gaps.md](coverage_and_gaps.md): search vocabulary, site coverage and remaining gaps

A record describes what an identifiable poster reported. It does not certify the poster’s conclusion. “Medium” means a useful engineering lead or credible qualitative observation, never manufacturing approval. “Indexed extract” means search returned substantive original-post text while a separate page-open attempt failed; it is not labelled as a full live-page inspection. Dates are copied from post text, not inferred from search engine age labels. Missing author/date details remain explicitly missing.

## Highest-value experimental leads

### Modified 964 rotor in a 3.2 assembly

[F02, Rob T.](https://forums.pelicanparts.com/porsche-911-technical-forum/755964-964-fan-3-2-a.html) is unusually useful because the author describes fabrication, an anemometer comparison and a later road-use update. It is a **modified 964 rotor in an earlier assembly**, not an OEM NA-versus-Turbo test. Use FC04–05 to recover the reported conditions. Before modelling it, obtain actual modified geometry, instrument position, area integration and RPM definition. A favourable oil-gauge observation cannot exclude hotter individual heads.

### 964 bench fan against a radiator

[F06, Michael Nealey](https://forums.pelicanparts.com/porsche-911-technical-forum/483605-did-porsche-screw-up-my-engine-plugged-post8337178.html) supplies a speed series rather than a single airflow number. Preserve its radiator load and failed pressure measurement. It is useful for constructing a test-method checklist, but cannot calibrate a Porsche engine simulation without knowing the actual flow restriction, leakage and measured shaft speed. A motor nameplate is not measured fan shaft power.

### On-car static-pressure attempt and later correction

[F05/F07, midlife](https://forums.pelicanparts.com/porsche-911-technical-forum/198878-cooling-fan-hp-5.html) provides a rare example of an author revising confidence in their method. Keep the correction attached to the earlier result. The report of a conversation at Porsche about an old curve is hearsay, not factory authentication. Do not cite the initial experiment as proof that Porsche designed a fan incorrectly.

### Italian shorter-belt experiment

[F25, Roberto B. / roberto30](https://www.porschemania.it/discus/messages/488172/763033.html?1450933847) records dimensions, a proposed ratio change and a tube-temperature baseline. The arithmetic is inconsistent and the paired thermal result was not present. Its value is exposing missing variables: belt pitch diameter, section, shim position, tension, slip and shaft RPM. It does not justify fitting a shorter belt.

### Historical racing underdrive experience

[F03, Henry Schmidt](https://forums.pelicanparts.com/911-engine-rebuilding-forum/944528-speeding-up-fan.html) is a first-person professional recollection with a declared commercial interest. It identifies a testable hypothesis for sustained high-RPM duty. No numerical A/B record was recovered, so the asserted power benefit and unchanged cooling cannot be transferred to idle, traffic, Turbo or other assemblies.

## Contradictions and propagation hazards

| Issue | Evidence conflict | Treatment |
|---|---|---|
| Five-blade diameter | Type911 article F18 says 226 mm; F01/F24 compilations say 245 mm | Retain conflict; determine exact part, never average values |
| Small SC fan years | F01 owner initially guesses 1980–81; same thread corrects to 1978–79 | Carry correction alongside original claim |
| 1975 versus MY1976 | F24 clarifies late-calendar-1975 cars can be MY1976 | Separate build date from model year |
| Oil-temperature benefit | F01/F24 report drops; F33 reports little change | Different duty, oil coolers and pulleys; no pooled effect size |
| Equal five/eleven airflow | F34 quotes unnamed tests claiming equality; F01 repeated table differs | Require RPM basis, exact assembly and original test |
| Tip speed | F04 labels roughly 462 as ft/s; F03 discussion calls roughly 460 mph | Correct unit before making transonic claims |
| Rotor diameter versus surrounding size | F04 lists 279.4 mm for 964/993; other literature uses other diameters | Do not assume it is rotor OD or silently relabel as housing OD |
| Later-fan noise versus cooling | Quieter subjective reports are used to infer efficiency | Record Q, pressure, shaft power and acoustic spectrum separately |
| Old pressure-curve provenance | Widely circulated Forstner curve questioned in F07 | Locate original publication and test article before calibration |
| Flat-fan power threshold | F29 cites 450 hp; other discussions cite much higher figures | Architecture/duty-dependent assertions, not an applicability limit |
| 917 versus 911 power | F27 mixes architectures and repeats L/min versus L/s ambiguity | Exclude from 911 validation until primary context recovered |
| Carbon-fibre aftermarket attribution | F21 reports a dry-carbon failure without brand | Do not attribute it to any named supplier |
| Coating-induced failure | Several posts assert heat, trapped corrosion or excess thickness | No universal process conclusion without material/cycle evidence |

### Independent arithmetic check

For the reported 245 mm rotor, 6100 crank rpm and 1.8 ratio, the calculated tip speed is approximately 140.85 m/s, 462.1 ft/s or 315.1 mph. This is a consistency check using the reported inputs, not measured performance. Tip circumferential speed is also not axial air velocity. Any claim that this same case is 462 mph is inconsistent with those inputs.

Similarly, F25’s reported circumferences imply 1.65 × 257 / 226 ≈ 1.876, not 1.74. This only identifies an inconsistency; it does not prove the actual speed ratio because belt contact/pitch geometry and slip were not measured.

## Digital-twin implications

The following are research recommendations derived from the failure and measurement patterns, not quoted factory specifications.

### Assembly identity and geometry

Maintain separate entities for rotor, metallic hub/insert, fan bearing, alternator shaft and bearings, pulley halves, shims/spacers, housing, stator/deflector and engine shroud. Store exact part numbers, casting marks, manufacturing revisions and alterations. Record the engine code and the alternator variant. A rotor swapped into an earlier housing must become a new configuration, not inherit the donor assembly’s flow curve.

Geometry to acquire from real hardware or authoritative drawings:

- Blade count, OD, span, local chord, thickness, twist, stagger, camber, leading/trailing-edge radii and root fillets
- Hub diameter, bore/shaft fit, axial offsets, rivet/fastener pattern and bearing/insert interface
- Housing bore and roundness, seating surfaces, stator count/angle, exit features and shroud seals
- Pulley pitch geometry, belt section, actual running position and hot/cold belt tension
- Cold radial/axial clearances around the full rotor, with mount clamping and belt load represented

This lane found **no verified production blade profile, airfoil-coordinate set, twist distribution, radial tolerance, balance grade or safe overspeed limit**. No substantiated 250 mm production rotor identity was recovered here. These gaps must not be filled by rounding another diameter or scaling photographs.

### Aerothermal validation

Record Q–pressure–power points across relevant fan speeds and engine restrictions, not only free-flow volume. Verify instrumentation and distinguish static from total pressure. Calibrate flow measurement, quantify leakage, record temperature/density, and specify whether RPM is crankshaft or fan shaft. For a complete engine comparison, measure each head/cylinder region, oil temperatures, engine load, ambient conditions, vehicle speed and any intercooler or A/C heat rejection.

Model shroud distribution and the exact oil-cooler/heater paths. Four-cylinder VW conversion criticism is useful for understanding distribution risk, but is not a six-cylinder Porsche dataset. A cylinder-only electric fan on a liquid-cooled-head architecture cannot establish adequacy for fully air-cooled heads.

### Structural and durability validation

Represent corrosion loss, root defects, hub/insert fit, bearing play, thermal expansion, coating thickness and belt/mount distortion in the clearance and stress budgets. Include rotating unbalance and rotor excursion. Rotor contact can damage both metallic and composite blades; changing material alone does not resolve an interference stack.

The reviewed anecdotes do not establish acceptable crack sizes. Do not treat narrow cracks, a stable paint mark, low-mileage use or a quiet hand-spin as evidence of safe service. Repaired/machined/coated/newly designed rotors need qualified inspection, balance and structural validation. Forum suggestions to sand, drill, weld or keep driving are not incorporated as approved procedures.

## Source hierarchy and rights

Original owner/professional measurements are primary evidence of their reported experiment, not necessarily accurate measurements of a stock design. Expert recollections are weaker than logged tests. Reposts of Anderson/Pelican tables are a single provenance family, even across languages. Vendor posts are labelled and should not be treated as independent comparative trials.

Only concise paraphrases, metadata and a small reported numerical series are included. Linked third-party photos, graphs and manuals have not been republished or granted a reuse licence. Image placeholders or captions identify a possible visual source, not an inspected dimension. Obtain permission or an applicable licence before copying imagery into a public repository.

## Source index

| ID | Community | Language | Source | Access |
|---|---|---|---|---|
| F01 | Pelican Parts | en | [11 Blade fan](https://forums.pelicanparts.com/porsche-911-technical-forum/623498-11-blade-fan.html) | full page read |
| F02 | Pelican Parts | en | [964 Fan on a 3,2?](https://forums.pelicanparts.com/porsche-911-technical-forum/755964-964-fan-3-2-a.html) | full page read |
| F03 | Pelican Parts | en | [Speeding up the fan -](https://forums.pelicanparts.com/911-engine-rebuilding-forum/944528-speeding-up-fan.html) | full page read |
| F04 | Pelican Parts | en | [Speeding up the fan - page 2](https://forums.pelicanparts.com/911-engine-rebuilding-forum/944528-speeding-up-fan-2.html) | indexed excerpt; open returned 403; no bypass |
| F05 | Pelican Parts | en | [Did Porsche screw up or is my engine plugged?](https://forums.pelicanparts.com/porsche-911-technical-forum/483605-did-porsche-screw-up-my-engine-plugged.html) | full first page read; some later pages unavailable |
| F06 | Pelican Parts | en | [Did Porsche screw up ... page 5 / 964 fan for small helicopter](https://forums.pelicanparts.com/porsche-911-technical-forum/483605-did-porsche-screw-up-my-engine-plugged-post8337178.html) | substantive indexed thread extract; open cache miss |
| F07 | Pelican Parts | en | [Cooling fan HP - page 5](https://forums.pelicanparts.com/porsche-911-technical-forum/198878-cooling-fan-hp-5.html) | substantive indexed extract; open decoding error |
| F08 | Rennlist | en | [Alternator-engine fan question](https://rennlist.com/forums/993-forum/355587-alternator-engine-fan-question.html) | substantive indexed thread extract; open internal error |
| F09 | Pelican Parts | en | [Is this 993 fan and housing salvageable, and, why is my alternator throwing belts?](https://forums.pelicanparts.com/porsche-911-technical-forum/1059881-993-fan-housing-salvageable-why-my-alternator-throwing-belts.html) | substantive indexed extract |
| F10 | Rennlist | en | [Secret to no fan rubbing](https://rennlist.com/forums/993-forum/1082426-secret-to-no-fan-rubbing.html) | substantive indexed extract |
| F11 | Rennlist | en | [How to balance a coollign fan?](https://rennlist.com/forums/911-forum/714238-how-to-balance-a-coollign-fan.html) | substantive indexed extract |
| F12 | Rennlist | en | [Cooling fan cracking, unusual? - page 2](https://rennlist.com/forums/964-forum/479394-cooling-fan-cracking-unusual-2.html) | substantive indexed extract |
| F13 | Rennlist | en | [Cooling Fan cracks,... Repair?](https://rennlist.com/forums/964-forum/677131-cooling-fan-cracks-repair.html) | substantive indexed extract |
| F14 | PFF | de | [Lüfterrad hat einen Riss / Fan wheel has a crack](https://www.pff.de/en/thread/2810526-fan-wheel-has-a-crack/) | substantive indexed extract; site English auto-translation; original German also seen through linked quotation |
| F15 | PFF | de | [Lüfterrad 1970–1973](https://www.pff.de/thread/2825126-luefterrad-1970-1973/?postID=156179323) | substantive indexed extract; open cache miss |
| F16 | PFF | de | [Porsche 911 Lüfterrad Unterschiede - page 5](https://www.pff.de/thread/2772479-porsche-911-luefterrad-unterschiede/?pageNo=5) | substantive indexed extract |
| F17 | PFF | de | [Verschiedene Lüfterräder?](https://www.pff.de/thread/2834731-verschiedene-luefterraeder/?postID=156501530) | substantive indexed extract; open cache miss |
| F18 | Type911 community | fr | [Spécifications 3,0L SC et Carrera 3,0](https://www.type911.org/articles/article.php?id=458) | substantive indexed article |
| F19 | Type911 community blog | fr | [Rénovation alternateur & mise en peinture turbine et carter](https://www.type911.org/blog/?idblog=11479) | substantive indexed extract |
| F20 | Type911 community blog | fr | [Fév–Juin 2020 : Remontage moteur et Confinement…](https://www.type911.org/blog/?idblog=11129) | substantive indexed extract; open cache miss |
| F21 | CARTUNE | ja | [993 カレラ customisation post](https://cartune.co.jp/notes/cHKYBihaUO) | substantive indexed owner post; open cache miss |
| F22 | Minkara | ja | [クーリングファン交換](https://minkara.carview.co.jp/userid/153982/car/1255685/2203442/note.aspx) | indexed lead only; open cache miss |
| F23 | PrancingHorse workshop blog | ja | [993カレラ クーリングファン](https://www.p-horse.com/2024/04/08/993%E3%82%AB%E3%83%AC%E3%83%A9%E3%80%80%E3%82%AF%E3%83%BC%E3%83%AA%E3%83%B3%E3%82%B0%E3%83%95%E3%82%A1%E3%83%B3/) | substantive indexed workshop account |
| F24 | PorscheMania | it | [Ventola a 5 pale ?](https://www.porschemania.it/discus/messages/488172/792111.html?1476404645) | full public thread read in cloud browser |
| F25 | PorscheMania | it | [Numero di giri ventolone 3.2](https://www.porschemania.it/discus/messages/488172/763033.html?1450933847) | full public thread read in cloud browser |
| F26 | PorscheMania | it | [Ventola 964](https://www.porschemania.it/discus/messages/488172/817620.html?1517765760) | full public thread inspected in cloud browser; long unrelated middle omitted from extraction |
| F27 | DDK | en | [911 engine cooling fan: power consumption?](https://www.ddk-online.com/phpBB2/viewtopic.php?t=72443) | substantive indexed thread extract |
| F28 | DDK | en | [911 engine cooling fan: power consumption? page 2](https://www.ddk-online.com/phpBB2/viewtopic.php?p=679817&sid=9528f48a890cbae29ab57f20dd6d0fab) | substantive indexed extract |
| F29 | Pelican Parts | en | [Where to find the type 935 flat fan?](https://forums.pelicanparts.com/999991-post23.html) | substantive indexed original post |
| F30 | Pelican Parts classifieds | en | [Flat fan assemblies](https://forums.pelicanparts.com/porsche-911-used-parts-sale-wanted/905416-flat-fan-assemblies.html) | indexed snippet only; open decoding error |
| F31 | Pelican Parts | en | [Rennline Billet Fan Housing - Whos done it?](https://forums.pelicanparts.com/porsche-911-technical-forum/1134688-rennline-billet-fan-housing-whos-done.html) | substantive indexed extract |
| F32 | Pelican Parts | en | [5 blade to 11 blade fan question](https://forums.pelicanparts.com/11739207-post1.html) | substantive indexed original post |
| F33 | Pelican Parts | en | [5 Blade fan vs. 11 Blade Fan - page 2](https://forums.pelicanparts.com/porsche-911-technical-forum/332048-5-blade-fan-vs-11-blade-fan-2.html) | substantive indexed extract |
| F34 | PorscheForum.nl | nl | [te hoog stationair](https://www.porscheforum.nl/viewtopic.php?t=4709) | substantive indexed extract |
| F35 | TheSamba | en | [Porsche fan shroud install](https://www.thesamba.com/vw/forum/viewtopic.php?p=967700&sid=c5530b0d8d6badc58922d30694256d0f) | indexed snippet only |
| F36 | TheSamba | en | [911 shroud question - page 4](https://www.thesamba.com/vw/forum/viewtopic.php?start=60&t=445459) | indexed snippet only |
