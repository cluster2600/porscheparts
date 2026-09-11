"""Couvercle de carter de chaine en titane : le choix est assume, pas maquille.

Le titane a ete demande explicitement. Ces tests ne discutent pas ce choix ; ils
verifient que ses consequences restent ecrites. La penalite de masse doit rester
visible, la marge de dilatation doit rester calculee et non affirmee, et la piece
ne doit pas glisser vers `non_critical` alors qu'elle retient de l'huile.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
PART = ROOT / "catalog/parts/993-eng-chain-case-lid-ti-f0-0001.json"
SCREEN = ROOT / "parts/993-eng-chain-case-lid-ti-f0-0001/evidence/parametric-screen.json"
SCRIPT = ROOT / "parts/993-eng-chain-case-lid-ti-f0-0001/source/chain_case_lid_screen.py"
DOC = ROOT / "docs/993/993_COUVERCLE_CARTER_CHAINE_TI.md"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ChainCaseLidTitaniumTests(unittest.TestCase):
    def test_the_identity_names_the_lid_and_its_gasket(self) -> None:
        numbers = load(PART)["vehicle"]["porsche_part_numbers"]
        self.assertIn("964 105 107 01", numbers)
        self.assertIn("964 105 181 01", numbers)

    def test_the_equal_geometry_penalty_is_stated_as_a_starting_point(self) -> None:
        mass = load(SCREEN)["mass_comparison"]
        self.assertGreater(mass["titanium_g"], mass["aluminium_g"])
        self.assertGreater(mass["titanium_penalty_percent"], 60.0)
        # La comparaison a geometrie egale ne doit pas etre presentee comme la
        # conclusion : l'epaisseur n'a aucune raison de rester egale.
        self.assertIn("pas la conclusion", mass["interpretation"])

    def test_the_three_thickness_criteria_disagree_and_all_three_are_published(self) -> None:
        """Le couvercle peut etre plus mince. De combien depend du critere, et
        les trois reponses ne vont pas dans le meme sens : c'est cela qu'il faut
        publier, pas une seule d'entre elles."""
        equivalence = load(SCREEN)["thickness_equivalence"]
        stiffness = equivalence["equal_bending_stiffness"]
        strength = equivalence["equal_bending_strength"]
        equal_mass = equivalence["equal_mass"]

        # Dans les trois cas le titane est plus mince que l'aluminium.
        for block in (stiffness, strength, equal_mass):
            self.assertLess(block["thickness_ratio"], 1.0)

        # A raideur egale il reste plus lourd, a resistance egale il devient
        # plus leger. Les deux doivent rester visibles.
        self.assertGreater(stiffness["mass_ratio_vs_aluminium"], 1.0)
        self.assertLess(strength["mass_ratio_vs_aluminium"], 1.0)

        # A masse egale, la raideur s'effondre : la publier empeche de conclure
        # trop vite que l'amincissement est gratuit.
        self.assertLess(equal_mass["remaining_bending_stiffness_fraction"], 0.5)

    def test_the_foundry_thickness_hypothesis_is_recorded(self) -> None:
        """Le cas le plus probable n'est ni la raideur ni la resistance : une
        piece de fonderie porte une epaisseur dictee par la fonderie."""
        equivalence = load(SCREEN)["thickness_equivalence"]
        self.assertIn("fonderie", equivalence["what_decides"])
        self.assertIn("D03", equivalence["how_to_settle_it"])

    def test_the_shift_is_taken_at_a_radius_not_over_the_whole_span(self) -> None:
        """La premiere version comparait la dilatation d'une portee entiere a un
        jeu radial, ce qui surestimait le probleme d'un facteur deux. Ce qui doit
        tenir dans le jeu est l'ecart **au percage le plus eloigne du point
        fixe**, donc un rayon."""
        expansion = load(SCREEN)["differential_expansion"]
        span = load(SCREEN)["inputs_mm"]["extreme_hole_span"]
        self.assertEqual(expansion["datum"], "centroid")
        self.assertAlmostEqual(expansion["worst_radius_mm"], span / 2.0)
        self.assertIn("r * (alpha_al - alpha_ti)", expansion["equations"]["relative_shift"])

    def test_the_expansion_margin_holds_with_room_to_spare(self) -> None:
        expansion = load(SCREEN)["differential_expansion"]
        self.assertTrue(expansion["play_covers_shift"])
        self.assertGreater(expansion["margin_mm"], 0.0)
        # Le jeu n'est pas consomme : c'est ce qui distingue ce couvercle du
        # carter entier, et le rapport doit continuer a le montrer.
        self.assertLess(expansion["utilisation_of_play"], 0.5)

    def test_the_assembly_assumption_is_declared(self) -> None:
        """Une vis deja en appui du mauvais cote au montage n'a aucun jeu. Le
        rapport doit le dire, sinon la marge se lit comme une reserve."""
        expansion = load(SCREEN)["differential_expansion"]
        self.assertIn("centrees", expansion["assembly_assumption"])

    def test_a_dowel_datum_doubles_the_shift(self) -> None:
        """La planche 103-05 porte une douille de centrage. Si elle tient le
        couvercle, le point fixe n'est plus le centre du semis et le pire rayon
        double."""
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--datum", "dowel"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        dowel = json.loads(result.stdout)["differential_expansion"]
        centroid = load(SCREEN)["differential_expansion"]
        self.assertAlmostEqual(
            dowel["relative_shift_at_worst_hole_mm"],
            2.0 * centroid["relative_shift_at_worst_hole_mm"],
        )

    def test_a_wide_enough_span_breaks_the_margin(self) -> None:
        """La marge n'est pas une propriete de la piece, c'est un resultat. Sur
        une portee de carter entier, elle doit tomber — c'est ce qui separe le
        couvercle du carter."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--bolt-span-mm", "500", "--datum", "dowel"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["differential_expansion"]["play_covers_shift"])

    def test_the_part_is_functional_because_it_holds_oil(self) -> None:
        part = load(PART)
        self.assertEqual(part["classification"]["safety_class"], "functional")
        limits = " ".join(part["validation"]["known_limits"])
        self.assertIn("retient de l'huile", limits)

    def test_the_route_is_milling_not_printing(self) -> None:
        part = load(PART)
        self.assertEqual(part["manufacturing"]["preferred_process"], "CNC")
        self.assertEqual(part["manufacturing"]["candidate_processes"], ["CNC"])
        decision = load(SCREEN)["manufacturing_decision"]
        self.assertIn("fraisage", decision["process"])
        self.assertIn("Aucune des trois familles", decision["why_not_additive"])

    def test_the_gasket_is_recognised_as_the_existing_isolation(self) -> None:
        galvanic = load(SCREEN)["galvanic"]
        self.assertIn("964 105 181 01", galvanic["existing_isolation"])
        self.assertFalse(galvanic["resolved"])

    def test_the_measurement_plan_names_the_two_deciding_dimensions(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn("D08", doc)
        self.assertIn("D13", doc)


if __name__ == "__main__":
    unittest.main()
