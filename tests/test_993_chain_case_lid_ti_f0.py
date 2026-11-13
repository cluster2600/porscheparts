"""Titanium chain case cover: the choice is owned, not disguised.

Titanium was explicitly requested. These tests do not debate that choice; they
check that its consequences stay written down. The mass penalty must stay
visible, the expansion margin must stay calculated rather than asserted, and the
part must not slide toward `non_critical` while it retains oil.
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
DOC = ROOT / "docs/993/993_CHAIN_CASE_LID_TI.md"


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
        # The equal-geometry comparison must not be presented as the
        # conclusion: the thickness has no reason to stay equal.
        self.assertIn("pas la conclusion", mass["interpretation"])

    def test_the_three_thickness_criteria_disagree_and_all_three_are_published(self) -> None:
        """The cover can be thinner. By how much depends on the criterion, and
        the three answers do not point the same way: that is what must be
        published, not just one of them."""
        equivalence = load(SCREEN)["thickness_equivalence"]
        stiffness = equivalence["equal_bending_stiffness"]
        strength = equivalence["equal_bending_strength"]
        equal_mass = equivalence["equal_mass"]

        # In all three cases the titanium is thinner than the aluminum.
        for block in (stiffness, strength, equal_mass):
            self.assertLess(block["thickness_ratio"], 1.0)

        # A raideur egale il reste plus lourd, a resistance egale il devient
        # plus leger. Les deux doivent rester visibles.
        self.assertGreater(stiffness["mass_ratio_vs_aluminium"], 1.0)
        self.assertLess(strength["mass_ratio_vs_aluminium"], 1.0)

        # At equal mass, stiffness collapses: publishing it prevents concluding
        # too quickly that thinning is free.
        self.assertLess(equal_mass["remaining_bending_stiffness_fraction"], 0.5)

    def test_the_foundry_thickness_hypothesis_is_recorded(self) -> None:
        """The most likely case is neither stiffness nor strength: a cast part
        carries a thickness dictated by the foundry."""
        equivalence = load(SCREEN)["thickness_equivalence"]
        self.assertIn("fonderie", equivalence["what_decides"])
        self.assertIn("D03", equivalence["how_to_settle_it"])

    def test_the_shift_is_taken_at_a_radius_not_over_the_whole_span(self) -> None:
        """The first version compared the expansion of a full span with a radial
        clearance, which overstated the problem by a factor of two. What must
        fit within the clearance is the offset **at the hole farthest from the
        fixed point**, so a radius."""
        expansion = load(SCREEN)["differential_expansion"]
        span = load(SCREEN)["inputs_mm"]["extreme_hole_span"]
        self.assertEqual(expansion["datum"], "centroid")
        self.assertAlmostEqual(expansion["worst_radius_mm"], span / 2.0)
        self.assertIn("r * (alpha_al - alpha_ti)", expansion["equations"]["relative_shift"])

    def test_the_expansion_margin_holds_with_room_to_spare(self) -> None:
        expansion = load(SCREEN)["differential_expansion"]
        self.assertTrue(expansion["play_covers_shift"])
        self.assertGreater(expansion["margin_mm"], 0.0)
        # The clearance is not consumed: that is what distinguishes this cover
        # from the whole case, and the report must keep showing it.
        self.assertLess(expansion["utilisation_of_play"], 0.5)

    def test_the_assembly_assumption_is_declared(self) -> None:
        """A bolt already bearing on the wrong side at assembly has no clearance.
        The report must say so, otherwise the margin reads as a reserve."""
        expansion = load(SCREEN)["differential_expansion"]
        self.assertIn("centrees", expansion["assembly_assumption"])

    def test_a_dowel_datum_doubles_the_shift(self) -> None:
        """Plate 103-05 shows a locating sleeve. If it holds the cover, the
        fixed point is no longer the center of the hole pattern and the worst
        radius doubles."""
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
        """The margin is not a property of the part, it is a result. Over a
        full case span it must fall — that is what separates the cover from the
        case."""
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
        self.assertIn("retains oil", limits)

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
