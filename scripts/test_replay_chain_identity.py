"""Test-only identity fixtures; no empirical research data."""
import unittest
from replay_research_integration import reviewed_projection


class ReplayChainIdentityTests(unittest.TestCase):
    def study(self, explicit):
        return {
            'asOf': '2026-10-09',
            'preserveExplicitChainIdentity': explicit,
            'marketAnalysis': {'title': 'TEST ONLY', 'conclusion': '', 'limitations': [], 'sections': []},
            'months': [], 'sources': [], 'sourceAliases': [], 'officialFacts': [], 'marketStatistics': {},
            'revisionChains': [{
                'id': 'test-official-vintage', 'label': 'TEST ONLY', 'description': 'TEST ONLY',
                'opinionIds': [], 'identityStatus': '官方统计版本修订',
                'limitation': '不是同机构预测修订，也不是机构预测误差。',
            }],
        }

    def test_explicit_identity_does_not_mislabel_official_or_different_author_chains(self):
        result = reviewed_projection(self.study(True), {'opinions': []})['revisionChains'][0]
        self.assertEqual(result['identityStatus'], '官方统计版本修订')
        self.assertEqual(result['limitation'], '不是同机构预测修订，也不是机构预测误差。')

    def test_legacy_projection_remains_byte_semantically_compatible_without_opt_in(self):
        result = reviewed_projection(self.study(False), {'opinions': []})['revisionChains'][0]
        self.assertEqual(result['identityStatus'], 'same_attributed_formal_institution')
        self.assertIn('同机构修订链', result['limitation'])


if __name__ == '__main__':
    unittest.main()
