"""Offline standalone OV lifecycle check; no GPU or physical validity claim."""
import json
from importlib.metadata import version

import ovstage
from ovphysx import PhysX

physics = PhysX()
try:
    assert callable(physics.destroy), "ovphysx 0.7 lifecycle unavailable"
finally:
    physics.destroy()
stage = ovstage.Stage("stack-smoke")
stage.destroy()
print(json.dumps({"status": "passed", "scope": "cpu_lifecycle_only",
                  "versions": {name: version(name) for name in
                               ("ovphysx", "ovstage", "warp-lang", "physx-usd-schemas")}}))
