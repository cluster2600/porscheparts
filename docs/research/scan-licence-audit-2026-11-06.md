# Licence audit of the 917 and 935 Wolfe Classics scans: 6 November 2026

Issue #462. **Verdict: licence unresolved for both scans.** No standard licence
identifier is recorded, because no licence text has been read that warrants one.

| Scan record | Source record | Product page | Local file SHA-256 (as recorded) |
|---|---|---|---|
| `SCAN-917-ENGINE-CASE-W-CYL-0P5MM` | `SRC-LOCAL-917-ENGINE-CASE-CYLINDERS-SCAN` | [Porsche 917 Engine Case Scan](https://www.wolfeclassics.com/shop/p/porsche-917-engine-case-scan) | `428c4143d073f8330022f2fecbd1ac1ee7784d4f1565f1160020448dbdffa0ae` |
| `SCAN-935-XTREME-CYLINDER-HEAD` | `SRC-WOLFE-CLASSICS-935-BILLET-CYLINDER-HEAD-SCAN` | [Porsche Billet Cylinder head 3D Scan](https://www.wolfeclassics.com/shop/p/p-car-billet-cylinder-head-scan) | `4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486` |

## What was checked

- **Both product pages, read on 2026-11-06.** Neither carries any licence,
  terms-of-use, redistribution, commercial-use or attribution text, and neither
  links to general terms. The 917 page says only that an OBJ file is delivered
  on purchase. Prices shown were USD 25 and USD 30.
- **Repository records.** Both source and scan records already say
  `open-reuse-user-confirmed; exact-license-identifier-not-captured`. That is the
  owner's assertion, not a licence text.
- **What was not available to the agent.** The purchase receipts, download
  e-mails and any correspondence with Wolfe Classics. These are the only places
  a grant could be stated, and they stay outside Git (personal data and
  commercial terms).

## Missing document

For each scan, the licensor's written grant: the receipt or download e-mail
text, or a reply from Wolfe Classics. It must state:

- the licensor identity and the exact asset;
- whether redistribution of the mesh and of derivatives is allowed;
- whether commercial use is allowed;
- any attribution requirement and any expiry.

Map it to an SPDX or Creative Commons identifier only if the text matches one
exactly. Otherwise record it as `LicenseRef-WolfeClassics-<asset>` with the
grant text kept privately and its SHA-256 recorded here.

## What does not change

- The scan records keep `exact-license-identifier-not-captured`. The 935 source
  record is pinned by `twins/reference-917-engine/head-architecture-authority-f45.json`
  and is not edited.
- Both twins stay archived, and the raw meshes and all derivatives stay outside
  Git, as the owner instructed.
- A viewable or "open" product page is not a redistribution licence. No mesh is
  published on the strength of this audit.
