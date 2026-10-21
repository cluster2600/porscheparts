# Native USD conversion readiness

The [receipt](receipt.json) records a passing **conversion-only** check of the
installed CAD to SimReady skill. It used native Linux x86_64, GLIBC 2.43 and a
dedicated CPython 3.12.13 environment with NVIDIA usd-convert-cad 0.2.0 and
PyYAML 6.0.3. Public download hashes, interpreter/archive byte bindings, exact
preflight source/lock hashes and the pinned guidance commit are retained.

The unmodified preflight ran in check-only mode for STL conversion, with
Content Agents and deployment skipped. It returned `ready` with no blockers.
No source asset was supplied. Native HOOPS/OpenUSD imports, converter help,
package checks and Git LFS discovery also passed separately.

The bundled HOOPS library directory must be configured before Python starts.
The receipt distinguishes the retained initial mount refusal, older-rootfs
GLIBC incompatibility, missing startup library path and archive HTTP refusal
from the subsequent successful native checks. They are not conversion runs.

The minimum USD validator requires its own `openusd_python` preflight entry;
this deliberately narrow conversion manifest does not contain that component.
Any later asset conversion and minimum-validation result need separate evidence.
Full validation services, physical materials, solver fields and rendering are
outside this receipt. Historical fidelity and manufacturing authorization remain
false. No private host/path, command, binary or third-party geometry is published.
