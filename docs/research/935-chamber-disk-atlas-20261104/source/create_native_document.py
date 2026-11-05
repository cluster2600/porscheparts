"""Save, reopen and re-export private acquired disk references in native FreeCAD."""
import hashlib
import json
import os
from pathlib import Path
import shutil

import FreeCAD as App
import Part


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            result.update(block)
    return result.hexdigest()


def counts(shape):
    return [len(shape.Vertexes), len(shape.Edges), len(shape.Faces), len(shape.Shells), len(shape.Solids)]


job = json.loads(Path(os.environ["PORSCHE_CHAMBER_ATLAS_JOB"]).read_text())
output, report, exported = map(Path, (job["output"], job["report"], job["roundtrip_directory"]))
if output.exists() or report.exists() or exported.exists():
    raise ValueError("Existing native atlas document output refused")
document = App.newDocument("AcquiredChamberDiskAtlas")
for item in job["items"]:
    if sha(item["native"]) != item["sha256"]:
        raise ValueError("Admitted native BREP hash mismatch")
    feature = document.addObject("Part::Feature", item["name"])
    feature.Label = item["label"]
    feature.Shape = Part.read(item["native"])
    if not feature.Shape.isValid() or counts(feature.Shape) != item["counts"]:
        raise ValueError("Native source reference import changed topology")
    for name, value in {
        "EvidenceRole": "Exact acquired facets in source-edge disk domains; anatomy unresolved",
        "SourceBREPHash": item["sha256"],
        "UnitsAuthority": "Owner-confirmed OBJ millimetres; not independent specimen metrology",
    }.items():
        feature.addProperty("App::PropertyString", name, "Evidence")
        setattr(feature, name, value)
    feature.addProperty("App::PropertyBool", "ManufacturingAuthorized", "Evidence")
    feature.ManufacturingAuthorized = False
document.recompute()
output.parent.mkdir(parents=True, exist_ok=True)
document.saveAs(str(output))
App.closeDocument(document.Name)
saved_hash = sha(output)
reopened = App.openDocument(str(output))
exported.mkdir(mode=0o700, parents=True)
checks = []
for item in job["items"]:
    feature = reopened.getObject(item["name"])
    if feature is None or not feature.Shape.isValid() or counts(feature.Shape) != item["counts"] or feature.ManufacturingAuthorized:
        raise ValueError("Saved FreeCAD source-reference topology failed")
    path = exported / item["basename"]
    feature.Shape.exportBrep(str(path))
    path.with_suffix(".units.json").write_text(json.dumps({
        "native_sha256": sha(path), "units": "mm",
        "authority": "owner-confirmed OBJ scale; not independent metrology"
    }, indent=2) + "\n")
    checks.append({"object": item["name"], "counts_vertices_edges_faces_shells_solids": counts(feature.Shape),
                   "actual_saved_feature_brep_sha256": sha(path), "valid": True})
App.closeDocument(reopened.Name)
if sha(output) != saved_hash:
    raise ValueError("Read-only saved-document inspection changed its bytes")
# The source fixture supplies an inspection precondition; it is not a document feature.
for source in job["fixture_files"]:
    if sha(source["path"]) != source["sha256"]:
        raise ValueError("Admitted inspection fixture changed")
    shutil.copy2(source["path"], exported / Path(source["path"]).name)
result = {"native_document_reopened": True, "objects": checks, "freecad_version": App.Version()[:3],
          "document_sha256": saved_hash, "fixture_is_document_feature": False,
          "actual_saved_feature_exports_require_independent_inspection": True,
          "full_head_created": False, "physical_acceptance": False, "manufacturing_authorized": False}
with report.open("x") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print("CHAMBER_ATLAS_DOCUMENT_OK")
