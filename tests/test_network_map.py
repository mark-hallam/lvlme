"""network_map.py: parse a sample LinkedIn Connections.csv and match companies to target orgs."""
import datetime as dt
import json
import os
import unittest
from unittest import mock

import helpers as H
import network_map as N
import validate as V

CSV = os.path.join(H.FIXTURES, "Connections.csv")


def config():
    cfg = H.example_config()
    cfg["targets"] = [{"id": "acme", "name": "Acme AI", "ats": "manual", "aliases": ["Acme Artificial Intelligence"]},
                      {"id": "globex", "name": "Globex Labs", "ats": "manual"},
                      {"id": "initech", "name": "Initech Robotics", "ats": "manual"}]
    return cfg


class NetworkMapTests(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(N.normalise("OpenAI, Inc."), "openai")
        self.assertEqual(N.normalise("The Acme Corporation"), "acme")
        self.assertEqual(N.normalise("Initech Robotics Pty Ltd"), "initech robotics")

    def test_matcher_aliases_and_prefixes(self):
        match = N.org_matcher(config())
        self.assertEqual(match("ACME AI"), "acme")
        self.assertEqual(match("Acme Artificial Intelligence"), "acme")
        self.assertEqual(match("Globex Labs, Inc."), "globex")
        self.assertEqual(match("Globex Labs Research"), "globex")
        self.assertIsNone(match("Initech Consulting Group"))
        self.assertIsNone(match(""))

    def test_example_config_matches_the_xai_board_name(self):
        """xAI's public Greenhouse board (slug xai) is named SpaceXSI, so a contact listing it counts for xAI."""
        match = N.org_matcher(H.example_config())
        self.assertEqual(match("SpaceXSI"), "xai")
        self.assertEqual(match("xAI Corp"), "xai")
        self.assertIsNone(match("SpaceX AI"))          # not seen on the board, so not an alias

    def test_build_network(self):
        rows = N.read_connections(CSV)
        self.assertEqual(len(rows), 6)
        previous = {"orgs": {"globex": {"count": 1, "first_degree": [
            {"name": "Jordan Sample", "company": "Globex Labs, Inc.", "knows_my_work": True, "note": "Former colleague"}]}},
            "second_degree": [{"org": "initech", "status": "asked", "via": "Morgan Test"}]}
        net = N.build_network(rows, config(), dt.date(2026, 11, 1), previous, source="intake/sources/Connections.csv")
        self.assertEqual(net["total_connections"], 6)
        self.assertEqual(net["matched_connections"], 4)
        self.assertEqual(net["orgs"]["globex"]["count"], 2)
        self.assertEqual(net["orgs"]["acme"]["count"], 2)
        self.assertEqual(net["orgs"]["initech"]["count"], 0)
        jordan = next(c for c in net["orgs"]["globex"]["first_degree"] if c["name"] == "Jordan Sample")
        self.assertEqual(jordan["connected_on"], "2022-03-12")
        self.assertEqual(jordan["months_connected"], 55)
        self.assertTrue(jordan["knows_my_work"])
        self.assertEqual(jordan["note"], "Former colleague")
        casey = next(c for c in net["orgs"]["globex"]["first_degree"] if c["name"] == "Casey Demo")
        self.assertEqual(casey["connected_on"], "2024-03-01")
        pat = next(c for c in net["orgs"]["acme"]["first_degree"] if c["name"] == "Pat Nodate")
        self.assertIsNone(pat["months_connected"])
        self.assertEqual(net["second_degree"], previous["second_degree"])
        self.assertNotIn("@", json.dumps(net))  # email addresses are never copied
        self.assertEqual(V.check(net, H.schema("network.schema.json")), [])

    def test_main_writes_file_and_prints_counts_only(self):
        ws = H.new_workspace(self, config())
        with mock.patch("builtins.print") as printed:
            self.assertEqual(N.main(["--workspace", ws, "--csv", CSV, "--today", "2026-11-01"]), 0)
        out = " ".join(str(c) for c in printed.call_args_list)
        self.assertNotIn("Jordan", out)
        net = H.load(os.path.join(ws, "profile", "network.json"))
        self.assertEqual(net["orgs"]["globex"]["count"], 2)

    def test_rejects_other_csv(self):
        path = os.path.join(H.new_workspace(self), "other.csv")
        with open(path, "w") as fh:
            fh.write("a,b\n1,2\n")
        with self.assertRaises(SystemExit):
            N.read_connections(path)


if __name__ == "__main__":
    unittest.main()
