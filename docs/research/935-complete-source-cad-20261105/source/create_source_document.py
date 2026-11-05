"""Native FreeCAD document from independently verified compressed source charts."""
import gc
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import FreeCAD as App
import Part


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):h.update(data)
    return h.hexdigest()


def counts(shape):
    return [len(shape.Vertexes), len(shape.Edges), len(shape.Faces), len(shape.Shells), len(shape.Solids)]


def identity(feature):
    return feature.Placement.Base.Length == 0 and feature.Placement.Rotation.Angle == 0


def main():
    job_path = Path(os.environ["PORSCHE_COMPLETE_SOURCE_CAD_JOB"]); before_job = sha(job_path)
    job = json.loads(job_path.read_text()); output = Path(job["output"]); report = Path(job["report"])
    assert not output.exists() and not report.exists() and 1 <= len(job["items"]) <= 83
    assert job["source_arrays_sha256"] == "dd94c37117a1f1277a4f2b7f0bf0023e0d1858991b943f766cf447db319a101a"
    assert job["source_plan_sha256"] == "f26389c910ded839b94de910f495c0110a0fd103fc860af2b4a07e25139d5026"
    assert len({i["chunk"] for i in job["items"]}) == len(job["items"])
    staging = Path(job["staging"]); staging.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic(); document = App.newDocument("AcquiredSourceReference935")
    if hasattr(document, "UndoMode"):document.UndoMode = 0
    try:
        for item in job["items"]:
            source = Path(item["gzip"]); assert sha(source) == item["gzip_sha256"]
            temporary = staging/("source-"+str(item["chunk"]).zfill(4)+".step")
            h = hashlib.sha256(); n = 0
            with gzip.open(source, "rb") as incoming, temporary.open("xb") as outgoing:
                for data in iter(lambda: incoming.read(1024**2), b""):
                    assert shutil.disk_usage(staging).free >= 4*1024**3
                    outgoing.write(data); h.update(data); n += len(data)
            assert h.hexdigest() == item["raw_step_sha256"] and n == item["raw_step_bytes"]
            feature = document.addObject("Part::Feature", "SourceChunk"+str(item["chunk"]).zfill(4))
            feature.Label = "Acquired source chart "+str(item["chunk"]).zfill(4)
            feature.Shape = Part.read(str(temporary))
            assert feature.Shape.isValid() and counts(feature.Shape) == item["counts"] and not feature.Shape.Solids
            assert identity(feature)
            for name, value in (("EvidenceRole", "Acquired facets; chart seams and point-contact fan splits remain explicit"),
                                ("SourceSTEPHash", item["raw_step_sha256"]),
                                ("OriginalArrayHash", job["source_arrays_sha256"]),
                                ("SourceAtlasPlanHash", job["source_plan_sha256"])):
                feature.addProperty("App::PropertyString", name, "Evidence"); setattr(feature, name, value)
            feature.addProperty("App::PropertyInteger", "SourceChunkIndex", "Evidence"); feature.SourceChunkIndex = item["chunk"]
            for name in ("ManufacturingAuthorized", "FunctionalPartIdentityAccepted"):
                feature.addProperty("App::PropertyBool", name, "Evidence"); setattr(feature, name, False)
            feature.addProperty("App::PropertyBool", "SourceChartSeamsUnsewn", "Evidence"); feature.SourceChartSeamsUnsewn = True
            temporary.unlink(); gc.collect()
            print(json.dumps({"native_source_chart_imported": item["chunk"], "original_faces": item["counts"][2]}), flush=True)
        document.recompute(); output.parent.mkdir(parents=True, exist_ok=True)
        document.saveAs(str(output)); App.closeDocument(document.Name); document = None; gc.collect()
        reopened = App.openDocument(str(output)); checks = []
        try:
            assert len(reopened.Objects) == len(job["items"])
            for item in job["items"]:
                feature = reopened.getObject("SourceChunk"+str(item["chunk"]).zfill(4))
                assert feature is not None and feature.Shape.isValid() and counts(feature.Shape) == item["counts"]
                assert not feature.Shape.Solids and identity(feature) and not feature.ManufacturingAuthorized
                assert not feature.FunctionalPartIdentityAccepted and feature.SourceChartSeamsUnsewn
                assert feature.SourceSTEPHash == item["raw_step_sha256"] and feature.OriginalArrayHash == job["source_arrays_sha256"]
                checks.append({"chunk": item["chunk"], "counts_vertices_edges_faces_shells_solids": counts(feature.Shape),
                               "valid": True, "identity_placement": True, "physical_flags_false": True})
        finally:
            App.closeDocument(reopened.Name)
        assert sha(job_path) == before_job
        for item in job["items"]:assert sha(item["gzip"]) == item["gzip_sha256"]
        result = {"source_sha256": sha(__file__), "job_sha256": before_job, "freecad_version": App.Version()[:3],
                  "native_document_saved_closed_and_reopened": True, "objects": checks,
                  "output_sha256": sha(output), "output_bytes": output.stat().st_size,
                  "all_original_source_gzip_inputs_rehashed_unchanged": True,
                  "full_bare_head_created": False, "anatomical_identity_accepted": False,
                  "physical_acceptance": False, "manufacturing_authorized": False, "seconds": time.monotonic()-started}
        with report.open("x") as stream:stream.write(json.dumps(result, indent=2)+"\n")
        print("COMPLETE_SOURCE_REFERENCE_DOCUMENT_OK", flush=True)
    finally:
        if document is not None:App.closeDocument(document.Name)


main()
