# Prescribed cooling and support-release coupon — source held

This is a fresh t=0 mechanical study on the existing425-node/256-HEX8 coupon. It preserves the accepted thermal tokens through .4s and the original BEGIN80 born-reference temperature. The new trajectory is clamped during heating/birth/cooling; it does not reuse the old unclamped displacement or stress history.

Twenty prescribed cooling steps reach300K at END180/.45s. Release occurs at BEGIN181/.4525s; the original six rigid-mode constraints then replace the plane clamp. Two constant300K equilibrium steps end at .455s. All cooling/clamping inputs are unmeasured research assumptions. There is no solved cooldown heat loss, plasticity, qualified CP1 law or head result.

- METHOD.md explains assumptions, phases, commands, resource bounds and independent evidence required.
- card.json and case-contract.json define the fixed SI case and sampled field inventory.
- thermoelastic-birth.i is the narrowly changed deck.
- prepare_continuation.py extends three accepted tables without repeating the321-CSV conversion.
- run_mac.py retains existing Mac cleanup/timeout/RSS/output/runtime controls.
- selfcheck.py has eight source/data groups; test_controls.py has six mocked control groups. All14 are UNRUN.
- source.diff and source-reuse.json retain whole-byte reversals and exact function reuse.
- held-preparation.json freezes33 input roles:30 permitted small bodies and three original-grid identities deferred until a future data operation. This informational README is added after that held seal and is not a consumed input or an authority grant.

No table conversion, prepared function/guard/module, runtime query, solver or actual has run. No output directory has been created. All source-held authority/qualification flags are false. A fresh selected-runtime24-object registry/TimePeriod binding, independently reviewed continuation3D assessor, accepted data result and separate exact native actual remain mandatory before any solve. The100s/sample2GiB/512MiB/one-thread limits are retained, with proposed115s/T10 outer cleanup; successful completion is not predicted.
