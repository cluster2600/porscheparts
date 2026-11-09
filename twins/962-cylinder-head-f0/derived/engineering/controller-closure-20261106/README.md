# macOS owned-group diagnostic for issue #447

The three-case probe reproduced EPERM (errno 1) when signalling an exited,
unreaped child on the owner Mac. TERM to a live child succeeded; KILL after its
NOTE_EXIT returned EPERM. Both TERM and KILL succeeded for the live child that
ignored TERM. All three were explicitly reaped and their groups were absent
after reap. No signal was sent after reap. These observations explain a possible
cause of the historical signal failures; they do not prove that cause for every
historical process group or establish that descendants have exited.

The fixed source is under `source/controller_closure_20261106/`. The selected
Python 3.10.11 executable matched the historical SHA-256
`72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621`.
Invocation used `python3.10 -B -I -S probe_owned_groups.py <fresh-output>`.
The external observer recorded 0.11076458299066871 seconds from startup through
return and final output census, return code zero and empty streams. This is
the diagnostic interval, not the historical controller's full interval.

`probe002.json` binds the source hash and saves the complete three-case result.
`probe001.json` retains the failed first attempt: Python 3.10 kqueue does not
provide the context-manager protocol. Its owned child was killed and reaped;
group absence was not measured. The correction uses standard-library `closing`.
Neither result qualifies the controller or an engineering phase.

The input audit independently rehashed all 35 protected source records: all
matched. A separate runtime audit matched all 91 historical Python runtime
files, the selected interpreter and its provider library (93/93 records).
The historical Z3 5.1.0 executable is absent, and its current alias
points to 5.3.2. The accepted runtime contract therefore cannot be replayed as
is. No consumed admission was reused, no native003 retry was issued, and no
native005 or head workload was executed. Restoring the exact accepted runtime
or preparing a separately reviewed runtime generation precedes a fresh owner
run. EPERM must not be reclassified as absence; descendant ownership and final
census remain required.

The fresh workflow ledger was generated and checked against the complete
19-phase contract. Every phase remains blocked: provenance, reconstruction,
picogk, surface, volume, coolant_cfd, cht, material_strength, lpbf_melt_pool,
lpbf_build, lpbf_release, omni_preflight, omni_conversion, omni_assignment,
omni_conformance, field_exchange, omni_render, physicsnemo and delivery.
This software investigation is associated with volume, material_strength,
lpbf_build and lpbf_release only. Manufacturing remains unauthorized.

Four portable tests independently review saved outcomes and source binding,
retain the failed attempt, and reject numeric PID signalling after a terminal
handshake reap or lost direct-child relationship. They do not emulate macOS
kernel behavior. Issue #447 remains open for the complete guarded owner run,
native005 input binding and independent full-result review.
