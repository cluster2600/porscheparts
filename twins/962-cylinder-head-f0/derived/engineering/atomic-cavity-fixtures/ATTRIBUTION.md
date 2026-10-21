# Source and licence attribution

Original project records, literal synthetic geometry, scripts and documentation retain the repository terms in [LICENSE.project](LICENSE.project). Third-party material keeps its own terms; the project licence does not replace them.

Source002's final shared-triangle scalar policy follows the retained installed CGAL 5.6 `Surface_mesh_simplification/internal/Edge_collapse.h`, lines 911–964 and constructor line 433. The header identifies Copyright (c) 2006 GeometryFactory (France), author Fernando Cacciola, and `SPDX-License-Identifier: GPL-3.0-or-later OR LicenseRef-Commercial`. Its retained SHA-256 is `e86265a275a2ac03609bb4272fcede472a4dc577304d8ec1b3b8dc3b8fd630b8`. Upstream-derived portions retain their licence; GPL-3.0-or-later is the public alternative recorded here. No full header or executable is distributed in this capsule.

Primary source: https://github.com/CGAL/cgal/blob/v5.6/Surface_mesh_simplification/include/CGAL/Surface_mesh_simplification/internal/Edge_collapse.h

GPL licence text: https://www.gnu.org/licenses/gpl-3.0.html

The predicate first requires the larger squared normal norm to be strictly less than 1e8 times the smaller, then accepts a positive normal dot product or applies the unchanged squared-cosine dihedral condition. Source002 applies that scalar policy to its final affected-neighbor pairs. This does not assert a historical SMS queue decision or the validity of hypothetical intermediate collapses.

The capsule [source bindings](source-bindings.json) identify the original project `quality_patch.cpp` include and the exact new source002 by SHA-256 at their repository source paths. They are not duplicated here. The small preserved source001-to002 diff contains the two additional project guard changes, not a copy of the upstream predicate. Actual binary/source association is retained through the original compile and fixture input maps; a compiler log does not independently attest every installed library build.
