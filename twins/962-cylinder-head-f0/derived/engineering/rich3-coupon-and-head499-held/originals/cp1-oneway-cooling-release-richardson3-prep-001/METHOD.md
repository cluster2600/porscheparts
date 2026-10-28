# Held RICH3 input: one additional Richardson correction

This is an unrun input-source preparation. The donor is the exact 15,537-byte staged RICH2 observer deck, SHA256 `190296e6c2ad1627feca4b374efd2c49739e0c2628764cd92388392a78fd2682`.

The new deck changes one ASCII byte at zero-based offset 14954, on line 590: the value corresponding to `-ksp_max_it` changes from `2` to `3`. The option name, count-based `skip` stopping test, Richardson scale, LU preconditioner, monitors, relative grid names, output file bases, material, loads, time controls and every other byte remain identical. No assessor/POLICY or `1e-7` gate is changed. Nonlinear tolerance literals remain unchanged and are inactive under the existing LINEAR/ksponly formulation.

The manifest binds both complete source identities and the exact unified diff. Forward substitution over the entire donor buffer produces the new deck; the inverse over the entire new buffer restores the donor byte-for-byte. Both buffers remain 15,537 bytes. These are text/hash checks, not a MOOSE parse, solver test or convergence observation.

The purpose of the future separate experiment is to measure the response to one additional existing correction. Three updates still establish only count completion. All original residual/field criteria, material calibration, strength and downstream qualification remain open. Root must separately stage exact grids and review/admit the existing native route. No grid/CSV/vector/runtime body, caller/controller, actual/admission, output root, solver operation or PUB/Git change is included here.

The author also wrote the preceding QP arithmetic audit and experiment proposal. This source-author preparation provides no independent scientific or execution acceptance. The captured donor and all prior failures remain immutable.
