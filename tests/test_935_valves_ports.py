"""Contract tests for the valve, seat and guide bodies, the declared port domain and the port CFD stop (935 head twin).

Issues #697, #698 and #700. They run on the committed records and on synthetic
geometry; the private scan, STEP files and meshes never reach CI.
"""

import importlib.util
import json
import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TWIN = ROOT / "twins" / "935-cylinder-head-cad-twin"
PARAMS = TWIN / "params"
SOURCE = TWIN / "source"
LOG = ROOT / "docs" / "research" / "935-valves-ports-20261122.md"
sys.path.insert(0, str(SOURCE))


def load(name):
    return json.loads((PARAMS / name).read_text())


def has(*mods):
    return all(importlib.util.find_spec(m) is not None for m in mods)


def register():
    return {item["id"].split("-")[0]: item for item in json.loads((TWIN / "hypotheses.json").read_text())["items"]}


def entries(case):
    """Every declared value of the case: (path, entry) for each dict that carries a value."""

    out = []

    def walk(node, path):
        if isinstance(node, dict):
            if "value" in node:
                out.append((path, node))
                return
            for key, child in node.items():
                walk(child, f"{path}/{key}")

    for block in ("valves", "seats", "guides"):
        walk(case[block], block)
    return out


class CaseTests(unittest.TestCase):
    """Every value of the case names its source or its hypothesis."""

    def setUp(self):
        self.case = load("valve-seat-guide-case.json")
        self.reg = register()

    def test_every_value_names_a_known_source_or_hypothesis(self):
        sources = self.case["sources"]
        for key, source in sources.items():
            self.assertTrue(source["url"].startswith(("https://", "http://")), key)
            self.assertTrue(source["accessed"] and source["terms"] and source["kind"], key)
            self.assertRegex(source["private_copy_sha256"], r"^[0-9a-f]{64}$", key)
        found = entries(self.case)
        self.assertGreater(len(found), 25)
        for path, entry in found:
            if entry["value"] is None:
                self.assertTrue(entry.get("blocker"), path)
                continue
            if "hypothesis" in entry:
                self.assertIn(entry["hypothesis"], self.reg, path)
            for sid in entry.get("sources", []):
                self.assertIn(sid, sources, path)
            # a value with no source is an explicit assumption with a range, or a fit on the scan
            if "hypothesis" in entry and not entry.get("sources") and isinstance(entry["value"], (int, float)):
                self.assertIn("explicit assumption", entry["how"], path)
                self.assertIn("range_mm", entry, path)

    def test_valve_heads_are_the_sizes_common_to_both_catalogue_families(self):
        def ranges(quotes, word):
            return [tuple(float(x) for x in re.match(r"([\d.]+)mm - ([\d.]+)mm " + word, q).groups())
                    for q in quotes if q.endswith(word)]

        for name, word in (("valve_y_minus", "intake valve"), ("valve_y_plus", "exhaust valve")):
            head = self.case["valves"][name]["head_diameter_mm"]
            families = ranges(head["quotes"], word)
            self.assertEqual(len(families), 2, name)
            low = max(lo for lo, _ in families)
            high = min(hi for _, hi in families)
            self.assertEqual(low, high, f"{name}: the families share one size only")
            self.assertEqual(head["value"], low, name)
            self.assertEqual(head["range_mm"], [min(lo for lo, _ in families), max(hi for _, hi in families)], name)
            self.assertIn(f"Valve head diameter [mm]: {head['value']:g}", head["quotes"], name)

    def test_the_stem_is_the_makers_and_the_production_stem_does_not_fit_the_fitted_bore(self):
        fits = load("feature-fits.json")
        bore = [r for r in fits["regions"] if r["id"] == "valve_y_minus_guide_bore"][0]["fit"]["diameter_mm"]
        for name in ("valve_y_minus", "valve_y_plus"):
            stem = self.case["valves"][name]["stem_diameter_mm"]["value"]
            self.assertEqual(stem, 8.0)
            self.assertLess(stem, bore)
        self.assertGreater(9.0, bore)  # the production 930 / 964 stem of the 2026-11-16 record
        guide_id = self.case["guides"]["inside_diameter_mm"]
        self.assertGreater(guide_id["value"], 8.0)
        self.assertLessEqual(guide_id["range_mm"][1] - 8.0, 0.13 + 1e-9)


class BodyTests(unittest.TestCase):
    """The revolved outlines, recomputed without CAD, against the committed record."""

    def setUp(self):
        import valve_seat_guide

        self.mod = valve_seat_guide
        self.case = load("valve-seat-guide-case.json")
        self.fits = load("feature-fits.json")
        self.prof = valve_seat_guide.profiles(self.case, self.fits)
        self.record = load("valve-seat-guide.json")

    @staticmethod
    def area(outline):
        return 0.5 * sum(r0 * s1 - r1 * s0 for (r0, s0), (r1, s1) in zip(outline, outline[1:] + outline[:1]))

    def test_record_numbers_follow_from_the_case_and_the_fits(self):
        for name, numbers in self.record["bodies"].items():
            self.assertEqual(self.prof[name]["numbers"], numbers, name)
        self.assertEqual(self.record["roles"], {"valve_y_minus": "inlet", "valve_y_plus": "exhaust"})
        window = self.mod.contact_band_in_window(self.prof, self.fits)
        for name in window:
            self.assertEqual(self.record["checks"][name]["contact_band_in_fitted_seat_window"], window[name])

    def test_outlines_are_simple_closed_and_off_the_axis(self):
        for name, parts in self.prof.items():
            for part in ("valve", "insert", "guide"):
                outline = parts[part]
                self.assertTrue(all(r >= 0.0 for r, _ in outline), (name, part))
                self.assertGreater(abs(self.area(outline)), 1.0, (name, part))

    def test_the_valve_closes_on_the_45_degree_cone_through_the_fitted_mid_band(self):
        for name, parts in self.prof.items():
            n = parts["numbers"]
            r_m, s_m = n["seat_mid_band"]["diameter_mm"] / 2, n["seat_mid_band"]["station_mm"]
            for d, s in zip(n["contact_band_diameters_mm"][::-1], n["contact_band_stations_mm"]):
                self.assertAlmostEqual(s, s_m + (r_m - d / 2), places=2, msg=name)
            # the insert's seat band is the valve's contact band
            insert = parts["insert"]
            self.assertAlmostEqual(2 * insert[4][0], n["contact_band_diameters_mm"][1], places=2)
            self.assertAlmostEqual(2 * insert[5][0], n["contact_band_diameters_mm"][0], places=2)
            v = self.case["valves"][name]
            width = n["contact_band_diameters_mm"][1] - n["contact_band_diameters_mm"][0]
            self.assertAlmostEqual(width / 2, v["seat_contact_width_mm"]["value"] * math.cos(math.radians(45)), places=2)
            self.assertGreater(n["contact_band_diameters_mm"][0], n["insert_diameters_mm"][0], name)
            self.assertEqual(n["stem_clearance_diametral_mm"], 0.05)

    def test_committed_checks_hold_and_the_exhaust_band_is_reported_beside_the_scan(self):
        checks = self.record["checks"]
        self.assertTrue(checks["bodies_consistent"])
        for name in ("valve_y_minus", "valve_y_plus"):
            self.assertTrue(all(v < 0.01 for v in checks[name]["overlap_mm3"].values()), name)
        self.assertGreater(checks["valve_heads_both_at_largest_lift_distance_mm"], 0.0)
        self.assertEqual(checks["contact_bands_inside_fitted_windows"], {"valve_y_minus": True, "valve_y_plus": False})
        band = self.record["bodies"]["valve_y_plus"]["contact_band_diameters_mm"][0]
        edge = checks["valve_y_plus"]["contact_band_in_fitted_seat_window"]["window_diameters_mm"][0]
        self.assertAlmostEqual((edge - band) / 2, 0.09, delta=0.005)
        readme = (TWIN / "README.md").read_text()
        self.assertIn("the exhaust band reaches 0.09 mm (radius) inside the\nwindow's inner edge", readme)
        for name, digest in self.record["private_files_sha256"].items():
            self.assertRegex(digest, r"^[0-9a-f]{64}$", name)
            self.assertIn(Path(name).suffix, {".step", ".stl"}, name)
        self.assertEqual(len(self.record["private_files_sha256"]), 8)


class PortDomainTests(unittest.TestCase):
    """The declared rule's helpers on known shapes, and the committed domain under the unchanged gates."""

    def setUp(self):
        import port_domain

        self.mod = port_domain

    def test_convex_exit_finds_the_faces_of_a_box(self):
        import numpy as np

        v = np.array([[x, y, z] for x in (-1.0, 3.0) for y in (-2.0, 2.0) for z in (-5.0, 5.0)])
        if not has("manifold3d"):
            self.skipTest("manifold3d not installed")
        import manifold3d as m3

        hull = m3.Manifold.hull_points(v).to_mesh64()
        hv = np.asarray(hull.vert_properties)[:, :3]
        hf = np.asarray(hull.tri_verts)
        ring = self.mod.convex_exit(hv, hf, np.zeros(3), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), 4)
        self.assertTrue(np.allclose(ring, [[3, 0, 0], [0, 2, 0], [-1, 0, 0], [0, -2, 0]], atol=1e-9))
        outside = self.mod.convex_exit(hv, hf, np.array([10.0, 0, 0]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), 4)
        self.assertTrue(np.isnan(outside).all())

    def test_boss_rays_are_replaced_by_their_neighbours(self):
        import numpy as np

        radii = np.full(8, 10.0)
        radii[2] = 3.0
        ring = self.mod.ring_points(np.zeros(3), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), radii)
        axis_point = ring[2] + np.array([0.0, 0.5, 0.0])
        out, count = self.mod.remove_boss(ring, radii, axis_point, np.array([0, 0, 1.0]), 1.0)
        self.assertEqual(count, 1)
        self.assertTrue(np.allclose(out, 10.0))

    def test_tube_mesh_is_closed_and_outward(self):
        import numpy as np

        ang = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        rings = [np.column_stack((2 * np.cos(ang), 2 * np.sin(ang), np.full(32, z))) for z in (0.0, 1.0, 3.0)]
        v, f = self.mod.tube_mesh(rings)
        tri = v[f]
        vol = np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6
        self.assertAlmostEqual(vol, 0.5 * 32 * 4 * math.sin(2 * math.pi / 32) * 3.0, places=6)
        edges = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        _, uses = np.unique(edges, axis=0, return_counts=True)
        self.assertTrue((uses == 2).all())

    def test_the_gates_are_unchanged_and_the_committed_domain_fails_gate_2_only(self):
        import audit_port_domain

        self.assertEqual(audit_port_domain.WALL_OBSERVED_MIN, 0.95)
        domain = load("port-domain.json")
        reg = json.loads((TWIN / "hypotheses.json").read_text())
        like = {"method": {"station_step_mm": domain["inputs"]["station_step_mm"]},
                "ports": [{"name": p["name"], "stations": p["stations"], "closed_stations": p["closed_stations"],
                           "loft_length_mm": round((p["stations"] - 1) * domain["inputs"]["station_step_mm"], 1),
                           "wall_points_observed_share": p["wall_points_observed_share"]} for p in domain["ports"]]}
        self.assertEqual(audit_port_domain.audit(like, reg), domain["audit_unchanged_gates"])
        fit = load("port-fit.json")
        self.assertEqual(domain["inputs"]["observed_within_mm"], fit["method"]["observed_within_mm"])
        self.assertEqual(domain["inputs"]["rays"], fit["method"]["rays"])
        for p in domain["audit_unchanged_gates"]["ports"]:
            self.assertEqual(p["gates"], {"closed_sections_along_whole_centreline": True,
                                          "wall_observed_share_at_least_min": False,
                                          "valve_seat_guide_modelled": True}, p["name"])
        for p in domain["ports"]:
            parts = p["parts"]
            n = [parts[k]["stations"] for k in ("loft", "bowl", "throat")]
            s = [parts[k]["observed_share"] for k in ("loft", "bowl", "throat")]
            self.assertEqual(sum(n), p["stations"])
            self.assertAlmostEqual(sum(a * b for a, b in zip(n, s)) / sum(n), p["wall_points_observed_share"], delta=0.002)
            needed = (0.95 * sum(n) - s[0] * n[0]) / (n[1] + n[2])
            self.assertAlmostEqual(needed, p["gate_2_needs_on_added_stations"], delta=0.002)
            # the scan sections are those of the port fit
            fitted = [q for q in fit["ports"] if q["name"] == p["name"]][0]
            self.assertEqual(n[0], fitted["loft_station_range"][1] - fitted["loft_station_range"][0])
            self.assertEqual(s[0], fitted["wall_points_observed_share"])
            self.assertEqual(p["domain"]["genus"], 0)
            self.assertEqual(p["domain"]["edges_not_used_twice_after_merge"], 0)
        needs = {p["name"]: p["gate_2_needs_on_added_stations"] for p in domain["ports"]}
        self.assertGreater(needs["port_y_minus"], 1.0)  # no declared rule can meet gate 2 on this port

    def test_the_twin_as_held_now_passes_gate_3_and_fails_gates_1_and_2(self):
        audit = load("port-cfd-audit.json")
        self.assertEqual(audit["verdict"], "not_admissible")
        self.assertNotIn(audit["hypothesis_h05_status"], ("not_modelled", "not_modelled_in_v0"))
        for p in audit["ports"]:
            self.assertEqual(p["gates"], {"closed_sections_along_whole_centreline": False,
                                          "wall_observed_share_at_least_min": False,
                                          "valve_seat_guide_modelled": True}, p["name"])
        self.assertNotIn("missing valve", audit["consequence"])


class StopRecordTests(unittest.TestCase):
    """The port CFD stopped at gate 2: the record says so, and it agrees with the audits."""

    def test_stop_record_agrees_with_both_audits_and_ran_nothing(self):
        stop = load("port-cfd.json")
        held, domain = load("port-cfd-audit.json"), load("port-domain.json")
        failing = lambda a: sorted({g for p in a["ports"] for g, ok in p["gates"].items() if not ok})  # noqa: E731
        self.assertEqual(sorted(stop["audits"]["twin_as_held"]["failing_gates"]), failing(held))
        self.assertEqual(stop["audits"]["declared_domain"]["failing_gates"], failing(domain["audit_unchanged_gates"]))
        for p in domain["ports"]:
            self.assertEqual(stop["audits"]["declared_domain"]["observed_share"][p["name"]], p["wall_points_observed_share"])
            self.assertEqual(stop["audits"]["declared_domain"]["gate_2_needs_on_added_stations"][p["name"]],
                             p["gate_2_needs_on_added_stations"])
        self.assertIn("gate 2", stop["stopped_at"])
        self.assertFalse(any(v for v in stop["not_run"].values()))
        self.assertEqual(stop["rental"], {"rented": False, "spend_usd": 0.0,
                                          "note": "the chain stopped at the audit, before any compute"})
        register = load("prepared-work.json")
        flow = [part for part in register["parts"] if part["id"] == "port-flow"][0]
        self.assertIn("gate 2", flow["state"])
        self.assertIn("twins/935-cylinder-head-cad-twin/params/port-cfd.json", [h["where"] for h in flow["held"]])


class RegisterTests(unittest.TestCase):
    """What the register says about H01, H04, H05, H07 to H10, H16 and H17."""

    def setUp(self):
        self.reg = register()

    def test_new_and_changed_hypotheses(self):
        for key in ("H16", "H17"):
            for field in ("region", "status", "how", "colour", "retire_with"):
                self.assertTrue(self.reg[key][field], (key, field))
        self.assertEqual(self.reg["H05"]["status"], "modelled_from_published_values_and_declared_assumptions")
        self.assertEqual(self.reg["H09"]["status"], "declared_with_published_indications")
        self.assertIn("kept_on_2026_11_22", self.reg["H10"])
        for key in ("H01", "H04", "H07", "H08"):
            searched = self.reg[key]["searched_on_2026_11_22"]
            self.assertTrue((ROOT / searched["record"]).exists(), key)
            self.assertNotIn("retired", self.reg[key]["status"], key)
        self.assertEqual(self.reg["H04"]["declared_rule_on_2026_11_22"]["hypothesis"], "H17-port-continuation-declared")
        self.assertEqual(load("port-domain.json")["rule"], "H17-port-continuation-declared")

    def test_the_role_indications_quote_the_committed_fits(self):
        fits = load("feature-fits.json")
        how = self.reg["H09"]["how"]
        about = {r["id"]: r.get("to_group_datum", {}).get("about_datum_axis") for r in fits["regions"]}
        for rid in ("valve_y_minus_seat", "valve_y_minus_throat", "valve_y_plus_seat", "valve_y_plus_throat"):
            self.assertIn(f"{about[rid]['diameter_mm']:.2f}", how, rid)
        for name in ("valve_y_minus", "valve_y_plus"):
            self.assertIn(f"{fits['group_datums'][name]['angle_to_frame_z_deg']:.2f}", how, name)
        ports = {p["name"]: p["station_detail"][0]["equivalent_diameter_mm"] for p in load("port-fit.json")["ports"]}
        self.assertIn(f"{ports['port_y_minus']:.1f} against {ports['port_y_plus']:.1f} mm", how)


class InferredShareTests(unittest.TestCase):
    def test_regions_add_up_and_the_total_is_the_scorecards(self):
        rec = load("inferred-share.json")
        card = load("scorecard-v2-loft-s025.json")
        regions = rec["by_region"]
        self.assertEqual(set(regions), {"H04", "cav", "H02", "rest"})
        self.assertAlmostEqual(sum(r["inferred_mm2"] for r in regions.values()), rec["inferred_mm2"], delta=0.5)
        self.assertAlmostEqual(sum(r["share_of_inferred_area"] for r in regions.values()), 1.0, delta=0.001)
        self.assertLess(abs(rec["inferred_mm2"] - card["twin_area_inferred_mm2"]), 1.0)
        self.assertAlmostEqual(rec["inferred_share_of_body_area"], 1 - card["twin_area_observed_supported_share"], places=4)
        self.assertEqual(rec["port_labels"], 2)
        readme = (TWIN / "README.md").read_text()
        self.assertIn(f"{100 * rec['inferred_share_of_body_area']:.1f}% of the v2 body", readme)
        self.assertIn(f"the port voids (H04) {100 * regions['H04']['share_of_body_area']:.1f}%", readme)


class ResearchLogTests(unittest.TestCase):
    def test_log_names_every_source_of_the_case_with_its_copy_hash(self):
        log = LOG.read_text()
        self.assertIn("Nothing here is a measurement of the scanned head", log)
        case = load("valve-seat-guide-case.json")
        for key, source in case["sources"].items():
            self.assertIn(source["url"], log, key)
            if key not in ("fia-3076", "fisa-b-298"):
                self.assertIn(source["private_copy_sha256"], log, key)
        self.assertIn("Hosts that refused automated readers", log)
        # numbers and short quotes only: no quote longer than about 25 words
        quotes = [q for line in log.splitlines() for q in re.findall(r'"([^"]{20,})"', line)]
        self.assertGreater(len(quotes), 15)
        for quote in quotes:
            self.assertLessEqual(len(quote.split()), 30, quote)


if __name__ == "__main__":
    unittest.main()
