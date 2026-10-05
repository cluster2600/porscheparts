# Private scan intake

[Program](../README.md) · [Audit tool](../source/audit_private_scan.py)

On October 3, 2026, candidate file
`Fan+0.5mm+back+not+lined+up+with+center.obj` was located in iCloud Downloads.
The search was limited to that folder and relevant names in local Downloads.
A second file, `Fan+Drive+0.21mm.obj`, exists in local Downloads; it was neither
treated as the same component nor imported.

Two independent local audits of the candidate agree on these counts:

| Original-data check | Result |
|---|---:|
| Size | 51,575,667 bytes |
| Vertices / triangles | 624,492 / 1,240,465 |
| Boundary edges | 8,611 |
| Edges incident to more than two triangles | 0 |
| Orientation conflicts on two-face edges | 0 |
| Surface components | 2 |
| Component vertices | 615,429 and 9,063 |
| Exactly zero-area triangles | 26 |
| Duplicate faces / unreferenced vertices | 0 / 0 |

SHA-256: `244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba`.
This digest identifies the audited file; it establishes neither authorship
nor reuse rights.

The OBJ contains only `v` and `f` records, with no declared unit, license or
part reference. A commercial Wolfe Classics acquisition was subsequently
confirmed by private purchase evidence consulted in the originating task.
The delivery name “Fan 0.5mm back not lined up with center.obj” matches the
encoded iCloud filename. No vendor digest verifies the delivery byte for byte;
the commercial title “Porsche 935 Fan 3D Scan” does not identify a Porsche part
number. Supporting documents, personal data and order details are not public.
They grant no redistribution license. Original delivery and product names
are retained as source wording, not adopted as the program's terminology.

“0.5mm” in the filename is not calibration evidence or a measure of scan error.
Extents, pose and diagnostic views remain in private reports. PCA alignment is
a rigid display transform, without a mechanical datum or scaling. Initial
audits did not check self-intersections; the later prepared-copy inspection
is described below.

## Intake decision

The scan is **open**. These counts qualify no volume, mass, minimum thickness,
physical sealing, fit or dimensional accuracy. Holes and the small component
must be identified on the physical part before deletion or filling. No repair
or geometry export was performed during the initial audit. The raw file remains
at its original location; reports and previews are in Git-ignored `work/`.
Do not force-add them.

Missing inputs: scan operator and acquisition conditions, exact specimen
identity/part reference, export units/software, independent measurement with
uncertainty, axis datum, explanation of rear alignment and permission to reuse/
publish derivatives. Rights remain `unconfirmed_private_only`. These inputs
have been requested; no missing answer is replaced by an assumption.

Once resolved, retain an immutable original, define a dimensioned frame,
treat components separately, document every repair and compare the repaired
surface with the raw scan under an approved tolerance. Missing coordinates
and functional interfaces must not be invented.

## Reversible preparation subsequently executed

The [private preparer](../source/prepare_private_scan.py) produced a local copy
with a right-handed orthonormal PCA pose, scale factor 1 and inverse matrix.
It preserves vertex order and all nonzero-area faces, removes only the 26
exactly zero-area faces and records their indices for reversibility. The
export is reread and transformed back to original coordinates to measure
numerical error. The raw digest is checked before and after, without overwriting
the original. Transforms, removed indices and working mesh all remain private
under `work/`.

This prepares inspection; it fills no hole and registers neither component
against the other. Global recentering does not fix a relative rear offset.
The proposed recovery method is to segment acquisition passes without discarding
them, identify a measured bore/axis and shared measured regions, then rigidly
register passes with a recorded transform and correspondence error. Without
those correspondences, automatic ICP risks fitting physically different
surfaces. No functional rear alignment is invented.

## Open-contour inspection

The original boundary graph has **48 contours**, all simple cycles with no
branching. After zero-area-face removal, the copy has **58 cycles** and
**8,657 boundary edges**: removing an invalid face may expose new edges.
Private reports retain contour sizes; a synthetic test distinguishes pinched
contours from simple cycles. Counts of edges with more than two incident faces
are therefore insufficient to characterize boundaries on their own.

A topological cycle is not automatically a hole to fill: it may represent an
intentional opening, acquisition boundary or missing surface. Reports publish
neither positions nor mesh and classify no contour without observing the
specimen. Volume closure and relative registration require those references.

## Further private diagnostics and next work

Contour inspection retains original indices and walks closed polylines without
modifying the surface. It computes a PCA plane, plane deviations and an
indicative circle fit in unknown source units. Screening requires at least
24 edges and radial/plane RMS each below 2% of fitted radius: an arbitrary
diagnostic threshold, not a functional tolerance. No contour meets it. This
proves neither absence of a bore nor a usable datum from an open edge.
Of 58 contours, 56 belong to the main surface and two to the secondary fragment.
Projections of sampled vertices and exact boundary polylines were inspected
privately. The fragment is not identified as a complete rear pass. A portable
script copy reproduces the numerical report identically; no coordinates are public.

An independent **OpenFOAM Foundation 13** check, build `13-18870c24d21c`,
`surfaceCheck -checkSelfIntersection`, examines the prepared copy in the
historical local image with digest
`sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`,
without network and limited to 4 CPU / 8 GiB. It reproduces the two components
and 8,657 open edges and reports **89 self-intersection locations**.
Exit code 0 means inspection completed, not that the surface passed. Native
part files, intersection points and log remain private. No solver starts.
Input is mounted read-only and its digest remains unchanged. This runtime
differs from Foundation 14 used for #105 CFD; results from one are not presented
as calculations by the other. The tool's “metre” label is not OBJ-unit evidence.

To repeat this inspection, mount the private copy read-only in the identified
image, mount a private output directory as `/output`, use `/output` as the
working directory, then run:

```sh
source /opt/openfoam13/etc/bashrc
surfaceCheck -checkSelfIntersection /input/scan.obj
```

Retain Docker options `--network none --cpus 4 --memory 8g` and the digest above.
The tool may write geometric part/point files: do not use a versioned output
directory. Record input digest, version/build, log, exit code and QA disposition
separately.

Next geometric work is to identify acquisition regions and interfaces,
establish functional frame A/B/C, classify gaps/intersections, then reconstruct
surfaces with measured deviations and traceable transforms. Global filling,
fragment projection or unconstrained ICP is not that reconstruction. Export
units, specimen reference and two independent dimensions with instrument/
uncertainty (outside diameter and bore) are the first requested inputs.
Material is unnecessary for this topological inspection; oriented properties,
metallurgical state and process remain indispensable to defensible mechanical
or LPBF simulation.
