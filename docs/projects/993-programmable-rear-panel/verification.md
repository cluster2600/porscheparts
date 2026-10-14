# Delivery checks

Dossier prepared on September 27, 2026. No hardware test, fitting, metrology,
radio/road qualification or certification of origin has been obtained.

## English data and schematic text — October 14, 2026

The prose pages were translated in PR 146. This change translates the remaining
French text: the free-text columns of `bom.csv`, `measurements.csv`,
`electronics/coupon-bom.csv` and `electronics/coupon-wiring.csv`, and the titles,
notes, sheet name and two component values (`S1` "LED CUTOFF", `J2` "LOGIC / DK
USB SEPARATE") in the three KiCad sheets. Identifiers, net names, pins,
references, numeric values, statuses and CSV columns are unchanged. The
schematic test expects the two new values.

| Check | Observed result |
|---|---|
| Schematic test, before any change | `kicad/kicad:9.0.2` container (`sha256:f36b185970d3…`), network disabled: 1 test, OK |
| Schematic test after translation | Same container: 1 test, OK; 172 components and 541 pins compared |
| ERC | `kicad-cli sch erc --severity-all --exit-code-violations`: exit 0, 0 errors, 0 warnings |
| Review PDF | Re-exported with the README command; the three pages were reviewed visually, no French text left |

The previous PDF was exported in another environment. Re-exporting the
unchanged schematic in this container does not give the same bytes: 538,176
versus 539,324 bytes. The PDF is a review export, not evidence. No electrical
content changed, and nothing here validates the coupon.

## Full PicoGK concept model — October 10, 2026

Base `5b7cb552`, isolated branch `codex/993-rear-panel-picogk`. The authorization
covers a **visual concept model with provisional dimensions**. Adds the C#/JSON
generator, four objects in a GLB, an assembled/exploded view and a
digest/check report. No change to the E0 electronics or the website.

| Check | Observed result |
|---|---|
| Locked restore and C# build | .NET 9.0.317 / PicoGK 2.3.0, macOS arm64: 0 errors, 0 warnings |
| C# self-test | 8 invalid configurations refused; interior/exterior points and hollow frame checked |
| CLI refusals | Existing directory preserved; null/incomplete JSON refused before any output is created |
| Native PicoGK generation | 4 non-empty STL files, read back by PicoGK; two generations with identical digests |
| Inspection and export | 4 closed, oriented, single-piece volumes; GLB read back with 4 objects and units/axes kept; 108 degenerate or duplicate faces of the display volume removed without changing its bounds |
| Visual review | Full lens and four objects visible in the exploded view; opaque concept render, no optical simulation |
| Targeted tests on macOS and Linux after the final export | 19 tests, OK, 1 skipped: KiCad CLI absent; 18 tests passed, including the 2 new revision/GLB checks |
| Links and index | `make docs-links-check reports-index-check` passed, 0 broken links in 825 Markdown files |
| Diff | `git diff --cached --check` passed |
| `make check`, native Linux | Suite of **3,584 tests, OK, 221 skipped**; F32/F34 checks and seven F37 tests passed. Stopped at `917-manufacturing-f37-lpbf-audit-check`, `/bin/sh: 1: docker: not found`, Makefile line 1025, overall exit code **2**; later targets not run |

Full suite in a local Debian trixie arm64 container, Python 3.13.5: copy on its
Linux file system, Git index, UID/GID 1000 and umask 022; network disconnected,
no secret or host Docker socket mounted. Cloud providers are simulated by the
tests. The full log stays local in
`work/993-rear-panel-picogk-20261010/make-check-linux.log`. After the last
anti-aliasing touch-up of the image, the export and the targeted tests were
replayed; the full suite was not repeated. No check disabled and no
manufacturing environment announced as validated.

The [detailed report](cad/preview/checks.json) links the exports to the sources
by SHA-256. The STL files and their archive with notice stay in the ignored
local directory `work/993-rear-panel-picogk-20261010/`; source and GLB are
versioned. Vehicle unknowns stay absent/null: no presumed hole or fastening
point. Self-intersections, mounting, retention, sealing, optics, thermal,
vibration, manufacturing and compliance **not verified**. The mathematical
closure of a mesh is not evidence of physical sealing.

## Native E0 schematic — October 2, 2026

Base `0efe260` (`origin/main`), after merging the previous E0 work. New
branch `codex/993-e0-kicad`, in the existing isolated worktree; no change from
the main working directory incorporated. Adds three editable A3 KiCad sheets,
the project and its attributed local library, a PDF and a netlist test.
Documentation, unsent RFQ and backlog updated. No purchase and no manufacturing.

| Check | Observed result |
|---|---|
| KiCad 9.0.2, `sch erc --severity-all --exit-code-violations` | **0 errors, 0 warnings**, no exclusion and no rule disabled |
| Schematic test on a fresh `kicadxml` export | **172 components, 172 nets, 541 pins**: complete connection groups, values, rails, 128 cathodes, driver chain, IREF, BLANK, thermal pad and unused pins conform to the E0 contract |
| `python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v`, Linux with KiCad | **17 tests passed**, none skipped |
| Same command on macOS without KiCad | 17 tests run, **OK, 1 skipped** (the schematic); does not replace the Linux check |
| KiCad PDF export | Three A3 pages visually reviewed, fields legible, author metadata absent; no PCB drawing |
| `make docs-links-check reports-index-check` | Passed, 0 broken links in 641 Markdown files; reports index up to date |
| `git diff --cached --check` | Passed after removing a trailing space in the imported license text |
| `make check`, native Linux | Suite of **3,250 tests, OK, 159 skipped**, then F32/F34/F37 checks passed. Stopped at `917-manufacturing-f37-lpbf-audit-check`, `/bin/sh: 1: docker: not found`, Makefile line 1014, overall exit code **2**; later targets not run |

Environment: local Debian trixie arm64 container, image
`debian:trixie-slim@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a`,
KiCad `9.0.2+dfsg-1`, symbols `9.0.2-1`, Python 3.13.5, NumPy 2.2.4,
Pillow 11.1.0, Node 20.19.2. Dependencies installed in this container only.
Copy on its Linux file system, local Git index, UID/GID 1000, umask 022; network
disconnected before the tests, no secret or host Docker socket mounted. The
publication/cloud messages of the full suite come from simulations.

Corrections during preparation: first generated file refused by KiCad (missing
closing parenthesis per instance), fixed before validation; first ERC runs
with symbol inheritance and unloaded local library warnings, fixed with explicit
local symbols and an associated project. First link check before adding the new
files to the Git index: five links reported missing, then zero after adding them.
No check disabled to obtain these results.

The schematic is **not validated for manufacturing**: footprints not assigned,
no PCB/DRC, no analog simulation and no measurement of current, temperature,
shutdown or parasitic power. Independent review, then routing and E0 tests
remain open. The power calculation, the costs and the hung-MCU limits from
September 28 remain unchanged assumptions. The global `make check` must still be
run in an environment with the Docker engine and the images the repository
requires; its result is not announced as passed.

## E0 electronics supplement — September 28, 2026

Adds the [E0 schematic circuit](electronics/coupon.md), the BOM/connection CSV files,
the TLC5947 encoder and the power calculation. The exact LED datasheet replaces
the example datasheet of another reference. Sources S01 and S31–S34 reviewed.

| Check | Result observed on this supplement |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_993_rear_panel*.py' -v` | **16 tests passed** on macOS/Python 3.10.11, including 6 new ones: SPI chain simulated independently on each of the 128 pixels, ceiling/invalid values, black after fault, coordinates/pins, calculations and generation without overwriting |
| `coupon_driver.py --output-dir /tmp/993-coupon-e0-20260928` and variant `--pitch-mm 4` | Two maps of 128 connections, two 216-byte frames per variant, JSON calculations; 2.46 mA nominal/channel and coupon allocation ≈2.114 W under assumptions, not measurement |
| CSV and documentation | 19 BOM rows, 34 connection rows, consistent columns; `make docs-links-check reports-index-check` passed, 0 broken links in 556 Markdown files; `git diff --check` passed |
| `make check` under native Linux in a local container | **3,062 tests, OK, 142 skipped**, then F32/F34/F37 tests passed; stopped at `917-manufacturing-f37-lpbf-audit-check`, `/bin/sh: 1: docker: not found`, make code 2. Later targets remain not run |

Same local image as described below, Python 3.11, NumPy 2.4.6, Pillow 12.3.0,
copy on the container's Linux file system, UID/GID 1000, umask 022. Network
disconnected before running the repository; no host Docker socket or secret
mounted. The cloud provider tests use their simulations: no paid machine launched.
First copy rejected by `validate_catalog.py` because of AppleDouble `._*` files
added by macOS archiving (UnicodeDecodeError). The archive was recreated
with `COPYFILE_DISABLE=1` and without extended attributes, then the command rerun;
no catalogue file or validation guard modified to make it pass.

At the September 28 delivery, `kicad-cli` was not available: no ERC/DRC run,
and no native EDA file or manufacturing export announced. The tests validate
only the host data and calculations. Electronics review, native schematic, routing,
automotive power supply, hardware watchdog, optical/thermal measurements and
MCU/BLE porting remain open. The E0 coupon requires human supervision on the bench.

The results below concern the initial delivery of September 27.

## Revision and scope

Remote base: `967f40c`. Branch: `codex/993-programmable-rear-panel`.
20 preparation files under `docs/projects/993-programmable-rear-panel/`
and one dedicated test file. Pre-existing changes in the main working directory
are not incorporated. GitHub read access and ADMIN right verified.
No purchase, quote request sent or commercial deployment.

## Reproducible results

| Check | Result actually observed |
|---|---|
| `python3 -m unittest discover -s tests -p 'test_993_rear_panel.py' -v` | **10 passed**, macOS, Python 3.10.11, Pillow 11.3.0; last targeted check after removing an unused import |
| `python3 docs/projects/993-programmable-rear-panel/software/panel_simulator.py` | Demonstration of two ASCII frames, then shutdown; no radio and no hardware |
| `python3 docs/projects/993-programmable-rear-panel/software/cost_model.py` | Consistent historical ranges and breakdowns; target 250; partial NRE 21,230–64,980; illustrative origin 115/205=56.10% |
| Variant `cost_model.py --rd-ch 20700 --units 1000` | 60.12% illustrative, no attestation; assumptions and sensitivity described in budget.md |
| CSV and local Markdown links | Consistent columns in the four CSV files; all local targets exist |
| `git diff --cached --check` | Passed |
| `make docs-links-check reports-index-check` under Linux | Passed: 0 broken links in 555 Markdown files; reports index up to date |
| HTML mockup | Page served only on loopback and checked in the browser: desktop rendering and warnings visible; server stopped. No mobile validation, no app compatibility test |
| Full suite, via `make check` in native Linux | **3,056 tests, OK, 142 skipped**, Python 3.11.15, NumPy 2.4.6, Pillow 12.3.0; count includes this project's tests |
| Later `make check` targets | F32/F34 and published F37 tests passed; then stopped at the Docker target described below |

## `make check` limit — full command not passed

Environment: local image `nikolaik/python-nodejs:python3.11-nodejs20` (arm64),
image ID `sha256:8f958bdc1b4a422bfafd97cab4f69836401f616ae985d4b57a53d254f5bcb038`,
copy on a Linux file system, user 1000:1000, umask 022, local Git index
initialized. NumPy/Pillow installed only in the disposable container;
network disconnected **before** the tests. No access to the host Docker engine
exposed to the container. No project dependency, locked image or repository rule
modified.

After the full suite passed and additional targets passed:

```text
/bin/sh: 1: docker: not found
make: *** [Makefile:1013: 917-manufacturing-f37-lpbf-audit-check] Error 127
```

The target requires `docker run` and a pinned mesh-cfd image. The global `make`
returns **2**; the later targets are therefore not covered by this run.
`make check` must still be rerun in the native Linux environment the project
expects, with the Docker engine and the required images available. Do not tick
"make check passed" in the PR. The 142 skipped tests concern optional
dependencies/runtimes, notably CAD/solvers; they are not passes.

## Earlier attempts on record

1. Minimal native Linux container, archive without a Git index, root user and no
   NumPy: 2,900 tests, 1 failure, 77 errors, 168 skipped. Causes found: 18 NumPy
   errors, 54 refusals of owner/permission metadata on guard modules,
   5 `git ls-files` calls without a repository; the F58 failure refused UID 0.
2. Existing image `3dprinting993-simready-workflow:f35`, amd64 under emulation:
   interrupted for excessive duration before an overall result, not counted as a pass.
3. Corrected native rerun above: these errors do not reappear; no guard code or
   existing test was changed to work around them.

The archive/check log files are temporary local artifacts, not committed. The
publication messages printed by some global tests come from simulations: the
container network was cut off.

## Product limits still open

BLE authentication injected by the tests, no radio encryption implemented;
DFU specified, not delivered; MCU/iOS/Android compatibility not tested. No scan,
dimension, routed PCB or real prototype. Anibis part and costs not verified.
Legal opinion, original functions, red transmission, aging, automotive power
supply, EMC/RF, thermal, yield and Swiss origin remain to be qualified.

The documentary gaps (Fedlex portal with no extracted text, UNECE 403,
cybersecurity text not extracted) are listed in sources.md. They prevent a
definitive regulatory conclusion, not the preparation of the consultations.
