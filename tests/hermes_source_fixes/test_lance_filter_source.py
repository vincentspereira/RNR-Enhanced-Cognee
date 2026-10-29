"""Stdlib/source checks for the new structural Lance filter contract.

These assert translation only. Real LanceDB acceptance is in the separate
real-engine suite, not SQLite or a query-language fixture.
"""
import unittest
from src.db_adapters import _vector_filter as vf


class LanceFilterSourceTests(unittest.TestCase):
    def test_empty_filter_remains_no_op(self):
        self.assertEqual(vf.to_lance_where(vf.normalise(None)), "")

    def test_nonempty_filter_without_complete_scan_fails_closed(self):
        norm = vf._NormalisedFilter(must=(vf._EqualityCondition("agent_id", "fleet-test"),))
        with self.assertRaisesRegex(NotImplementedError, "complete ID/payload scan"):
            vf.to_lance_where(norm)

    def test_no_exact_identity_match_emits_false_not_match_all(self):
        norm = vf._NormalisedFilter(must=(vf._EqualityCondition("agent_id", "fleet-test"),))
        rows = [
            {"id": "nested", "payload": '{"nested":{"agent_id":"fleet-test"}}'},
            {"id": "prefix", "payload": '{"agent_id":"fleet-test-extra"}'},
            {"id": "bad", "payload": '{'},
        ]
        self.assertEqual(vf.to_lance_where(norm, rows), "false")

    def test_matching_id_is_sql_literal_not_payload_like(self):
        norm = vf._NormalisedFilter(must=(vf._EqualityCondition("agent_id", "fleet_%'"),))
        rows = [{"id": "id' OR true --", "payload": {"agent_id": "fleet_%'"}}]
        self.assertEqual(vf.to_lance_where(norm, rows), "id IN ('id'' OR true --')")


if __name__ == "__main__":
    unittest.main()
