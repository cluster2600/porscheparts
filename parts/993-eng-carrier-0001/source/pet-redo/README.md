# PET-led redo — 993 115 021 53

**Improved Turbo carrier brief; functional CAD blocked by missing interfaces and load cases.**

The [research and interface requirements](requirements.json) retain the exact
variant, assembly, photo references and unknown measurements. No replacement
STL or manufacturing geometry has been produced from invented coordinates.

The official [Porsche PET](https://assets-v2.porsche.com/us/-/media/Project/PCOM/SharedSite/PorscheClassic/Original-Parts-Catalogue/PDF-EN-US/KAT517_USA_911_98_KATALOG#page=117),
group 109-00, shows the Turbo carrier at position 17 and bracket at 18. Four
M10 × 20 bolts join them. The two end bosses receive the engine-mount studs;
four M8 × 40 bolts secure the two mountings to the body. This establishes the
qualitative load path and the attachment count. The relevant drawing and table
provide no hole-centre coordinates, carrier bore sizes, datums, section
thicknesses or tolerances. Bolt threads and washer designations do not supply
clearance-hole dimensions. PET is therefore necessary but insufficient for a
functional reconstruction.

All four [FVD gallery views](https://www.fvd.net/en-us/shop/engine-suspension-bracket-carrier-993-turbo-99311502153~p248965)
were visually inspected. The blade has two round central openings and four
smaller mounting holes, with raised edges and cylindrical end features. The
end close-ups show seams resembling weld beads and differing end recesses.
These observations contradict the retained F1 frame windows and the earlier
claim of a confirmed monolithic part. They do not establish the original
manufacturing route, alloy, coating or dimensions. The listed 600 × 50 × 50 mm
and 1.96 kg remain vendor claims. No photo was imported, calibrated or used as
training data; reuse rights are unconfirmed.

[Sunset Porsche](https://www.sunsetporscheparts.com/oem-parts/porsche-engine-carrier-99311502154)
lists suffix 54 as replacing 53. That is a documentary supersession lead,
not proof that every geometric detail is identical.
[Rennline M01-RS](https://www.rennline.com/rennline-rsr-style-stainless-steel-engine-carrier-porsche-sku-m01-rs/)
explicitly lists both numbers, but its vehicle-year table is inconsistent.
The former blanket statement that no Turbo alternative exists is withdrawn;
fitment remains unresolved. A [TEILE used-part listing](https://teile.com/en/porsche-parts-shop/model-911-993/2/Engine-cooling/109-Engine-suspension/5/109-00-Engine-suspension/Engine-carrier/9768)
provides a potential reference-part lead, with availability on request and a
Sold marker. No purchase, supplier contact or physical access is confirmed.

Follow the existing [measurement plan](../../evidence/measurement-plan.md).
Measure the four central attachment centres, axes and mating face first,
then both end axes, bore/recess geometry and contact faces in a common datum
system. Capture the blade profile, thickness, flanges, openings and joints.
Each numeric parameter needs a traceable measurement or dimensioned drawing
and uncertainty. Keep unmeasured values null; do not scale the PET perspective
or vendor photographs to fill them.

The [Qwen correction and independent preflight](../qwen-concept-f1/README.md)
address the original omission. A model response cannot serve as dimensional
inspection evidence. Only after independent interface inspection can editable
CAD advance to engineering review, material/process qualification and an
approved validation plan. The current catalogue master and rejected F1 files
remain historical concepts, not accepted replacements.

## Improved replacement brief

The user wants greater durability at higher engine output and lower cost,
rather than an OEM silhouette copy. The reported failure above 700 hp is
recorded as a user observation; no exact-53 test establishes that universal
threshold. [Rothsport](https://rothsport.com/products/reinforced-engine-carrier-993)
reports customer carrier failures and supplies gusseted carriers, but gives
neither an exact Turbo reference nor a load spectrum or quantitative validation.
Do not transfer non-Turbo failures or aftermarket material claims to suffix 53.

The first candidate to assess is a formed steel channel with local gussets at
the boss junctions and smooth transitions around the central four-hole joint.
This follows the flange/gusset strategy described by the
[Rennline manufacturer](https://www.rennline.com/rennline-rsr-style-stainless-steel-engine-carrier-porsche-sku-m01-rs/).
It is an engineering hypothesis, not a selected alloy, proven strength gain or
price estimate. Compare fabrication cost with machined alternatives after
measuring the envelope; an expensive billet or additive route is not justified
by the available evidence.

Preserve the measured central and end interfaces, required tool access,
mount seating faces and packaging. Establish engine torque versus speed,
engine/gearbox mass and centre of gravity, mount stiffness/preload, body support
locations, shock and launch duty, temperature/corrosion environment and required
life. Include the bracket, fasteners, rubber mounts and body in the load model;
a stiffer carrier may transfer larger loads into those neighbours. Power alone
cannot set bolt forces or a fatigue requirement.

Compare the measured original and candidate under the same reviewed load
cases. Inspect stress and fatigue at central holes, flange transitions and
boss joints; control weld quality and distortion if that route is chosen.
Check stiffness, mounting clearances and a physical load/fatigue test against
pre-agreed criteria before a functional release. Geometry optimisation starts
after the interface/load contracts are populated, not from a guessed hole
pattern or a model-generated strength claim.

The new 360-step Qwen candidate was also run on this real brief as a separate
diagnostic. It returned all three interfaces as missing and unverified, with
unknown material and no manufacturing authorization; that matches the external
audit because no replacement geometry exists. The input, raw response and
adapter hash are retained in [requirements.json](requirements.json). This one
result does not rescue its failed 39/70 validation score or select the adapter.
