"""Route matrix and conditional go/no-go of the first titanium part (ADR 0014).

The test does not say that any route works. It checks that every cell of the
matrix names its basis, that every cited source and file exists, that the
masses and margins are the arithmetic they claim to be, and that the go/no-go
rule fails closed: an unknown or synthetic temperature never opens a route.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "catalog/manufacturing/exhaust-tip-route-matrix.json"
PART = ROOT / "catalog/parts/993-exh-oval-tip-ti-f1-0001.json"
SCHEMA = ROOT / "catalog/schemas/part.schema.json"
SOURCES = ROOT / "catalog/sources"
TEMPLATE = ROOT / "catalog/templates/manufacturing-request-titanium.md"
REQUEST = ROOT / "docs/993/993-exh-oval-tip-ti-f1-0001-manufacturing-request.md"
SCREEN_TI64 = ROOT / "parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json"

REQUIRED_CATEGORIES = {"LPBF", "CNC", "sheet_metal", "casting", "aluminium_or_polymer"}
REVIEW_HEADER = "| Reviewer | Role | Date | Decision |"
DRAFT_MARKER = "Status: draft, not reviewed"
SAFE_WORDING = re.compile(r"\bsaf(e|er|est|ely)\b", re.IGNORECASE)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk(node):
    """Yield every dict nested in node."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def decide(rule: dict, t_max_c: float | None, sourced: bool) -> str:
    """Apply the declared bands; anything not sourced is the 'unknown' band."""
    bands = {band["id"]: band for band in rule["bands"]}
    if t_max_c is None or not sourced:
        return bands["unknown"]["decision"]
    for band in rule["bands"]:
        if band["id"] == "unknown":
            continue
        lower = band.get("lower_c", float("-inf"))
        upper = band.get("upper_c", float("inf"))
        if lower < t_max_c <= upper:
            return band["decision"]
    raise AssertionError(f"no band covers {t_max_c}")


def review_rows(text: str) -> list[list[str]]:
    """Cells of the review table, up to the first line that is not a table row."""
    lines = text.split(REVIEW_HEADER, 1)[1].splitlines()[2:]
    rows = []
    for line in lines:
        if not line.startswith("|"):
            break
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def review_state_errors(text: str) -> list[str]:
    """A draft keeps an empty review table; leaving draft requires a filled one."""
    if not re.search(r"(?m)^Status: \S", text):
        return ["the request has no status line"]
    rows = review_rows(text)
    if not rows:
        return ["the review table has no row"]
    filled = [cells for cells in rows if any(cells)]
    if DRAFT_MARKER in text:
        errors = []
        if filled:
            errors.append("a draft request keeps its review table empty")
        if "must not be sent" not in text or "PROPOSED, NOT REVIEWED" not in text:
            errors.append("a draft request keeps its do-not-send warning")
        return errors
    if not filled:
        return ["a request that leaves draft status names its reviewers"]
    if any(not all(cells) for cells in filled):
        return ["a review row names reviewer, role, date and decision"]
    return []


class ExhaustTipRouteMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = load(MATRIX)
        cls.vocabulary = set(cls.matrix["basis_vocabulary"])
        cls.criteria = [entry["id"] for entry in cls.matrix["criteria"]]

    def test_the_matrix_is_a_proposal_that_authorizes_nothing(self) -> None:
        self.assertEqual(self.matrix["status"], "proposed_not_reviewed")
        self.assertEqual(self.matrix["reviewed_by"], "")
        self.assertIsNone(self.matrix["reviewed_on"])
        self.assertIs(self.matrix["manufacturing_authorized"], False)
        self.assertTrue((ROOT / self.matrix["decision_record"]).is_file())

    def test_the_five_route_families_are_all_compared(self) -> None:
        categories = {route["category"] for route in self.matrix["routes"]}
        self.assertTrue(REQUIRED_CATEGORIES <= categories, categories)

    def test_every_cell_names_a_known_basis(self) -> None:
        for route in self.matrix["routes"]:
            self.assertEqual(sorted(route["cells"]), sorted(self.criteria), route["route_id"])
            for criterion, cell in route["cells"].items():
                with self.subTest(route=route["route_id"], criterion=criterion):
                    basis = cell["basis"]
                    self.assertTrue(basis and set(basis) <= self.vocabulary, basis)
                    self.assertTrue(cell["summary"].strip())
                    if "sourced" in basis:
                        self.assertTrue(cell["source_ids"], "a sourced cell cites a source")
                    if "repo_evidence" in basis:
                        self.assertTrue(cell["refs"], "a repo_evidence cell cites a file")
                    if "arithmetic" in basis:
                        self.assertIn("formula", cell)

    def test_every_cited_source_and_file_exists(self) -> None:
        for node in walk(self.matrix):
            for source_id in node.get("source_ids", []) + (
                [node["source_id"]] if isinstance(node.get("source_id"), str) else []
            ):
                with self.subTest(source_id=source_id):
                    path = SOURCES / f"{source_id.lower()}.json"
                    self.assertTrue(path.is_file(), path)
                    self.assertEqual(load(path)["source_id"], source_id)
            for ref in node.get("refs", []):
                with self.subTest(ref=ref):
                    self.assertTrue((ROOT / ref).is_file(), ref)

    def test_masses_are_volume_times_density(self) -> None:
        volume = self.matrix["inputs"]["cad_volume_mm3"]["value"]
        self.assertAlmostEqual(volume, load(SCREEN_TI64)["results"]["cad_volume_mm3"], places=6)
        for route in self.matrix["routes"]:
            cell = route["cells"]["mass"]
            masses = cell["value_g"] if isinstance(cell["value_g"], list) else [cell["value_g"]]
            densities = (
                cell["density_g_cm3"] if isinstance(cell["density_g_cm3"], list) else [cell["density_g_cm3"]]
            )
            for mass, density in zip(masses, densities):
                with self.subTest(route=route["route_id"], density=density):
                    self.assertAlmostEqual(mass, volume * density / 1000.0, delta=0.006)
        ti64 = next(r for r in self.matrix["routes"] if r["route_id"] == "lpbf_ti64")
        self.assertAlmostEqual(
            ti64["cells"]["mass"]["value_g"], load(SCREEN_TI64)["results"]["screening_mass_g"], delta=0.006
        )

    def test_deltas_and_billet_ratio_follow_from_the_data(self) -> None:
        volume = self.matrix["inputs"]["cad_volume_mm3"]["value"]
        routes = {route["route_id"]: route for route in self.matrix["routes"]}
        baseline = routes["stainless_fabricated"]["cells"]["mass"]
        self.assertEqual(
            baseline["density_g_cm3"], self.matrix["inputs"]["stainless_baseline_density_g_cm3"]["value"]
        )
        light, heavy = sorted(baseline["value_g"])
        compared = set()
        for route_id, route in routes.items():
            cell = route["cells"]["mass"]
            if "delta_vs_stainless_baseline_percent" not in cell:
                continue
            compared.add(route_id)
            given = cell["delta_vs_stainless_baseline_percent"]
            expected = sorted(
                [(cell["value_g"] / heavy - 1.0) * 100.0, (cell["value_g"] / light - 1.0) * 100.0]
            )
            with self.subTest(route=route_id):
                self.assertEqual(given, sorted(given))
                for value, want in zip(given, expected, strict=True):
                    self.assertLessEqual(abs(value - want), 0.05 + 1e-9, (value, want))
        self.assertEqual(compared, set(routes) - {"stainless_fabricated"})
        cnc = routes["cnc_billet"]["cells"]["mass"]
        envelope = self.matrix["inputs"]["envelope_mm"]["value"]
        self.assertEqual(cnc["inputs"]["envelope_mm"], envelope)
        billet = envelope[0] * envelope[1] * envelope[2]
        self.assertAlmostEqual(cnc["billet_volume_mm3"], billet, places=6)
        self.assertLessEqual(abs(cnc["billet_to_part_volume_ratio"] - billet / volume), 0.05 + 1e-9)
        self.assertEqual(cnc["billet_to_part_volume_ratio"], 25.4)

    def test_margins_are_ceiling_minus_the_declared_temperatures(self) -> None:
        surface = self.matrix["inputs"]["declared_tip_surface_c"]
        gas = self.matrix["inputs"]["declared_exhaust_gas_c"]
        self.assertEqual(surface["status"], "synthetic_never_measured")
        self.assertEqual(gas["status"], "synthetic_never_measured")
        ceiling_types = set(self.matrix["ceiling_type_vocabulary"])
        for route in self.matrix["routes"]:
            cell = route["cells"]["temperature_margin"]
            with self.subTest(route=route["route_id"], check="ceiling_type"):
                # Ceilings of different kinds are compared: each one says which kind it is.
                self.assertIn(cell["ceiling_type"], ceiling_types)
                self.assertEqual(cell["ceiling_c"] is None, cell["ceiling_type"] == "not_quantified")
            if cell["ceiling_c"] is None:
                self.assertIn("open", cell["basis"])
                continue
            with self.subTest(route=route["route_id"]):
                self.assertAlmostEqual(
                    cell["margin_vs_declared_surface_c"], cell["ceiling_c"] - surface["value"], places=2
                )
                self.assertAlmostEqual(
                    cell["margin_vs_declared_gas_c"], cell["ceiling_c"] - gas["value"], places=2
                )

    def test_the_go_no_go_rule_fails_closed(self) -> None:
        rule = self.matrix["go_no_go_rule"]
        self.assertEqual(rule["status"], "project_decision_rule_pending_professional_review")
        self.assertEqual(rule["input_status"], "blocked")
        surface = self.matrix["inputs"]["declared_tip_surface_c"]["value"]
        # The repository's own figure is synthetic: it can never open the route.
        self.assertEqual(decide(rule, surface, sourced=False), "no_go")
        self.assertEqual(decide(rule, 300.0, sourced=False), "no_go")
        self.assertEqual(decide(rule, None, sourced=True), "no_go")
        # Sourced values: only the band at or under 350 C is conditional.
        self.assertEqual(decide(rule, 350.0, sourced=True), "conditional_go")
        for value in (350.1, 400.0, 427.0, 550.0, 600.0):
            with self.subTest(t_max_c=value):
                self.assertEqual(decide(rule, value, sourced=True), "no_go")
        self.assertNotIn("go", {band["decision"] for band in rule["bands"]})
        # The request's prerequisites include a toleranced drawing; the rule carries it too.
        self.assertTrue(
            any("drawing with tolerances" in condition for condition in rule["other_conditions_for_conditional_go"])
        )
        self.assertIn("a drawing with tolerances", REQUEST.read_text(encoding="utf-8"))
        self.assertTrue(rule["ceiling_reference"]["source_caveat"].strip())

    def test_no_route_or_document_is_called_safe(self) -> None:
        texts = {MATRIX.name: MATRIX.read_text(encoding="utf-8")}
        for path in (ROOT / self.matrix["decision_record"], REQUEST, TEMPLATE):
            texts[path.name] = path.read_text(encoding="utf-8")
        for name, text in texts.items():
            with self.subTest(file=name):
                self.assertEqual(SAFE_WORDING.findall(text), [])

    def test_the_part_record_carries_its_fatigue_assumptions(self) -> None:
        titanium = load(PART)["titanium"]
        self.assertTrue(titanium["fatigue_assumptions"].strip())
        block = load(SCHEMA)["properties"]["titanium"]
        self.assertIn("fatigue_assumptions", block["properties"])
        self.assertNotIn("fatigue_assumptions", block["required"])
        self.assertEqual(load(PART)["classification"]["safety_class"], "functional")

    def test_the_review_table_follows_the_status_line(self) -> None:
        for path in (TEMPLATE, REQUEST):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn(REVIEW_HEADER, text)
                for heading in ("## Coupon plan", "## Non-destructive testing", "## Traceability"):
                    self.assertIn(heading, text)
                self.assertEqual(review_state_errors(text), [])
        self.assertIn(DRAFT_MARKER, TEMPLATE.read_text(encoding="utf-8"))
        request = REQUEST.read_text(encoding="utf-8")
        step = load(ROOT / "twins/993-exhaust-tip-ti-f0/evidence/lpbf-f1/"
                         "993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json")["master"]["sha256"]
        self.assertIn(step, request)

    def test_the_review_check_accepts_a_real_review_and_rejects_a_filled_draft(self) -> None:
        request = REQUEST.read_text(encoding="utf-8")
        self.assertIn(DRAFT_MARKER, request)
        empty_row = "| | | | |"
        self.assertIn(empty_row, request)
        # Synthetic row for the check only; it names no real reviewer.
        signed = "| A. Reviewer | engineer | 2026-11-01 | accepted with comments |"
        filled_draft = request.replace(empty_row, signed, 1)
        self.assertIn(
            "a draft request keeps its review table empty", review_state_errors(filled_draft)
        )
        reviewed = filled_draft.replace(DRAFT_MARKER, "Status: reviewed, see the review table")
        self.assertEqual(review_state_errors(reviewed), [])
        unsigned = request.replace(DRAFT_MARKER, "Status: reviewed, see the review table")
        self.assertEqual(
            review_state_errors(unsigned), ["a request that leaves draft status names its reviewers"]
        )
        partial = request.replace(empty_row, "| A. Reviewer | | | |", 1).replace(
            DRAFT_MARKER, "Status: reviewed, see the review table"
        )
        self.assertEqual(review_state_errors(partial), ["a review row names reviewer, role, date and decision"])
        self.assertEqual(review_state_errors(request.replace(DRAFT_MARKER, "")), ["the request has no status line"])


if __name__ == "__main__":
    unittest.main()
