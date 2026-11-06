# Scan acquisition correspondence audit: 7 November 2026

Refs #462. **Both licences remain unresolved.** This supplements the
[6 November audit](scan-licence-audit-2026-11-06.md): the connected mailbox now
provides acquisition correspondence, but the reviewed messages supply no
explicit licence grant or standard licence identifier.

## Coverage and asset correspondence

The bounded mailbox search for Wolfe Classics and scan/licence/917/935 terms
returned eight messages. This audit read the four original purchase and
fulfilment messages for the two relevant purchases, plus all five messages
returned from the associated vendor conversation. The other search hits were
one later fulfilment resend, two later purchase confirmations and the
conversation message used to retrieve its thread. No claim is made that this
search exhausts all correspondence or contractual terms.

| Purchase product label | Fulfilment file label | Existing scan record |
|---|---|---|
| Porsche Billet Cylinder head 3D Scan | `935 Xtreme Cyl head.obj` | `SCAN-935-XTREME-CYLINDER-HEAD` |
| Porsche 917 Engine Case Scan | `917 engine case w cyl 0.5mm.obj` | `SCAN-917-ENGINE-CASE-W-CYL-0P5MM` |

Both purchase/fulfilment pairs are dated 31 August 2026. These names connect the
vendor products to the recorded asset names; they do **not** independently
verify the downloaded bytes, revision or ownership of the underlying design.
No download link was followed and no asset was fetched or republished.
The local raw-file hashes remain those recorded in the preceding audit.

## Rights finding

The four purchase/fulfilment messages contain HTML bodies and no MIME
attachments. Their text and link labels provide product/download information,
but no explicit reuse, redistribution, derivative-work or commercial-use
grant, attribution requirement, expiry or licence identifier. Purchase and
availability of a download do not supply those missing terms.

The five-message vendor conversation discusses acquisition and intended
research/parts work, followed by potential further turbo scans. It contains no
explicit licence grant for either of these two assets. A buyer describing an
intended use and a vendor discussing future acquisitions do not establish the
scope of a grant for the purchased files.

Still required for **each** asset: the licensor's written grant identifying the
asset/revision and covering redistribution of raw meshes and derivatives,
commercial use, attribution and expiry. No grant document was found, so there
is no grant-text hash or SPDX/Creative Commons identifier to archive. A custom
`LicenseRef` would name a documented licence; inventing one now would not
resolve the missing grant.

## Preservation

Correspondence, personal and purchase identifiers, private download links and
commercial terms are excluded from this report and Git. No message was sent
or drafted. The historical audit, pinned source/evidence records, existing
licence fields and archived status remain unchanged. Raw scans and derivatives
remain private. Issue #462 remains open pending the missing grant.
