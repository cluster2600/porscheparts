"""Lossless standard-decimal coordinates for CalculiX's F20.0 node reader."""

import math
import struct


def format_coordinate(value: float) -> str:
    """Return a token of at most 20 characters with identical binary64 bits.

    Reject values that cannot be represented by the supported standard decimal
    forms. Callers must handle that refusal before accepting a mesh; silently
    rounding a midpoint can invalidate an exact nested-refinement contract.
    Fortran's implicit exponent syntax is deliberately outside this interface.
    """
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("A CalculiX coordinate must be finite")
    expected = struct.pack("d", value)
    candidates = []
    forms = [repr(value)]
    forms.extend(format(value, f".{n}g") for n in range(1, 18))
    forms.extend(format(value, f".{n}f") for n in range(25))
    for token in forms:
        if "e" in token:
            mantissa, exponent = token.split("e")
            token = mantissa + "e" + str(int(exponent))
        if token.startswith("-0."):
            token = "-." + token[3:]
        elif token.startswith("0."):
            token = token[1:]
        if len(token) <= 20 and struct.pack("d", float(token)) == expected:
            candidates.append(token)
    if not candidates:
        raise ValueError("No exact standard decimal coordinate fits 20 characters")
    return min(candidates, key=lambda token: (len(token), token))
