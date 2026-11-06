"""Independently reopen the saved FreeCAD file and export actual stored features."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

import FreeCAD as App


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):h.update(data)
    return h.hexdigest()


def counts(shape):
    return [len(shape.Vertexes), len(shape.Edges), len(shape.Faces), len(shape.Shells), len(shape.Solids)]


def main():
    job_path = Path(os.environ["PORSCHE_COMPLETE_SOURCE_CAD_JOB"]); before = sha(job_path)
    job = json.loads(job_path.read_text()); native_report = json.loads(Path(job["report"]).read_text())
    source = Path(job["output"]); assert sha(source) == native_report["output_sha256"]
    output = Path(job["roundtrip_output"]); output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic(); document = App.openDocument(str(source)); exported = []
    try:
        assert len(document.Objects) == len(job["items"])
        for item in job["items"]:
            feature = document.getObject("SourceChunk"+str(item["chunk"]).zfill(4))
            assert feature is not None and feature.Shape.isValid() and counts(feature.Shape) == item["counts"]
            assert not feature.Shape.Solids and not feature.ManufacturingAuthorized and not feature.FunctionalPartIdentityAccepted
            assert feature.Placement.Base.Length == 0 and feature.Placement.Rotation.Angle == 0
            assert feature.SourceSTEPHash == item["raw_step_sha256"]
            raw = output/("saved-feature-"+str(item["chunk"]).zfill(4)+".step")
            feature.Shape.exportStep(str(raw)); raw_sha = sha(raw); raw_bytes = raw.stat().st_size
            packed = raw.with_suffix(raw.suffix+".gz")
            with raw.open("rb") as incoming, packed.open("xb") as target:
                with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as archive:
                    for data in iter(lambda: incoming.read(1024**2), b""):
                        assert shutil.disk_usage(output).free >= 4*1024**3
                        archive.write(data)
            h = hashlib.sha256(); n = 0
            with gzip.open(packed, "rb") as incoming:
                for data in iter(lambda: incoming.read(1024**2), b""):h.update(data); n += len(data)
            assert h.hexdigest() == raw_sha and n == raw_bytes
            raw.unlink(); exported.append({"chunk": item["chunk"], "gzip": packed.name,
                "gzip_sha256": sha(packed), "gzip_bytes": packed.stat().st_size,
                "actual_saved_feature_raw_step_sha256": raw_sha, "actual_saved_feature_raw_step_bytes": raw_bytes,
                "source_comparison_not_yet_performed": True})
            print(json.dumps({"actual_saved_native_feature_exported": item["chunk"]}), flush=True)
    finally:
        App.closeDocument(document.Name)
    assert sha(source) == native_report["output_sha256"] and sha(job_path) == before
    result = {"source_sha256": sha(__file__), "job_sha256": before, "native_document_sha256": sha(source),
              "actual_saved_features_exported": exported, "native_document_rehashed_unchanged": True,
              "source_comparison_required_before_acceptance": True, "physical_acceptance": False,
              "manufacturing_authorized": False, "seconds": time.monotonic()-started}
    with (output/"report.json").open("x") as stream:stream.write(json.dumps(result, indent=2)+"\n")
    print("COMPLETE_SOURCE_REFERENCE_SAVED_EXPORT_OK", flush=True)


main()
