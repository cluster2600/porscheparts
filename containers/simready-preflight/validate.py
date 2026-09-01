#!/usr/bin/env python3
"""Validate the packaged CAD converter used by the immutable workflow image."""

import subprocess


subprocess.run(
    ["/opt/usd-convert-cad/bin/usd-convert-cad", "--help"],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
print("usd-convert-cad packaged runtime OK")
