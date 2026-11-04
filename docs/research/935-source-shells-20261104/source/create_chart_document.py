"""Create and reopen a private native FreeCAD source-chart review document."""
import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8388608), b""):
            h.update(block)
    return h.hexdigest()


def counts(shape):
    return [len(shape.Vertexes), len(shape.Edges), len(shape.Faces),
            len(shape.Shells), len(shape.Solids)]


job = json.loads(Path(os.environ["PORSCHE_SOURCE_CHART_JOB"]).read_text())
output, report = Path(job["output"]), Path(job["report"])
if output.exists() or report.exists():
    raise RuntimeError("Existing native chart document refused")
document = App.newDocument("ObservedSourceCharts")
for item in job["items"]:
    if digest(item["step"]) != item["sha256"]:
        raise RuntimeError("Verified STEP checksum mismatch")
    feature = document.addObject("Part::Feature", item["name"])
    feature.Label = item["label"]
    feature.Shape = Part.read(item["step"])
    if not feature.Shape.isValid() or counts(feature.Shape) != item["counts"]:
        raise RuntimeError("Native chart import topology mismatch")
    feature.addProperty("App::PropertyString", "EvidenceRole", "Evidence")
    feature.EvidenceRole = "Exact acquired facets; source vertex point contacts separated into manifold charts"
    feature.addProperty("App::PropertyString", "SourceSTEPHash", "Evidence")
    feature.SourceSTEPHash = item["sha256"]
    feature.addProperty("App::PropertyBool", "ManufacturingAuthorized", "Evidence")
    feature.ManufacturingAuthorized = False
document.recompute()
output.parent.mkdir(parents=True, exist_ok=True)
document.saveAs(str(output))
App.closeDocument(document.Name)
reopened = App.openDocument(str(output))
checks = []
for item in job["items"]:
    feature = reopened.getObject(item["name"])
    if feature is None or not feature.Shape.isValid() or counts(feature.Shape) != item["counts"] or feature.ManufacturingAuthorized:
        raise RuntimeError("Saved native source-chart verification failed")
    checks.append({"object": item["name"], "counts_vertices_edges_faces_shells_solids": counts(feature.Shape),
                   "valid": True})
App.closeDocument(reopened.Name)
result = {"native_document_reopened": True, "objects": checks,
          "freecad_version": App.Version()[:3], "output_sha256": digest(output),
          "full_head_created": False, "physical_acceptance": False,
          "manufacturing_authorized": False}
with report.open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print("SOURCE_CHART_DOCUMENT_OK")
