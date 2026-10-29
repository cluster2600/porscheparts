# Component identity before central-cell CAD

**Decision: the observed central lower strip is not admitted as a tunnel
interior or a structural wall.** Its resemblance to a separate underbody cover
is a candidate identification, not a verified part assignment. The two ribbed
floor regions are useful exterior observations, but neither establishes an
interior surface, thickness or carbon laminate.

This review advances the [architecture correction](../shape-review-20261029/README.md)
using the [source-preserving scan](../scan-coverage-20261029/README.md). It adds
component context and a documented geometry-admission decision, not a new
monocoque or an executable CAD gate. The historic geometry and analysis remain
rejected as the product baseline. No stiffness result transfers to a redesigned
cell.

## What Porsche's catalogue establishes

The official German [964 PET, Kat 013](https://files.porsche.com/f/332100/b26b3c7233/kat013-d-911-94-katalog.pdf)
was checked against the retained 794-page file by SHA-256. Original diagrams
and their tables were visually inspected; the table text was checked separately.
Page numbers below are PDF pages, counted from one.

| Assembly context | Plate / pages | Identification facts |
|---|---|---|
| Floor | 801-10 / 391–392 | Position 1 lists 96450150102 and 99350150100. The diagram shows ribs, circular features and a raised centre. |
| Central underbody cover | 801-45 / 421–422 | Position 8 is 99350404300, listed separately from the floor. Peripheral fixings appear in the diagram. |
| Control console | 801-10 / 392 | Position 5 distinguishes C2/C4 and through-1991/from-1992 variants; the earlier C2 entry has a Tiptronic rework note. |

These are identification facts, not donor measurements. A 993-prefixed service
number in the 964 catalogue does not identify the scanned car as a 993, prove
interchangeability, or determine its model year. The exploded drawing is not
used as a scaled template. The catalogue and its page images remain private;
only references, facts and hashes are published.

## Interpretation of the acquired surface

The [ledger](review.json) links every existing search region to its exact source
face-ID digest. It distinguishes the following observations and inferences:

| Scan observation | Interpretation | Permitted next use |
|---|---|---|
| Ribbed lower panels on both sides of the centre | Floor candidates; visible pattern resembles the floor drawing | Locate actual boundaries and retain observed exterior patches as references |
| Long central strip with a perimeter seam and repeated edge features | Separate cover candidate, consistent with plate 801-45 | Keep as a packaging obstacle/reference; exclude from tunnel-interior reconstruction |
| Partial surfaces at both lateral edges | Sill search only; inner/outer layers and trims unresolved | Identify seams, adjoining parts and missing coverage before defining a sill section |
| Front and rear transition regions | Mixed body and assembled mechanical surfaces | Separate identified components before fitting bulkheads or structural connections |

No region is a semantic component segmentation. In particular, all 157,129
triangles in `CentralRouteSearch` must not be labelled as one identified cover:
the rectangular search window can also contain nearby hardware, gaps and
adjoining surfaces. The candidate part number is not written into the original
USD as an established identity.

## Consequence for the requested shape

The replacement architecture must explicitly connect two footwells, the centre
tunnel, both sills and front/rear bulkheads into the central load-bearing cell.
It must distinguish exterior panels and front/rear assemblies, and retain the
required upper load paths and door interfaces. The [ZESAD reference](https://zesad.com/product/porsche-964-and-993-carbon-fiber-monocoque-for-restomods/)
sets the requested architecture, not dimensions or laminate design. The all-carbon
structural intent remains; a RUF reference does not authorize substituting its
steel structures for the requested design.

For the tunnel, three different things must be acquired and kept separate:

1. The removable lower cover and its actual attachment boundary.
2. The body tunnel itself, including interior walls and its joins to the floor.
3. The installed controls and services, their motion and service-access envelopes.

The existing scan supports investigation of the first item and parts of the
exterior floor. It does not establish the other two. Closing its lower strip
into a generic box, mirroring the underside into an interior, or tracing a
vendor photograph would reproduce the original modelling error.

The next admissible geometry step is identified source-patch extraction, with
original face IDs and a reviewed boundary. Functional tunnel, bulkhead, sill
and attachment geometry additionally requires the missing surfaces and
independently identified datums in the existing
[interface survey](../../interface-measurement-plan.md). The owner-reported C2
is the current scope; gearbox and model year remain unknown. C4 and 993
compatibility remain separate open tasks.

## Verification and limits

The source file digest matches the existing PET catalogue record. The scan,
stage, region and image digests in `review.json` match the retained review;
every existing search region is covered exactly once in this ledger. This is
a documentary and visual review: no automatic component recognition, new
surface fitting, structural solve, manufacture or Omniverse execution is
claimed. The underlying raw geometry, six sections and media are unchanged.
