# 935 engine and horizontal cooling-system evidence

[Repository home](../../../README.md) · [System program and 50-entry input matrix](../README.md) · [Related impeller research](../../993-engine-cooling-fan-system-f0/program/research/README.md)

Forty bounded language passes are complete. Their four verified public synthesis
views are available below, preserved byte for byte. They contain **535 source/access
records, 418 claim observations and 143 parameter/gap entries, including 66 nulls**.
These counts include repeated publications, unread leads, wrong-model exclusions,
contradictions and gaps. They are not independent engineering facts or measurements.
Seven supplementary source/lead records are counted separately and may overlap.

| Read or inspect | Purpose |
|---|---|
| [Consolidated report](CONSOLIDATED_REPORT.md) | Variant-specific findings, operating context, contradictions and missing inputs |
| [Source families](SOURCE_FAMILIES.json) | 461 publication/URL families; 535 lane records, translations, copy lineage, reading status, URLs and locators |
| [Engine/fan parameter ledger](ENGINE_FAN_PARAMETER_LEDGER.json) | 143 classified parameters/gaps and 418 original claim observations with provenance; all automatic admission flags false |
| [Original synthesis QA](QA_SUMMARY.json) | Forty-lane coverage, original artifact hashes, source-reference checks, exclusions and publication boundaries |
| [Matrix crosswalk](matrix-crosswalk.json) | Navigation from each of the 50 requirements to selected ledger parameters; six matrix variants remain separate |
| [Coverage](coverage.json) | Received public/private counts, bounded scope and incomplete engine data |
| [Import manifest](import-manifest.json) | Bundle and four-file digests, unchanged-byte policy and transfer history |

## Reading evidence without filling unknown inputs

Start with the report's selected variant, then follow its ledger record to the
source family, original artifact hash, external URL and recorded locator. Source
access metadata distinguishes an actual page read from an indexed snippet,
bibliographic lead or failed access. Repeated URLs and identified translations
share publication provenance; neither the source count nor family count proves
independent corroboration. Units, operating conditions, rejected transfers and
uncertainty limitations remain attached to each assertion.

The crosswalk is a navigation aid. Its record references include reported
quantities, explicit gaps and contextual exclusions. They do not satisfy the
matrix's required evidence or establish applicability to another variant. Matrix
values and accepted-claim lists remain empty; automatic model admission and
physical-validation flags in the research ledger remain false. Null means
unestablished, never numerical zero. Engine brake power, fan shaft power and
heat rejection remain distinct; reported horsepower labels and pressure
references must not be silently converted or resolved.

Factory 1976, factory 1977, factory 1978/Moby Dick, Kremer K3, Kremer K4 and an
individually declared replica remain six separate matrix templates. The ledger
also retains Baby, customer cars, Group C engine designations and named restored
or reproduction builds. Those additional contexts are not silently folded into
a template. The 1978 water-cooled-head architecture cannot be assigned to K3/K4
without direct applicability evidence. Public historical chassis, engine and
part references delimit a reported configuration; they do not identify the
private scanned specimen or establish 935/993 interchangeability.

## Private originals and verified public views

The first 97-file, 23-lane original bundle was verified and retained privately.
The subsequent four-file synthesis covers forty lanes and records hashes for
160 lane artifacts and three supplements. Of those 163 input identities, 94
match the locally received private originals exactly; 69 were not received
locally. Coverage and hash provenance for those additional inputs are supplied
by the verified synthesis QA, not by a claimed local receipt of every original.
The first private batch also has three ancillary registers outside that
163-entry synthesis input manifest.

Only the four authorized public views are imported. No original lane reports,
source PDFs, DOC files, photographs, HTML/text caches, raw scan or restricted
geometry derivatives are published by this intake. Source quote/excerpt fields
and local/cache paths are excluded from the public views. Original artifact
names and hashes in QA are audit identities, not promised public-file links.
The four imported files have no text transformation; a future changed view
must be identified as a derivative with its original digest and documented diff.

Two failed original-bundle downloads are retained in private evidence. A third
attempt succeeded after diagnosing an empty Python trust store and selecting an
already installed CA bundle only for that invocation. The public synthesis also
completed through the authorized network invocation. Certificate and hostname
verification stayed enabled; no package, keychain, persistent environment or
security configuration was changed. The public-safe history is in the import
manifest; private transport URLs and Library identities are excluded.

## Engineering gaps and next intake

Language-pass completion does not establish exhaustive internet coverage or a
complete engine dataset. The target/specimen identity, scan scale, measured
interfaces and shroud gaps, signed fan speed/view, crank-to-fan ratio,
pressure–flow–power and installed-resistance maps, head/cylinder heat loads,
oil/drive/bearing circuits, relevant turbo/intercooler/coolant routes, duty
conditions and qualified material/process calibration remain separate gates.

A first prescribed-speed isolated cold-flow study needs fewer inputs than full
engine coupling; the [program](../README.md) sets those dependencies explicitly.
No new web search, physics solve, manufacturing, hardware operation or physical
release was performed for this integration. OpenUSD display and passing software
checks do not establish a correlated physical twin.

From the repository root, run:

```sh
python3 twins/935-horizontal-cooling-system/source/check_input_matrix.py
python3 -m unittest discover -s tests -p 'test_935_horizontal_input_matrix.py'
make check
```
