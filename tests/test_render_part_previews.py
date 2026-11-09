"""Public image coverage must fail on absent, changed or mislabelled assets."""
import base64
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_part_previews as previews


class PublicPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.records = self.root / "catalog/parts"
        self.records.mkdir(parents=True)
        self.parts = self.root / "parts"
        self.record = {"part_id": "993-TEST-0001", "geometry": {"derived_files": []}}
        self.record_path = self.records / "993-test-0001.json"
        self.write_record()
        for name, value in (("ROOT", self.root), ("RECORDS", self.records), ("PARTS", self.parts)):
            mock = patch.object(previews, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.media = self.parts / "993-test-0001/media"
        self.media.mkdir(parents=True)

    def write_record(self):
        self.record_path.write_text(json.dumps(self.record))

    def publish(self, files=()):
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jSZkAAAAASUVORK5CYII=")
        names = ["preview.png", "views.png"] if files else ["preview.png"]
        for name in names:
            (self.media / name).write_bytes(png)
        info = {"part_id": self.record["part_id"],
                "kind": "geometry_render" if files else "status_card",
                "note": "Concept CAD; no fit or manufacturing qualification." if files else
                        "Status card; no part geometry depicted.",
                "images": names,
                "sources": [{"path": f.relative_to(self.root).as_posix(),
                             "sha256": previews.sha256(f)} for f in files]}
        previews.save_manifest(self.record, info)

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return previews.check()

    def test_every_record_requires_a_public_preview_even_without_cad(self):
        self.assertEqual(self.check(), 1)
        self.publish()
        self.assertEqual(self.check(), 0)

    def test_empty_image_list_cannot_pass(self):
        self.publish()
        manifest = self.media / "preview.json"
        info = json.loads(manifest.read_text())
        info["images"] = []
        manifest.write_text(json.dumps(info))
        self.assertEqual(self.check(), 1)

    def test_deleted_or_modified_image_fails(self):
        self.publish()
        (self.media / "preview.png").write_bytes(b"not a PNG")
        self.assertEqual(self.check(), 1)
        self.publish()
        with (self.media / "preview.png").open("ab") as stream:
            stream.write(b"changed")
        self.assertEqual(self.check(), 1)
        (self.media / "preview.png").unlink()
        self.assertEqual(self.check(), 1)

    def test_record_change_invalidates_status_card(self):
        self.publish()
        self.record["name"] = "Revised study"
        self.write_record()
        self.assertEqual(self.check(), 1)

    def test_catalogue_cad_outside_part_folder_requires_real_views(self):
        cad = self.root / "twins/study/derived/part.stl"
        cad.parent.mkdir(parents=True)
        cad.write_bytes(b"fixture CAD")
        self.record["geometry"]["derived_files"] = [cad.relative_to(self.root).as_posix()]
        self.write_record()
        self.assertEqual(previews.sources(self.record["part_id"]), [cad])
        self.publish()
        self.assertEqual(self.check(), 1)
        self.publish([cad])
        self.assertEqual(self.check(), 0)
        cad.write_bytes(b"updated CAD")
        self.assertEqual(self.check(), 1)

    def test_picogk_caption_identifies_the_actual_master_outside_legacy_catalogue(self):
        self.record["geometry"].update(
            master_format="PicoGK", master_file="twins/assumed-cell/picogk/Program.cs")
        note = previews.geometry_note(self.record, picogk_model=True, rotation_x_deg=0)
        self.assertIn("twins/assumed-cell/picogk/Program.cs", note)
        self.assertNotIn("parts/picogk-catalog/", note)
        self.record["geometry"]["master_file"] = "parts/picogk-catalog/body/Cell.cs"
        self.assertEqual(
            previews.geometry_note(self.record, picogk_model=True, rotation_x_deg=0),
            "Geometry views of the part's PicoGK concept model (parts/picogk-catalog/). "
            "Not a photograph, not a render of a manufactured part, not evidence of fit or function.")

    def test_missing_declared_cad_does_not_become_a_status_card(self):
        self.record["geometry"]["derived_files"] = ["twins/missing.stl"]
        self.write_record()
        with self.assertRaises(ValueError):
            previews.sources(self.record["part_id"])
        self.assertEqual(self.check(), 1)

    def test_declared_cad_cannot_escape_repository(self):
        self.record["geometry"]["derived_files"] = ["../outside.stl"]
        self.write_record()
        with self.assertRaises(ValueError):
            previews.sources(self.record["part_id"])

    def private_native_fixture(self):
        study = self.root / "twins/study"
        study.mkdir(parents=True)
        paths = {role: study / filename for role, filename in
                 (("master", "Program.cs"), ("source", "geometry.py"),
                  ("parameters", "parameters.json"), ("canonical", "canonical-model.json"))}
        paths["master"].write_text("// Native wall exporter fixture\n")
        paths["source"].write_text("# Canonical authoring fixture\n")
        paths["parameters"].write_text('{"status":"assumed"}\n')
        paths["canonical"].write_text(json.dumps({
            "study_id": self.record["part_id"],
            "source_builder_sha256": previews.sha256(paths["source"]),
            "parameter_sha256": previews.sha256(paths["parameters"])}))
        # The binary identity guard is tested without pretending these bytes
        # are a real native geometry run; the actual F2 render exercises VTK.
        mesh = self.root / "private.stl"
        mesh.write_bytes(b"private native artifact identity fixture")
        receipt = {"kind": "private_native_wall_preview", "part_id": self.record["part_id"],
                   "artifact": {"format": "STL", "sha256": previews.sha256(mesh),
                                "size_bytes": mesh.stat().st_size},
                   "inputs": [{"role": role, "path": path.relative_to(self.root).as_posix(),
                               "sha256": previews.sha256(path)} for role, path in paths.items()]}
        receipt_path = study / "native-preview.json"
        receipt_path.write_text(json.dumps(receipt))
        self.record["geometry"].update(master_format="PicoGK",
            master_file=paths["master"].relative_to(self.root).as_posix(),
            private_preview_receipt=receipt_path.relative_to(self.root).as_posix())
        self.write_record()
        return mesh, receipt_path, receipt, paths

    def test_private_native_mesh_identity_is_mandatory_before_rendering(self):
        mesh, _, _, _ = self.private_native_fixture()
        self.assertEqual(previews.private_cad_source(self.record, mesh), mesh)
        with self.assertRaisesRegex(ValueError, "requires --write"):
            previews.private_cad_source(self.record, None)
        # Same size, different bytes: size alone must not admit an artifact.
        mesh.write_bytes(b"X" * mesh.stat().st_size)
        with self.assertRaisesRegex(ValueError, "bytes do not match"):
            previews.private_cad_source(self.record, mesh)

    def test_public_native_preview_checks_lineage_without_private_mesh_bytes(self):
        mesh, _, receipt, paths = self.private_native_fixture()
        self.publish(previews.sources(self.record["part_id"]))
        manifest = self.media / "preview.json"
        info = json.loads(manifest.read_text())
        info["private_artifact"] = previews.private_artifact_metadata(receipt)
        manifest.write_text(json.dumps(info))
        mesh.unlink()
        self.assertEqual(self.check(), 0)
        paths["master"].write_text("// Changed native exporter\n")
        self.assertEqual(self.check(), 1)

    def test_stale_or_misbound_canonical_receipt_fails_closed(self):
        _, receipt_path, receipt, paths = self.private_native_fixture()
        for role in ("canonical", "source", "parameters"):
            original = paths[role].read_bytes()
            paths[role].write_bytes(original + b" ")
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, "Stale private preview input"):
                previews.private_preview(self.record)
            paths[role].write_bytes(original)
        canonical = json.loads(paths["canonical"].read_text())
        canonical["source_builder_sha256"] = "0" * 64
        paths["canonical"].write_text(json.dumps(canonical))
        # Rehashing the changed canonical file cannot hide its stale builder.
        next(s for s in receipt["inputs"] if s["role"] == "canonical")["sha256"] = previews.sha256(paths["canonical"])
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "Canonical model does not bind"):
            previews.private_preview(self.record)

    def test_fresh_input_hashes_do_not_admit_a_stale_canonical_summary(self):
        _, receipt_path, receipt, paths = self.private_native_fixture()
        receipt["canonical_model_sha256"] = previews.sha256(paths["canonical"])
        receipt_path.write_text(json.dumps(receipt))
        previews.private_preview(self.record)
        receipt["canonical_model_sha256"] = "0" * 64
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "canonical summary is stale"):
            previews.private_preview(self.record)

    def test_reduced_display_is_rejected_even_with_bound_native_and_exporter_hashes(self):
        native, receipt_path, receipt, paths = self.private_native_fixture()
        display = self.root / "display.stl"
        display.write_bytes(b"display-only artifact identity fixture")
        exporter = paths["source"].with_name("display_lod.py")
        exporter.write_text("# Explicit display reduction fixture\n")
        receipt["inputs"].append({"role": "display_source", "path": exporter.relative_to(self.root).as_posix(),
                                  "sha256": previews.sha256(exporter)})
        receipt["display_artifact"] = {"format": "STL", "sha256": previews.sha256(display),
            "size_bytes": display.stat().st_size, "source_native_sha256": receipt["artifact"]["sha256"],
            "kind": "reduced_display", "reduced": True,
            "method": "Display-only topology-preserving reduction fixture; no native modification"}
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "Only lossless native transport"):
            previews.private_preview(self.record)

    def test_lossless_vtp_needs_exact_readback_proof_not_just_an_unreduced_label(self):
        _, receipt_path, receipt, paths = self.private_native_fixture()
        transport = self.root / "native.vtp"
        transport.write_bytes(b"lossless indexed transport identity fixture")
        exporter = paths["source"].with_name("export_vtp.py")
        exporter.write_text("# Exact ordered-array transport fixture\n")
        receipt["inputs"].append({"role": "display_source", "path": exporter.relative_to(self.root).as_posix(),
                                  "sha256": previews.sha256(exporter)})
        receipt["display_artifact"] = {"format": "VTP", "sha256": previews.sha256(transport),
            "size_bytes": transport.stat().st_size, "source_native_sha256": receipt["artifact"]["sha256"],
            "kind": "lossless_native_transport", "reduced": False, "method": "Lossless indexed-array fixture"}
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "requires a current transport equality receipt"):
            previews.private_preview(self.record)
        equality = {"kind": "lossless_native_transport_equality",
            "native_stl_sha256": receipt["artifact"]["sha256"],
            "replayed_stl_sha256": receipt["artifact"]["sha256"],
            "transport_sha256": previews.sha256(transport), "point_count": 8, "triangle_count": 12,
            "vertices_equal": True, "triangles_equal": True,
            "source_vertices_sha256": "a"*64, "readback_vertices_sha256": "a"*64,
            "source_triangles_sha256": "b"*64, "readback_triangles_sha256": "b"*64}
        proof = paths["source"].with_name("transport-equality.json")
        proof.write_text(json.dumps(equality))
        receipt["inputs"].append({"role": "transport_equality", "path": proof.relative_to(self.root).as_posix(),
                                  "sha256": previews.sha256(proof)})
        receipt_path.write_text(json.dumps(receipt))
        self.assertEqual(previews.private_cad_source(self.record, transport), transport)
        note = previews.geometry_note(self.record, True, 0)
        self.assertIn("full native", note)
        self.assertNotIn("display-only reduced", note)
        receipt["full_native_triangles"] = 13
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "count does not match its transport proof"):
            previews.private_preview(self.record)
        receipt["full_native_triangles"] = 12
        receipt_path.write_text(json.dumps(receipt))
        previews.private_preview(self.record)
        # Even a freshly rehashed public receipt must fail on changed arrays.
        equality["readback_triangles_sha256"] = "c"*64
        proof.write_text(json.dumps(equality))
        next(s for s in receipt["inputs"] if s["role"] == "transport_equality")["sha256"] = previews.sha256(proof)
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "array hashes do not prove"):
            previews.private_preview(self.record)

    def test_native_defect_caption_requires_the_actual_artifact_count_and_failed_verdict(self):
        _, receipt_path, receipt, paths = self.private_native_fixture()
        quality = {"native_stl_sha256": receipt["artifact"]["sha256"],
                   "zero_area_triangle_count": 36, "geometry_admitted": False,
                   "checked_triangle_count": 100}
        report = paths["source"].with_name("native-quality.json")
        report.write_text(json.dumps(quality))
        entry = {"role": "native_quality", "path": report.relative_to(self.root).as_posix(),
                 "sha256": previews.sha256(report)}
        receipt["inputs"].append(entry)
        receipt["native_mesh_quality"] = {"admitted": False, "zero_area_face_count": 36}
        receipt["full_native_triangles"] = 100
        receipt_path.write_text(json.dumps(receipt))
        note = previews.geometry_note(self.record, True, 0)
        self.assertIn("Unqualified diagnostic", note)
        self.assertIn("36 collapsed", note)
        receipt["full_native_triangles"] = 101
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "count does not match its quality report"):
            previews.private_preview(self.record)
        receipt["full_native_triangles"] = 100
        for field, value in (("zero_area_triangle_count", 35),
                             ("native_stl_sha256", "0"*64), ("geometry_admitted", True)):
            report.write_text(json.dumps({**quality, field: value}))
            entry["sha256"] = previews.sha256(report)
            receipt_path.write_text(json.dumps(receipt))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "does not match"):
                previews.private_preview(self.record)

    def illustrate(self, cad):
        image = self.media / "photo-concept.png"
        image.write_bytes((self.media / "preview.png").read_bytes())
        photo = {
            "part_id": self.record["part_id"], "kind": "ai_illustration",
            "record_sha256": previews.sha256(self.record_path),
            "reference_sha256": previews.sha256(self.media / "preview.png"),
            "sources": [{"path": cad.relative_to(self.root).as_posix(),
                         "sha256": previews.sha256(cad)}],
            "images": [image.name], "image_sha256": {image.name: previews.sha256(image)},
            "prompt": "Studio illustration of the supplied CAD concept.",
            "generator": "Imagegen", "note": "AI concept; not a photograph.",
            "license": "Fixture",
        }
        manifest = self.media / "photo.json"
        manifest.write_text(json.dumps(photo))
        return image, manifest, photo

    def test_ai_illustration_requires_its_cad_sources_and_honest_kind(self):
        cad = self.parts / "993-test-0001/derived/part.stl"
        cad.parent.mkdir()
        cad.write_bytes(b"CAD fixture")
        self.publish([cad])
        image, manifest, photo = self.illustrate(cad)
        manifest.unlink()
        self.assertEqual(self.check(), 1)
        manifest.write_text(json.dumps(photo))
        self.assertEqual(self.check(), 0)
        for key, value in (("kind", "photograph"), ("sources", []),
                           ("reference_sha256", ""), ("record_sha256", "")):
            with self.subTest(key=key):
                manifest.write_text(json.dumps({**photo, key: value}))
                self.assertEqual(self.check(), 1)
        manifest.write_text(json.dumps(photo))
        image.write_bytes(b"corrupt")
        self.assertEqual(self.check(), 1)

    def test_ai_illustration_survives_prose_edits_but_not_cad_changes(self):
        cad = self.parts / "993-test-0001/derived/part.stl"
        cad.parent.mkdir()
        cad.write_bytes(b"CAD fixture")
        self.publish([cad])
        self.illustrate(cad)
        self.record["validation"] = {"limitations": ["Revised wording only."]}
        self.write_record()
        self.publish([cad])
        self.assertEqual(self.check(), 0)
        cad.write_bytes(b"revised CAD")
        self.publish([cad])
        self.assertEqual(self.check(), 1)

    def test_back_face_up_rotor_rejects_generic_camera_manifest(self):
        part_id = "993-ENG-K16-COMPRESSOR-WHEEL-ALSI10MG-F0-0001"
        record_path = self.records / (part_id.lower() + ".json")
        self.record_path.rename(record_path)
        self.record_path = record_path
        self.record["part_id"] = part_id
        self.write_record()
        folder = self.parts / part_id.lower()
        self.media.parent.rename(folder)
        self.media = folder / "media"
        derived = folder / "derived"
        derived.mkdir()
        cad = derived / "compressor_wheel_alsi10mg_f0-picogk.stl"
        cad.write_bytes(b"back-face-up CAD fixture")
        self.publish([cad])
        # Valid image/CAD hashes alone do not catch a view of the wrong face.
        self.assertEqual(self.check(), 1)
        manifest = self.media / "preview.json"
        info = json.loads(manifest.read_text())
        info["display_rotation_x_deg"] = 180
        manifest.write_text(json.dumps(info))
        self.assertEqual(self.check(), 0)


if __name__ == "__main__":
    unittest.main()
