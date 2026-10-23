"""UI-only release must never weaken the immutable research contract."""
import copy
import json
import unittest
from unittest.mock import patch
from pathlib import Path
from verify_replay_reading_publish import verify_reading, ROOT
from verify_economic_mechanisms_publish import baseline_root


class ReadingPublicationTests(unittest.TestCase):
    def setUp(self):
        # All original assertions run on the exact immutable release-04 fixture.
        self.root = self.enterContext(baseline_root(ROOT))
        self.receipt = json.loads((ROOT / 'release/replay-reading-publication-04.json').read_bytes())

    def test_current_release_and_reusable_template(self):
        result = verify_reading(self.receipt, root=self.root)
        self.assertEqual(result['newResearchParagraphs'], 7)
        self.assertFalse(result['fullStageReady'])
        self.assertTrue(result['researchReceiptUnchanged'])
        template = (ROOT / 'docs/macro-replay-reading-template.md').read_text(encoding='utf-8')
        for text in ['阶段总结', '观点 / 事前预期', '现实', '机制', '分歧 / 预期差', '市场含义',
                     '实例 / 原文与数据', '验证条件', '三级', '不自动改写', '严格历史', 'Wind数量例外']:
            self.assertIn(text, template)
        self.assertIn('macro-replay-reading-template.md', (ROOT / 'docs/macro-replay-template.md').read_text(encoding='utf-8'))

    def test_fail_closed_authorization_scope_receipt_and_pin_coverage(self):
        for field, value in [('schemaVersion', 'wrong'), ('publicationAuthorized', False),
                             ('pageQAComplete', False), ('scope', 'all-stages'), ('pinEncoding', 'ignore-all-whitespace'),
                             ('researchReceiptSHA256', '0' * 64)]:
            changed = copy.deepcopy(self.receipt)
            changed[field] = value
            with self.assertRaises(ValueError):
                verify_reading(changed, root=self.root)
        for name in list(self.receipt['publicFilePins']):
            changed = copy.deepcopy(self.receipt)
            del changed['publicFilePins'][name]
            with self.assertRaises(ValueError):
                verify_reading(changed, root=self.root)

    def test_changed_ui_data_or_template_rejected(self):
        for name in self.receipt['publicFilePins']:
            changed = copy.deepcopy(self.receipt)
            changed['publicFilePins'][name] = '0' * 64
            with self.assertRaises(ValueError):
                verify_reading(changed, root=self.root)

    def test_original_research_receipt_is_read_not_replaced(self):
        original = Path.read_bytes
        def changed_read(path):
            raw = original(path)
            return raw + b'\n' if path.name == 'replay-renewed-easing-publication-03.json' else raw
        with patch.object(Path, 'read_bytes', changed_read):
            with self.assertRaises(ValueError):
                verify_reading(self.receipt, root=self.root)


if __name__ == '__main__':
    unittest.main()
