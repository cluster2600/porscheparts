"""Checks for the turbo comparison basis of issue #396; no solver, mesher or container runs.

They cover the authorised source allowlist, FTS5 retrieval against known
citations, the interface ledger rule (sourced, or bound to a missing-data
gate, never measured without evidence), the quantity conventions and the
G03 gate revision evaluated by the unchanged baseline evaluator.
"""
import contextlib
import copy
import importlib.util
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins/bionic-turbo-f1"
HERE = TWIN / "basis-20261112"
spec = importlib.util.spec_from_file_location("turbo_basis", HERE / "basis.py")
basis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(basis)

GATE = "G03-measured-interfaces-and-basis"
BLOCKERS = ["no-measured-operating-conditions", "no-measured-interfaces",
            "no-physical-reference-variant", "no-admitted-compressor-or-turbine-map"]


def read_lines(relative, first, last):
    """Independent of basis.span_text: plain file lines, 1-based inclusive."""
    return "\n".join((ROOT / relative).read_text(encoding="utf-8").split("\n")[first - 1:last])


class PrerequisiteAndGateTests(unittest.TestCase):
    def test_committed_basis_validates(self):
        self.assertEqual(basis.check_all(), [])

    def test_prerequisite_gates_pass_by_the_unchanged_evaluator(self):
        fresh = basis.verify_prerequisites()
        self.assertEqual(fresh["parent_ledger_errors"], [])
        for gate in ("G01-baseline-frozen", "G01-execution-contract", "G02-evidence-recoverable"):
            self.assertEqual(fresh["gate_states"][gate], "engineering_passed")
            self.assertEqual(fresh["evaluations"][gate], {"may_open": True, "reasons": []})
        recorded = basis.load("prerequisites")
        self.assertEqual(basis.check_prerequisites(recorded), [])
        self.assertFalse(recorded["downstream_geometry_solver_and_release_authorized"])
        recorded["gate_states"]["G02-evidence-recoverable"] = "investigated"
        self.assertTrue(basis.check_prerequisites(recorded))

    def test_only_g03_changes_and_it_records_blockers_without_passing(self):
        parent = json.loads((TWIN / "recovery-20261106/gate-ledger.json").read_text())
        current = basis.load("ledger")
        self.assertEqual(basis.check_gate_ledger(current), [])
        for key in ("opening_rule", "states", "release_separation", "paired_comparison_contract"):
            self.assertEqual(parent[key], current[key])
        for old, new in zip(parent["gates"], current["gates"], strict=True):
            if old["id"] != GATE:
                self.assertEqual(old, new)
        gate = next(g for g in current["gates"] if g["id"] == GATE)
        self.assertEqual(gate["state"], "investigated")
        self.assertEqual([b["id"] for b in gate["blockers"]], BLOCKERS)
        self.assertEqual(gate["prerequisites"], next(g for g in parent["gates"] if g["id"] == GATE)["prerequisites"])

    def test_unchanged_evaluator_refuses_g03_for_its_blockers_only(self):
        verdict = basis.evaluate_gate()
        self.assertFalse(verdict["may_open"])
        self.assertEqual(verdict["reasons"], [f"open blocker: {name}" for name in BLOCKERS])
        self.assertEqual(verdict, basis.load("evaluation"))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(basis.main(["gate"]), 1)
        self.assertIn("stays closed", out.getvalue())

    def test_dependent_gates_stay_closed_and_a_forced_pass_is_rejected(self):
        ledger, matrix = basis.load("ledger"), json.loads((ROOT / basis.MATRIX).read_text())
        receipt = {"path": basis.REVISION + "/retrieval-receipt.json",
                   "sha256": basis.sha256_file(HERE / "retrieval-receipt.json")}
        for dependent in ("G05-full-geometry", "G08-paired-compressor-comparison", "G09-turbine-wastegate-shaft-balance"):
            accepted, reasons = basis.parent().evaluate_gate(
                dependent, ledger, matrix, {"gate": dependent, "receipts": [receipt]}, ROOT)
            self.assertFalse(accepted)
            self.assertIn(f"prerequisite {GATE} is investigated, not engineering_passed", reasons)
        forced = copy.deepcopy(ledger)
        next(g for g in forced["gates"] if g["id"] == GATE)["state"] = "engineering_passed"
        errors = basis.check_gate_ledger(forced)
        self.assertTrue(any("engineering_passed with open blockers" in e for e in errors))
        self.assertTrue(any("cannot pass the gate" in e for e in errors))
        dropped = copy.deepcopy(ledger)
        next(g for g in dropped["gates"] if g["id"] == GATE)["blockers"].pop(1)
        self.assertTrue(any("dropped an inherited blocker" in e for e in basis.check_gate_ledger(dropped)))
        weakened = copy.deepcopy(ledger)
        weakened["opening_rule"] = "A gate may open on request."
        self.assertTrue(any("opening_rule" in e for e in basis.check_gate_ledger(weakened)))


class AllowlistAndCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allowlist, cls.corpus = basis.load("allowlist"), basis.load("corpus")

    def test_corpus_rows_are_exact_spans_of_pinned_allowlisted_files(self):
        self.assertEqual(basis.check_allowlist(self.allowlist), [])
        self.assertEqual(basis.build_corpus(self.allowlist), self.corpus)
        pins = {source["path"]: source["sha256"] for source in self.allowlist["sources"]}
        rows = [row for row in self.corpus["documents"] if row["evidence_status"] != "synthetic_control"]
        self.assertEqual(len(rows), 73)
        self.assertEqual(len(self.corpus["documents"]) - len(rows), 3)
        for row in rows:
            with self.subTest(row=row["id"]):
                span = row["span"]
                self.assertEqual(basis.sha256_file(ROOT / span["path"]), pins[span["path"]])
                self.assertEqual(row["source_sha256"], pins[span["path"]])
                self.assertEqual(basis.sha256_text(row["text"]), span["text_sha256"])
                if "lines" in span:
                    self.assertEqual(row["text"], read_lines(span["path"], *span["lines"]))
                self.assertIn(row["variant"], self.allowlist["variants"])
                self.assertTrue(row["rights"].strip())
                self.assertIsInstance(row["units"], list)
                self.assertNotEqual(row["evidence_status"], "measured")
                for upstream in row["upstream"]:
                    self.assertTrue(upstream["license"].strip())

    def test_third_party_records_keep_their_rights_and_variant_identity(self):
        rows = {row["id"]: row for row in self.corpus["documents"]}
        kkk = rows["k16-map-sjm-2467"]
        self.assertEqual(kkk["variant"], "kkk-5316-988-6717-2467-gga-ggb")
        self.assertEqual(kkk["evidence_status"], "published_other_variant")
        self.assertEqual([u["source_id"] for u in kkk["upstream"]], ["SRC-993-RESEARCH-SJM-K16-6717"])
        self.assertEqual(kkk["upstream"][0]["redistribution"], "prohibited")
        self.assertIn("Identity with the 993 units is not established", kkk["variant_identity"])
        self.assertEqual({"mbar", "K"} - set(kkk["units"]), set())
        self.assertFalse(any(row["evidence_status"] == "measured" for row in rows.values()))
        self.assertNotIn("measured", basis.EVIDENCE_SCOPE)

    def test_carrier_documents_cannot_become_turbo_evidence(self):
        for path in ("benchmarks/free-tools/corpus.json",
                     "docs/reports/carrier-resume-20261020/CONVERGENCE.md",
                     "catalog/parts/993-eng-carrier-0001.json"):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())
                changed = copy.deepcopy(self.allowlist)
                changed["sources"].append({
                    "path": path, "sha256": basis.sha256_file(ROOT / path), "kind": "twin_record",
                    "variant": "bionic-turbo-f1-pair", "rights": "any",
                    "spans": [{"id": "carrier-as-turbo", "title": "carrier", "lines": [1, 1],
                               "evidence_status": "study_assumption", "units": [], "must_contain": [""]}]})
                self.assertTrue(any("excluded" in e for e in basis.check_allowlist(changed)))
                with self.assertRaisesRegex(basis.BasisError, "excluded from turbo evidence"):
                    basis.build_corpus(changed)
        relaxed = copy.deepcopy(self.allowlist)
        relaxed["excluded"] = [rule for rule in relaxed["excluded"] if rule["path"] != "docs/reports/"]
        self.assertTrue(any("no longer excludes carrier documents" in e for e in basis.check_allowlist(relaxed)))
        smuggled = copy.deepcopy(self.corpus)
        smuggled["documents"][0]["span"]["path"] = "benchmarks/free-tools/corpus.json"
        self.assertTrue(any("not an allowlisted turbo source" in e
                            for e in basis.check_corpus(smuggled, self.allowlist)))

    def test_stale_hash_moved_span_or_edited_text_is_refused(self):
        stale = copy.deepcopy(self.allowlist)
        stale["sources"][0]["sha256"] = "0" * 64
        self.assertTrue(any("stale" in e for e in basis.check_allowlist(stale)))
        moved = copy.deepcopy(self.allowlist)
        span = next(s for s in moved["sources"][0]["spans"] if s["id"] == "cfd-inlet-state-and-gas")
        span["lines"] = [194, 194]
        self.assertTrue(any("cfd-inlet-state-and-gas" in e and "is not in" in e for e in basis.check_allowlist(moved)))
        self.assertTrue(any("corpus differs" in e for e in basis.check_corpus(self.corpus, moved)))
        edited = copy.deepcopy(self.corpus)
        edited["documents"][0]["text"] += " measured"
        self.assertTrue(any("corpus differs" in e for e in basis.check_corpus(edited, self.allowlist)))
        promoted = copy.deepcopy(self.allowlist)
        promoted["sources"][0]["spans"][0]["evidence_status"] = "measured"
        self.assertTrue(any("evidence status 'measured' is not allowed" in e for e in basis.check_allowlist(promoted)))
        with self.assertRaises(basis.BasisError):
            basis.span_text(ROOT, "twins/bionic-turbo-f1/cfd/prepare_case.py", {"lines": [1, 100000]})
        with self.assertRaises(basis.BasisError):
            basis.span_text(ROOT, "../outside.py", {"lines": [1, 1]})
        with self.assertRaises(basis.BasisError):
            basis.resolve_pointer({"records": [{"id": "a"}, {"id": "a"}]}, "/records/[id=a]")


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.knowledge = basis.knowledge()
        cls.corpus_path = HERE / "turbo-corpus.json"
        cls.database = cls.knowledge.build(cls.corpus_path, Path(cls.temp.name) / "index")
        cls.citations = basis.load("citations")["citations"]

    def context(self, question):
        return self.knowledge.context(self.database, self.corpus_path, question)

    def test_fts5_retrieves_every_known_citation_with_its_exact_span(self):
        result = basis.evaluate_retrieval(self.database)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["frozen_evaluation"]["passed"],
                         {"reference": 10, "unknown": 10, "conflict": 5, "hostile": 5})
        self.assertEqual(result["known_citations"]["count"], 26)
        self.assertEqual(result["known_citations"]["passed"], 26)
        self.assertEqual([item["failures"] for item in result["known_citations"]["results"]], [[]] * 26)
        recorded = basis.load("retrieval")
        for key in ("status", "frozen_evaluation", "corpus_sha256", "cases_sha256",
                    "citations_sha256", "knowledge_sha256"):
            self.assertEqual(result[key], recorded[key])
        self.assertEqual((recorded["known_citations"]["count"], recorded["known_citations"]["passed"]), (26, 26))

    def test_known_citations_agree_with_the_files_read_directly(self):
        line_checked = 0
        for citation in self.citations:
            with self.subTest(citation=citation["id"]):
                path, locator = citation["source"].split("#", 1)
                raw = (ROOT / path).read_text(encoding="utf-8")
                if locator.startswith("L"):
                    first, last = (int(part[1:]) for part in locator.split("-"))
                    self.assertIn(citation["exact_phrase"], read_lines(path, first, last))
                    line_checked += 1
                elif "[id=" in locator:
                    self.assertIn('"' + locator.split("[id=")[1].split("]")[0] + '"', raw)
                row = next(s for s in self.context(citation["question"])["sources"]
                           if s["id"] == citation["expected_id"])
                self.assertIn(citation["exact_phrase"], row["text"])
                self.assertEqual(row["source"], citation["source"])
        self.assertEqual(line_checked, 13)

    def test_a_wrong_citation_or_a_stale_index_fails(self):
        good = self.citations[0]
        brief = self.context(good["question"])
        self.assertEqual(basis.check_citation(good, brief), (1, []))
        for field, value, message in (
                ("exact_phrase", "p0, temperature, gamma, gas_r = 101325., 300.0, 1.4, 287.05", "exact phrase is absent"),
                ("source", "twins/bionic-turbo-f1/cfd/prepare_case.py#L194-L194", "span locator"),
                ("variant", "borgwarner-k16-5316-988-6735-6736", "variant identity differs"),
                ("evidence_status", "published_other_variant", "evidence status differs"),
                ("units", ["bar"], "units of the known citation")):
            with self.subTest(field=field):
                failures = basis.check_citation({**good, field: value}, brief)[1]
                self.assertTrue(any(message in failure for failure in failures))
        self.assertEqual(basis.check_citation({**good, "expected_id": "k16-chart-journal-diameter"}, brief),
                         (None, ["expected citation was not retrieved"]))
        changed = Path(self.temp.name) / "changed.json"
        changed.write_text(self.corpus_path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "stale corpus"):
            self.knowledge.context(self.database, changed, "inlet total pressure")

    def test_unknowns_stay_unknown_and_conflicts_are_flagged(self):
        rows = {row["id"]: row for row in basis.load("corpus")["documents"]}
        cases = basis.load("cases")
        self.assertEqual(basis.check_cases(cases, basis.load("citations"), basis.load("corpus")), [])
        for case in cases:
            with self.subTest(case=case["id"]):
                brief = self.context(case["question"])
                found = [source["id"] for source in brief["sources"]]
                self.assertTrue(set(case["expected_sources"]) <= set(found))
                self.assertIs(brief["engineering_authorized"], False)
                self.assertIs(brief["unknowns_must_remain_unknown"], True)
                if case["kind"] == "unknown":
                    expected = rows[case["expected_sources"][0]]
                    self.assertIn(expected["evidence_status"], {"documented_unknown", "contract_null"})
                    self.assertEqual(found[0], expected["id"])
                if case["kind"] == "conflict":
                    self.assertEqual(brief["status"], "conflicting_sources")
        weak = copy.deepcopy(cases)
        next(case for case in weak if case["id"] == "unknown-01")["expected_sources"] = ["k16-map-sjm-2467"]
        self.assertTrue(any("must resolve to a documented unknown" in e
                            for e in basis.check_cases(weak, basis.load("citations"), basis.load("corpus"))))

    def test_hostile_fixture_is_data_and_changes_no_ledger_state(self):
        with patch.object(self.knowledge, "checked") as execution:
            brief = self.context("What is the measured wheel shroud tip clearance?")
            text = self.knowledge.prompt(brief)
        execution.assert_not_called()
        found = [source["id"] for source in brief["sources"]]
        self.assertEqual(found[0], "f1-contract-measured-interfaces")
        self.assertIn("control-hostile", found)
        self.assertIn("untrusted reference data", text)
        self.assertIs(brief["engineering_authorized"], False)
        self.assertEqual(basis.ledger_summary(basis.load("interfaces"))["measured"], 0)
        self.assertEqual(basis.evaluate_gate()["may_open"], False)


class InterfaceLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = basis.load("interfaces")
        cls.allowlist, cls.corpus, cls.gate_ledger = basis.load("allowlist"), basis.load("corpus"), basis.load("ledger")

    def check(self, ledger):
        return basis.check_interface_ledger(ledger, self.allowlist, self.corpus, self.gate_ledger)

    def entry(self, ledger, name):
        return next(entry for entry in ledger["entries"] if entry["id"] == name)

    def test_every_entry_is_sourced_or_bound_to_a_missing_data_gate(self):
        self.assertEqual(self.check(self.ledger), [])
        gates = {gate["id"] for gate in self.ledger["missing_data_gates"]}
        groups = {entry["group"] for entry in self.ledger["entries"]}
        self.assertEqual(groups, set(basis.LEDGER_GROUPS))
        literal_checked = 0
        for entry in self.ledger["entries"]:
            with self.subTest(entry=entry["id"]):
                self.assertIsNone(entry["measured"])
                self.assertIsNone(entry["uncertainty"])
                self.assertIn(entry["missing_data_gate"], gates)
                study = entry["study_value"]
                if study is None:
                    continue
                self.assertIn(study["status"], {"assumed", "model_derived", "numerical_construct"})
                self.assertTrue(study["uncertainty_statement"].strip())
                source = study["source"]
                self.assertEqual(basis.sha256_file(ROOT / source["path"]), source["sha256"])
                if "lines" in source:
                    text = read_lines(source["path"], *source["lines"])
                    for literal in source["literals"]:
                        self.assertIn(literal, text)
                        literal_checked += 1
        self.assertEqual(self.ledger["summary"], {
            "entries": 79, "measured": 0, "with_missing_data_gate": 79, "with_study_value": 54,
            "null_without_study_value": 25,
            "study_values_by_status": {"assumed": 35, "model_derived": 4, "numerical_construct": 15},
            "entries_by_group": {"reference_identity": 1, "rotor_stator": 23, "nut": 4, "ports": 9,
                                 "mrf_interface": 6, "clearances": 8, "shaft_speed": 4,
                                 "pressure_temperature_boundary_conditions": 15, "reference_geometry": 9}})
        self.assertGreater(literal_checked, 40)
        self.assertEqual(self.ledger["scope_verdict"]["justified_scope"], "provisional_synthetic_comparison_only")

    def test_historical_cfd_hypotheses_stay_labelled_as_hypotheses(self):
        expected = {"speed.rotor_speed_operating_point": 100000, "bc.inlet_total_pressure": 101325,
                    "bc.inlet_total_temperature": 298.15, "bc.outlet_static_pressure": 121590,
                    "bc.outlet_static_to_inlet_total_ratio": 1.2}
        for name, value in expected.items():
            with self.subTest(entry=name):
                entry = self.entry(self.ledger, name)
                self.assertIsNone(entry["measured"])
                self.assertEqual(entry["study_value"]["status"], "assumed")
                self.assertEqual(entry["study_value"]["value"], value)
                self.assertTrue(entry["study_value"]["used_by_historical_cfd"])
                self.assertEqual(entry["study_value"]["source"]["path"], "twins/bionic-turbo-f1/cfd/prepare_case.py")
        self.assertAlmostEqual(101325 * 1.2, 121590, places=6)
        for name in ("mrf.zone_radius", "ports.rear_closure", "ports.inlet_plane"):
            self.assertEqual(self.entry(self.ledger, name)["study_value"]["status"], "numerical_construct")
        # The precision-16 generator pinned by G01 carries the same hypotheses: one line differs.
        old = (TWIN / "cfd/prepare_case.py").read_text().split("\n")
        new = (TWIN / "cfd/prepare_case_v2.py").read_text().split("\n")
        self.assertEqual([i + 1 for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b], [242])
        # The pair differs in the volute law only, so a housing value cited from one file holds for both.
        reference, bionic = (json.loads((TWIN / name).read_text()) for name in ("baseline.json", "candidate.json"))
        self.assertEqual({key for key in reference if reference[key] != bionic[key]}, {"volute_law"})

    def test_no_field_is_promoted_to_measured_without_admitted_evidence(self):
        name = "rotor.compressor_wheel.exducer_diameter"
        bare = copy.deepcopy(self.ledger)
        self.entry(bare, name)["measured"] = 60.5
        self.assertTrue(any("never a bare figure" in e for e in self.check(bare)))
        partial = copy.deepcopy(self.ledger)
        self.entry(partial, name)["measured"] = {"value": 60.5, "unit": "mm"}
        errors = self.check(partial)
        for needle in ("measured without instrument", "measured without specimen_id", "measured without licence",
                       "measured without a stated numeric uncertainty", "measured without an admitted measurement record",
                       "measured without a review independent of its contributor", "summary is stale"):
            self.assertTrue(any(needle in e for e in errors), needle)
        published = copy.deepcopy(self.ledger)
        self.entry(published, name)["published_context"][0]["transferable"] = True
        self.assertTrue(any("never transferable" in e for e in self.check(published)))
        relabelled = copy.deepcopy(self.ledger)
        self.entry(relabelled, name)["study_value"]["status"] = "measured"
        self.assertTrue(any("study value status 'measured' is not allowed" in e for e in self.check(relabelled)))
        ungated = copy.deepcopy(self.ledger)
        self.entry(ungated, "clearance.tip_running_clearance")["missing_data_gate"] = None
        self.assertTrue(any("neither measured nor bound to a missing-data gate" in e for e in self.check(ungated)))
        uncertain = copy.deepcopy(self.ledger)
        self.entry(uncertain, name)["uncertainty"] = {"value": 0.05, "unit": "mm"}
        self.assertTrue(any("uncertainty is stated without a measurement" in e for e in self.check(uncertain)))
        invented = copy.deepcopy(self.ledger)
        self.entry(invented, name)["study_value"]["source"]["literals"] = ['("exducer_diameter_mm", 61.0f)']
        self.assertTrue(any("is not in" in e for e in self.check(invented)))
        unsourced = copy.deepcopy(self.ledger)
        self.entry(unsourced, "clearance.tip_running_clearance")["study_value"] = {
            "status": "assumed", "value": 0.4, "unit": "mm", "uncertainty_statement": "guess", "source": None}
        self.assertTrue(any("no source" in e for e in self.check(unsourced)))
        foreign = copy.deepcopy(self.ledger)
        self.entry(foreign, name)["study_value"]["source"]["path"] = "benchmarks/free-tools/corpus.json"
        self.assertTrue(any("not an allowlisted turbo source" in e for e in self.check(foreign)))

    def test_missing_data_gates_are_requests_never_purchases_or_owner_tasks(self):
        blockers = {b["id"] for b in next(g for g in self.gate_ledger["gates"] if g["id"] == GATE)["blockers"]}
        gates = self.ledger["missing_data_gates"]
        self.assertEqual([gate["id"] for gate in gates],
                         [f"MD-{n:02d}" for n in range(1, 13)] + ["MD-N1", "MD-N2"])
        self.assertEqual({gate["gate_blocker"] for gate in gates} - {None}, blockers)
        for gate in gates:
            with self.subTest(gate=gate["id"]):
                self.assertIn(gate["route"], basis.GATE_ROUTES)
                self.assertTrue(gate["required_evidence"] and gate["essential_for"])
                self.assertNotRegex(gate["request"].lower(), r"\b(purchase|commission|hire)\b")
        bought = copy.deepcopy(self.ledger)
        bought["missing_data_gates"][5]["route"] = "purchase_dataset"
        self.assertTrue(any("route 'purchase_dataset' is not allowed" in e for e in self.check(bought)))
        widened = copy.deepcopy(self.ledger)
        widened["scope_verdict"]["justified_scope"] = "measured_comparison"
        self.assertTrue(any("provisional synthetic comparison" in e for e in self.check(widened)))


class ConventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conventions = basis.load("conventions")

    def test_required_quantities_are_defined_with_a_basis(self):
        self.assertEqual(basis.check_conventions(self.conventions, basis.load("allowlist")), [])
        self.assertEqual({item["id"] for item in self.conventions["quantities"]}, basis.REQUIRED_QUANTITIES)
        reference = self.conventions["reference_conditions"]
        self.assertEqual((reference["temperature_k"], reference["pressure_pa"]), (288.15, 101325))
        self.assertEqual(reference["status"], "convention_not_measurement")
        relabelled = copy.deepcopy(self.conventions)
        relabelled["reference_conditions"]["status"] = "measured"
        relabelled["model_constants"][0]["status"] = "measured"
        relabelled["quantities"] = relabelled["quantities"][1:]
        errors = basis.check_conventions(relabelled, basis.load("allowlist"))
        for needle in ("labelled a convention", "must stay labelled assumed", "conventions lack ['mass_flow']"):
            self.assertTrue(any(needle in e for e in errors), needle)

    def test_corrected_flow_reproduces_the_register_points_computed_independently(self):
        data = json.loads((ROOT / self.conventions["independent_check"]["path"]).read_text())
        assumed = data["matching_assumptions"]
        records = data["matching_demand_records"]
        self.assertEqual(len(records), 20)
        for record in records:
            corrected = basis.corrected_mass_flow(
                record["actual_mass_flow_per_turbo_kg_s"],
                record["compressor_inlet_temperature_C"] + 273.15,
                record["compressor_inlet_pressure_bar_absolute"] * 1e5,
                assumed["flow_reference_temperature_K"], assumed["flow_reference_pressure_Pa"])
            self.assertTrue(math.isclose(corrected, record["corrected_mass_flow_per_turbo_kg_s"], rel_tol=1e-12))

    def test_definitions_hold_as_identities_and_keep_their_signs(self):
        self.assertEqual(basis.corrected_mass_flow(0.2, 288.15, 101325, 288.15, 101325), 0.2)
        self.assertEqual(basis.corrected_speed(90000, 288.15, 288.15), 90000)
        self.assertTrue(math.isclose(basis.corrected_speed(100000, 4 * 288.15, 288.15), 50000))
        self.assertTrue(math.isclose(basis.corrected_mass_flow(1.0, 4 * 288.15, 2 * 101325, 288.15, 101325), 1.0))
        self.assertEqual(basis.total_pressure_ratio(202650, 101325), 2.0)
        omega = basis.angular_velocity(100000, 1)
        self.assertTrue(math.isclose(omega, 2 * math.pi * 100000 / 60))
        self.assertEqual(basis.angular_velocity(100000, -1), -omega)
        self.assertEqual(basis.shaft_power(omega, 3.0), omega * 3.0)
        self.assertGreater(basis.compressor_power_from_fluid_moment(omega, -3.0), 0)
        self.assertLess(basis.compressor_power_from_fluid_moment(omega, 3.0), 0)
        self.assertEqual(basis.compressor_power_from_fluid_moment(omega, -3.0), basis.shaft_power(omega, 3.0))
        gamma, ratio = 1.4, 2.0
        isentropic = 300.0 * ratio ** ((gamma - 1) / gamma)
        self.assertTrue(math.isclose(basis.isentropic_efficiency_tt(ratio, 300.0, isentropic, gamma), 1.0))
        self.assertTrue(math.isclose(
            basis.isentropic_efficiency_tt(ratio, 300.0, 300.0 + 2 * (isentropic - 300.0), gamma), 0.5))
        for call in (lambda: basis.corrected_mass_flow(0.1, -1.0, 101325, 288.15, 101325),
                     lambda: basis.corrected_speed(float("nan"), 288.15, 288.15),
                     lambda: basis.total_pressure_ratio(0.0, 101325),
                     lambda: basis.angular_velocity(100000, 0),
                     lambda: basis.isentropic_efficiency_tt(2.0, 300.0, 290.0, 1.4),
                     lambda: basis.shaft_power(True, 1.0)):
            with self.assertRaises(basis.BasisError):
                call()

    def test_illustration_is_arithmetic_on_the_assumed_inputs_only(self):
        shown = self.conventions["illustration_from_assumed_inputs"]
        self.assertEqual(shown["status"], "arithmetic_on_hypotheses_not_a_result")
        self.assertEqual(shown["corrected_mass_flow_per_unit_mass_flow"],
                         basis.corrected_mass_flow(1.0, 298.15, 101325.0, 288.15, 101325))
        self.assertEqual(shown["corrected_speed_rpm"], basis.corrected_speed(100000.0, 298.15, 288.15))
        self.assertEqual(shown["angular_velocity_rad_s"], basis.angular_velocity(100000.0, 1))
        constants = {item["id"]: item for item in self.conventions["model_constants"]}
        self.assertEqual(constants["cp"]["value"], 1.4 * 287.05 / (1.4 - 1))
        for forbidden in ("mass_flow_kg_s", "shaft_power_w", "efficiency"):
            self.assertNotIn(forbidden, shown)


if __name__ == "__main__":
    unittest.main()
