# Failed observer host-registration check

**The host check is refused: the host exits with SIGSEGV (-11), and its outer owner exits with code 2.** The plugin loads, the framed constructed-type list contains `CouponEnd181DofMap` once and stderr prints “Syntax OK”. Those observations do not satisfy the required normal-exit conjunction.

One root-owned `combined-opt --check-input --list-constructed-objects` invocation used the unchanged coupon physics, materials, loads and solver controls. Additions are limited to observer registration, its output configuration and passive PETSc vector monitors. The check-only source route performs input actions and problem setup, then avoids executioner initialization and time stepping. No observer callback, live DOF map or solver-vector capture was requested.

The selected existing OS crash report for the exact failed process places the fault in `OutputWarehouse` destruction, followed by `MooseApp` destruction. Pinned public MOOSE source suggests a concrete dynamic-library/object-lifetime ordering to investigate. The exact invalid object, installed/source ABI equivalence and causal mechanism remain unproved. Only selected crash fields and frames are published; the private raw report is excluded.

All 63 selected records and 22 declared provider-path associations remain unchanged. The saved owner records no controller stop request or termination action, and the owned process group is absent. Independent metadata accounting gives 566,535 generated/control/log bytes including the receipt, after subtracting only the four pinned staged inputs. The sampled peak RSS is 165,642,240 bytes. These observations preserve the failed result; they do not qualify the runtime ABI or establish a hard memory quota.

- [Input/source contract](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-check-prep-001/held-check-plan.json)
- [Exact-child review and mandatory postchecks](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-exact-child-peer-001/review.json)
- [Explicit outer no-site variant](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-outer-no-site-peer-001/review.json)
- [Complete host stdout](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-root-execution-001/host.stdout)
- [Complete host stderr and loader trace](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-root-execution-001/host.stderr)
- [Execution receipt](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-root-execution-001/receipt.json)
- [Selected crash extract](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-root-review-001/os-crash-selected-extract.json)
- [Independent result refusal](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-result-peer-001/review.json)
- [Root refusal acknowledgement](records/cp1-oneway-cooling-release-richardson2-observer003-host-registration-root-review-001/independent-refusal-acknowledgement.json)
- [Inventory and original-source identities](FILES.json)

The 32 byte-exact originals retain editable input/controller, source associations, staging/runtime metadata, reviews, admission, full logs and refusal evidence. Original workspace paths are provenance. Raw grid/field bodies, runtime binaries, objects, raw private OS report and third-party source bodies are excluded.

The earlier [18 synthetic observer assertions](../cp1-END181-observer-validator/README.md) remain accepted in their software scope. This failed host check accepts no live callback/map, new native mechanical trajectory, strength, material, calibrated LPBF process or manufacturing result. All twelve existing coupon equilibrium failures remain open. No unchanged retry occurred.
