# Source and upstream attribution

Original project source, reports and documentation remain under `LICENSE.project`. Third-party material retains its own licence; the project licence does not replace it.

`sources/installed-header-telemetry.diff` is an attributed diagnostic patch against CGAL 5.6 `Surface_mesh_simplification/internal/Edge_collapse.h`. The original header states: Copyright (c) 2006 GeometryFactory (France); author Fernando Cacciola; `SPDX-License-Identifier: GPL-3.0-or-later OR LicenseRef-Commercial`. The diff retains upstream context. Its upstream-derived portions retain that licence; GPL-3.0-or-later is the public licence alternative recorded here. No full upstream header or compiled executable is included. The diff adds a friend accessor and observational event labels; it does not grant permission to bypass guards.

Primary source: https://github.com/CGAL/cgal/blob/v5.6/Surface_mesh_simplification/include/CGAL/Surface_mesh_simplification/internal/Edge_collapse.h

Licence text: https://www.gnu.org/licenses/gpl-3.0.html

Original retained installed header SHA256: e86265a275a2ac03609bb4272fcede472a4dc577304d8ec1b3b8dc3b8fd630b8. Instrumented header SHA256: 546fa3309f3f7cbde3984f6dde188331674139d01741c1fe6883682c94fdebec. The patch source SHA256 is in the capsule receipt.

The source main includes the existing project dependency `twins/962-cylinder-head-f0/source/analysis-cgal/quality_patch.cpp` (6a56acf7a1d7a4882251044f9331ff0e4590042a4d1d15f0b4599e0ab241d9ee). The corrected endpoint guard snapshot derives from existing `finest_endpoint_003.cpp` (e80bb80f39f25f3c30cb02b7096df06c093de9343dab9afffc33720797e8256b). Their frozen dependencies and actual build image are bound in `projections.json`; a visible source or successful compile is not a standalone reproducible-runtime claim.

No executable is distributed; the diagnostic grants no head or manufacturing qualification.
