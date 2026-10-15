# Source register

**Consulted: September 27, 2026, except S01/S34 reviewed on September 28 and S31–S33/S35 reviewed on October 2, 2026.** Supplier pages
attest a published offer, not a commitment, stock or automotive suitability.
Documents are linked, not copied into the repository. The engineering assumptions
and financial envelopes of this dossier are our proposals, not data extracted
from these sources.

| ID | Primary source / link | Supported item and limits |
|---|---|---|
| S01 | [Kingbright — low-current 0402 LED](https://www.kingbrightusa.com/category.asp?catalog_name=LED&category_name=KCLow+Current-1.0X0.5MM+%280402%29&page=1); [exact datasheet APHHS1005LSECK/J3-PF](https://www.kingbrightusa.com/images/catalog/spec/aphhs1005lseck-j3-pf.pdf) | V.6A, 4 pages: red component 1.0×0.5 mm, typical Vf 1.8 V / max 2.1 V at 2 mA and 25 °C, absolute maximum current 30 mA under conditions. Does not prove the pitch, an intensity behind the front face or automotive durability. The APG1005 datasheet cited initially was another reference, replaced here by the exact datasheet |
| S02 | [Waveshare — RGB-Matrix-P2.5-64x32](https://www.waveshare.com/rgb-matrix-p2.5-64x32.htm) | 64×32, 2.5 mm pitch, HUB75, 5 V/2.5 A supply, power ≤12 W as stated. Prices shown 17.99–21.99 USD depending on variant; selection/taxes/shipping to be confirmed |
| S03 | [Waveshare — P2/P2.5 64×64 range](https://www.waveshare.com/product/rgb-matrix-p2.5-64x64.htm) | Variant table including P2 64×64; not a guarantee of availability or outdoor durability |
| S04 | [Newhaven — NHD-1.5-128128G, datasheet](https://newhavendisplay.com/content/specs/NHD-1.5-128128G.pdf) | Example of a small 128×128 OLED; lifetime/temperature to consider under the specified conditions. No full-width OLED qualified |
| S05 | [Formlabs — Clear Resin V5](https://formlabs.com/products/clear-resin/); [material datasheet](https://formlabs-media.formlabs.com/datasheets/2401900-TDS-ENUS-0.pdf) | Transparency and finish possible, lighting/prototypes; no established automotive exterior qualification |
| S06 | [Stratasys — VeroClear](https://www.stratasys.com/en/materials/materials-catalog/polyjet-materials/veroclear/) | Rigid transparent PolyJet photopolymer; compare with real thermoplastics, do not treat them as equivalent |
| S07 | [Protolabs — European processes](https://www.protolabs.com/en-gb/services/3d-printing/); [plastic materials](https://www.protolabs.com/services/3d-printing/plastic/); [finishes](https://www.protolabs.com/media/1021595/us_3dp_surface_finish_guide.pdf) | Clear SLA/WaterShed and PolyJet documented; available grade, plant and finish to be confirmed for the European quote |
| S08 | [Texas Instruments — LM7480-Q1](https://www.ti.com/product/LM7480-Q1); [datasheet](https://www.ti.com/lit/ds/symlink/lm7480-q1.pdf) | Reverse-polarity/load-dump protection controller, external MOSFETs; does not validate a complete circuit |
| S09 | [Nordic — nRF52840, specification](https://docs-be.nordicsemi.com/bundle/nRF52-Series-PS/raw/resource/enus/nRF52840_PS_v1.0.pdf); [boot chain](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/app_dev/bootloaders_dfu/mcuboot_nsib/bootloader.html) | Candidate BLE MCU and boot/DFU infrastructure; module, stable SDK/version and memory to be fixed during porting |
| S10 | [Apple — Apple Media Service Reference](https://developer.apple.com/library/archive/documentation/CoreBluetooth/Reference/AppleMediaService_Reference/Introduction/Introduction.html) | Accessory as a GATT client of iOS metadata over BLE; archived document, dated 2014, reviewed directly. Current compatibility to be tested |
| S11 | [Android — MediaSessionManager](https://developer.android.com/reference/android/media/session/MediaSessionManager) | Access to active sessions subject to a system permission or an authorized notification listener; not universal access without consent |
| S12 | [Ab Concept — scan](https://abconcept.ch/prestation/scan-3d/); [location](https://abconcept.ch/contact/) | Component scanning, STL, reconstruction; La Chaux-de-Fonds. Page reviewed directly after a one-off failure of the web tool |
| S13 | [INCO 3D](https://www.inco3d.ch/) | Scanning/reverse-engineering/printing/thermoforming services and Pully location; automotive transparency and lead times not proven |
| S14 | [gigAtec](https://gigatec.ch/) | Development, industrialization and local production in Vallorbe announced; origin of incoming parts and specific experience to be qualified |
| S15 | [Systronic-EMS](https://systronic-ems.com/) | Design/assembly and presence in French-speaking Switzerland published; ordering site to be verified |
| S16 | [Eurocircuits — PCBA capabilities](https://www.eurocircuits.com/services/pcb-assembly-capabilities/); [services/manufacturing](https://www.eurocircuits.com/blog/eurocircuits-launch-5-working-day-pcb-assembly-prototype-service/) | Assembles its own PCBs; capabilities page shows 3/5/7/10 working days under conditions. General offer Germany/Hungary. Total lead time, stock, site and shipping to be confirmed; do not equate assembly time with delivered lead time |
| S17 | [Bourquin — services](https://www.bourquinsa.ch/fr/que-faisons-nous/services/); [sites](https://www.bourquinsa.ch/ueberuns/standorte/) | Packaging design and Couvet site; manufacturing allocation, MOQ and project prices unknown |
| S18 | [DTC — modification examinations](https://www.dtc-ag.ch/fr/prestations/securite-active/examens-de-modifications) | Swiss/international examination offer in Vauffelin; mandate scope to be agreed |
| S19 | [TÜV Rheinland — automotive lighting](https://www.tuv.com/luxembourg/de/pr%C3%BCfung-lichttechnischer-einrichtungen.html) | Berlin laboratory and test reports for type approval; published accreditations, current contract to be confirmed |
| S20 | [Porsche Classic — 993](https://www.porsche.com/australia/accessoriesandservice/classic/models/993/993/) | Manufacturer description of the panel and the red reflective logo; does not give the approved inventory per reference |
| S21 | [Bergvill F/X — 993 kit instructions distributed by Design911](https://www.design911.co.uk/uploads/pdfs/bergvillfx/Rear_fog_light_conversion_kit_Porsche%20993.pdf) | Reflector/rear fog light assembly and rear fog light function on the configurations concerned; accessory manufacturer document, no regulatory approval of the conversion inferred |
| S22 | [Fedlex — OETV RS 741.41](https://www.fedlex.admin.ch/eli/cc/1995/4425_4425_4425/fr) | Official portal reached but consolidated text not extracted (JavaScript); articles/version to be confirmed before a formal opinion |
| S23 | [FEDRO (OFROU) — identification of lamps/retro-reflectors](https://www.astra.admin.ch/dam/astra/fr/dokumente/homologation_vonfahrzeugen/kennzeichnung_derlichterundrueckstrahlerece-eg.pdf.download.pdf/identification_desfeuxetdescatadioptresece-ce.pdf); [approvals](https://www.astra.admin.ch/fr/homologations) | Identification of categories and entry point to the authorities, not an approval for this part |
| S24 | [StVZO §49a](https://www.gesetze-im-internet.de/stvzo_2012/__49a.html) | Official text reviewed: permitted lighting equipment, including an illuminated dynamic exterior display |
| S25 | [StVZO §19](https://www.gesetze-im-internet.de/stvzo_2012/__19.html) | Possible consequences of modifications on the Betriebserlaubnis; specific legal review needed |
| S26 | [EUR-Lex — RED 2014/53/UE](https://eur-lex.europa.eu/eli/dir/2014/53/oj/eng) | Official text accessible; harmonized standards/version applicable to the product to be selected with the laboratory |
| S27 | [OFCOM — conditions for placing on the market](https://www.bakom.admin.ch/fr/conditions-de-mise-sur-le-marche) | Assessment, dossier, declarations, information and radio marking; page dated January 16, 2025 |
| S28 | [Bluetooth SIG — qualification](https://www.bluetooth.com/develop-with-bluetooth/qualify/) | Qualification before sale/distribution; fees and exact route not costed here |
| S29 | [IPI — criteria for industrial products](https://www.ige.ch/en/protecting-your-ip/indications-of-source/indications-of-source-basics/criteria-for-determining-origin/industrial-products) | 60% threshold, essential activity and Swiss physical step, official calculator |
| S30 | [IPI — Swissness FAQ](https://www.ige.ch/fr/droit-et-politique/evolutions-nationales/indications-de-provenance/indications-de-provenance-suisses/questions-frequentes-swissness) | Included/excluded costs and exceptions; page reviewed directly, packaging and after-sales service excluded in particular |

## Electronics supplement — consulted on September 28, 2026

| ID | Primary source / link | Supported item and limits |
|---|---|---|
| S31 | [TI — TLC5947, datasheet SBVS114B](https://www.ti.com/lit/ds/symlink/tlc5947.pdf) | Rev. B, DAP pins §5; VCC 3–5.5 V, recommended current 2–30 mA, logic thresholds §6.3; logic supply §6.6; ideal current `41 × 1.20 / R`; BLANK high required at start-up and undefined initial register §8.3; 288-bit chain, MSB first, and latch §8.4. Thermal protection with automatic recovery. Low-current margins not validated for our coupon |
| S32 | [TI — SN74LVC125A, datasheet SCAS290T](https://www.ti.com/lit/ds/symlink/sn74lvc125a.pdf) | Rev. T: PW 14 pinout, 3-state buffer, supply 1.65–3.6 V; high threshold 2 V in the 2.7–3.6 V range. Do not mistake it for isolation, nor allow hot-plugging without a study of the rails |
| S33 | [TI — SN74LVC1G04, datasheet SCES214AF](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf) | Rev. AF: inverter, DBV 5 pinout, high threshold 2 V at 3.3 V, Ioff protection; replaces neither a watchdog nor a voltage supervisor |
| S34 | [Nordic — nRF52840 DK power supply](https://docs.nordicsemi.com/r/bundle/ug_nrf52840_dk/page/ug/dk/hw_power_supply.html); [source selection](https://docs.nordicsemi.com/r/bundle/ug_nrf52840_dk/page/ug/dk/power_source.html); [guide v1.4.1 §8.3](https://infocenter.nordicsemi.com/pdf/nRF52840_DK_User_Guide_v1.4.1.pdf) | Power modes and 3 V regulator in VDD mode; does not permit drawing LED power from the DK. Board revision and GPIO to be identified before wiring |

The prices, stock and lead times of these four components have not been verified.
Manufacturer files are only linked; no proprietary PDF copied.

## References to be confirmed, not presented as read in full

- [UNECE — regulations 141–160](https://unece.org/transport/vehicle-regulations-wp29/standards/addenda-1958-agreement-regulations-141-160): direct access returned 403 during this pass.
  The R148/R150 scope and the other regulations mentioned are a list of
  questions for the laboratory; series/version and transitional provisions not verified.
- [EUR-Lex — delegated regulation 2022/30](https://eur-lex.europa.eu/eli/reg_del/2022/30/oj/eng): direct response with no usable text in this pass. Verify the consolidated text,
  dates and cybersecurity scope with a radio body; no exemption asserted.
- Anibis 180 CHF and historical budgets: **source = owner's brief**; listing,
  acquisition and original quotes not available; no URL invented.

## Native E0 schematic — supplement of October 2, 2026

| ID | Source | Verification / limit |
|---|---|---|
| S35 | [KiCad — CLI 9](https://docs.kicad.org/9.0/en/cli/cli.html), [schematic format](https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/), [library license](https://www.kicad.org/libraries/license/) | Netlist/PDF export and ERC; KiCad 9.0.2 run locally under Debian, symbols 9.0.2. CC BY-SA 4.0 with an exception for circuits; attribution and license included for the derived local library. Does not constitute a manufacturing validation |

S31–S33: TI datasheets reviewed for the DAP/PW/DBV pinouts, with no change to the
candidate references. Manufacturer PDFs are not redistributed in the repository.

## Limits of the initial collection (September 27)

Targeted searches in FR/DE/EN and on manufacturer/authority sites; no global audit,
supplier contact, registration or purchase. The web search tool then
returned an expired-authentication error (401). The necessary public pages
were reviewed directly with the system HTTP client, with TLS validation kept;
no access restriction was bypassed. A first Python attempt had failed
on the local certificate chain. Blocked sources remain marked as such;
no search loop to force them. No paid standards text, proprietary manual,
third-party scan or photograph is incorporated.
