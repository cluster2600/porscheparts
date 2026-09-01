#!/usr/bin/env python3
"""Compatibility entrypoint expected by NVIDIA CAD-to-SimReady preflight."""

import os
import sys


os.execv("/opt/usd-convert-cad/bin/usd-convert-cad", ["usd-convert-cad", *sys.argv[1:]])
