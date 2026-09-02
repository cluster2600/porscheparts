"""Narrow capability manifest for the immutable packaged CAD adapter.

The NVIDIA CAD-to-SimReady router reads this file through the Python AST.  It
is intentionally limited to the STEP formats exercised by this repository.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatInfo:
    file_types: tuple[str, ...]


SUPPORTED_FORMATS = (
    FormatInfo((".step", ".stp")),
)
