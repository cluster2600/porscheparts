# Request for 964 C2 / 993 body-reference data

Prepared 4 November 2026. Draft only; no message has been sent.
The original donor is unavailable; any new specimen must be identified separately.

We are developing a research digital twin of a carbon central body cell. We
already hold the Porsche 964 body-control spans and Celette setup sheets
564.300, 564.310, 564.320 and the 993 complement 564.307. We need the following
additional information, not another copy of the existing setup diagrams.

1. Confirm the exact model, body style, model-year range and drawing revision
   covered. Supply 964 Carrera 2 and 993 entries separately. Preserve the two
   rear-strut reference families through MY1990 / from MY1991.
2. Supply the available nominal body coordinates and the definition of their
   origin, axes, units, plane and any bench offsets. Include the original
   tolerance definitions; do not infer individual point uncertainty from a
   left/right pair tolerance.
3. Identify the physical contact for each point with a labelled photograph:
   body hole/axis, threaded hole, seating plane, or installed mechanical fastener.
   State whether mechanical assemblies are fitted or removed and identify the
   probe, socket, fixture and offset used. A bolt-head contact is not silently
   interchangeable with the body mounting face beneath it.
4. Provide the mapping between the Porsche manual point IDs and the measuring
   system's own point/fixture IDs where documented. For the legacy Celette set,
   identify the additional 425.D4G sheet and available contact-tool dimensions
   or calibration definitions. Do not reinterpret MZ tower codes or bench
   station numbers as body XYZ coordinates.
5. State the licence for internal engineering use, derived data, private CAD
   and redistribution of factual extracts. Do not send customer identities,
   vehicle identifiers, insurance details or unrelated workshop records.

The companion `donor-interfaces.csv` contains 36 blank left/right measurement
rows for the 18 existing manual identities. It is a capture form, not nominal
geometry. The existing 19 span observations remain the independent documentary
checks. No point position should be filled by mirroring or nearest-neighbour
selection from an unidentified mesh feature.

For a survey of another reference body, please also identify installed gearbox, body
modifications and scan configuration. Survey the tunnel body, removable lower
cover, shift mechanism and service-access envelope separately. Acquire interior
footwells, sill layers, bulkhead joints, window/door openings and upper-cell
load-path surfaces. Record original files, instrument/method, uncertainty,
units, frame definition and independent check points. The engineer responsible
for each interface should agree the acceptance tolerances before acquisition.

Access/disassembly and any physical loading require a qualified workshop's
procedure. This request is not an instruction to disassemble, lift or load the
vehicle.

## Confirmed source routes

- Celette setup sheets already in the repository's source register:
  https://github.com/cluster2600/porscheparts/tree/main/twins/964-chassis/body-reference-research-20261030
- Celette Cameleon Webtools manual, June 2023 revision 1.1, pp. 6–7 (variant
  and assembly state), 10–11 (point images, offsets and contact types), 14–16
  (drawing/report outputs):
  https://www.celette.com/wp-content/uploads/2025/10/Cameleon-Webtools-GB.pdf
- Celette Eagle user manual (reference-surface and point-detail workflow):
  https://www.celette.com/wp-content/uploads/2025/10/Eagle-User-Manual-EN.pdf
- Live WebTools inspection on 4 November reached the login/register page;
  no account was created and no model-specific database entry was accessed:
  https://app.celette.com/

The generic manuals describe a way to obtain data. They do not prove that the
provider has the exact 964 C2 or 993 dataset required here.
