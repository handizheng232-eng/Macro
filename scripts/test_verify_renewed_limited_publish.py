"""Public release-03 contract, including self-rehashed semantic mutations."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
from verify_renewed_limited_publish import verify, verify_assets
ROOT = Path(__file__).resolve().parents[1]

class LimitedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.raw = (ROOT/'src/data/historyReplayRenewedEasingQtEnd.json').read_bytes()
        self.data = json.loads(self.raw)
        self.receipt = json.loads((ROOT/'release/replay-renewed-easing-publication-03.json').read_bytes())

    def test_current_approved_limited_release(self):
        result = verify(self.data, self.raw, self.receipt)
        self.assertEqual(result['nodes'], 240)
        self.assertEqual(result['newResearchParagraphs'], 7)
        self.assertFalse(result['fullStageReady'])
        self.assertFalse(result['rawOriginalReadbackPerformed'])

    def test_all_seven_paragraphs_and_references_are_bound_independently(self):
        for section in self.data['marketAnalysis']['sections']:
            for entries in section['deepDive'].values():
                for node in entries:
                    if node['id'].startswith(('local02-WP', 'local03-')):
                        for field, replacement in [('text',node['text'][:-20]),('sourceIds',[]),('reportIds',[]),('evidenceRefs',[]),('historicalAsOfEligible',True)]:
                            changed=copy.deepcopy(self.data)
                            target=next(n for s in changed['marketAnalysis']['sections'] for ns in s['deepDive'].values() for n in ns if n['id']==node['id'])
                            target[field]=replacement
                            self.reject_rehashed(changed)

    def reject_rehashed(self, data, receipt=None):
        raw=json.dumps(data,ensure_ascii=False).encode()
        r=copy.deepcopy(receipt or self.receipt)
        r['datasetSHA256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):verify(data,raw,r)

    def test_quantity_exception_never_upgrades_reference_count_or_completeness(self):
        for mode in ('wind','references','complete','exception','cme','privacy','wind-text'):
            d=copy.deepcopy(self.data)
            if mode=='wind':d['monthlyCoverage']['rows'][3]['channels']['Wind']['bodyCount']=15
            if mode=='references':d['experimentStatus']['wechatAcceptedTotal']=27
            if mode=='complete':d['experimentStatus']['fullStageReady']=True
            if mode=='exception':d['monthlyCoverage']['rows'][3]['channels']['Wind']['quantityException']['qualityReviewWaived']=True
            if mode=='cme':
                n=next(n for s in d['marketAnalysis']['sections'] for ns in s['deepDive'].values() for n in ns if n['id']=='local02-cme-gap');n['text']='CME probability 99%'
            if mode=='privacy':d['privateLocalPath']='C:/Users/private/file.pdf'
            if mode=='wind-text':d['windIncrement'][0]['claims'][0]['renderedView']='shortened'
            self.reject_rehashed(d)

    def test_dist_must_match_exact_assets_not_just_allowed_extensions(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            dist=Path(directory)
            asset=b'public-test-fixture'
            (dist/'assets').mkdir()
            (dist/'assets/app.js').write_bytes(asset)
            (dist/'assets/app.css').write_bytes(asset)
            (dist/'index.html').write_text('<script src="/Macro/assets/app.js"></script><link href="/Macro/assets/app.css">',encoding='utf-8')
            receipt={'distAssetPins':{'assets/app.js':hashlib.sha256(asset).hexdigest(),'assets/app.css':hashlib.sha256(asset).hexdigest()}}
            verify_assets(dist,receipt)
            (dist/'assets/app.js').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_assets(dist,receipt)
            (dist/'assets/app.js').write_bytes(asset)
            (dist/'unreviewed.js').write_bytes(b'also public but not approved')
            with self.assertRaises(ValueError):verify_assets(dist,receipt)

    def test_authorization_and_exact_bytes_required(self):
        for field,value in [('publicationAuthorized',False),('pageQAComplete',False),('fullStageReady',True)]:
            r=copy.deepcopy(self.receipt);r[field]=value
            with self.assertRaises(ValueError):verify(self.data,self.raw,r)
        with self.assertRaises(ValueError):verify(self.data,self.raw+b'\n',self.receipt)

if __name__=='__main__':unittest.main()
