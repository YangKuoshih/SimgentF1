"""Offline tests for the data pipeline safeguards (no network)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.tools import data_manifest as M  # noqa: E402
from app.tools import revalidate as R  # noqa: E402


class FingerprintTests(unittest.TestCase):
    def test_formatting_differences_do_not_count(self):
        def doc(q2):
            row = {"Driver": {"driverId": "x"}, "position": "1", "Q1": "1:30.000"}
            if q2 is not None:
                row["Q2"] = q2
            return {"MRData": {"RaceTable": {"Races": [{"QualifyingResults": [row]}]}}}
        self.assertEqual(R.fingerprint("qualifying", doc(None)), R.fingerprint("qualifying", doc("")))
        self.assertNotEqual(R.fingerprint("qualifying", doc(None)), R.fingerprint("qualifying", doc("1:29.000")))


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = (M.CACHE_ROOT, M.MANIFEST)
        M.CACHE_ROOT = self.tmp
        M.MANIFEST = os.path.join(self.tmp, "MANIFEST.json")
        os.makedirs(os.path.join(self.tmp, "jolpica"))
        self.f = os.path.join(self.tmp, "jolpica", "2026_1_results.json")
        with open(self.f, "w") as fh:
            json.dump({"MRData": {"url": "https://api.jolpi.ca/x"}}, fh)

    def tearDown(self):
        M.CACHE_ROOT, M.MANIFEST = self.saved
        shutil.rmtree(self.tmp)

    def test_hand_edit_is_detected(self):
        M.record(self.f, "https://api.jolpi.ca/x")
        self.assertEqual(M.changed_files(), [])
        with open(self.f, "a") as fh:
            fh.write(" ")
        self.assertEqual(M.changed_files(), [("jolpica/2026_1_results.json", "content differs")])

    def test_rebuild_keeps_recorded_source_for_unchanged_files(self):
        M.record(self.f, "https://example/source", note="corrected")
        M.rebuild("bulk")
        with open(M.MANIFEST) as fh:
            entry = json.load(fh)["files"]["jolpica/2026_1_results.json"]
        self.assertEqual((entry["source"], entry["note"]), ("https://example/source", "corrected"))


if __name__ == "__main__":
    unittest.main()
