# DDK coverage and additional source context

This extends the [selected DDK bridge](../ddk-interface-bridge-20261104/README.md)
without changing its frozen records. All **139** unique records tagged 964 or
993, across 85 original posts, have now been classified at **metadata level**.
This is not an exhaustive reading of the original posts, untagged records or
the wider forum. [review.json](review.json) records provenance and scope;
[metadata-coverage.csv](metadata-coverage.csv) lists the individual records.

## Coverage

The retained dataset SHA-256 is
`8a288acd49ff46123ba51cc6d482e582ee47e0e71173bab41896c9445a7b15a5`.
The current PorscheFanatics revision has the same dataset Git blob as the
earlier bridge revision. No new measured dataset was acquired.

| Metadata classification | Records |
|---|---:|
| In the earlier original-post-reviewed bridge | 10 |
| Additional body-adjacent leads | 3 |
| Installed ride heights or lowering settings | 11 |
| Door/dash trim tool sizes | 4 |
| Other component/configuration masses | 24 |
| Performance figures and damper click settings | 4 |
| Other mechanical, service, engine and wheel data | 83 |
| **Total** | **139** |

The earlier bridge has 15 facts; five lie outside this tagged union. The 129
other tagged records were not part of that earlier selection. Classification
does not promote their extracted provenance labels to metrology acceptance.
After the four additional post readings below, 15 tagged records have prior or
new original context review; 124 remain metadata-only in this audit.

Four additional original post bodies were actually downloaded and read at
their exact post anchors in this increment:

| Post | What the original context establishes | Limit for the monocoque |
|---|---|---|
| [614100](https://www.ddk-online.com/phpBB2/viewtopic.php?p=614100#p614100) | An owner describes disagreement about an early 993 wheel/brace restriction and refers to a Porsche bulletin. | Follow the manufacturer source below; the forum statement is not blanket retrofit permission. |
| [523851](https://www.ddk-online.com/phpBB2/viewtopic.php?p=523851#p523851) | Quoted RS ride heights of 124/107 mm and a reported ±10 mm range; the author then raises an installed suspension. | The post supplies no measuring-point construction or original specification. These are not floor elevations or scan tolerances. |
| [632883](https://www.ddk-online.com/phpBB2/viewtopic.php?p=632883#p632883) | An approximate 1.5-inch seating-position drop with aftermarket buckets. | No seat-rail pattern, attachment face or body datum. |
| [146589](https://www.ddk-online.com/phpBB2/viewtopic.php?p=146589#p146589) | A reported roughly 2 kg door-mass difference in an older-911 conversion involving a 964 intrusion-beam door. | No measured beam, hinge, striker, aperture or structural test. |

A bounded follow-up found corroborating RS height values in mirrored service
text and reproduced measuring figures. The numeric table image was a blank
placeholder, and the original RS publication/revision was not visually
authenticated. The detailed procedure is labelled standard model. These remain
a partial documentary lead: neither a 964 target nor a new scan datum. The
private reading receipt and its hash are retained in `review.json`.

## Manufacturer constraint for the separate 993 variant

The [Porsche certificate 62/20, dated July 2021](https://static.nhtsa.gov/odi/tsbs/2021/MC-10199869-0001.pdf),
page 5, separates eligible body reinforcement from an additional steering-rack
brace for specified early 993 wheel applications. Its exclusion is not removed
by fitting a brace. The dated German manufacturer certificate, section 1.6,
provides corresponding historical context. These are manufacturer documents
for specified production vehicles, not approval of this carbon structure.

The new [source record](../../../catalog/sources/src-porsche-993-wheel-certificate-62-20.json)
retains the fixed revision and PDF hash. The existing
[German-source record](../../../catalog/sources/src-pff-993-porsche-wheel-certificate.json)
is preserved. No current approval status, donor identity or identical bytes at
different mirrors is inferred. Source PDFs, page images and vehicle identifiers
are not redistributed here.

**Engineering consequence, R-993-WHEEL-STRUCTURAL-CONFIG:** the 993 configuration
must declare its wheel/tyre package and applicable body/steering support
architecture before deriving interface loads or claiming compatibility. A
brace, its clamps and fastening interfaces need their own geometry and load
path review if selected. Their coordinates, axes, bearing faces, tolerances,
loads and applicability to the replacement structure remain unknown. This
extends M0/M4 requirements; it closes neither M1 nor structural qualification.

The [new rear-layer inspection](../rear-bracket-depth-20261107/README.md) likewise
adds acquired-layer visibility, not a qualified body contact. The full
[cell, mold, simulation and native Omniverse requirements](../contact-registration-20261106/goal-ledger.json)
remain in force. No geometry, source-to-scan pose or final-twin validation is
generated by this source review.
