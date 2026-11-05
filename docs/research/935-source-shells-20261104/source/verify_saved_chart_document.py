"""Read-only native reopen check; intended to run under outbound denial."""
import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8388608), b""):
            result.update(block)
    return result.hexdigest()


job = json.loads(Path(os.environ["PORSCHE_SOURCE_CHART_JOB"]).read_text())
expected = json.loads(Path(job["report"]).read_text())
output = Path(os.environ["PORSCHE_SOURCE_CHART_OFFLINE_REPORT"])
if output.exists() or digest(job["output"]) != expected["output_sha256"]:
    raise RuntimeError("Existing report or changed native document refused")
document = App.openDocument(job["output"])
for item in job["items"]:
    feature = document.getObject(item["name"])
    shape = feature.Shape
    measured = [len(shape.Vertexes), len(shape.Edges), len(shape.Faces), len(shape.Shells), len(shape.Solids)]
    if not shape.isValid() or measured != item["counts"] or feature.ManufacturingAuthorized:
        raise RuntimeError("Offline native source-chart check failed")
App.closeDocument(document.Name)
if digest(job["output"]) != expected["output_sha256"]:
    raise RuntimeError("Read-only check changed the native document")
with output.open("x") as stream:
    json.dump({"native_readonly_reopen_passed": True, "document_sha256": expected["output_sha256"],
               "source_sha256": digest(__file__), "physical_acceptance": False,
               "manufacturing_authorized": False}, stream, indent=2)
    stream.write("\n")
print("SOURCE_CHART_OFFLINE_REOPEN_OK")
