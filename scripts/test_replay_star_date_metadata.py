"""Test-only source metadata, without claiming real platform evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from replay_parent_sources import _original_star


class StarDateMetadataTests(unittest.TestCase):
    def test_filename_priority_keeps_platform_day_and_raw_literal_and_visible_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            stage = Path(temp)
            topic = 'https://wx.zsxq.com/group/TEST_ONLY/topic/TEST_ONLY'
            name = 'TEST_ONLY演讲260915_原文.pdf'
            (stage / 'topic.json').write_text(json.dumps({'topicURL': topic,
                'renderedBodyText': '#调研纪要\n' + name}), encoding='utf-8')
            record = {'filenameDate': '2026-09-15', 'publicationDate': None,
                      'postDate': '2026-09-16', 'postDateRaw': ' 2026-09-16 06:30 ',
                      'topicURL': topic, 'originalFilename': name,
                      'topicDOMEvidence': 'topic.json', 'versionType': 'original_audio_transcript_pdf'}
            parent = {'qualified': True, 'allPageHashPairsMatched': True}
            result = _original_star(record, parent, b'', stage, stage)
            self.assertEqual(result['date'], '2026-09-15')
            self.assertIsNone(result['publicationDate'])
            self.assertEqual(result.get('postDate'), '2026-09-16')
            self.assertEqual(result.get('postDateRaw'), ' 2026-09-16 06:30 ')
            self.assertIs(result.get('dateConflict'), True)


if __name__ == '__main__':
    unittest.main()
