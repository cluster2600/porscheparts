# Programmable rear panel — Porsche 993

**Preparation dossier, September 27, 2026. No hardware manufactured, measured,
tested or approved. No purchase, quote request sent, commercial publication or order.**

## Proposed decision

Start with a **monochrome red coupon at a 2.5 to 4 mm pitch**, compared with an
off-the-shelf RGB matrix behind the same front-face samples. A 1 × 0.5 mm LED
exists; that defines neither the pitch nor the final resolution.
Keep RGB as an option, undecided until optical tests and quotes.

The target product replaces the original panel, with the same outlines,
fastenings and interfaces, **without modifying the car**. This is a goal, not a
demonstrated result. Neither the outer dimensions nor the variant reference are
fixed. The power supply must also be reversible: no drilling, splicing or
unqualified power tap on a lighting circuit.

The project owner does all the mechanical CAD and the final assembly of the
first batches. An external specialist supports the electronics. Extra help from
EPFL students is a future possibility, with no institutional agreement and no
recruitment committed. Personal names and contact details stay out of this
repository.

The part spotted on Anibis at **180 CHF** is information supplied by the owner;
purchase, availability, reference, condition and scan rights remain to be
confirmed. It is neither acquired nor measured. A deformed part is not enough to
establish the original nominal geometry.

## Deliverables and reading order

1. [Roadmap and backlog](roadmap.md): dependencies, owners and decision gates.
2. [Mechanics, scan and optics](mechanical-optical.md), [measurement sheet](measurements.csv)
   and [full PicoGK concept model](cad/README.md) (provisional dimensions, no OEM interfaces).
3. [Electronics architecture and prototype](electronics.md), [preliminary BOM](bom.csv),
   [E0 coupon: circuit, wiring, BOM and bring-up](electronics/coupon.md),
   [editable KiCad schematic](electronics/kicad/README.md) and [review PDF](electronics/coupon-e0.pdf).
4. [Software and BLE](software.md), [simulator](software/panel_simulator.py).
5. [Budget](budget.md), [editable costs](budget.csv), [Swissness register](swissness.csv).
6. [Suppliers](suppliers.md), [unsent quote requests](rfqs.md).
7. [Compliance and origin](compliance.md), [validation](validation.md).
8. [Commercialization](commercial.md), [local mockup](product-preview.html).
9. [Sources and research limits](sources.md), [check results](verification.md).

## Run locally

From the repository root, Python 3.10+; no dependency for the first two commands:

```sh
python3 docs/projects/993-programmable-rear-panel/software/panel_simulator.py
python3 docs/projects/993-programmable-rear-panel/software/cost_model.py
python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v
```

The simulator prints two ASCII frames of a **virtual 16 × 8 pixel coupon**.
This format is neither a dimension nor a resolution of the 993 part.
The optional GIF import uses Pillow, only if it is already installed; see
[the software contract](software.md). The cost model is readable in a
terminal and its CSV files open in a spreadsheet. No hardware configuration,
radio connection or device update is performed.

The [E0 electronics work](electronics/coupon.md) adds a TLC5947 reference
encoder, a map of the 128 channels and a power calculation with explicit
assumptions. It runs without hardware; the results do not validate a physical
circuit.

## What is reused / what is missing

The remote repository `cluster2600/porscheparts` was checked; the working base is
`967f40c` (`origin/main` at the start of this preparation). The targeted search of
repository paths, local history and PRs mentioning "rear panel" found no
dedicated dossier, budget or patch. This search is not an audit of all remote
branches, messages or private archives. The three historical ranges from the
brief are kept in the budget, with their unverified status.

The work is isolated on `codex/993-programmable-rear-panel`; pre-existing changes
in the main working directory are not incorporated. No validated part record is
added to `catalog/parts/`. This dossier is a study, not an extension of the
authoritative catalogue. The documentation was first written in French, as
explicitly requested at the time; it was translated to English on October 14, 2026, following
[docs/TRANSLATION.md](../../TRANSLATION.md). `RTK.md` was not found at the
instruction paths consulted.
