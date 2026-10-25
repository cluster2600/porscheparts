"""Independent analytical cantilever worker used through OpenMDAO ExternalCodeComp."""

import argparse

from ft_common import finite, load, write


def solve(values):
    if values.get("units") != {
        "length": "m",
        "force": "N",
        "modulus": "Pa",
        "density": "kg/m3",
    }:
        raise ValueError("explicit SI beam units required")
    length, width, height, force, modulus, density = [
        finite(values[key], positive=True)
        for key in ("length", "width", "height", "force", "modulus", "density")
    ]
    return {
        "mass": finite(density * length * width * height, positive=True),
        "deflection": finite(
            4 * force * length**3 / (modulus * width * height**3), positive=True
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write(args.output, solve(load(args.input)))


if __name__ == "__main__":
    main()
