"""Real local LanceDB engine regressions for the Enhanced Cognee adapter.

Synthetic vectors only (not embeddings or semantic-quality evidence). Storage
is isolated under Hermes scratch. Never substitute a SQL or mock engine here.
"""
import json
from types import SimpleNamespace as NS
import tempfile
import unittest
import warnings

from src.db_adapters.vector_lancedb import _LanceDBClient



def condition(key, value):
    return NS(key=key, match=NS(value=value))


def filtered(key, value):
    return NS(must=[condition(key, value)], should=None, must_not=None)


class RealLanceIdentityTests(unittest.TestCase):
    def setUp(self):
        import lancedb  # A missing real engine must fail, not silently pass.
        self.tmp = tempfile.TemporaryDirectory(prefix="enhanced-lance-filter-")
        self.addCleanup(self.tmp.cleanup)
        self.client = _LanceDBClient(self.tmp.name)
        self.client.create_collection("memories", NS(size=2, distance="Cosine"))
        self.table = self.client._connect().open_table("memories")

    def insert(self, rows):
        self.client.upsert("memories", [NS(id=ident, vector=vector, payload=payload)
                           for ident, vector, payload in rows])

    def test_search_returns_hit_fields_without_optional_pandas(self):
        self.insert([("point", [1.0, 0.0], {"agent_id": "fleet-test", "n": 7})])
        hits = self.client.search("memories", [1.0, 0.0], limit=1)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].id, "point")
        self.assertEqual(hits[0].payload, {"agent_id": "fleet-test", "n": 7})
        self.assertAlmostEqual(hits[0].score, 1.0)
        self.assertEqual(hits[0].version, 0)
        self.assertIsNone(hits[0].vector)

    def test_json_boolean_identity_does_not_match_numeric_identity(self):
        self.insert([
            ("boolean", [1.0, 0.0], {"agent_id": True}),
            ("number", [1.0, 0.0], {"agent_id": 1}),
            ("string", [1.0, 0.0], {"agent_id": "1"}),
        ])
        hits = self.client.search("memories", [1.0, 0.0],
                                  query_filter=filtered("agent_id", True))
        self.assertEqual({h.id for h in hits}, {"boolean"})
        self.client.delete("memories", NS(filter=filtered("agent_id", 1)))
        remaining = self.client._connect().open_table("memories").to_arrow().to_pylist()
        self.assertEqual({r["id"] for r in remaining}, {"boolean", "string"})

    def test_delete_identity_keeps_nested_and_wildcard_mismatches(self):
        self.insert([
            ("target", [1.0, 0.0], {"agent_id": "fleet_test%"}),
            ("other", [1.0, 0.0], {"agent_id": "fleetXtest-secret"}),
            ("nested", [1.0, 0.0], {"nested": {"agent_id": "fleet_test%"}}),
            ("prefix", [1.0, 0.0], {"agent_id": "fleet_test%-extra"}),
        ])
        self.table.add([{"id": "compact", "vector": [1.0, 0.0],
                         "payload": '{"agent_id":"fleet_test%"}'}])
        self.client.delete("memories", NS(filter=filtered("agent_id", "fleet_test%")))
        remaining = self.client._connect().open_table("memories").to_arrow().to_pylist()
        self.assertEqual({r["id"] for r in remaining}, {"other", "nested", "prefix"})

    def test_quotes_wildcards_backslashes_and_dotted_keys_remain_literal(self):
        cases = [
            ("agent_id", "o'brien"),
            ("agent_id", 'fleet-"quoted"'),
            ("agent_id", "fleet_%"),
            ("agent_id", "fleet\\path"),
            ("agent_id", "x' OR true --"),
            ('key\'"_%', 'value\'"_%\\tail'),
            ("nested.agent_id", "fleet-test"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.client._connect().open_table("memories").delete("true")
                self.insert([
                    ("target", [0.8, 0.2], {key: value}),
                    ("nested", [1.0, 0.0], {"nested": {key: value}}),
                    ("prefix", [1.0, 0.0], {key: value + "-extra"}),
                    ("suffix", [1.0, 0.0], {key: "extra-" + value}),
                    ("other", [1.0, 0.0], {key: "fleet-X-secret"}),
                ])
                table = self.client._connect().open_table("memories")
                # IDs with SQL metacharacters exercise the new ID prefilter;
                # direct engine insertion isolates legacy upsert-ID quoting.
                quoted_id = "id' OR true --"
                table.add([
                    {"id": quoted_id, "vector": [0.7, 0.3],
                     "payload": json.dumps({key: value}, separators=(",", ":"))},
                    {"id": "text", "vector": [1.0, 0.0],
                     "payload": json.dumps({"text": json.dumps({key: value})})},
                    {"id": "malformed", "vector": [1.0, 0.0], "payload": "not JSON"},
                    {"id": "array", "vector": [1.0, 0.0], "payload": json.dumps([{key: value}])},
                ])
                hits = self.client.search("memories", [1.0, 0.0], limit=1,
                                          query_filter=condition(key, value))
                self.assertEqual([h.id for h in hits], ["target"])
                hits = self.client.search("memories", [1.0, 0.0], limit=20,
                                          query_filter=filtered(key, value))
                self.assertEqual({h.id for h in hits}, {"target", quoted_id})
                self.client.delete("memories", NS(filter=filtered(key, value)))
                remaining = self.client._connect().open_table("memories").to_arrow().to_pylist()
                self.assertEqual({r["id"] for r in remaining},
                                 {"nested", "prefix", "suffix", "other", "text", "malformed", "array"})

    def test_no_match_is_empty_search_and_no_op_delete(self):
        self.insert([("other", [1.0, 0.0], {"agent_id": "fleet-other"})])
        self.assertEqual(self.client.search("memories", [1.0, 0.0],
                         query_filter=filtered("agent_id", "fleet-missing")), [])
        self.client.delete("memories", NS(filter=filtered("agent_id", "fleet-missing")))
        self.assertEqual(self.client.count("memories").count, 1)

    def test_compound_and_empty_delete_filters_fail_without_deleting(self):
        self.insert([("point", [1.0, 0.0], {"agent_id": "fleet-test"})])
        for filt in (
            NS(must=[condition("agent_id", "fleet-test"), condition("n", 1)], should=None, must_not=None),
            NS(must=[condition("agent_id", "fleet-test")], should=[condition("n", 1)], must_not=None),
            NS(must=[condition("agent_id", "fleet-test")], should=None, must_not=[condition("n", 1)]),
        ):
            with self.subTest(filt=filt):
                with self.assertRaises(NotImplementedError):
                    self.client.search("memories", [1.0, 0.0], query_filter=filt)
                with self.assertRaises(NotImplementedError):
                    self.client.delete("memories", NS(filter=filt))
                self.assertEqual(self.client.count("memories").count, 1)
        with self.assertRaises(NotImplementedError):
            self.client.delete("memories", NS(filter=NS(must=[], should=None, must_not=None)))
        self.assertEqual(self.client.count("memories").count, 1)

    def test_existing_crud_unfiltered_search_and_threshold_are_preserved(self):
        self.insert([
            ("a", [1.0, 0.0], {"agent_id": "fleet-test"}),
            ("b", [0.0, 1.0], {"agent_id": "fleet-other"}),
        ])
        self.assertEqual(self.client.count("memories").count, 2)
        # table_names() is unchanged baseline code deprecated in LanceDB 0.40.
        # Record (do not promote) its warning so strict pytest warning policy
        # cannot turn get_collections()'s broad except into a fake empty list.
        # All result assertions remain exact; this is not a CRUD source fix.
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always", DeprecationWarning)
            self.assertEqual([c.name for c in self.client.get_collections().collections], ["memories"])
            self.assertEqual(self.client.get_collection("memories").status, "green")
        hits = self.client.search("memories", [1.0, 0.0], score_threshold=0.5)
        self.assertEqual([h.id for h in hits], ["a"])
        self.insert([("a", [1.0, 0.0], {"agent_id": "fleet-updated"})])
        self.assertEqual(self.client.count("memories").count, 2)
        hits = self.client.search("memories", [1.0, 0.0],
                                  query_filter=filtered("agent_id", "fleet-updated"))
        self.assertEqual([h.id for h in hits], ["a"])
        self.client.close()
        hits = self.client.search("memories", [1.0, 0.0],
                                  query_filter=filtered("agent_id", "fleet-updated"))
        self.assertEqual([h.id for h in hits], ["a"])
        self.client.delete("memories", ["a"])
        self.assertEqual(self.client.count("memories").count, 1)
        self.client.delete("memories", NS(points=["b"]))
        self.assertEqual(self.client.count("memories").count, 0)

    def test_search_matches_writer_json_and_legacy_compact_json_before_limit(self):
        self.insert([(f"other-{i}", [1.0, 0.01], {"agent_id": "fleet-other"})
                     for i in range(12)] + [
                         ("spaced", [0.8, 0.2], {"agent_id": "fleet-test"}),
                     ])
        self.table.add([{
            "id": "compact", "vector": [0.7, 0.3],
            "payload": json.dumps({"agent_id": "fleet-test"}, separators=(",", ":")),
        }])
        # Prove that this actually exercises the adapter's existing writer.
        self.assertIn('"agent_id": "fleet-test"',
                      next(r["payload"] for r in self.table.to_arrow().to_pylist()
                           if r["id"] == "spaced"))
        hits = self.client.search("memories", [1.0, 0.0], limit=1,
                                  query_filter=filtered("agent_id", "fleet-test"))
        self.assertEqual([h.id for h in hits], ["spaced"])
        all_hits = self.client.search("memories", [1.0, 0.0], limit=10,
                                      query_filter=filtered("agent_id", "fleet-test"))
        self.assertEqual({h.id for h in all_hits}, {"spaced", "compact"})
        self.assertTrue(all(h.payload["agent_id"] == "fleet-test" for h in all_hits))


if __name__ == "__main__":
    unittest.main()
