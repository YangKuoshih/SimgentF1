"""What the app shows must match what the data supports (fixes from a pre-launch review).

Historic circuits are never shown as another circuit or with today's figures, cards are not
double-escaped, questions without a race on screen use the latest race, "why" championship
questions explain, and the UI does not claim live timing or car telemetry. Offline."""
import json
import math
import os
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools import jolpica_sync as J  # noqa: E402
from app.tools import race_replay as R  # noqa: E402
from app.tools.guardrails import sanitize_a2ui_card  # noqa: E402
from app.tools.race_agent import answer_race_engineer_query as ask  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_offline = patch.object(J, "_http", lambda url, retries=4: None)


def setUpModule():
    _offline.start()


def tearDownModule():
    _offline.stop()


def track(year, rnd):
    m = R.build_replay(year, rnd)
    return m["meta"], m["track"]


class HistoricCircuits(unittest.TestCase):
    def test_historic_circuits_are_drawn_on_the_layout_raced(self):
        # Bremgarten and Rouen used to replay on a generic loop; Reims 1950 on its OSM outline
        for (year, rnd), layout, name, source in (((1950, 4), "bremgarten-1", "Bremgarten", "f1-circuits-svg"),
                                                  ((1957, 4), "rouen-2", "Rouen", "f1-circuits-svg"),
                                                  ((1957, 7), "pescara-1", "Pescara", "f1-circuits-svg"),
                                                  ((1950, 6), "reims-1", "Reims", "OpenStreetMap")):
            meta, tr = track(year, rnd)
            self.assertIn(name, meta["circuit_name"])
            self.assertFalse(tr.get("schematic"), layout)
            self.assertEqual(tr["layout_id"], layout)
            self.assertEqual(tr["outline_source"], source)
            self.assertTrue(tr["length_km"] and tr["turns_count"], layout)
            self.assertEqual(tr["drs_zones"], [])

    def test_resolver_never_substitutes_another_circuit(self):
        for year in (1950, 1955, 1961):
            for race in R.season_races(year, net=False):
                res = J.results(year, race["round"], net=False) or {}
                raw = res.get("Circuit", {}).get("circuitId", "")
                if raw and raw != "silverstone":
                    self.assertNotEqual(R.resolve_canonical_circuit(year, race["round"], raw_circuit_id=raw),
                                        "silverstone", (year, race["round"], raw))

    def test_pre_1996_races_show_the_layout_raced(self):
        meta, tr = track(1950, 1)
        self.assertEqual(meta["circuit_name"], "Silverstone Circuit")
        self.assertEqual((tr["layout_id"], tr["length_km"], tr["turns_count"]), ("silverstone-1", 4.649, 8))
        self.assertIsNone(tr["lap_record"])  # today's record never appears on an old layout
        self.assertEqual(tr["race_fastest_lap"]["driver"], "Nino Farina")
        self.assertEqual(tr["drs_zones"], [])

    def test_drs_only_from_2011_and_straight_line_mode_from_2026(self):
        self.assertEqual(track(2005, 9)[1]["drs_zones"], [])
        tr = track(2019, 10)[1]
        self.assertTrue(tr["drs_zones"])
        self.assertEqual(tr["aero_zone_label"], "DRS")
        self.assertEqual(track(2026, 17)[1]["aero_zone_label"], "Straight-line mode")

    def test_no_lap_record_set_after_the_race(self):
        for year, rnd in ((2019, 10), (2005, 9), (2026, 17)):
            record = track(year, rnd)[1].get("lap_record") or ""
            for y in re.findall(r"\b(?:19|20)\d{2}\b", record):
                self.assertLessEqual(int(y), year, (year, rnd, record))

    def test_no_invented_default_figures(self):
        geo = R.circuit_geometry("some_circuit_without_data")
        self.assertTrue(geo["schematic"])
        self.assertIsNone(geo["length_km"])
        self.assertEqual(geo["drs_zones"], [])
        with open(os.path.join(ROOT, "app", "tools", "race_replay.py"), encoding="utf-8") as f:
            src = f.read()
        for default in ('"1:30.000"', '"Level 3/5"', '"length_km": 5.2'):
            self.assertNotIn(default, src)


class EveryRaceShowsItsOwnCircuit(unittest.TestCase):
    """All 1950-2026 races from the cached schedules, offline."""

    @classmethod
    def setUpClass(cls):
        cls.races = []
        for year in range(1950, 2027):
            winners = J.season_winners(year, net=False)
            for race in J.schedule(year, net=False):
                rnd = int(race["round"])
                if rnd in winners:
                    cls.races.append((year, rnd, race, winners[rnd]))
        assert len(cls.races) > 1100

    def test_resolved_circuit_is_the_one_raced(self):
        # The event-name fallback once put the British GP at Brands Hatch on Silverstone,
        # Adelaide on Albert Park and Fuji on Suzuka (91 races)
        wrong = [(y, r, race["Circuit"]["circuitId"], cid) for y, r, race, _ in self.races
                 if (cid := R.resolve_canonical_circuit(y, r, raw_circuit_id=race["Circuit"]["circuitId"],
                                                        race_name=race["raceName"])) != race["Circuit"]["circuitId"]
                 and (y, r) not in R.EVENT_RELOCATIONS]
        self.assertEqual(wrong, [])

    def test_shown_length_fits_the_race_distance(self):
        # Winner laps x shown length is a race distance unless the race was cut short;
        # anything else means the layout shown is not the one raced that year
        shortened = {(2003, 3), (2009, 2), (2021, 12), (2022, 7), (2022, 18), (1996, 6), (1997, 5), (1997, 7)}
        odd = []
        for y, r, race, w in self.races:
            if y < 1996:
                continue
            cid = R.resolve_canonical_circuit(y, r, raw_circuit_id=race["Circuit"]["circuitId"], race_name=race["raceName"])
            geo = R.track_for_year(cid, y, race["Circuit"], r) or {}
            if geo.get("length_km") and (y, r) not in shortened:
                dist = int(w["laps"]) * geo["length_km"]
                if not 250 <= dist <= 320:
                    odd.append((y, r, cid, round(dist)))
        self.assertEqual(odd, [])

    def test_earlier_layouts_are_drawn_as_raced(self):
        cases = {(2005, 11): ("silverstone-7", 5.141), (2001, 12): ("hockenheimring-3", 6.825),
                 (2010, 1): ("bahrain-2", 6.299), (2020, 15): ("bahrain-1", 5.412), (2020, 16): ("bahrain-3", 3.543)}
        for (year, rnd), (layout, km) in cases.items():
            tr = track(year, rnd)[1]
            self.assertEqual(tr["layout_id"], layout, (year, rnd))
            self.assertAlmostEqual(tr["length_km"], km, places=2)

    def test_every_race_has_its_layout_and_figures(self):
        missing = []
        for y, r, race, _ in self.races:
            cid = R.resolve_canonical_circuit(y, r, raw_circuit_id=race["Circuit"]["circuitId"], race_name=race["raceName"])
            geo = R.track_for_year(cid, y, race["Circuit"], r) or {}
            if geo.get("schematic") or not geo.get("layout_id") or not (geo.get("length_km") and geo.get("turns_count")):
                missing.append((y, r, cid))
        self.assertEqual(missing, [])

    def test_map_outlines_measure_the_layout_they_stand_for(self):
        # Estoril's outline is the post-2000 layout (-4.5%), Indianapolis' and Jacarepagua's other
        # road courses: those races must use the drawing of the layout raced
        feats = R._geo_features()
        for lid, lay in R._circuit_layouts()["layouts"].items():
            if lay["shape"] != "geographic" or lid == "reims-1":  # Reims: traced along rebuilt roads
                continue
            f = feats[R.CIRCUIT_MAP[lay["circuit"]]]
            c = f["geometry"]["coordinates"]
            lat0 = sum(p[1] for p in c) / len(c)
            P = [(p[0] * 111320 * math.cos(math.radians(lat0)), p[1] * 110540) for p in c]
            length = sum(math.dist(P[i], P[i + 1]) for i in range(len(P) - 1)) / 1000
            self.assertLess(abs(length - lay["length_km"]) / lay["length_km"], 0.013, lid)
        for year, rnd, layout in ((1985, 2, "estoril-1"), (2005, 9, "indianapolis-2"), (1985, 1, "jacarepagua-1")):
            tr = track(year, rnd)[1]
            self.assertEqual((tr["layout_id"], tr["outline_source"]), (layout, "f1-circuits-svg"))

    def test_each_race_gets_the_drawing_for_its_own_season(self):
        # F1DB: Montreal 1988-93 is one layout; the drawings split 1988-90 and 1991-93
        self.assertEqual(R.race_layout(1992, 7)["layout_info"]["svg_layout"], "montreal-3")
        self.assertEqual(R.race_layout(1989, 6)["layout_info"]["svg_layout"], "montreal-2")
        self.assertEqual(track(1992, 7)[1]["layout_id"], "montreal-3")

    def test_race_direction(self):
        # The outline data had Marina Bay and Paul Ricard backwards; the Indy 500 oval runs anticlockwise
        for (year, rnd), clockwise in (((2026, 17), False), ((2018, 8), True), ((1960, 3), False), ((2019, 10), True)):
            tr = track(year, rnd)[1]
            self.assertEqual(R._is_clockwise([tuple(p) for p in tr["points"]]), clockwise, (year, rnd))
            self.assertEqual(tr["direction"], "CLOCKWISE" if clockwise else "ANTI_CLOCKWISE")

    def test_silverstone_2010_started_on_the_old_pit_straight(self):
        p2010, p2019 = track(2010, 10)[1]["points"][0], track(2019, 10)[1]["points"][0]
        self.assertGreater(abs(p2010[0] - p2019[0]) + abs(p2010[1] - p2019[1]), 0.2)

    def test_no_invented_drs_zones_or_turn_numbers(self):
        geo = R.circuit_geometry("hungaroring")  # no stored DRS or corner positions
        self.assertEqual(geo["drs_zones"], [])
        self.assertEqual(geo["turns"], [])
        self.assertEqual(geo["turns_count"], 14)  # official count, not detected apexes
        self.assertEqual(geo["length_km"], 4.381)  # official length, not the measured outline


class CircuitOutlinesAndLicensing(unittest.TestCase):
    def test_openstreetmap_outlines_match_the_official_length(self):
        with open(os.path.join(ROOT, "data", "osm-circuits.geojson"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["license"], "ODbL-1.0")
        self.assertIn("OpenStreetMap contributors", data["attribution"])
        self.assertEqual({f["properties"]["id"] for f in data["features"]},
                         {"osm-jerez", "osm-fuji", "osm-yeongam", "osm-reims"})
        for feat in data["features"]:
            p = feat["properties"]
            # Race-track outlines match the official length within 1%; a historic road circuit
            # traced along today's roads (Reims-Gueux, rebuilt Garenne corner) within 5%
            limit = 0.05 if p.get("traced_along_roads") else 0.01
            self.assertLess(abs(p["measured_length"] - p["length"]) / p["length"], limit, p["id"])
            self.assertEqual(feat["geometry"]["coordinates"][0], feat["geometry"]["coordinates"][-1])

    def test_openstreetmap_outlines_are_shown_and_credited(self):
        for year, rnd_cid in ((1997, "jerez"), (2008, "fuji"), (2010, "yeongam")):
            geo = R.track_for_year(rnd_cid, year)
            self.assertFalse(geo.get("schematic"), rnd_cid)
            self.assertEqual(geo["outline_source"], "OpenStreetMap")
            self.assertTrue(geo["length_km"] and geo["turns_count"], rnd_cid)
        self.assertEqual(R.track_for_year("silverstone", 2020)["outline_source"], "bacinger/f1-circuits")
        self.assertIsNone(R.track_for_year("fuji", 1976)["length_km"])  # old layout

    def test_reims_gueux_is_the_1926_1951_layout(self):
        # The 1950 French GP was drawn on a made-up schematic loop
        geo = R.track_for_year("reims", 1950)
        self.assertFalse(geo.get("schematic"))
        self.assertEqual(geo["outline_source"], "OpenStreetMap")
        self.assertIn("1926-1951 layout raced that year", geo["layout_note"])
        self.assertIsNone(geo["length_km"])  # no figures before 1996
        # Shape: a triangle about 3 km wide and 1.8 km tall, the long side the RN31 to Thillois
        with open(os.path.join(ROOT, "data", "osm-circuits.geojson"), encoding="utf-8") as f:
            feat = next(x for x in json.load(f)["features"] if x["properties"]["id"] == "osm-reims")
        lon0, lat0, lon1, lat1 = feat["bbox"]
        self.assertAlmostEqual((lon1 - lon0) * 111.32 * 0.653, 3.0, delta=0.3)
        self.assertAlmostEqual((lat1 - lat0) * 110.57, 1.8, delta=0.2)
        start = feat["geometry"]["coordinates"][0]  # start/finish by the grandstand on the D27
        self.assertLess(abs(start[0] - 3.9317) + abs(start[1] - 49.2543), 0.002)
        # From 1953 Reims ran a longer layout: the outline is only a reference
        self.assertIn("layout was different", R.track_for_year("reims", 1958)["layout_note"])

    def test_circuit_layouts_file_is_pinned_and_credited(self):
        with open(os.path.join(ROOT, "data", "circuit-layouts.json"), encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["sources"]["f1db"]["license"], "CC-BY-4.0")
        self.assertRegex(data["sources"]["f1-circuits-svg"]["commit"], r"^[0-9a-f]{40}$")
        for path in ("data/CIRCUIT-LAYOUTS-LICENSE.md", "data/f1-circuits-svg.LICENSE"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, path)), path)
        with open(os.path.join(ROOT, "frontend", "static", "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn("github.com/f1db/f1db", html)
        self.assertIn("f1-circuits-svg", html)
        self.assertTrue(all(l["shape"] for l in data["layouts"].values()))

    def test_license_files_and_credits_exist(self):
        for path in ("data/OSM-LICENSE.md", "data/f1-circuits.LICENSE"):
            self.assertTrue(os.path.exists(os.path.join(ROOT, path)), path)
        with open(os.path.join(ROOT, "NOTICE.md"), encoding="utf-8") as f:
            notice = f.read()
        self.assertIn("ODbL", notice)
        self.assertIn("Tomislav Bacinger", notice)
        with open(os.path.join(ROOT, "frontend", "static", "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="map-attribution"', html)
        self.assertIn("openstreetmap.org/copyright", html)
        self.assertIn("Jolpica-F1", html)

    def test_turn_counts_and_layout_years(self):
        self.assertEqual(R.track_for_year("marina_bay", 2025)["turns_count"], 19)
        self.assertIsNone(R.track_for_year("catalunya", 2022)["length_km"])  # chicane until 2022
        self.assertEqual(R.track_for_year("catalunya", 2023)["turns_count"], 14)
        self.assertEqual(R.track_for_year("losail", 2021)["length_km"], 5.38)
        self.assertIsNone(R.track_for_year("losail", 2023)["length_km"])  # 5.419 km layout
        madring = R.track_for_year("madring", 2026)
        self.assertIsNone(madring["length_km"])
        self.assertIn("sources disagree", madring["layout_note"])


class ReconstructedSessionsAreLabelled(unittest.TestCase):
    def test_sprint_points_come_from_the_classification(self):
        m = R.build_replay(2021, 10, session_type="sprint")  # 2021 sprints paid 3-2-1
        self.assertFalse(m["meta"]["has_lap_data"])
        finish = m["events"][-1]["consequence"]
        self.assertIn("(3 pts)", finish)
        self.assertNotIn("8 pts", finish)


class CardsAreNotDoubleEscaped(unittest.TestCase):
    def test_text_stays_plain_for_the_client_to_escape(self):
        card = sanitize_a2ui_card({"title": "Results & Classification", "action": "VIEW",
                                   "metrics": [{"label": "P1 & P2", "value": "<b>x</b>", "color": "red;x"}]})
        self.assertEqual(card["title"], "Results & Classification")
        self.assertEqual(card["metrics"][0]["label"], "P1 & P2")
        self.assertNotIn("&amp;", str(card))
        self.assertEqual(card["metrics"][0]["value"], "bx/b")  # no markup survives
        self.assertTrue(re.fullmatch(r"#[0-9A-Fa-f]{3,8}", card["metrics"][0]["color"]))

    def test_control_characters_and_length_are_capped(self):
        card = sanitize_a2ui_card({"title": "a\x00b\x1b" + "x" * 200})
        self.assertTrue(card["title"].startswith("ab"))
        self.assertLessEqual(len(card["title"]), 80)


class NoRaceOnScreen(unittest.TestCase):
    def test_q1_without_context_uses_the_latest_race(self):
        for q in ("Who got knocked out in Q1?", "which drivers were eliminated in Q1"):
            r = ask(q, {}, [])
            self.assertEqual(r["tool"], "qualifying_segment_lookup", q)
            self.assertIn("Qualifying", r["text"])
            self.assertNotIn("retirement", r["text"].lower())

    def test_named_race_and_session(self):
        r = ask("who was knocked out in Q1 at monza 2024", {"year": 2026, "round": 17}, [])
        self.assertEqual(r["tool"], "qualifying_segment_lookup")
        self.assertIn("2024 Italian Grand Prix", r["text"])


class ChampionshipWhy(unittest.TestCase):
    def test_why_includes_the_deciding_race_whatever_is_on_screen(self):
        for ctx in ({}, {"year": 2026, "round": 17}):
            r = ask("Why did Hamilton lose the 2021 championship?", ctx, [])
            self.assertIn("Max Verstappen", r["text"])
            self.assertIn("Latifi", r["text"], ctx)

    def test_why_without_a_write_up_says_so(self):
        r = ask("why did button win the 2009 title", {}, [])
        self.assertIn("no write-up", r["text"])

    def test_who_won_stays_short(self):
        r = ask("who won the 2009 title", {}, [])
        self.assertNotIn("How it was decided", r["text"])


class UiClaims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "frontend", "static", "index.html"), encoding="utf-8") as f:
            cls.html = f.read()

    def test_no_live_timing_or_telemetry_overclaims(self):
        for claim in ("LIVE TIMING FEED", "Corner-by-Corner Telemetry", "telemetry archives",
                      "76+ years of Grand Prix telemetry", "Calibrated track telemetry layout",
                      "Deeper Entry", "Earlier Full Throttle"):
            self.assertNotIn(claim, self.html)

    def test_driver_fields_are_not_put_into_inline_handlers(self):
        self.assertNotRegex(self.html, r"onclick=\"\w+\('\$\{")

    def test_readme_states_what_is_modelled(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            readme = f.read()
        self.assertIn("1996", readme)
        self.assertIn("no car telemetry", readme.lower().replace("there is ", ""))


if __name__ == "__main__":
    unittest.main()
