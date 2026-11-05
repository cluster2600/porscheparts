# Issue 12: torque relations, bearings and filters (2026-11-05 gate review)

Scope: two open checklist items on issue #12. This note records the result of
the admission gate and adds no catalogue record. Nothing below is a fitting
instruction or a release.

## Torque-table mounting relations

The validator (`scripts/validate_components.py`) admits a `mounting_relations`
entry only on an assembly, between instances of component records. Its torque
must equal a `torque_spec` value from a `structured_derived` or
`manually_checked` transcription, and its fastener count must come from a
sourced count parameter.

| candidate | manual value | verdict |
|---|---|---|
| Wheel to hub, both Fuchs sets | M14x1.5, 130 Nm (MNL-TORQUE-0134/0155/0168) | already recorded in #266 |
| Pauter rod set to crankshaft | Porsche rod bolt M9x1.25, 30 Nm + 90° (MNL-TORQUE-0001/0002) | blocked: the Pauter rods use ARP 2000 bolts. The Porsche value applies to the series bolt, not to this product, and ARP or Pauter publishes no size or torque for this part (MEZGER-P014). |
| Oil filter, drain plugs, spark plugs | MNL-TORQUE-0011, -0020, -0077 and others | blocked: no admissible component record exists for the filter, the plug or the counterpart (see below). A relation without its components would give a torque to no part. |
| Suspension, steering and brake joints | MNL-TORQUE-0124, -0132, -0190 and others | out of scope: safety domain, inventory only, and no component records |

Result: no new relation is admissible from the sources in the repository. The
next relation needs a new component record first, for example a filter or a
bearing that passes the gate below.

## Bearings and filters as components

The gate needs the manufacturer's own public sheet to give mass and material,
plus a cited 993 fitment.

| candidate | manufacturer data checked 2026-11-05 | verdict |
|---|---|---|
| MANN-FILTER spin-on oil filters, W 7xx family | The MANN catalogue page (W 724 example) gives dimensions, thread M20x1.5 and bypass pressure. It has no weight field and no material field, and lists the 964 Turbo, not the 993. No MANN page for a 993 application could be retrieved. | blocked |
| W 719/22 | Weight and "enhanced cellulose" media appear only on reseller listings, with 944/968 fitment | blocked: not manufacturer data and not a 993 fitment |
| FAG 713 6122 xx wheel bearing kits, SKF VKBA 1400 | Retailer listings give fitment and some dimensions. No manufacturer page with mass and material was retrieved, and the SKF search page returned no product data. | blocked |
| Porsche 999 053 041 04 kit (FAG) | One reseller gives "0.5942" without unit | blocked: reseller, unit unknown |

Result: no bearing or filter is admitted. Wheel bearings are also suspension
parts, so they would stay inventory only under `SAFETY.md` even once admitted.

## Exit criteria

- A filter or bearing becomes a component when a manufacturer page or PDF
  gives net mass and material, and a manufacturer or Porsche PET page gives
  the 993 fitment. Record licence and access date as for the Fuchs sources.
- A torque relation for it then needs a `torque_spec` value in
  `MEAS-MANUAL-993-ALL` that states the same thread, cited with its value id.
