"""No-launch checks for the maintained functional runner's failure semantics."""
import importlib.util
from pathlib import Path
import sys
import unittest

DEPLOY=Path(__file__).resolve().parents[2]/'integrations/hermes/deployment'
sys.path.insert(0,str(DEPLOY))
import functional_memory_test as functional

class FunctionalRunnerTests(unittest.TestCase):
    def test_failure_never_exits_zero(self):
        summary=functional.verdict([{'name':'invented','status':'ERR'}])
        self.assertFalse(summary['complete']);self.assertEqual(functional.exit_status(summary),1)
    def test_skip_never_claims_complete(self):
        summary=functional.verdict([{'name':'model','status':'SKIP'}])
        self.assertFalse(summary['complete']);self.assertEqual(functional.exit_status(summary),2)
    def test_clarification_is_not_successful_cleanup(self):
        responses=iter([(200,{'version':1}),(409,{'clarification_required':True})])
        self.assertFalse(functional.retract_owned(lambda *a:next(responses),'invented','owned-id'))
    def test_successful_retraction_needs_absence_readback(self):
        responses=iter([(200,{'version':1}),(200,{}),(200,{'id':'owned-id'})])
        self.assertFalse(functional.retract_owned(lambda *a:next(responses),'invented','owned-id'))
    def test_complete_retraction_positive_control(self):
        responses=iter([(200,{'version':1}),(200,{}),(404,{})])
        self.assertTrue(functional.retract_owned(lambda *a:next(responses),'invented','owned-id'))

if __name__=='__main__':unittest.main()
