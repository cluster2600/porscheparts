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
