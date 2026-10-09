"""The Pages payload must not reveal private archive locations."""
import unittest
from pathlib import Path

from replay_public_export import public_snapshot


class PublicReplayExportTests(unittest.TestCase):
    def test_absolute_archive_paths_are_not_exported_and_original_is_unchanged(self):
        root = Path('E:/HermesProject/macro')
        data = {'reports': [{'path': 'E:/HermesProject/macro/reports/a.pdf',
                             'sourcePath': 'D:/Private/research/b.pdf',
                             'sourcePaths': ['D:/Private/research/b.pdf', 'reports/c.pdf']}],
                'events': [{'auditPath': 'E:/HermesProject/macro/audit.json'}]}
        result = public_snapshot(data, root)
        self.assertEqual(result['reports'][0]['path'], 'reports/a.pdf')
        self.assertEqual(result['reports'][0]['sourcePath'], 'b.pdf')
        self.assertEqual(result['reports'][0]['sourcePaths'], ['b.pdf', 'reports/c.pdf'])
        self.assertEqual(result['events'][0]['auditPath'], 'audit.json')
        self.assertEqual(data['reports'][0]['sourcePath'], 'D:/Private/research/b.pdf')


if __name__ == '__main__':
    unittest.main()
