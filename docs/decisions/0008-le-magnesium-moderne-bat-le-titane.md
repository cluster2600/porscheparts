# 0008 — For the chain case cover, modern magnesium beats titanium

Date: 2026-09-11

## Decision

Retain as the best route for `964 105 107 01` a **modern magnesium cover** —
high-purity alloy, machined, PEO-treated — and not a titanium cover, nor the
aftermarket billet aluminum cover.

The initial request was for titanium. It is set aside on numbers, not on a
preference.

## The reversal, in two steps

**First step: the original part is not aluminum, it is magnesium.** Every mass
comparison made before this discovery set titanium against the *aftermarket
replacement*, not against the original part.

**Second step: the magnesium of 1995 is not the magnesium of today.** It was not
the material that was bad; it was its era.

| | 1995 | today |
|---|---|---|
| surface technology | chromate conversion, hexavalent chromium | **PEO / MAO**, ceramic layer |
| environmental profile | toxic, carcinogenic | REACH-compliant |
| mechanism | passive barrier | active coatings, sol-gel |
| alloy | standard purity | **high purity**, Fe/Ni/Cu capped |

The decisive line is the last one. Magnesium corrosion is driven by three
impurities — iron, nickel, copper — that form **internal** cathodic sites. The
ASTM limits for AZ91D cap them at 0.004%, 0.001% and 0.015%, and high-purity
alloys are reported to be **up to a hundred times** more resistant than standard
alloys in salt spray, more resistant even than cast 380 aluminum or cold-rolled
steel.

The 1995 cover does not rot because it is magnesium. It rots because it is
magnesium **from 1995**.

## The table that settles it

| route | density | stiffness `E^⅓/ρ` | strength `σ^½/ρ` | couple with the Mg case |
|---|---:|---:|---:|---|
| **modern magnesium** | **1.81** | **1.965** | **6.988** | **none — same metal** |
| billet aluminum (the market) | 2.70 | 1.526 | 4.969 | mild |
| Ti-6Al-4V | 4.43 | 1.095 | 6.503 | **the worst in the grid** |

Magnesium wins **both** indices, by a wide margin. It removes the galvanic
couple because it is of the same nature as the case it bolts onto. It cancels
differential expansion, which drops to zero instead of titanium's 0.072 mm. And
it addresses the failure mode **at its root** instead of working around it.

Titanium, for its part, protected its own seat while risking aggravated attack
on the case opposite — that is, moving the problem onto the part that cannot be
replaced.

## What this says beyond this part

Three times in this project, the right answer has been **the original material,
done properly**, and not a nobler material:

- the switch trim ring: turned 6063, not sintered AlSi10Mg;
- the chain case and the camshaft housing: aluminum, not titanium;
- this cover: magnesium, not titanium.

The lesson deserves to be written down. An old part that fails does not always
indict its material — often it indicts the **state of the art of its era**. The
first question to ask is therefore not "what should replace it", but **"what can
we do today that we could not do then"**.

## The real obstacles, not investigated

- **Machining magnesium requires an equipped shop**: fine chips are flammable,
  and not every shop takes the work. This is the dominant supplier constraint.
- **PEO deposits 5 to 40 µm.** On a joint face, this is masked or re-machined
  after treatment.
- **Common wrought plate is AZ31B**, not cast AZ91E: the alloy available as bar
  stock is not the original one, and its performance with PEO remains to be
  established for this use.
- None of these three questions is investigated here.

## Credit

The reversal came from the user, who raised the question of modern treatment
after this repository had concluded on a materials comparison. The repository
was right on the numbers and wrong on the question.
