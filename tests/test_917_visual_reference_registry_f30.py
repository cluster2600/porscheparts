"""Tests fail-closed du registre link-only de références visuelles F30."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Iterator, Tuple


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    ROOT
    / "twins"
    / "reference-917-engine"
    / "visual-reference-registry-f30.json"
)
DOC_PATH = ROOT / "docs" / "917_VISUAL_REFERENCE_REGISTRY_F30.md"

EXPECTED_CAPTURE_VARIANTS = {
    "photo_01": "917_30",
    "photo_02": "917_30",
    "photo_03": "type_912_4_5_na",
    "photo_04": "unknown",
    "photo_05": "917_k",
    "photo_06": "unknown",
    "photo_07": "unknown",
    "photo_08": "917_10",
    "photo_09": "917_10",
    "photo_10": "917_10",
}

EXPECTED_VARIANT_PARTITION = {
    "type_912_4_5_na": ["photo_03"],
    "917_k": ["photo_05"],
    "917_10": ["photo_08", "photo_09", "photo_10"],
    "917_30": ["photo_01", "photo_02"],
    "unknown": ["photo_04", "photo_06", "photo_07"],
}

EXPECTED_SUPPLEMENTAL_MEDIA = {
    "canepa_917_10_image_007": "917_10",
    "canepa_917_10_image_008": "917_10",
    "canepa_917_10_image_009": "917_10",
    "canepa_917_10_image_010": "917_10",
    "canepa_917_30_build_up_page": "917_30",
    "canepa_917_30_featured_image_02": "917_30",
    "canepa_917_30_spare_engine_10_attachment": "917_30",
    "canepa_917_30_time_lapse_page": "917_30",
}

EXPECTED_SOURCE_PAGES = {
    "alamy_34459663": (
        "https://www.alamy.com/stock-photo-the-twelve-cylinder-turbo-engine-"
        "of-the-porsche-917-30-1200-hp-porsche-34459663.html"
    ),
    "alamy_34459654": (
        "https://www.alamy.com/stock-photo-the-twelve-cylinder-turbo-engine-"
        "of-the-porsche-917-30-1200-hp-porsche-34459654.html"
    ),
    "suber_factory_917_engine_collection": (
        "https://suberfactory.com/porsche-917-engine-collection/"
    ),
    "wikimedia_15664155148": (
        "https://commons.wikimedia.org/wiki/"
        "File:Porsche_Museum_IMG_20141112_123129_(15664155148).jpg"
    ),
    "pixels_alain_jamar_917_engine": (
        "https://pixels.com/featured/917-porsche-engine-illustration-alain-jamar.html"
    ),
    "reddit_machineporn_28ay8k": (
        "https://www.reddit.com/r/MachinePorn/comments/28ay8k/"
        "1972_the_heart_of_the_porsche_91730_turbopanzer_a/"
    ),
    "rm_sothebys_r1029": (
        "https://rmsothebys.com/auctions/ny15/lots/"
        "r1029-porsche-type-917-miniature-engine/"
    ),
    "canepa_917_10_teardown": (
        "https://www.canepa.com/porsche-917-10-engine-tear-down-canepa-distractions/"
    ),
    "canepa_917_30_build_up": (
        "https://www.canepa.com/porsche-917-30-engine-build-up/"
    ),
    "canepa_917_30_time_lapse": (
        "https://www.canepa.com/porsche-917-30-engine-time-build-time-lapse/"
    ),
    "canepa_917_30_spare_engine_attachment": "https://www.canepa.com/?p=196757482",
}


def walk_json(value: Any, path: Tuple[str, ...] = ()) -> Iterator[Tuple[Tuple[str, ...], Any]]:
    """Parcourt les clés JSON sans interpréter le contenu documentaire."""

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            yield child_path, child
            yield from walk_json(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_json(child, (*path, str(index)))


class VisualReferenceRegistryF30Tests(unittest.TestCase):
    """Vérifie la couverture et les barrières fail-closed de F30."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_registry_covers_exactly_ten_captures(self) -> None:
        captures = self.registry["captures"]
        capture_ids = [capture["capture_id"] for capture in captures]

        self.assertEqual(self.registry["phase"], "F30")
        self.assertEqual(self.registry["capture_count"], 10)
        self.assertEqual(len(captures), 10)
        self.assertEqual(capture_ids, list(EXPECTED_CAPTURE_VARIANTS))
        self.assertEqual(
            [capture["capture_ordinal"] for capture in captures],
            list(range(1, 11)),
        )
        self.assertEqual(len(capture_ids), len(set(capture_ids)))

    def test_variants_are_strictly_partitioned(self) -> None:
        actual_capture_variants = {
            capture["capture_id"]: capture["variant_id"]
            for capture in self.registry["captures"]
        }

        self.assertEqual(
            set(self.registry["allowed_variant_ids"]),
            set(EXPECTED_VARIANT_PARTITION),
        )
        self.assertEqual(actual_capture_variants, EXPECTED_CAPTURE_VARIANTS)
        self.assertEqual(
            self.registry["variant_policy"]["capture_ids_by_variant"],
            EXPECTED_VARIANT_PARTITION,
        )
        self.assertTrue(
            self.registry["variant_policy"]["single_variant_id_per_record_required"]
        )
        self.assertFalse(
            self.registry["variant_policy"]["cross_variant_geometry_transfer_authorized"]
        )

    def test_supplemental_media_are_exact_and_canepa_only(self) -> None:
        media = self.registry["supplemental_media"]
        actual = {item["media_id"]: item["variant_id"] for item in media}
        sources = self.registry["source_registry"]

        self.assertEqual(self.registry["supplemental_media_count"], 8)
        self.assertEqual(len(media), 8)
        self.assertEqual(actual, EXPECTED_SUPPLEMENTAL_MEDIA)
        for item in media:
            self.assertEqual(sources[item["source_id"]]["publisher"], "Canepa")
            self.assertTrue(item["remote_url"].startswith("https://"))

    def test_metrology_is_empty_for_every_record(self) -> None:
        records = [*self.registry["captures"], *self.registry["supplemental_media"]]

        self.assertTrue(
            self.registry["metrology_policy"]["metric_values_required_empty"]
        )
        for record in records:
            self.assertEqual(
                record["metrology"],
                {"status": "not_available", "metric_values": []},
                record.get("capture_id", record.get("media_id")),
            )
        for policy_key, authorized in self.registry["metrology_policy"].items():
            if policy_key.endswith("_authorized"):
                self.assertIs(authorized, False, policy_key)

    def test_registry_remains_link_only(self) -> None:
        media_policy = self.registry["media_policy"]
        records = [*self.registry["captures"], *self.registry["supplemental_media"]]
        forbidden_path_keys = {
            "download_path",
            "file_path",
            "image_path",
            "local_path",
            "media_path",
        }

        self.assertTrue(media_policy["link_only"])
        self.assertFalse(media_policy["download_authorized"])
        self.assertFalse(media_policy["local_path_recording_authorized"])
        self.assertFalse(media_policy["copyrighted_asset_import_authorized"])
        self.assertEqual(media_policy["repository_media_payload_count"], 0)
        for record in records:
            self.assertIs(record["local_copy"], False)
        for path, _value in walk_json(self.registry):
            self.assertNotIn(path[-1], forbidden_path_keys, ".".join(path))

    def test_sources_rights_and_limitations_are_resolvable(self) -> None:
        sources = self.registry["source_registry"]
        rights_profiles = self.registry["rights_profiles"]
        records = [*self.registry["captures"], *self.registry["supplemental_media"]]

        self.assertEqual(
            {source_id: source["page_url"] for source_id, source in sources.items()},
            EXPECTED_SOURCE_PAGES,
        )
        for source_id, source in sources.items():
            self.assertTrue(source["page_url"].startswith("https://"), source_id)
            self.assertIn(source["rights_profile_id"], rights_profiles)
            self.assertIn("provenance_chain", source)
        for record in records:
            self.assertIn(record["source_id"], sources)
            self.assertIn(record["rights_profile_id"], rights_profiles)
            self.assertEqual(
                record["rights_profile_id"],
                sources[record["source_id"]]["rights_profile_id"],
            )
            self.assertGreater(len(record["limitations"]), 0)
            self.assertIs(record["release_authority"], False)
        for rights_id, profile in rights_profiles.items():
            self.assertIs(profile["repository_copy_authorized"], False, rights_id)

        self.assertEqual(
            rights_profiles["wikimedia_cc_by_sa_2_0"]["license_id"],
            "CC-BY-SA-2.0",
        )
        self.assertEqual(
            rights_profiles["unknown_reddit_tumblr"]["license_id"],
            "rights_unknown",
        )
        self.assertEqual(
            rights_profiles["alamy_rights_managed"]["license_id"],
            "rights_managed",
        )

    def test_observations_keep_topology_separate_from_metrology(self) -> None:
        observation_ids = [
            observation["observation_id"]
            for capture in self.registry["captures"]
            for observation in capture["observations"]
        ]

        self.assertEqual(len(observation_ids), len(set(observation_ids)))
        self.assertTrue(
            {
                "photo_08_cam_and_intermediate_shafts",
                "photo_09_connecting_rods",
                "photo_09_oil_filter_layers",
                "photo_10_crankshaft_context",
                "photo_10_valves_and_springs",
            }.issubset(observation_ids)
        )

    def test_all_release_gates_remain_closed(self) -> None:
        release_gates = self.registry["release_gates"]

        self.assertGreater(len(release_gates), 0)
        for gate_id, value in release_gates.items():
            self.assertIs(value, False, gate_id)

    def test_french_documentation_exists_without_embedded_media(self) -> None:
        documentation = DOC_PATH.read_text(encoding="utf-8")

        self.assertIn("exactement les dix captures", documentation)
        self.assertIn("Tous les champs de `release_gates` restent à `false`", documentation)
        self.assertNotIn("![", documentation)


if __name__ == "__main__":
    unittest.main()
