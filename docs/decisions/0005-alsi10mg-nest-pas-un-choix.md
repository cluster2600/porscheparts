# 0005 — The ring's AlSi10Mg was never chosen

Date: 2026-09-11

## Decision

Stop presenting `AlSi10Mg` as the material of the switch trim ring
`993-INT-SWITCH-TRIM-RING-F1-0001`. It is **inherited**, not selected. Reopen
the material question and the process question together, before sending
anything to a service provider.

## What actually decided

AlSi10Mg is the only grade for which the repository has a
material-machine-process map
([`eos-m290-alsi10mg-30um.json`](../../catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json)).
The ring is, moreover, the only `non_critical` part in the catalogue to list
LPBF among its candidate processes — the other two non-critical parts are
polymer. The metal pilot therefore came out of a double elimination, on safety
on one side and on available documentation on the other. At no point did a
functional criterion come into play.

## The three reasons to reopen

**1. The criterion that governs this part is appearance, not strength.** A
dashboard trim ring carries nothing. The step 04 screening shows it without
saying it: the only mechanical gate, the minimum wall, passes by a wide margin,
and no load case exists. What decides here is the surface finish, the gloss and
the match with the neighboring trim.

**2. AlSi10Mg is bad precisely at the operation the part needs.** Its silicon
content of 9 to 11% makes it unfit for decorative anodizing: since silicon is
not soluble in aluminum, only the silicon-poor areas anodize, and the part comes
out gray-brown to black (`SRC-FEHRMANN-ALMGTY-ANODISING-ALSI10MG-LIMIT`). Yet
anodizing is explicitly listed among the record's planned post-processing steps.
On top of this comes an as-built Ra of 12 to 25 µm stated by the candidate
service provider, on a visible part. The wrought 6xxx grades do the opposite:
6063 T6 is rated excellent for bright anodizing
(`SRC-1STCHOICEMETALS-6XXX-BRIGHT-ANODISING`), and that is very likely what the
original ring is, described as "aluminum" with no further detail by the seller.

**3. The repository's grid already excludes this part from additive
manufacturing.** [`TITANIUM.md`](../TITANIUM.md) retains three families where
additive manufacturing wins: internal passages that cannot be machined, castings
that cannot be cored, and consolidation of subassemblies. A 6 g axisymmetric
ring is none of the three. Its own catalogue record has said so from the start:
"the axisymmetric geometry probably favors CNC turning; the benefit of LPBF
remains to be demonstrated".

## Consequence

The material question and the process question are one and the same. For this
part, the likely answer is **6xxx bar stock, turned and then bright-anodized**,
not laser sintering of a casting alloy. The quote remains useful — it was
requested to find out what a Chinese service provider is willing to put in
writing, not to obtain the ring — but it must now cover both routes and be
judged on the comparison, not on the LPBF price alone.

## Accepted limitation

The repository has no 6xxx material map, no measurement of the original ring and
no identification of its actual grade. The sentence "it is probably
bright-anodized 6063" is a level B assumption, not an identification. It becomes
a decision only after a sample has been measured.

## What this opens

If the goal is to print metal because additive manufacturing is the right
answer, and not because the part was the least risky, then the choice must be
made within the three families of `TITANIUM.md`. The catalogue candidates that
genuinely belong to them — internal ducts, water boxes, manifolds — are all
currently classified `functional` or `prohibited_pending_engineering`. Choosing
one of them means accepting an engineering path, not a digital-chain pilot. It
is a trade-off to be stated explicitly, not to be sidestepped by going back to
the most harmless part.
